"""Catalogue éditorial et rendu commun des notifications institutionnelles (HTML et texte)."""

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.dateparse import parse_date

from .models import Alerte

ARMOIRIES = Path(__file__).parent / "assets" / "armoiries.png"
PREFIXE = "[MEFB — Tableau de bord]"
MODELE_PRINCIPAL = "depense_arbitrage_ministre"

# Objet, suite recommandée, constat d'illustration. Les données d'exemple ne sont jamais enregistrées.
MODELES = {
    "depense_sous_execution": (
        "Exécution budgétaire — Points d’attention",
        "Examiner avec les services financiers concernés les facteurs de sous-exécution et les mesures envisageables.",
        "Deux ministères fictifs présentent un taux d’engagement inférieur à 50 %. "
        "Crédits non engagés : 25 milliards GNF.",
    ),
    "depense_projection_faible": (
        "Exécution budgétaire — Projection de fin d’exercice",
        "Examiner avec la direction du budget les hypothèses de projection et les ajustements envisageables.",
        "Au rythme observé, le taux d’engagement projeté se situe entre 65 % et 72 %. "
        "Cette estimation reste indicative.",
    ),
    "investissement_faible": (
        "Investissements — Situation des engagements",
        "Examiner avec les ministères porteurs le calendrier des engagements et de passation des marchés.",
        "Trois projets fictifs de plus de 1 milliard GNF ne présentent aucun engagement à la date de situation.",
    ),
    "depense_paiements_retard": (
        "Paiements — Délais nécessitant un examen",
        "Examiner avec le Trésor les facteurs de retard et leur prise en compte dans le plan de trésorerie.",
        "Pour deux ministères fictifs, le paiement représente moins de 35 % de l’ordonnancement ajusté.",
    ),
    "depense_lignes_depassement": (
        "Crédits budgétaires — Dépassements constatés",
        "Faire vérifier les lignes concernées et examiner, le cas échéant, "
        "les modalités de régularisation appropriées.",
        "Quatre lignes budgétaires fictives présentent des crédits disponibles négatifs.",
    ),
    "depense_hors_chaine": (
        "Paiements hors chaîne — Rapprochement à effectuer",
        "Rapprocher les montants concernés avec les écritures du Trésor afin de confirmer leur traitement.",
        "Des opérations fictives de solde et de débit d’office, exclues du paiement ajusté, "
        "nécessitent un rapprochement.",
    ),
    "depense_restes_anciens": (
        "Restes à payer — Ancienneté à examiner",
        "Examiner l’ancienneté des restes à payer et les priorités d’apurement, après vérification des dossiers.",
        "Des ordonnancements fictifs de plus de six mois restent à payer pour 8 milliards GNF.",
    ),
    "depense_arbitrage_ministre": (
        "Retard de traitement — Dossiers en attente",
        "Solliciter les services concernés pour préciser les motifs du retard, les suites à donner "
        "et le calendrier de traitement. Si nécessaire, soumettre le dossier à arbitrage. "
        "Renseigner les suites données dans le tableau de bord.",
        "Dossier n° DEMO-001 en attente de visa depuis 20 jours. "
        "Acteur : service de contrôle fictif. Montant : 12 milliards GNF.",
    ),
    "tresorerie_sous_seuil": (
        "Trésorerie — Seuil de couverture franchi",
        "Examiner avec le Trésor les prévisions de ressources et les priorités de décaissement.",
        "Le solde fictif couvre 18 jours de décaissements, pour un seuil de référence d’un mois.",
    ),
    "impots_sous_objectif": (
        "Recettes fiscales — Écart aux objectifs",
        "Examiner avec les services fiscaux les écarts constatés et les mesures de recouvrement envisageables.",
        "Deux catégories fiscales fictives présentent un taux de réalisation inférieur à 80 % de l’objectif.",
    ),
    "douanes_exonerations": (
        "Douanes — Situation des exonérations",
        "Examiner avec les services douaniers les régimes concernés et l’incidence des exonérations constatées.",
        "Les exonérations fictives représentent 15 % des recettes douanières, soit 6 milliards GNF.",
    ),
    "paie_doublons": (
        "Masse salariale — Doublons à vérifier",
        "Faire vérifier les cas signalés par les services compétents avant toute décision concernant les paiements.",
        "Trois cas potentiels de doublons fictifs sont signalés pour un examen par les services compétents.",
    ),
    "patrimoine_non_inventories": (
        "Patrimoine — Inventaires à actualiser",
        "Examiner avec les services du patrimoine la programmation de l’inventaire des biens concernés.",
        "Douze biens fictifs n’ont pas fait l’objet d’un inventaire depuis plus de deux ans.",
    ),
    "portefeuille_dividendes": (
        "Portefeuille de l’État — Dividendes en attente",
        "Vérifier les échéances et les versements avec les services chargés du portefeuille de l’État.",
        "Deux sociétés fictives présentent des dividendes votés non enregistrés comme versés, pour 4 milliards GNF.",
    ),
    "portefeuille_organismes": (
        "Portefeuille de l’État — Situation financière à examiner",
        "Examiner la situation des organismes concernés et solliciter, le cas échéant, les états financiers manquants.",
        "Deux organismes fictifs présentent un déficit ; un troisième n’a pas transmis ses états financiers.",
    ),
    "marches_entente_directe": (
        "Marchés publics — Recours à l’entente directe",
        "Examiner avec les services des marchés publics les justifications "
        "et le cadre applicable aux procédures concernées.",
        "Sur un jeu fictif, l’entente directe représente 30 % des marchés, au-delà du seuil de référence de 20 %.",
    ),
    "marches_coherence": (
        "Marchés publics — Écarts à vérifier",
        "Faire vérifier les écarts de rapprochement par les services des marchés publics et du contrôle financier.",
        "Le rapprochement fictif signale un marché sans réservation et un paiement sans marché immatriculé.",
    ),
}


@dataclass
class Courriel:
    sujet: str
    texte: str
    html: str
    reference: str


def lien_application(route=""):
    base = settings.TDB_URL_PUBLIQUE.rstrip("/")
    try:
        url = urlsplit(base)
    except ValueError:
        return ""
    if url.scheme not in {"http", "https"} or not url.netloc or "\\" in base:
        return ""
    if route and (not route.startswith("/") or route.startswith("//") or "\\" in route):
        return ""
    return base + route


def composer_mail(*, categorie="test", regle=None, alertes=(), maintenant=None, exemple=False):
    maintenant = maintenant or timezone.now()
    code = regle.code if regle else ""
    meta = MODELES.get(code)
    titre = meta[0] if meta else "Points d’attention — Situation à examiner"
    reference = f"MEFB-{maintenant:%Y%m%d}-{uuid4().hex[:8].upper()}"
    introduction = (
        "Le tableau de bord des finances publiques porte à votre attention les éléments ci-dessous pour examen."
    )
    if code == MODELE_PRINCIPAL:
        introduction = (
            "Le tableau de bord des finances publiques signale un retard de traitement pour les dossiers ci-dessous, "
            "dont la durée d’attente dépasse le seuil de signalement paramétré. "
            "Cette notification vise à faciliter leur suivi et la coordination avec les services concernés."
        )
    if categorie == "relance":
        introduction = (
            "À la date de cette relance, aucune clôture n’est enregistrée dans l’application "
            "pour les éléments ci-dessous. "
            "Nous vous invitons à examiner leur situation et à renseigner les suites données dans le tableau de bord."
        )
    if categorie == "test":
        titre = "Vérification du service de notification"
        introduction = (
            "Ce message a été envoyé à votre adresse à la demande d’un administrateur afin de vérifier "
            "le fonctionnement du service de notification du tableau de bord des finances publiques. "
            "Aucune action métier n’est requise."
        )
    sujet = f"{PREFIXE} {'Relance — ' if categorie == 'relance' else ''}{titre}"
    if exemple:
        sujet = f"[TEST] {sujet}"
    elements = []
    for a in alertes:
        donnees = a.donnees or {}
        libelle = "Cas de doublons de paie à vérifier" if code == "paie_doublons" else a.titre
        if code == MODELE_PRINCIPAL:
            libelle = a.titre.removeprefix("Arbitrage : ")
        constat = a.message
        if code == "paie_doublons":
            constat = "Signalement automatique à confirmer après vérification : " + constat.replace(
                "agents en doublon", "cas potentiels de doublons"
            )
        elements.append(
            {
                "reference": f"Alerte n° {a.pk}" if a.pk else "Exemple fictif — DEMO-001",
                "titre": libelle,
                "constat": constat,
                "date_situation": a.date_situation,
                "severite": a.get_severite_display(),
                "source": (
                    "Jeu fictif de démonstration"
                    if exemple
                    else (a.source.application if a.source_id else "Non renseignée")
                ),
                "illustration": bool(a.chargement_id and (a.chargement.detail or {}).get("demo")),
                "numero": donnees.get("numero"),
                "etape": donnees.get("etape"),
                "acteur": donnees.get("acteur"),
                "jours": donnees.get("jours"),
                "depuis": parse_date(str(donnees.get("depuis", ""))),
                "notification_initiale": a.notifiee_le if categorie == "relance" else None,
                "lien": lien_application(a.lien) if a.lien else "",
            }
        )
    contexte = {
        "titre": titre,
        "introduction": introduction,
        "reference": reference,
        "date_envoi": timezone.localtime(maintenant),
        "elements": elements,
        "categorie": categorie,
        "exemple": exemple,
        "retard_dossier": code == MODELE_PRINCIPAL,
        "seuil_retard": (regle.seuils or {}).get("delai_jours", 15) if code == MODELE_PRINCIPAL else None,
        "action": (
            (
                meta[1]
                if meta
                else "Examiner les éléments signalés et renseigner les suites données dans le tableau de bord."
            )
            if categorie != "test"
            else ""
        ),
        "delai": (regle.seuils or {}).get("relance_heures", 48) if regle and categorie == "relance" else None,
        "lien": lien_application(regle.lien if regle and regle.lien else ""),
        "bouton": (
            "Consulter les dossiers" if code == "depense_arbitrage_ministre" else "Consulter dans le tableau de bord"
        ),
        "armoiries": ARMOIRIES.exists(),
    }
    return Courriel(
        sujet,
        render_to_string("mails/notification.txt", contexte),
        render_to_string("mails/notification.html", contexte),
        reference,
    )


def catalogue_modeles():
    return [
        {"code": code, "titre": MODELES[code][0]} for code in sorted(MODELES, key=lambda c: c != MODELE_PRINCIPAL)
    ] + [{"code": "test", "titre": "Vérification du service de notification"}]


def exemple_mail(modele="test", categorie="alerte", maintenant=None):
    """Rendu d'exemple isolé : pas de lecture de dossiers réels ni de création d'alerte."""
    from .alertes import REGLES
    from .models import RegleAlerte

    maintenant = maintenant or timezone.now()
    if modele == "test":
        return composer_mail(maintenant=maintenant)
    definition = next(r for r in REGLES if r[0] == modele)
    regle = RegleAlerte(code=modele, severite=definition[2], seuils={"relance_heures": 48}, lien=definition[8])
    a = Alerte(
        titre=MODELES[modele][0],
        message=MODELES[modele][2],
        severite=regle.severite,
        date_situation=timezone.localdate(maintenant),
        lien=regle.lien,
        notifiee_le=maintenant - timedelta(hours=49),
    )
    if modele == MODELE_PRINCIPAL:
        a.donnees = {
            "numero": "DEMO-001",
            "etape": "Visa",
            "acteur": "Service de contrôle fictif",
            "jours": 20,
            "depuis": (maintenant - timedelta(days=20)).date().isoformat(),
        }
    return composer_mail(categorie=categorie, regle=regle, alertes=[a], maintenant=maintenant, exemple=True)
