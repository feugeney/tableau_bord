"""Notification des alertes par courriel, puis relance si personne n'a statué.

Les destinataires sont lus dans les seuils de la règle d'alerte (Administration → Règles d'alerte) :
- « destinataires » : reçoivent chaque nouvelle alerte de la règle (ex. la Ministre et sa conseillère) ;
- « destinataires_relance » : sollicités si l'alerte n'est pas traitée au bout de « relance_heures »
  (48 h par défaut).
Une entrée est un identifiant de compte (son adresse est alors celle du compte) ou une adresse.
"""

from __future__ import annotations

import logging
import smtplib
from collections.abc import Iterable
from datetime import datetime, timedelta
from email.mime.image import MIMEImage
from typing import Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from .mails_institutionnels import ARMOIRIES, MODELE_PRINCIPAL, composer_mail
from .models import Alerte, NotificationMail, RegleAlerte, StatutAlerte, Utilisateur

logger = logging.getLogger(__name__)


def adresses(entrees: Iterable[str]) -> list[str]:
    """Identifiants de comptes actifs ou adresses → adresses (sans doublon, ordre conservé)."""
    sortie: list[str] = []
    for e in entrees or []:
        e = str(e).strip()
        if not e:
            continue
        if "@" in e:
            adresse = e
        else:
            adresse = (
                Utilisateur.objects.filter(username=e, is_active=True).values_list("email", flat=True).first() or ""
            )
            if not adresse:
                logger.warning("Destinataire « %s » sans adresse de courriel : ignoré", e)
                continue
        if adresse not in sortie:
            sortie.append(adresse)
    return sortie


def transmettre_mail(sujet, corps, destinataires, html=""):
    message = EmailMultiAlternatives(sujet, corps, settings.DEFAULT_FROM_EMAIL, destinataires)
    if html:
        message.attach_alternative(html, "text/html")
        if ARMOIRIES.exists():
            message.mixed_subtype = "related"
            image = MIMEImage(ARMOIRIES.read_bytes(), _subtype="png")
            image.add_header("Content-ID", "<armoiries-mefb>")
            image.add_header("Content-Disposition", "inline", filename="armoiries.png")
            message.attach(image)
    return message.send(fail_silently=False)


def envoyer_mail(
    sujet,
    corps,
    destinataires,
    *,
    html="",
    type="test",
    regle=None,
    alertes_ids=None,
    utilisateur=None,
    reference="",
    modele="",
):
    """Trace chaque tentative ; une acceptation SMTP ne garantit pas la réception en boîte."""
    trace = NotificationMail.objects.create(
        sujet=sujet,
        destinataires=destinataires,
        type=type,
        regle=regle,
        alertes_ids=alertes_ids or [],
        utilisateur=utilisateur,
        reference=reference,
        modele=modele,
    )
    try:
        nombre = transmettre_mail(sujet, corps, destinataires, html)
        simulation = settings.EMAIL_BACKEND in {
            "django.core.mail.backends.console.EmailBackend",
            "django.core.mail.backends.filebased.EmailBackend",
            "django.core.mail.backends.dummy.EmailBackend",
        }
        if simulation:
            trace.statut = NotificationMail.Statut.SIMULATION
        elif nombre == 1:
            trace.statut = NotificationMail.Statut.ENVOYE
        else:
            trace.statut = NotificationMail.Statut.ECHEC
            trace.erreur = "Aucun message accepté par la messagerie."
    except Exception as exc:
        trace.statut = NotificationMail.Statut.ECHEC
        # Ne jamais exposer les réponses brutes du serveur ni les identifiants SMTP.
        if isinstance(exc, smtplib.SMTPAuthenticationError):
            trace.erreur = "Authentification SMTP refusée. Vérifier le compte et le mot de passe d’application."
        elif isinstance(exc, smtplib.SMTPRecipientsRefused):
            trace.erreur = "Adresse destinataire refusée par le serveur SMTP."
        elif isinstance(exc, smtplib.SMTPSenderRefused):
            trace.erreur = "Adresse expéditrice refusée par le serveur SMTP."
        elif isinstance(exc, (TimeoutError, OSError)):
            trace.erreur = "Connexion SMTP impossible ou délai dépassé. Vérifier le réseau, le port et TLS."
        else:
            trace.erreur = "Échec de l’envoi. Vérifier la configuration de la messagerie."
        logger.warning("Notification mail %s en échec (%s)", trace.pk, exc.__class__.__name__)
    trace.termine_le = timezone.now()
    trace.save(update_fields=["statut", "erreur", "termine_le"])
    return trace


def _envoyer(courriel, destinataires: list[str], **contexte) -> bool:
    if not destinataires:
        return False
    return (
        envoyer_mail(
            courriel.sujet,
            courriel.texte,
            destinataires,
            html=courriel.html,
            reference=courriel.reference,
            modele=contexte["regle"].code,
            **contexte,
        ).statut
        == NotificationMail.Statut.ENVOYE
    )


def _regles_notifiees(cle: str) -> Iterable[RegleAlerte]:
    for regle in sorted(RegleAlerte.objects.filter(actif=True), key=lambda r: r.code != MODELE_PRINCIPAL):
        if (regle.seuils or {}).get(cle):
            yield regle


def notifier_nouvelles_alertes(maintenant: Optional[datetime] = None) -> int:
    """Un courriel par règle pour les alertes jamais notifiées ; renvoie le nombre d'alertes notifiées."""
    maintenant = maintenant or timezone.now()
    total = 0
    for regle in _regles_notifiees("destinataires"):
        alertes = list(
            Alerte.objects.filter(regle=regle, notifiee_le=None).exclude(statut=StatutAlerte.TRAITEE).order_by("id")
        )
        if not alertes:
            continue
        destinataires = adresses(regle.seuils["destinataires"])
        courriel = composer_mail(categorie="alerte", regle=regle, alertes=alertes, maintenant=maintenant)
        if _envoyer(
            courriel,
            destinataires,
            type="alerte",
            regle=regle,
            alertes_ids=[a.pk for a in alertes],
        ):
            Alerte.objects.filter(pk__in=[a.pk for a in alertes]).update(notifiee_le=maintenant)
            total += len(alertes)
    return total


def relancer_alertes(maintenant: Optional[datetime] = None) -> int:
    """Relance les destinataires de relance pour les alertes notifiées et non traitées après le délai."""
    maintenant = maintenant or timezone.now()
    total = 0
    for regle in _regles_notifiees("destinataires_relance"):
        delai = timedelta(hours=float(regle.seuils.get("relance_heures", 48)))
        alertes = list(
            Alerte.objects.filter(regle=regle, relancee_le=None, notifiee_le__lte=maintenant - delai)
            .exclude(statut=StatutAlerte.TRAITEE)
            .order_by("id")
        )
        if not alertes:
            continue
        courriel = composer_mail(categorie="relance", regle=regle, alertes=alertes, maintenant=maintenant)
        if _envoyer(
            courriel,
            adresses(regle.seuils["destinataires_relance"]),
            type="relance",
            regle=regle,
            alertes_ids=[a.pk for a in alertes],
        ):
            Alerte.objects.filter(pk__in=[a.pk for a in alertes]).update(relancee_le=maintenant)
            total += len(alertes)
    return total
