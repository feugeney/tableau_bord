"""Chantier 3 de la mise en conformité : profil analyste, exploration libre, accès pour un outil de BI."""

import json
from decimal import Decimal
from io import BytesIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from openpyxl import load_workbook

from apps.core import exploration
from apps.core.models import JournalAudit
from apps.marches_publics.models import FaitMarche

from .test_api import client_pour, utilisateur
from .test_telemo import classeur as classeur_telemo

pytestmark = pytest.mark.django_db
MD = 10**9


@pytest.fixture
def telemo(db, tmp_path):
    from etl.connecteurs.generique import ExcelGenericConnector

    ch = ExcelGenericConnector("telemo", None, classeur_telemo(tmp_path)).executer()
    assert ch.statut == "succes", ch.message_erreur
    return ch


@pytest.fixture
def analyste(db):
    return client_pour(utilisateur("ana", "analyste", ["marches_publics"]))


def requete(client, q, chemin="requete/"):
    return client.get(f"/api/v1/exploration/{chemin}", {"q": json.dumps(q)})


# ------------------------------------------------------------------ profil


def test_profil_analyste():
    u = utilisateur("ana", "analyste", ["marches_publics"])
    assert u.exige_2fa and not u.voit_tout()
    assert u.peut_voir("marches_publics") and not u.peut_voir("dette") and u.peut_exporter("marches_publics")
    assert client_pour(u, otp=False).get("/api/v1/exploration/jeux/").status_code == 403  # sans double authentification
    moi = client_pour(u).get("/api/v1/auth/moi/").data
    assert moi["peut_explorer"] and not moi["est_admin"] and moi["role_libelle"].startswith("Analyste")


@pytest.mark.parametrize("role", ["directeur", "lecteur", "ministre_cabinet"])
def test_exploration_reservee(role):
    c = client_pour(utilisateur("x", role, ["marches_publics"]))
    assert c.get("/api/v1/exploration/jeux/").status_code == 403
    assert requete(c, {"jeu": "fait_marche"}).status_code == 403
    assert not c.get("/api/v1/auth/moi/").data["peut_explorer"]


def test_catalogue_limite_aux_domaines(analyste, telemo):
    d = analyste.get("/api/v1/exploration/jeux/").data
    assert {j["code"] for j in d["jeux"]} == {"fait_reservation_credit", "fait_marche", "fait_paiement_marche"}
    marche = next(j for j in d["jeux"] if j["code"] == "fait_marche")
    assert marche["statut_source"] == "reel" and marche["situations"] == [
        {"exercice": 2026, "date_situation": "2026-06-30"}
    ]
    axes = {a["code"]: a["type"] for a in marche["axes"]}
    assert axes["mode_passation"] == "liste" and axes["section"] == "reference" and axes["recours"] == "booleen"
    assert axes["date_immatriculation:trimestre"] == "periode"
    mesures = {m["code"]: m["agregat_defaut"] for m in marche["mesures"]}
    assert mesures["montant_ttc"] == "somme" and mesures["avancement_physique"] == "moyenne"
    assert "exercice" not in axes and "chargement" not in axes  # colonnes techniques masquées
    admin = client_pour(utilisateur("dnsi", "dnsi_admin"))
    assert len(admin.get("/api/v1/exploration/jeux/").data["jeux"]) == len(exploration.jeux())


# ------------------------------------------------------------------ requêtes


def test_regroupement_et_totaux(analyste, telemo):
    r = requete(analyste, {"jeu": "fait_marche", "axes": ["mode_passation"], "mesures": [{"champ": "montant_ttc"}]})
    assert r.status_code == 200, r.data
    d = r.data["data"]
    assert r.data["meta"]["source"] == "telemo" and r.data["meta"]["date_situation"] == "2026-06-30"
    assert [c["code"] for c in d["colonnes"]] == ["mode_passation", "montant_ttc__somme", "nombre_lignes"]
    lignes = {x["mode_passation"]: x for x in d["lignes"]}
    assert (
        lignes["aoo"]["montant_ttc__somme"] == 10 * MD
        and lignes["aoo"]["mode_passation__libelle"] == "Appel d'offres ouvert"
    )
    assert lignes["entente_directe"]["montant_ttc__somme"] == pytest.approx(1.2 * MD)
    assert d["lignes"][0]["mode_passation"] == "aoo"  # tri décroissant sur la première mesure
    assert d["totaux"]["montant_ttc__somme"] == pytest.approx(11.8 * MD) and d["totaux"]["nombre_lignes"] == 3
    assert d["nb_groupes"] == 3 and not d["tronque"]


def test_axe_periode_libelle_par_la_dimension_temps(analyste, telemo):
    r = requete(
        analyste,
        {
            "jeu": "fait_marche",
            "axes": ["date_immatriculation:mois"],
            "mesures": [{"champ": "montant_ttc", "agregat": "maximum"}],
            "tri": {"champ": "date_immatriculation_mois", "sens": "asc"},
        },
    )
    d = r.data["data"]
    assert [x["date_immatriculation:mois__libelle"] for x in d["lignes"]] == ["mars 2026", "avril 2026"]
    assert d["lignes"][0]["montant_ttc__maximum"] == 10 * MD and d["lignes"][0]["nombre_lignes"] == 2
    trimestre = requete(analyste, {"jeu": "fait_marche", "axes": ["date_immatriculation:trimestre"]}).data["data"]
    assert {x["date_immatriculation:trimestre__libelle"] for x in trimestre["lignes"]} == {"T1 2026", "T2 2026"}


def test_filtres(analyste, telemo):
    def nb(filtres):
        return requete(analyste, {"jeu": "fait_marche", "filtres": filtres}).data["data"]["totaux"]["nombre_lignes"]

    assert nb([{"champ": "mode_passation", "operateur": "egal", "valeur": "aoo"}]) == 1
    assert nb([{"champ": "mode_passation", "operateur": "different", "valeur": "aoo"}]) == 2
    assert nb([{"champ": "mode_passation", "operateur": "parmi", "valeur": "aoo; cotation"}]) == 2
    assert nb([{"champ": "objet", "operateur": "contient", "valeur": "route"}]) == 1
    assert nb([{"champ": "montant_ttc", "operateur": "superieur", "valeur": "1 000 000 000"}]) == 2
    assert nb([{"champ": "date_immatriculation", "operateur": "inferieur", "valeur": "2026-03-10"}]) == 2
    assert nb([{"champ": "titulaire_nif", "operateur": "egal", "valeur": ""}]) == 3  # filtre vide ignoré


def test_tri_par_defaut_sur_la_premiere_mesure(analyste, telemo):
    q = {"jeu": "fait_marche", "axes": ["numero_immatriculation"]}
    for mesures in (
        [{"champ": "montant_ttc"}, {"champ": "delai_execution_jours", "agregat": "minimum"}],
        [{"champ": "montant_taxes"}, {"champ": "montant_ht"}, {"champ": "montant_ttc"}],
    ):
        d = requete(analyste, {**q, "mesures": mesures}).data["data"]
        premiere = d["colonnes"][1]["code"]
        valeurs = [x[premiere] for x in d["lignes"]]
        assert valeurs == sorted(valeurs, reverse=True) and len(set(valeurs)) > 1
    # MP-3 a le délai le plus court (30 jours) mais le plus petit montant : le tri suit bien la première mesure.
    d = requete(
        analyste,
        {**q, "mesures": [{"champ": "delai_execution_jours", "agregat": "minimum"}, {"champ": "montant_ttc"}]},
    ).data["data"]
    assert [x["numero_immatriculation"] for x in d["lignes"]] == ["MP-1", "MP-2", "MP-3"]
    croissant = {**q, "mesures": [{"champ": "montant_ttc"}], "tri": {"champ": "montant_ttc__somme", "sens": "asc"}}
    assert requete(analyste, croissant).data["data"]["lignes"][0]["numero_immatriculation"] == "MP-3"


def test_sans_axe_ni_mesure_compte_les_lignes(analyste, telemo):
    d = requete(analyste, {"jeu": "fait_paiement_marche"}).data["data"]
    assert d["lignes"] == [{"nombre_lignes": 3}] and d["nb_groupes"] == 1


def test_limite_et_troncature(analyste, telemo):
    d = requete(analyste, {"jeu": "fait_marche", "axes": ["numero_immatriculation"], "limite": 2}).data["data"]
    assert len(d["lignes"]) == 2 and d["nb_groupes"] == 3 and d["tronque"]


def test_seul_le_chargement_actif_est_lu(analyste, telemo, tmp_path):
    """Un second chargement à la même date remplace le premier dans les résultats (pas de double compte)."""
    from etl.connecteurs.generique import ExcelGenericConnector

    assert ExcelGenericConnector("telemo", None, classeur_telemo(tmp_path)).executer().statut == "succes"
    assert FaitMarche.objects.count() == 6
    assert requete(analyste, {"jeu": "fait_marche"}).data["data"]["totaux"]["nombre_lignes"] == 3


@pytest.mark.parametrize(
    "q",
    [
        {"jeu": "inconnu"},
        {"jeu": "core_utilisateur"},  # seules les tables de faits sont des jeux
        {"jeu": "fait_marche", "axes": ["password"]},
        {"jeu": "fait_marche", "axes": ["chargement"]},
        {"jeu": "fait_marche", "axes": ["mode_passation", "mode_passation"]},
        {"jeu": "fait_marche", "mesures": [{"champ": "montant_ttc", "agregat": "pg_sleep"}]},
        {"jeu": "fait_marche", "mesures": [{"champ": "titulaire"}]},
        {"jeu": "fait_marche", "filtres": [{"champ": "source__code", "operateur": "egal", "valeur": "x"}]},
        {"jeu": "fait_marche", "filtres": [{"champ": "montant_ttc", "operateur": "egal", "valeur": "1; DROP TABLE"}]},
        {"jeu": "fait_marche", "filtres": [{"champ": "montant_ttc", "operateur": "contient", "valeur": "1"}]},
        {"jeu": "fait_marche", "exercice": "abc"},
        "pas du json",
    ],
)
def test_requetes_refusees(analyste, telemo, q):
    r = analyste.get("/api/v1/exploration/requete/", {"q": q if isinstance(q, str) else json.dumps(q)})
    assert r.status_code == 400, r.data


def test_jeu_hors_perimetre(analyste, charge):
    assert requete(analyste, {"jeu": "fait_engagement"}).status_code == 403
    admin = client_pour(utilisateur("dnsi", "dnsi_admin"))
    d = requete(admin, {"jeu": "fait_engagement", "axes": ["section"], "mesures": [{"champ": "montant_engage"}]}).data[
        "data"
    ]
    assert d["lignes"] and " — " in d["lignes"][0]["section__libelle"]  # code — libellé du référentiel


def test_export_excel_journalise(analyste, telemo):
    q = {
        "jeu": "fait_marche",
        "axes": ["mode_passation"],
        "mesures": [{"champ": "montant_ttc"}],
        "filtres": [{"champ": "type_marche", "operateur": "different", "valeur": "services"}],
    }
    r = requete(analyste, q, "export.xlsx")
    assert r.status_code == 200 and "exploration-fait_marche-2026-06-30.xlsx" in r["Content-Disposition"]
    wb = load_workbook(BytesIO(r.content))
    assert wb.sheetnames == ["Lisez-moi", "Résultat"]
    lisez_moi = {ligne[0]: ligne[1] for ligne in wb["Lisez-moi"].iter_rows(values_only=True) if ligne[0]}
    assert (
        lisez_moi["Statut de la source"] == "réel"
        and "type_marche different services" in lisez_moi["Filtres appliqués"]
    )
    assert "GNF" in lisez_moi["Unités"] and lisez_moi["Exporté par"] == "ana"
    lignes = list(wb["Résultat"].iter_rows(values_only=True))
    assert lignes[0] == ("Mode de passation", "Montant TTC (somme)", "Nombre de lignes")
    assert lignes[1] == ("Appel d'offres ouvert", 10 * MD, 1)
    assert lignes[-1][0] == "Total" and lignes[-1][1] == pytest.approx(11.8 * MD)
    j = JournalAudit.objects.filter(action="export").latest("id")
    assert j.objet == "exploration : fait_marche" and j.detail["requete"]["axes"] == ["mode_passation"]


# ------------------------------------------------------------------ accès pour un outil de BI


def _droit(role, table):
    with connection.cursor() as c:
        c.execute("SELECT has_table_privilege(%s, %s, 'SELECT')", [role, table])
        return c.fetchone()[0]


def test_compte_bi_en_lecture_seule(monkeypatch):
    with pytest.raises(CommandError):
        call_command("creer_acces_bi")  # mot de passe absent
    monkeypatch.setenv("BI_MOT_DE_PASSE", "un-mot-de-passe-long-2026")
    call_command("creer_acces_bi")
    assert _droit("tdb_bi", "mart.mv_depense_procedures") and _droit("tdb_bi", "ref.dim_temps")
    assert not _droit("tdb_bi", "dw.fait_engagement") and not _droit("tdb_bi", "public.core_utilisateur")
    with connection.cursor() as c:
        c.execute("SELECT rolsuper, rolcreaterole, rolconfig FROM pg_roles WHERE rolname = 'tdb_bi'")
        superutilisateur, creation, config = c.fetchone()
        c.execute("SELECT has_table_privilege('tdb_bi', 'ref.dim_temps', 'INSERT, UPDATE, DELETE')")
        assert not c.fetchone()[0]
    assert not superutilisateur and not creation and "default_transaction_read_only=on" in config
    call_command("creer_acces_bi", detail=True)  # mise à jour : accès au détail
    assert _droit("tdb_bi", "dw.fait_engagement") and not _droit("tdb_bi", "public.core_utilisateur")
    call_command("creer_acces_bi")  # retour au périmètre agrégé
    assert not _droit("tdb_bi", "dw.fait_engagement")
    call_command("creer_acces_bi", supprimer=True)
    with connection.cursor() as c:
        c.execute("SELECT 1 FROM pg_roles WHERE rolname = 'tdb_bi'")
        assert c.fetchone() is None


def test_montants_exacts():
    """Les agrégats restent des décimaux exacts côté serveur."""
    assert exploration._convertir(FaitMarche._meta.get_field("montant_ttc"), "1 234,50") == Decimal("1234.50")
