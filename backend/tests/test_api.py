import pytest
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework.test import APIClient

from apps.core.models import Alerte, JournalAudit, Utilisateur

MDP = "Mot-de-passe-2026!"
pytestmark = pytest.mark.django_db


def utilisateur(identifiant, role, domaines=None):
    return Utilisateur.objects.create_user(identifiant, password=MDP, role=role, domaines=domaines or [])


def client_pour(u, otp=True):
    from apps.core.api import jetons

    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {jetons(u, otp)['access']}")
    return c


@pytest.fixture
def cabinet(db):
    return client_pour(utilisateur("cabinet", "ministre_cabinet"))


@pytest.fixture
def dnsi(db):
    return client_pour(utilisateur("dnsi", "dnsi_admin"))


# ------------------------------------------------------------------ authentification


def test_connexion_et_profil():
    utilisateur("dgb", "directeur", ["depense"])
    r = APIClient().post("/api/v1/auth/connexion/", {"identifiant": "dgb", "mot_de_passe": MDP}, format="json")
    assert r.status_code == 200
    assert r.data["utilisateur"]["domaines"] == ["synthese", "depense"]
    assert JournalAudit.objects.filter(action="connexion", identifiant="dgb").exists()
    moi = APIClient()
    moi.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    assert moi.get("/api/v1/auth/moi/").data["role"] == "directeur"


def test_connexion_refusee():
    utilisateur("dgb", "directeur")
    r = APIClient().post("/api/v1/auth/connexion/", {"identifiant": "dgb", "mot_de_passe": "faux"}, format="json")
    assert r.status_code == 401
    assert JournalAudit.objects.filter(action="echec_connexion").exists()


def test_donnees_exigent_authentification():
    assert APIClient().get("/api/v1/depense/indicateurs/").status_code == 401


def test_2fa_obligatoire_pour_le_cabinet():
    u = utilisateur("cabinet", "ministre_cabinet")
    r = client_pour(u, otp=False).get("/api/v1/synthese/")
    assert r.status_code == 403 and r.data["code"] == "2fa_requis"


def test_enrolement_puis_connexion_2fa():
    u = utilisateur("cabinet", "ministre_cabinet")
    c = client_pour(u, otp=False)
    assert c.post("/api/v1/auth/2fa/activer/").data["otpauth_url"].startswith("otpauth://")
    d = TOTPDevice.objects.get(user=u)
    code = str(totp(d.bin_key)).zfill(6)
    r = c.post("/api/v1/auth/2fa/confirmer/", {"code_otp": code}, format="json")
    assert r.status_code == 200
    ok = APIClient()
    ok.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    assert ok.get("/api/v1/synthese/").status_code == 200

    anonyme = APIClient()
    r = anonyme.post("/api/v1/auth/connexion/", {"identifiant": "cabinet", "mot_de_passe": MDP}, format="json")
    assert r.status_code == 401 and r.data["code"] == "otp_requis"
    d.refresh_from_db()
    d.last_t = -1
    d.save()
    r = anonyme.post(
        "/api/v1/auth/connexion/", {"identifiant": "cabinet", "mot_de_passe": MDP, "code_otp": "000000"}, format="json"
    )
    assert r.status_code == 401


# ------------------------------------------------------------------ permissions


def test_directeur_limite_a_son_domaine(charge):
    c = client_pour(utilisateur("dgi", "directeur", ["recettes_fiscales"]))
    assert c.get("/api/v1/depense/indicateurs/").status_code == 403
    assert c.get("/api/v1/recettes-fiscales/").status_code == 200
    kpis = {k["code"]: k for k in c.get("/api/v1/synthese/").data["data"]["indicateurs"]}
    assert kpis["depenses_engagees"]["masque"] and "valeur" not in kpis["depenses_engagees"]
    assert all(a["domaine"] == "recettes_fiscales" for a in c.get("/api/v1/alertes/").data)


def test_import_reserve_dnsi(cabinet, classeur):
    with open(classeur, "rb") as f:
        r = cabinet.post("/api/v1/sources/chaine_depense/import/", {"fichier": f}, format="multipart")
    assert r.status_code == 403


def test_parametres_modifiables_par_dnsi(cabinet, dnsi):
    assert cabinet.patch("/api/v1/parametres/recouvrement_taux_min/", {"valeur": 0.9}, format="json").status_code == 403
    assert dnsi.patch("/api/v1/parametres/recouvrement_taux_min/", {"valeur": 0.9}, format="json").status_code == 200
    assert JournalAudit.objects.filter(action="parametre", objet="recouvrement_taux_min").exists()


# ------------------------------------------------------------------ données


def test_depense_enveloppe_meta(cabinet, charge):
    r = cabinet.get("/api/v1/depense/indicateurs/")
    assert r.status_code == 200
    m = r.data["meta"]
    assert m["source"] == "chaine_depense" and m["statut_source"] == "reel"
    assert m["date_situation"] == "2026-09-15" and m["genere_le"]
    assert r.data["data"]["credit_actuel"] == 105e9
    assert JournalAudit.objects.filter(action="consultation", objet="depenses").exists()


@pytest.mark.parametrize(
    "url",
    [
        "/api/v1/depense/chaine/",
        "/api/v1/depense/natures/",
        "/api/v1/depense/sections/",
        "/api/v1/depense/sections/14/",
        "/api/v1/depense/mensuel/",
        "/api/v1/depense/restes-a-payer/anciennete/",
        "/api/v1/depense/procedures/",
        "/api/v1/depense/beneficiaires/?top=3",
        "/api/v1/investissement/",
        "/api/v1/synthese/",
        "/api/v1/qualite/",
        "/api/v1/sources/",
        "/api/v1/alertes/?severite=critique",
    ],
)
def test_points_d_acces(cabinet, charge, url):
    assert cabinet.get(url).status_code == 200


def test_filtres_communs(cabinet, charge):
    r = cabinet.get("/api/v1/depense/indicateurs/?nature=investissement&paiement=brut")
    assert r.data["data"]["credit_actuel"] == 30e9 and r.data["meta"]["paiement"] == "brut"
    assert cabinet.get("/api/v1/depense/indicateurs/?nature=autre").status_code == 400
    assert cabinet.get("/api/v1/depense/indicateurs/?date_situation=pas-une-date").status_code == 400
    assert cabinet.get("/api/v1/depense/sections/XX/").status_code == 404


@pytest.mark.parametrize(
    "prefixe", ["recettes-fiscales", "douanes", "tresor", "dette", "paie", "patrimoine", "portefeuille"]
)
def test_source_non_raccordee_sans_erreur(cabinet, prefixe):
    r = cabinet.get(f"/api/v1/{prefixe}/indicateurs/")
    assert r.status_code == 200
    assert r.data["meta"]["statut_source"] == "non_raccorde" and r.data["data"] is None


def test_synthese_sans_aucune_donnee(cabinet):
    r = cabinet.get("/api/v1/synthese/")
    assert r.status_code == 200
    assert all(k["valeur"] is None for k in r.data["data"]["indicateurs"])
    assert len(r.data["data"]["sources"]) == 11  # dont Telemo (marchés publics)


def test_depense_sans_donnee(cabinet):
    r = cabinet.get("/api/v1/depense/indicateurs/")
    assert r.status_code == 200 and r.data["data"] is None


def test_import_par_api(dnsi, classeur):
    with open(classeur, "rb") as f:
        r = dnsi.post("/api/v1/sources/chaine_depense/import/", {"fichier": f, "apercu": True}, format="multipart")
    assert r.status_code == 201 and r.data["statut"] == "apercu"
    with open(classeur, "rb") as f:
        r = dnsi.post("/api/v1/sources/chaine_depense/import/", {"fichier": f}, format="multipart")
    assert r.status_code == 201 and r.data["statut"] == "succes" and r.data["lignes_chargees"] == 14
    assert JournalAudit.objects.filter(action="import").count() == 2
    assert dnsi.get("/api/v1/sources/chaine_depense/chargements/").status_code == 200


def test_import_format_refuse(dnsi, tmp_path):
    f = tmp_path / "x.pdf"
    f.write_bytes(b"%PDF")
    with open(f, "rb") as fh:
        assert (
            dnsi.post("/api/v1/sources/chaine_depense/import/", {"fichier": fh}, format="multipart").status_code == 400
        )


def test_cache_invalide_apres_chargement(cabinet, charge, tmp_path):
    from etl.connecteurs.chaine_depense import ExcelChaineDepenseConnector

    from .classeur import ecrire_classeur

    assert cabinet.get("/api/v1/depense/indicateurs/").data["meta"]["date_situation"] == "2026-09-15"
    ExcelChaineDepenseConnector(ecrire_classeur(tmp_path, nom="SC de 2025-2025 en date du 30-09-2026.xlsx")).executer()
    assert cabinet.get("/api/v1/depense/indicateurs/").data["meta"]["date_situation"] == "2026-09-30"


def test_changer_statut_alerte(cabinet, charge):
    a = Alerte.objects.first()
    r = cabinet.patch(f"/api/v1/alertes/{a.id}/", {"statut": "traitee", "titre": "ignoré"}, format="json")
    assert r.status_code == 200
    a.refresh_from_db()
    assert a.statut == "traitee" and a.titre != "ignoré"
    assert a.id not in [x["id"] for x in cabinet.get("/api/v1/synthese/").data["data"]["alertes"]]


def test_alertes_triees_par_severite(cabinet, charge):
    sev = [a["severite"] for a in cabinet.get("/api/v1/alertes/").data]
    ordre = {"critique": 0, "serieux": 1, "vigilance": 2}
    assert sev == sorted(sev, key=ordre.get)


def test_journal_reserve_dnsi(cabinet, dnsi):
    assert cabinet.get("/api/v1/journal/").status_code == 403
    assert dnsi.get("/api/v1/journal/").status_code == 200


def test_docs_openapi(cabinet):
    assert cabinet.get("/api/schema/").status_code == 200


def test_situations(cabinet, charge):
    r = cabinet.get("/api/v1/situations/")
    assert r.data["exercices"] == [{"exercice": 2025, "dates": ["2026-09-15"]}]
