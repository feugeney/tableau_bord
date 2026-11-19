import pytest
from rest_framework.test import APIClient

from apps.core.models import JetonPartage, JournalAudit, MappingColonnes, RegleAlerte, Source, Utilisateur

from .test_api import client_pour, utilisateur

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(db):
    return client_pour(utilisateur("dnsi", "dnsi_admin"))


@pytest.fixture
def cabinet(db):
    return client_pour(utilisateur("cab", "ministre_cabinet"))


@pytest.mark.parametrize(
    "url",
    [
        "sources/",
        "mappings/",
        "chargements/",
        "regles-alerte/",
        "utilisateurs/",
        "partages/",
        "tables-cibles/",
        "entrepot/",
        "referentiels/",
    ],
)
def test_reserve_dnsi(admin, cabinet, url):
    assert cabinet.get(f"/api/v1/admin/{url}").status_code == 403
    assert admin.get(f"/api/v1/admin/{url}").status_code == 200


def test_admin_exige_2fa():
    u = utilisateur("dnsi2", "dnsi_admin")
    assert client_pour(u, otp=False).get("/api/v1/admin/sources/").status_code == 403


def test_configurer_connecteur(admin):
    r = admin.patch(
        "/api/v1/admin/sources/sicom/",
        {
            "connecteur": "postgres",
            "planification_cron": "30 1 * * *",
            "configuration": {"table_cible": "fait_patrimoine", "requete": "SELECT * FROM v_patrimoine"},
        },
        format="json",
    )
    assert r.status_code == 200, r.data
    assert r.data["variable_connexion"] == "SICOM_DATABASE_URL"
    assert r.data["connexion_configuree"] is False
    assert JournalAudit.objects.filter(objet="source sicom").exists()


@pytest.mark.parametrize(
    "conf, erreur",
    [
        ({"requete": "DELETE FROM x"}, "lecture"),
        ({"requete": "SELECT 1; DROP TABLE x"}, "lecture"),
        ({"mot_de_passe": "x"}, "secret"),
    ],
)
def test_configuration_refusee(admin, conf, erreur):
    r = admin.patch("/api/v1/admin/sources/sicom/", {"configuration": conf}, format="json")
    assert r.status_code == 400 and erreur in str(r.data)


def test_cron_invalide(admin):
    assert (
        admin.patch("/api/v1/admin/sources/sicom/", {"planification_cron": "chaque nuit"}, format="json").status_code
        == 400
    )


def test_tester_connexion(admin):
    r = admin.post("/api/v1/admin/sources/sicom/tester/")
    assert r.status_code == 200 and r.data["ok"] is False  # connecteur non défini ou variable absente
    r = admin.post("/api/v1/admin/sources/chaine_depense/tester/")
    assert r.data["ok"] is True  # import de fichier


def test_mappings(admin):
    r = admin.post(
        "/api/v1/admin/mappings/",
        {
            "source": "fugas",
            "table_cible": "fait_paie",
            "colonne_source": "Effectif",
            "champ_cible": "effectif",
            "type_donnee": "entier",
            "obligatoire": True,
        },
        format="json",
    )
    assert r.status_code == 201, r.data
    assert (
        admin.post(
            "/api/v1/admin/mappings/",
            {"source": "fugas", "table_cible": "fait_paie", "colonne_source": "X", "champ_cible": "inexistant"},
            format="json",
        ).status_code
        == 400
    )
    assert admin.get("/api/v1/admin/mappings/?source=fugas").data[0]["champ_cible"] == "effectif"
    assert admin.delete(f"/api/v1/admin/mappings/{r.data['id']}/").status_code == 204
    assert not MappingColonnes.objects.filter(source__code="fugas").exists()


def test_tables_cibles(admin):
    tables = {t["table"]: t for t in admin.get("/api/v1/admin/tables-cibles/").data}
    assert "fait_paie" in tables and "fait_situation_ligne" not in tables
    assert {c["nom"] for c in tables["fait_paie"]["champs"]} >= {"mois", "section", "effectif"}


def test_regles_alerte(admin):
    r = RegleAlerte.objects.get(code="paie_doublons")
    assert admin.patch(f"/api/v1/admin/regles-alerte/{r.id}/", {"actif": False}, format="json").status_code == 200
    r.refresh_from_db()
    assert not r.actif
    assert admin.post("/api/v1/admin/regles-alerte/evaluer/").status_code == 200


def test_utilisateurs(admin):
    r = admin.post(
        "/api/v1/admin/utilisateurs/",
        {"username": "dgi", "role": "directeur", "domaines": ["recettes_fiscales"]},
        format="json",
    )
    assert r.status_code == 201, r.data
    assert r.data["mot_de_passe_initial"]  # affiché une seule fois
    u = Utilisateur.objects.get(username="dgi")
    assert u.check_password(r.data["mot_de_passe_initial"])
    assert (
        admin.post(
            "/api/v1/admin/utilisateurs/", {"username": "x", "mot_de_passe": "faible"}, format="json"
        ).status_code
        == 400
    )
    assert (
        admin.patch(f"/api/v1/admin/utilisateurs/{u.id}/", {"domaines": ["inconnu"]}, format="json").status_code == 400
    )
    assert admin.patch(f"/api/v1/admin/utilisateurs/{u.id}/", {"is_active": False}, format="json").status_code == 200
    assert admin.post(f"/api/v1/admin/utilisateurs/{u.id}/reinitialiser-2fa/").status_code == 200


def test_pas_de_desactivation_de_soi():
    u = utilisateur("moi", "dnsi_admin")
    c = client_pour(u)
    assert c.patch(f"/api/v1/admin/utilisateurs/{u.id}/", {"is_active": False}, format="json").status_code == 400


def test_partage_par_jeton(admin, charge):
    r = admin.post(
        "/api/v1/admin/partages/",
        {"nom": "Tableau Primature", "destinataire": "Système tiers", "domaines": ["depense"]},
        format="json",
    )
    assert r.status_code == 201, r.data
    cle = r.data["cle"]
    assert cle.startswith("tdb_") and not JetonPartage.objects.filter(empreinte=cle).exists()  # jamais en clair
    tiers = APIClient()
    tiers.credentials(HTTP_AUTHORIZATION=f"Jeton {cle}")
    assert tiers.get("/api/v1/depense/indicateurs/").status_code == 200
    assert tiers.get("/api/v1/recettes-fiscales/").status_code == 403  # hors du périmètre partagé
    assert tiers.get("/api/v1/admin/sources/").status_code == 403
    assert tiers.patch("/api/v1/alertes/1/", {"statut": "vue"}, format="json").status_code == 401  # lecture seule
    assert JetonPartage.objects.get().derniere_utilisation is not None
    # Le compte technique n'apparaît pas parmi les utilisateurs.
    assert all(not u["username"].startswith("partage-") for u in admin.get("/api/v1/admin/utilisateurs/").data)
    # Révocation.
    jid = r.data["id"]
    assert admin.patch(f"/api/v1/admin/partages/{jid}/", {"actif": False}, format="json").status_code == 200
    assert tiers.get("/api/v1/depense/indicateurs/").status_code == 401
    assert admin.delete(f"/api/v1/admin/partages/{jid}/").status_code == 204
    assert not JetonPartage.objects.exists()


def test_jeton_invalide():
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Jeton tdb_faux")
    assert c.get("/api/v1/synthese/").status_code == 401


def test_entrepot(admin):
    assert set(admin.get("/api/v1/admin/entrepot/").data["zone_brute"]) == {"fichiers", "octets"}
    d = admin.get("/api/v1/admin/entrepot/").data
    assert any(t["table"] == "fait_situation_ligne" for t in d["tables"])
    assert admin.post("/api/v1/admin/entrepot/", {"action": "rafraichir"}, format="json").status_code == 200
    assert admin.post("/api/v1/admin/entrepot/", {"action": "demo"}, format="json").status_code == 200
    assert Source.objects.filter(statut="demo").count() == 9
    assert Source.objects.get(code="tofe").statut == "demo"
    assert admin.post("/api/v1/admin/entrepot/", {"action": "demo_supprimer"}, format="json").status_code == 200
    assert admin.post("/api/v1/admin/entrepot/", {"action": "autre"}, format="json").status_code == 400
