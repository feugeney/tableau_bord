"""Plan d'engagement (GDEP.TD_PLAN_ENG*) : chargement, calcul de la page et API Pilotage."""

from datetime import date, datetime
from decimal import Decimal

import pandas as pd
import pytest

from apps.core.filtres import resoudre_filtres
from apps.depense.plan_engagement import page
from etl.connecteurs.base import ErreurChargement
from etl.connecteurs.plan_engagement import PlanEngagementConnector

MD = 10**9


def _periode(code, etat="PE6", mobilisable=None, ouverture=None, courante="0", reference="2019/527/MB/CAB"):
    return {
        "exercice": 2019,
        "periode": code,
        "etat_code": etat,
        "etat_libelle": "Plan eng validé" if etat == "PE6" else "Parametrage plan eng",
        "montant_mobilisable": mobilisable,
        "montant_imprevu": 10 * MD,
        "montant_obligatoire_titre2": 40 * MD,
        "montant_repartissable": None,
        "reference_arrete": reference,
        "date_validation": datetime(2019, 2, 18),
        "date_ouverture": ouverture,
        "periode_courante": courante,
        "periode_execution": "0",
    }


def _plafond(periode, section, titre, plafond, engage_ouverture, libelle="MINISTERE DE LA SANTE"):
    return {
        "exercice": 2019,
        "periode": periode,
        "section": section,
        "libelle_section": libelle,
        "titre": titre,
        "credit": 1000 * MD,
        "engage_ouverture": engage_ouverture,
        "plafond": plafond,
        "montant_propose": 0,
        "montant_arbitrage": 0,
    }


def donnees(ouverture_t2=datetime(2019, 4, 2)):
    return {
        "periodes": pd.DataFrame(
            [
                _periode("T1", mobilisable=150 * MD, ouverture=datetime(2019, 1, 15), reference="0"),
                _periode("T2", mobilisable=200 * MD, ouverture=ouverture_t2, courante="1"),
                _periode("T3", etat="PE1"),
            ]
        ),
        "plafonds": pd.DataFrame(
            [
                _plafond("T1", "18", "3", 100 * MD, 0),
                _plafond("T1", "18", "5", 50 * MD, 0),
                _plafond("T2", "18", "3", 120 * MD, 120 * MD),
                _plafond("T2", "18", "5", 80 * MD, 30 * MD),
            ]
        ),
        "ajustements": pd.DataFrame(
            [
                {
                    "exercice": 2019,
                    "periode": "T1",
                    "section_source": "18",
                    "titre_source": "5",
                    "section_destination": "18",
                    "titre_destination": "3",
                    "montant": 5 * MD,
                    "observation": "Instruction conseil des ministres",
                    "date_ajustement": datetime(2019, 2, 1),
                }
            ]
        ),
    }


@pytest.fixture
def plan(db):
    ch = PlanEngagementConnector(2019, donnees=donnees(), date_situation=date(2026, 11, 18)).executer()
    assert ch.statut == "succes", ch.message_erreur
    return ch


def test_chargement_et_controles(plan):
    assert plan.lignes_chargees == 3 + 4 + 1
    controles = {c["code"]: c for c in plan.detail["controles"]}
    assert controles["plafond_unique"]["reussi"]
    # T1 : 150 Mds de plafonds = 150 Mds mobilisables ; T2 : 200 = 200.
    assert controles["plafonds_enveloppe"]["reussi"]


def test_trimestre_clos_engage_entre_deux_ouvertures(plan):
    d = page(resoudre_filtres({"exercice": "2019"}, "plan_engagement"), "T1")
    i = d["indicateurs"]
    assert i["plafond"] == 150 * MD
    # Titre 3 : 120 engagés pour 100 de plafond (dépassement) ; titre 5 : 30 pour 50.
    assert i["engage_periode"] == 150 * MD
    assert i["nb_depassements"] == 1
    section = d["sections"][0]
    assert section["libelle"] == "Ministère de la Santé"
    assert [t["depassement"] for t in section["titres"]] == [True, False]
    assert d["methode_engage"]["code"] == "ouverture_suivante"
    # « 0 » n'est pas une référence d'arrêté.
    assert d["entete"]["reference_arrete"] == ""
    assert d["ajustements"][0]["montant"] == 5 * MD


def test_trimestre_courant_par_defaut_sans_engage_connu(plan):
    d = page(resoudre_filtres({"exercice": "2019"}, "plan_engagement"))
    assert d["periode"] == "T2"
    assert d["indicateurs"]["engage_periode"] is None
    assert d["indicateurs"]["taux"] is None
    assert d["methode_engage"]["code"] is None
    assert [c["atteint"] for c in d["circuit"]] == [True] * 7


def test_ouverture_tardive_du_trimestre_suivant(db):
    ch = PlanEngagementConnector(
        2019, donnees=donnees(ouverture_t2=datetime(2022, 4, 8)), date_situation=date(2026, 11, 18)
    ).executer()
    assert ch.statut == "succes"
    d = page(resoudre_filtres({"exercice": "2019"}, "plan_engagement"), "T1")
    assert d["indicateurs"]["engage_periode"] is None
    assert "08/04/2022" in d["methode_engage"]["libelle"]


def test_plafond_en_double_bloque(db):
    jeu = donnees()
    jeu["plafonds"] = pd.concat([jeu["plafonds"], jeu["plafonds"].iloc[[0]]])
    ch = PlanEngagementConnector(2019, donnees=jeu, date_situation=date(2026, 11, 18)).executer()
    assert ch.statut == "echec"
    assert "Un plafond par trimestre" in ch.message_erreur


def test_production_refusee_aux_heures_ouvrees():
    c = PlanEngagementConnector(2019, maintenant=datetime(2026, 11, 18, 10, 0))
    with pytest.raises(ErreurChargement, match="heures ouvrées"):
        c.verifier_creneau()
    PlanEngagementConnector(2019, maintenant=datetime(2026, 11, 18, 10, 0), replique=True).verifier_creneau()
    PlanEngagementConnector(2019, maintenant=datetime(2026, 11, 21, 10, 0)).verifier_creneau()  # samedi


@pytest.fixture
def client_cabinet(db):
    from tests.test_api import client_pour, utilisateur

    return client_pour(utilisateur("cabinet", "ministre_cabinet"))


def test_api_pilotage(plan, client_cabinet):
    r = client_cabinet.get("/api/v1/pilotage/plan-engagement/", {"exercice": 2019, "periode": "T1"})
    assert r.status_code == 200, r.content
    corps = r.json()
    assert corps["meta"]["source"] == "plan_engagement"
    assert corps["data"]["periode"] == "T1"
    assert Decimal(str(corps["data"]["indicateurs"]["plafond"])) == 150 * MD
    assert client_cabinet.get("/api/v1/pilotage/plan-engagement/", {"periode": "T9"}).status_code == 400


def test_restriction_desactivee_en_developpement(settings):
    """ORACLE_RESTRICTION_HEURES_OUVREES=False (settings/dev.py) : lecture autorisée à toute heure."""
    from etl.connecteurs.chaine_depense import OracleChaineDepenseConnector

    settings.ORACLE_RESTRICTION_HEURES_OUVREES = False
    mardi_10h = datetime(2026, 11, 17, 10, 0)
    PlanEngagementConnector(2019, maintenant=mardi_10h).verifier_creneau()
    OracleChaineDepenseConnector(maintenant=mardi_10h).verifier_creneau()


# ------------------------------------------------------------------ flux ETL (Administration → Flux ETL)


@pytest.fixture
def flux_plan(db, settings):
    from apps.core.models import FluxETL

    settings.SOURCES_EXTERNES = {
        **settings.SOURCES_EXTERNES,
        "chaine_depense_oracle": {**settings.SOURCES_EXTERNES["chaine_depense_oracle"], "dsn": "hote:1521/devdep"},
    }
    flux = FluxETL.objects.get(code="oracle-plan-engagement")
    flux.exercice = 2019
    flux.actif = True
    flux.save()
    return flux


@pytest.fixture
def admin_etl(db):
    from tests.test_api import client_pour, utilisateur

    return client_pour(utilisateur("etl-plan", "dnsi_admin"))


def test_flux_cree_a_linitialisation_sans_connecteur_de_source(db):
    from apps.core.initialisation import REMARQUE_PLAN_ENGAGEMENT, initialiser_flux
    from apps.core.models import FluxETL, Source

    initialiser_flux()  # idempotent
    flux = FluxETL.objects.get(code="oracle-plan-engagement")
    assert flux.profil == "oracle_plan_engagement" and flux.source.code == "plan_engagement"
    assert not flux.actif and flux.planification_cron == ""
    # La source n'est pas basculée sur le connecteur de la Chaîne Dépense (aucune planification par source).
    source = Source.objects.get(code="plan_engagement")
    assert source.connecteur == "aucun" and source.remarque == REMARQUE_PLAN_ENGAGEMENT


def test_lancement_du_flux_charge_le_plan(admin_etl, flux_plan):
    from unittest.mock import patch

    from apps.core.models import Chargement
    from apps.depense.models import FaitPlanEngagement

    url = f"/api/v1/admin/flux-etl/{flux_plan.pk}/lancer/"
    with patch.object(PlanEngagementConnector, "extract", return_value=donnees()) as extraire:
        r = admin_etl.post(url, {"apercu": True, "exception_horaire_ponctuelle": True}, format="json")
        assert r.status_code == 200 and r.data["statut"] == "apercu", r.data
        assert not FaitPlanEngagement.objects.exists()
        r = admin_etl.post(url, {"apercu": False}, format="json")
        assert r.status_code == 200 and r.data["statut"] == "succes", r.data
        assert extraire.call_count == 2
    ch = Chargement.objects.get(pk=r.data["id"])
    assert ch.source.code == "plan_engagement" and ch.exercice == 2019
    assert ch.detail["flux_etl"] == "oracle-plan-engagement" and ch.detail["declenchement"] == "manuel"
    assert FaitPlanEngagement.objects.filter(chargement=ch).exists()
    liste = admin_etl.get("/api/v1/admin/flux-etl/").data
    assert next(f for f in liste if f["code"] == "oracle-plan-engagement")["derniere_execution"]["statut"] == "succes"


def test_flux_refuse_sans_connexion_oracle_ou_desactive(admin_etl, flux_plan, settings):
    url = f"/api/v1/admin/flux-etl/{flux_plan.pk}/lancer/"
    flux_plan.actif = False
    flux_plan.save()
    r = admin_etl.post(url, {"apercu": False}, format="json")
    assert r.status_code == 400 and "désactivé" in str(r.data)
    flux_plan.actif = True
    flux_plan.save()
    settings.SOURCES_EXTERNES = {
        **settings.SOURCES_EXTERNES,
        "chaine_depense_oracle": {**settings.SOURCES_EXTERNES["chaine_depense_oracle"], "dsn": ""},
    }
    r = admin_etl.post(url, {"apercu": True}, format="json")
    assert r.status_code == 400 and "CHAINE_DEPENSE_ORACLE_DSN" in str(r.data)


def test_programmation_aux_heures_ouvrees_refusee(admin_etl, flux_plan, settings):
    settings.ORACLE_RESTRICTION_HEURES_OUVREES = True
    url = f"/api/v1/admin/flux-etl/{flux_plan.pk}/"
    assert admin_etl.patch(url, {"planification_cron": "0 10 * * 1-5"}, format="json").status_code == 400
    assert admin_etl.patch(url, {"planification_cron": "0 2 * * *"}, format="json").status_code == 200


def test_exercice_sans_plan_indique_les_exercices_disponibles(db):
    from unittest.mock import patch

    vide = {k: v.iloc[0:0] for k, v in donnees().items()}
    with (
        patch.object(PlanEngagementConnector, "extract", return_value=vide),
        patch("etl.connecteurs.plan_engagement.exercices_disponibles", return_value=[2018, 2019, 2020, 2023]),
    ):
        ch = PlanEngagementConnector(2025, date_situation=date(2026, 11, 23)).executer()
    assert ch.statut == "echec"
    assert "aucun plan d'engagement ouvert pour 2025" in ch.message_erreur
    assert "exercices disponibles dans la Chaîne Dépense : 2018, 2019, 2020, 2023" in ch.message_erreur
