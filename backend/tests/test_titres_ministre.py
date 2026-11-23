"""Note à Madame la Ministre : vue par titre, fiche d'un titre, arbitrages notifiés par courriel."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core import mail
from django.utils import timezone

from apps.core import regles
from apps.core.alertes import evaluer_alertes
from apps.core.models import Alerte, RegleAlerte
from apps.core.notifications import adresses, relancer_alertes
from apps.depense.models import FaitEngagement
from apps.depense.titres import dossiers_en_attente_visa, titre_detail, titres

from .test_api import client_pour, utilisateur

pytestmark = pytest.mark.django_db
MD = 10**9


# ------------------------------------------------------------------ règles


def test_temps_ecoule_et_voyants():
    assert regles.temps_ecoule_exercice(2026, date(2026, 12, 31)) == 1
    assert regles.temps_ecoule_exercice(2025, date(2026, 1, 20)) == 1  # période complémentaire
    assert regles.temps_ecoule_exercice(2026, date(2025, 12, 31)) == 0
    t = regles.temps_ecoule_exercice(2026, date(2026, 11, 18))
    assert round(t, 2) == Decimal("0.88")
    # Valeurs de la maquette au 18 novembre : T2 vert, T3 et T4 jaunes, T5 rouge.
    assert regles.voyant_titre(Decimal("0.815"), t) == "bon"
    assert regles.voyant_titre(Decimal("0.609"), t) == "vigilance"
    assert regles.voyant_titre(Decimal("0.464"), t) == "vigilance"
    assert regles.voyant_titre(Decimal("0.187"), t) == "critique"
    assert regles.voyant_titre(None, t) is None
    assert regles.voyant_titre(Decimal("0.5"), 0) is None
    assert regles.voyant_paiement(Decimal("0.33")) == "critique"
    assert regles.voyant_paiement(Decimal("0.6")) == "vigilance"
    assert regles.voyant_paiement(Decimal("0.9")) == "bon"
    assert regles.titres_paiement_non_suivi({"titres_paiement_non_suivi": "1, 2"}) == {"1", "2"}


# ------------------------------------------------------------------ vue 1


def test_vue_titres_payé_de_la_chaine_et_dette_non_suivie(filtres):
    v = titres(filtres)
    assert v["temps_ecoule"] == 1  # exercice 2025, situation de 2026
    par_titre = {t["titre"]: t for t in v["titres"]}
    t1, t5 = par_titre["1"], par_titre["5"]
    assert t1["libelle_titre"] == "T1 · Dette"
    assert t1["paiement_suivi"] is False and t1["taux_paiement"] is None and t1["voyant"] is None
    assert t5["paiement_suivi"] is True
    assert t5["taux_paiement"] == regles.taux(1 * MD, 30 * MD)  # payé brut de la chaîne / crédits
    assert t5["voyant"] == "critique"  # 10 % engagé sur un exercice écoulé
    # Le titre 2 garde le payé brut de la chaîne (salaires inclus, payés 5 Md sur 45 Md de crédits).
    assert par_titre["2"]["taux_paiement"] == regles.taux(5 * MD, 45 * MD)


# ------------------------------------------------------------------ vue 2


def test_fiche_titre_investissement(filtres):
    d = titre_detail(filtres, "5")
    assert [e["code"] for e in d["chaine"]] == ["credits", "engage", "liquide", "ordonnance", "paye"]
    assert d["chaine"][0]["montant"] == 30 * MD and d["chaine"][-1]["montant"] == 1 * MD
    assert d["ministeres"][0]["code"] == "14" and d["nb_ministeres"] == 1
    acteurs = {a["code"]: a for a in d["acteurs"]}
    assert set(acteurs) == {"dgcmp", "controle_financier", "tresor", "dgip"}
    assert acteurs["dgip"]["raccorde"] is False and "Non raccordé" in acteurs["dgip"]["texte"]
    assert acteurs["dgcmp"]["valeur"] == 0  # aucun engagement du titre 5 par marché public
    assert acteurs["tresor"]["valeur"] == regles.taux(1 * MD, 2 * MD)
    # Dates de visa égales aux dates de création dans l'extraction de test : délai nul.
    assert acteurs["controle_financier"]["valeur"]["mediane_jours"] == 0
    assert acteurs["controle_financier"]["voyant"] == "bon"


def test_fiche_titre_dette_et_credits_non_engages(filtres):
    d = titre_detail(filtres, "1")
    assert d["paiement_suivi"] is False
    assert d["chaine"][-1]["montant"] is None
    tresor = next(a for a in d["acteurs"] if a["code"] == "tresor")
    assert tresor["voyant"] is None and "hors chaîne" in tresor["texte"]
    assert not any(a["code"] == "dgip" for a in d["acteurs"])
    d3 = titre_detail(filtres, "3")
    assert d3["alertes"] == []


def test_dossiers_en_attente_visa(charge, filtres):
    qs = FaitEngagement.objects.filter(chargement=charge)
    vieux = filtres.date_situation - timedelta(days=40)
    qs.filter(numero__startswith="2").update(date_visa_cf=None, date_creation=vieux)
    d = dossiers_en_attente_visa(filtres, 15)
    assert [x["numero"] for x in d] == ["2"]
    assert d[0]["jours"] == 40 and d[0]["montant"] == 1 * MD and d[0]["acteur"] == "Contrôle financier"
    assert dossiers_en_attente_visa(filtres, 15, montant_min=2 * MD) == []
    assert dossiers_en_attente_visa(filtres, 60) == []
    # Engagement abandonné ou payé hors chaîne : pas de dossier à débloquer.
    qs.filter(numero__startswith="2").update(objet="x")
    eng = qs.get(numero__startswith="2")
    from apps.referentiels.models import RefEtatDossier

    eng.etat_dossier = RefEtatDossier.objects.create(libelle="Engagement abandonné", engagement_valide=False)
    eng.save(update_fields=["etat_dossier"])
    assert dossiers_en_attente_visa(filtres, 15) == []
    # La fiche du titre 5 le signale dans ses alertes quand il est ouvert.
    qs.filter(numero__startswith="1", titre="5").update(date_visa_cf=None, date_creation=vieux)
    alertes = titre_detail(filtres, "5")["alertes"]
    assert any("attente de visa" in a["texte"] for a in alertes)


# ------------------------------------------------------------------ arbitrages et courriels


@pytest.fixture
def regle_arbitrage(db):
    r = RegleAlerte.objects.get(code="depense_arbitrage_ministre")
    r.seuils |= {
        "montant_min": 1 * MD,
        "delai_jours": 15,
        "destinataires": ["ministre", "conseillere@exemple.gn"],
        "destinataires_relance": ["conseillere@exemple.gn"],
        "relance_heures": 48,
    }
    r.save()
    u = utilisateur("ministre", "ministre_cabinet")
    u.email = "ministre@exemple.gn"
    u.save()
    return r


def test_arbitrage_notifie_une_fois_puis_relance(charge, filtres, regle_arbitrage):
    FaitEngagement.objects.filter(chargement=charge, numero__startswith="2").update(
        date_visa_cf=None, date_creation=filtres.date_situation - timedelta(days=30)
    )
    mail.outbox.clear()
    evaluer_alertes(domaine="depense")
    a = Alerte.objects.get(regle=regle_arbitrage)
    assert a.cle and a.donnees["numero"] == "2" and a.donnees["acteur"] == "Contrôle financier"
    assert a.donnees["procedure"] == "Procedure normale" and a.donnees["imputation"].startswith("5.")
    assert a.donnees["sous_section"] == "140100000000" and a.donnees["date_creation"]
    assert a.titre.startswith("Arbitrage : T5 · Investissement")
    assert a.notifiee_le is not None
    assert len(mail.outbox) == 1
    assert set(mail.outbox[0].to) == {"ministre@exemple.gn", "conseillere@exemple.gn"}
    assert "Dossier n° 2" in mail.outbox[0].body

    # Nouvelle évaluation : même alerte, pas de second courriel, statut conservé.
    Alerte.objects.filter(pk=a.pk).update(statut="vue")
    evaluer_alertes(domaine="depense")
    assert Alerte.objects.get(regle=regle_arbitrage).pk == a.pk
    assert Alerte.objects.get(pk=a.pk).statut == "vue"
    assert len(mail.outbox) == 1

    # Pas de relance avant 48 h ; relance unique ensuite, à la conseillère seulement.
    assert relancer_alertes(timezone.now() + timedelta(hours=47)) == 0
    assert relancer_alertes(timezone.now() + timedelta(hours=49)) == 1
    assert mail.outbox[-1].to == ["conseillere@exemple.gn"] and "Relance" in mail.outbox[-1].subject
    assert relancer_alertes(timezone.now() + timedelta(hours=100)) == 0


def test_arbitrage_traite_pas_de_relance_et_dossier_debloque(charge, filtres, regle_arbitrage):
    eng = FaitEngagement.objects.filter(chargement=charge, numero__startswith="2")
    eng.update(date_visa_cf=None, date_creation=filtres.date_situation - timedelta(days=30))
    evaluer_alertes(domaine="depense")
    a = Alerte.objects.get(regle=regle_arbitrage)
    Alerte.objects.filter(pk=a.pk).update(statut="traitee")
    assert relancer_alertes(timezone.now() + timedelta(hours=49)) == 0
    # Dossier visé : l'alerte nouvelle disparaît, l'historique traité reste.
    Alerte.objects.filter(pk=a.pk).update(statut="nouvelle")
    eng.update(date_visa_cf=filtres.date_situation)
    evaluer_alertes(domaine="depense")
    assert not Alerte.objects.filter(regle=regle_arbitrage).exists()


def test_adresses_ignore_comptes_sans_courriel(db):
    utilisateur("sans-mail", "lecteur")
    assert adresses(["sans-mail", "a@b.gn", "a@b.gn", " "]) == ["a@b.gn"]


# ------------------------------------------------------------------ API


def test_api_titres(filtres):
    c = client_pour(utilisateur("cab-titres", "ministre_cabinet"))
    r = c.get("/api/v1/depense/titres/")
    assert r.status_code == 200, r.content
    assert {t["titre"] for t in r.json()["data"]["titres"]} == {"1", "2", "3", "5"}
    r = c.get("/api/v1/depense/titres/5/")
    assert r.status_code == 200 and r.json()["data"]["libelle_titre"] == "T5 · Investissement"
    assert c.get("/api/v1/depense/titres/9/").status_code == 404
    r = c.get("/api/v1/alertes/", {"regle": "depense_arbitrage_ministre"})
    assert r.status_code == 200 and r.json() == []


# ------------------------------------------------------------------ fiche de suivi en PDF


def test_fiche_dossier_pdf_structuree_et_droits(charge, filtres, regle_arbitrage):
    from io import BytesIO

    from pypdf import PdfReader

    FaitEngagement.objects.filter(chargement=charge, numero__startswith="2").update(
        date_visa_cf=None, date_creation=filtres.date_situation - timedelta(days=30)
    )
    evaluer_alertes(domaine="depense")
    a = Alerte.objects.get(regle=regle_arbitrage)
    url = f"/api/v1/alertes/{a.pk}/fiche-pdf/"

    c = client_pour(utilisateur("cab-fiche", "ministre_cabinet"))
    r = c.get(url)
    assert r.status_code == 200, r.content[:300]
    assert r["Content-Type"] == "application/pdf"
    assert 'filename="fiche-dossier-2.pdf"' in r["Content-Disposition"]
    pdf = PdfReader(BytesIO(r.content))
    page = pdf.pages[0]
    assert round(float(page.mediabox.width)) == 595 and round(float(page.mediabox.height)) == 842  # A4 portrait
    texte = " ".join(p.extract_text() for p in pdf.pages)
    for attendu in (
        "Dossier n° 2",
        "RÉPUBLIQUE DE GUINÉE",
        "1. Action proposée",
        "2. Objet du dossier",
        "3. Situation et traitement",
        "4. Rattachement administratif",
        "5. Dates et notifications",
        "6. Origine de l'alerte",
        "7. Décision",
        "Contrôle financier",
        "Procedure normale",
        "diffusion restreinte",
        f"Page 1 / {len(pdf.pages)}",
    ):
        assert attendu in texte, attendu
    assert pdf.metadata.title == "Fiche de suivi - dossier n° 2"
    # Mention de droits visible ; crédit des armoiries provisoires seulement dans les propriétés du PDF.
    assert "SMSI - Tous droits réservés" in texte
    assert "Turn685" not in texte and "Turn685" in pdf.metadata["/Keywords"]

    # Lecteur : pas d'export ; alerte sans dossier : pas de fiche.
    assert client_pour(utilisateur("lect-fiche", "lecteur", ["depense"])).get(url).status_code == 403
    autre = Alerte.objects.create(domaine="depense", severite="vigilance", titre="Sans dossier", message="x")
    assert c.get(f"/api/v1/alertes/{autre.pk}/fiche-pdf/").status_code == 404
