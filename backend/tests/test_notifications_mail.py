import smtplib
from unittest.mock import patch

import pytest
from django.core import mail

from apps.core.alertes import REGLES
from apps.core.mails_institutionnels import MODELES, composer_mail, exemple_mail, lien_application
from apps.core.models import Alerte, NotificationMail, RegleAlerte
from apps.core.notifications import notifier_nouvelles_alertes

from .test_api import client_pour, utilisateur

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin():
    return client_pour(utilisateur("admin-mails", "dnsi_admin"))


@pytest.fixture
def alerte():
    r = RegleAlerte.objects.get(code="depense_arbitrage_ministre")
    r.seuils |= {"destinataires": ["test@example.org"]}
    r.save()
    return Alerte.objects.create(
        regle=r, domaine=r.domaine, severite=r.severite, titre="Dossier de test", message="Test"
    )


def test_test_mail_trace_et_conf_sans_secret(admin, settings):
    settings.EMAIL_HOST_PASSWORD = "secret-ne-jamais-exposer"
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    r = admin.post("/api/v1/admin/notifications/tester/", {"destinataire": "test@example.org"})
    assert r.status_code == 200 and r.data["statut"] == "envoye"
    assert mail.outbox[-1].to == ["test@example.org"]
    assert NotificationMail.objects.get().utilisateur.username == "admin-mails"
    assert not Alerte.objects.exists()
    c = admin.get("/api/v1/admin/notifications/configuration/")
    assert c.status_code == 200
    assert "secret-ne-jamais-exposer" not in str(c.data)
    assert "EMAIL_HOST_PASSWORD" not in str(c.data)
    h = admin.get("/api/v1/admin/notifications/?statut=envoye&limit=1&offset=0")
    assert h.data["count"] == 1 and h.data["results"][0]["type"] == "test"
    assert admin.get("/api/v1/admin/notifications/?statut=echec").data["count"] == 0


def test_adresse_invalide_pas_denvoi(admin):
    with patch("apps.core.notifications.transmettre_mail") as envoi:
        r = admin.post("/api/v1/admin/notifications/tester/", {"destinataire": "invalide"})
    assert r.status_code == 400 and not envoi.called
    assert not NotificationMail.objects.exists()


@pytest.mark.parametrize("role,otp", [("lecteur", True), ("dnsi_admin", False)])
def test_permissions_notifications(role, otp):
    c = client_pour(utilisateur("mail-permissions", role), otp=otp)
    assert c.get("/api/v1/admin/notifications/").status_code == 403
    assert c.get("/api/v1/admin/notifications/configuration/").status_code == 403
    with patch("apps.core.notifications.transmettre_mail") as envoi:
        assert c.post("/api/v1/admin/notifications/tester/", {"destinataire": "test@example.org"}).status_code == 403
    assert not envoi.called


def test_echec_smtp_repris_et_erreur_sans_secret(alerte, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    with patch("apps.core.notifications.transmettre_mail", side_effect=smtplib.SMTPAuthenticationError(535, b"secret")):
        assert notifier_nouvelles_alertes() == 0
    alerte.refresh_from_db()
    assert alerte.notifiee_le is None
    trace = NotificationMail.objects.get()
    assert trace.statut == "echec" and "secret" not in trace.erreur
    with patch("apps.core.notifications.transmettre_mail", return_value=1):
        assert notifier_nouvelles_alertes() == 1
        assert notifier_nouvelles_alertes() == 0
    alerte.refresh_from_db()
    assert alerte.notifiee_le is not None
    assert NotificationMail.objects.filter(statut="envoye").count() == 1


def test_simulation_ne_marque_pas_notifiee(alerte, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    assert notifier_nouvelles_alertes() == 0
    alerte.refresh_from_db()
    assert alerte.notifiee_le is None
    assert NotificationMail.objects.get().statut == "simulation"


def test_rendu_chargement_reel_et_marqueur_demo(alerte, charge):
    alerte.chargement = charge
    charge.detail = {**(charge.detail or {}), "demo": False}
    reel = composer_mail(categorie="alerte", regle=alerte.regle, alertes=[alerte])
    assert "Données d’illustration — source non raccordée" not in reel.texte
    charge.detail["demo"] = True
    demo = composer_mail(categorie="alerte", regle=alerte.regle, alertes=[alerte])
    assert "Données d’illustration — source non raccordée" in demo.texte


def test_zero_message_accepte_est_echec(admin, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    with patch("apps.core.notifications.transmettre_mail", return_value=0):
        r = admin.post("/api/v1/admin/notifications/tester/", {"destinataire": "test@example.org"})
    assert r.data["statut"] == "echec"


@pytest.mark.parametrize("modele", ["test", *MODELES])
@pytest.mark.parametrize("categorie", ["alerte", "relance"])
def test_rendu_de_tous_les_modeles(modele, categorie):
    mail = exemple_mail(modele, categorie)
    assert "Ministère de l’Économie, des Finances et du Budget" in mail.texte
    assert "Madame, Monsieur" in mail.texte
    assert "Référence : MEFB-" in mail.texte
    assert '<html lang="fr">' in mail.html
    assert "{{" not in mail.html and "{%" not in mail.html
    if modele != "test":
        assert mail.sujet.startswith("[TEST] [MEFB — Tableau de bord]")
        assert "Données fictives" in mail.texte
        assert MODELES[modele][1] in mail.texte
        if categorie == "relance":
            assert "aucune clôture n’est enregistrée" in mail.texte
            assert "Notification initiale :" in mail.texte
    assert not NotificationMail.objects.exists()
    assert not Alerte.objects.exists()


def test_catalogue_couvre_toutes_les_regles():
    assert set(MODELES) == {r[0] for r in REGLES}


def test_notification_principale_centree_sur_retard():
    from apps.core.mails_institutionnels import MODELE_PRINCIPAL, catalogue_modeles

    assert catalogue_modeles()[0]["code"] == MODELE_PRINCIPAL
    message = exemple_mail(MODELE_PRINCIPAL)
    assert "Retard de traitement — Dossiers en attente" in message.sujet
    assert "Arbitrage requis" not in message.sujet
    assert "Seuil de signalement du retard : 15 jours" in message.texte
    assert "Durée d’attente constatée : 20 jours" in message.texte
    assert "Étape en attente : Visa" in message.texte
    assert "En attente depuis le :" in message.texte
    assert "Si nécessaire, soumettre le dossier à arbitrage" in message.texte


def test_html_echappe_contenu_et_texte_preserve_caracteres(alerte):
    alerte.titre = '<script>alert("x")</script>'
    alerte.message = "Budget A & B < 10"
    alerte.lien = "//exemple.org"
    mail = composer_mail(categorie="alerte", regle=alerte.regle, alertes=[alerte])
    assert "<script>" not in mail.html
    assert "&lt;script&gt;" in mail.html
    assert "Budget A & B < 10" in mail.texte
    assert 'href="//exemple.org"' not in mail.html


def test_apercu_sans_envoi_et_envoi_modele_isole(admin, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    params = {"modele": "paie_doublons", "categorie": "relance"}
    with patch("apps.core.notifications.transmettre_mail") as envoyer:
        a = admin.get("/api/v1/admin/notifications/apercu/", params)
    assert a.status_code == 200 and not envoyer.called
    assert "data:image/png;base64," in a.data["html"]
    assert not NotificationMail.objects.exists()
    r = admin.post("/api/v1/admin/notifications/tester/", {**params, "destinataire": "test@example.org"})
    assert r.status_code == 200 and r.data["type"] == "test"
    message = mail.outbox[-1]
    assert message.subject.startswith("[TEST]") and "Relance" in message.subject
    assert message.to == ["test@example.org"]
    assert r.data["reference"] in message.body
    assert r.data["modele"] == "paie_doublons"
    assert any(a.mimetype == "text/html" for a in message.alternatives)
    assert any(a.get("Content-ID") == "<armoiries-mefb>" for a in message.attachments)
    assert not Alerte.objects.exists()


def test_modele_inconnu_refuse(admin):
    assert admin.get("/api/v1/admin/notifications/apercu/?modele=inconnu").status_code == 400
    assert (
        admin.post(
            "/api/v1/admin/notifications/tester/",
            {
                "modele": "inconnu",
                "destinataire": "test@example.org",
            },
        ).status_code
        == 400
    )
    assert not NotificationMail.objects.exists()


@pytest.mark.parametrize(
    "base,route",
    [
        ("javascript:alert(1)", "/depenses"),
        ("https://tableau.example.org", "//externe.example.org"),
        ("https://tableau.example.org", "/\\externe.example.org"),
    ],
)
def test_liens_non_http_ou_routes_externes_ecartes(settings, base, route):
    settings.TDB_URL_PUBLIQUE = base
    assert lien_application(route) == ""
