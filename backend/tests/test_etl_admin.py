"""Contrats, permissions et chargements du pilote ETL, sans connexion externe."""

import json
from unittest.mock import patch

import pandas as pd
import pytest
from django.utils import timezone
from django_celery_beat.models import PeriodicTask

from apps.core.etl_admin import executer_flux, synchroniser_flux
from apps.core.filtres import Filtres
from apps.core.initialisation import initialiser_flux, requetes_oracle_preparees
from apps.core.models import Chargement, FluxETL, Source
from apps.portefeuille.models import FaitDividende
from apps.portefeuille.services import page
from etl.connecteurs.sysop import SysopPortefeuilleConnector
from etl.mart import version_donnees

from .test_api import client_pour, utilisateur
from .test_oracle_rapprochement import connecteur_test
from .test_sysop_import import donnees_test

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin():
    return client_pour(utilisateur("etl-admin", "dnsi_admin"))


@pytest.fixture
def flux():
    flux = FluxETL.objects.get(code="sysop-portefeuille")
    flux.source.connecteur = "postgres"
    flux.source.save()
    flux.exercice = 2025
    flux.actif = True
    flux.save()
    return flux


@pytest.fixture
def extraction():
    def extraire(connecteur):
        connecteur.informations_chargement = {"profil": "sysop_portefeuille"}
        return donnees_test()

    with (
        patch.object(SysopPortefeuilleConnector, "extract", extraire),
        patch.object(SysopPortefeuilleConnector, "apres_chargement"),
    ):
        yield


def test_catalogue_permissions_et_absence_de_secrets(admin):
    cabinet = client_pour(utilisateur("etl-cabinet", "ministre_cabinet"))
    for chemin in ["alimentation/", "flux-etl/"]:
        assert cabinet.get(f"/api/v1/admin/{chemin}").status_code == 403
        assert admin.get(f"/api/v1/admin/{chemin}").status_code == 200
    catalogue = admin.get("/api/v1/admin/alimentation/").data
    assert len(catalogue["onglets"]) == 12
    assert "configuration" not in catalogue["onglets"][0]["sources"][0]
    assert "TOFE" in [c["onglet"] for c in catalogue["onglets"]]
    sans_otp = client_pour(utilisateur("etl-sans-otp", "dnsi_admin"), otp=False)
    assert sans_otp.get("/api/v1/admin/flux-etl/").status_code == 403


@pytest.mark.parametrize("corps", [{"exercice": 1999}, {"exercice": 2100}, {"planification_cron": "0 99 * * *"}])
def test_configuration_invalide(admin, flux, corps):
    assert admin.patch(f"/api/v1/admin/flux-etl/{flux.pk}/", corps, format="json").status_code == 400


def test_planification_exercice_et_desactivation(admin, flux):
    url = f"/api/v1/admin/flux-etl/{flux.pk}/"
    assert admin.patch(url, {"planification_cron": "0 2 * * *"}, format="json").status_code == 200
    tache = PeriodicTask.objects.get(name=f"flux-etl-{flux.pk}")
    assert tache.task == "etl.executer_flux"
    assert json.loads(tache.kwargs) == {"flux_id": flux.pk}
    assert str(tache.crontab.timezone) == "Africa/Conakry"
    assert admin.patch(url, {"actif": False}, format="json").status_code == 200
    assert not PeriodicTask.objects.filter(name=tache.name).exists()
    with patch.object(SysopPortefeuilleConnector, "executer") as lancer:
        assert admin.post(f"{url}lancer/", {"apercu": False}, format="json").status_code == 400
        lancer.assert_not_called()


def test_apercu_necrit_aucune_donnee_metier(admin, flux, extraction):
    r = admin.post(f"/api/v1/admin/flux-etl/{flux.pk}/lancer/", {"apercu": True}, format="json")
    assert r.status_code == 200 and r.data["statut"] == "apercu"
    assert r.data["lignes_lues"] == 6
    assert not FaitDividende.objects.exists()
    ch = Chargement.objects.get(pk=r.data["id"])
    assert ch.detail["flux_etl"] == flux.code
    assert ch.detail["controles"]


def test_reexecution_sans_cumul_et_echec_conserve_derniere_reussite(flux, extraction):
    for _ in range(2):
        ch = executer_flux(flux)
        assert ch.statut == "succes", ch.message_erreur
    filtres = Filtres(2025, timezone.localdate())
    assert page(filtres)["indicateurs"]["dividendes_encaisses"] == 75
    invalides = donnees_test()
    invalides["resultats"] = pd.concat([invalides["resultats"]] * 2)
    with patch.object(SysopPortefeuilleConnector, "extract", return_value=invalides):
        echec = executer_flux(flux)
    assert echec.statut == "echec"
    assert page(filtres)["indicateurs"]["dividendes_encaisses"] == 75
    assert not FaitDividende.objects.filter(chargement=echec).exists()


def test_verrou_concurrent_refuse_sans_extraire(flux):
    from rest_framework.exceptions import ValidationError

    with (
        patch("apps.core.etl_admin.connection.cursor") as curseur,
        patch.object(SysopPortefeuilleConnector, "executer") as lancer,
    ):
        curseur.return_value.__enter__.return_value.fetchone.return_value = [False]
        with pytest.raises(ValidationError, match="déjà en cours"):
            executer_flux(flux)
        lancer.assert_not_called()


def test_initialisation_idempotente_et_pilote_manuel(flux):
    flux.planification_cron = "30 3 * * *"
    flux.save()
    initialiser_flux()
    flux.refresh_from_db()
    assert flux.exercice == 2025 and flux.actif and flux.planification_cron == "30 3 * * *"
    FluxETL.objects.all().delete()
    Chargement.objects.create(source=flux.source, exercice=2025, statut="succes")
    initialiser_flux()
    neuf = FluxETL.objects.get(code="sysop-portefeuille")
    assert neuf.exercice == 2025
    assert not neuf.actif and not neuf.planification_cron
    synchroniser_flux(neuf)
    assert not PeriodicTask.objects.filter(name=f"flux-etl-{neuf.pk}").exists()


def test_marqueur_cache_reagit_aux_imports_dautres_processus():
    avant = version_donnees()
    Chargement.objects.create(source=Source.objects.get(code="sysop"), statut="apercu")
    assert version_donnees() == avant
    Chargement.objects.create(source=Source.objects.get(code="sysop"), statut="succes")
    assert version_donnees() != avant


@pytest.fixture
def flux_oracle():
    flux = FluxETL.objects.get(code="oracle-chaine-depense")
    flux.source.connecteur = "oracle_chaine_depense"
    flux.source.configuration = {"requetes": requetes_oracle_preparees()}
    flux.source.save()
    flux.exercice = 2025
    flux.actif = True
    flux.save()
    return flux


def test_contrat_oracle_reprend_correspondances_existantes(admin, flux_oracle):
    from etl.connecteurs.chaine_depense import OBLIGATOIRES, OracleChaineDepenseConnector

    r = admin.get(f"/api/v1/admin/flux-etl/{flux_oracle.pk}/")
    requetes = {q["table"]: q for q in r.data["requetes"]}
    for table, cle in [
        ("situation", OracleChaineDepenseConnector.cle_ligne),
        ("engagements", ["exercice", "groupe_administratif", "numero"]),
    ]:
        assert set(OBLIGATOIRES[table] + cle) <= set(requetes[table]["champs"])
        assert ":exercice" in requetes[table]["sql"]
        assert "SELECT" in requetes[table]["sql"]
    assert "GDEP.LBUDG" in requetes["situation"]["sql"]
    assert "GDEP.ENGAGEMENT" in requetes["engagements"]["sql"]
    assert (
        admin.patch(
            "/api/v1/admin/sources/chaine_depense/",
            {"configuration": flux_oracle.source.configuration},
            format="json",
        ).status_code
        == 200
    )


def test_oracle_parametres_et_exception_uniquement_pour_lancement(admin, flux_oracle):
    from etl.connecteurs.chaine_depense import OracleChaineDepenseConnector

    url = f"/api/v1/admin/flux-etl/{flux_oracle.pk}/lancer/"
    with patch.object(OracleChaineDepenseConnector, "extract", return_value=connecteur_test().donnees) as extraire:
        # La validation et les contrôles sont réels ; seul l'accès externe est simulé.
        r = admin.post(url, {"apercu": True, "exception_horaire_ponctuelle": True}, format="json")
        assert r.status_code == 200 and r.data["statut"] == "apercu", r.data
        assert r.data["detail"]["exception_horaire_ponctuelle"] is True
        r = admin.post(url, {"apercu": True}, format="json")
        assert r.data["detail"]["exception_horaire_ponctuelle"] is False
        assert extraire.call_count == 2
    from apps.depense.models import FaitSituationLigne

    assert not FaitSituationLigne.objects.exists()


def test_planification_oracle_passe_par_flux_et_conserve_restrictions(flux_oracle):
    from etl.planification import synchroniser_planification

    flux_oracle.source.planification_cron = "0 2 * * *"
    synchroniser_planification(flux_oracle.source)
    assert not PeriodicTask.objects.filter(name="chargement-chaine_depense").exists()
    flux_oracle.planification_cron = "0 2 * * *"
    synchroniser_flux(flux_oracle)
    tache = PeriodicTask.objects.get(name=f"flux-etl-{flux_oracle.pk}")
    assert json.loads(tache.kwargs) == {"flux_id": flux_oracle.pk}


# ------------------------------------------------------------------ planification des chargements


def test_expression_cron_correspondance_et_prochaine_occurrence():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from etl.planificateur import analyser, correspond, prochaine_occurrence

    conakry = ZoneInfo("Africa/Conakry")
    ouvres = analyser("30 2 * * 1-5")
    vendredi = datetime(2026, 11, 13, 2, 30, tzinfo=conakry)
    assert correspond(ouvres, vendredi)
    assert not correspond(ouvres, vendredi.replace(day=14))  # samedi
    assert prochaine_occurrence(ouvres, vendredi) == datetime(2026, 11, 16, 2, 30, tzinfo=conakry)
    assert prochaine_occurrence(analyser("0 2 * * *"), vendredi) == datetime(2026, 11, 14, 2, 0, tzinfo=conakry)


@pytest.mark.parametrize(
    "cron, replique, attendu",
    [
        ("0 10 * * 1-5", False, 400),
        ("0 10 * * *", False, 400),
        ("30 18 * * 3", False, 400),
        ("0 2 * * *", False, 200),
        ("0 10 * * 6", False, 200),
        ("0 10 * * *", True, 200),
    ],
)
def test_programmation_oracle_refusee_en_heures_ouvrees(admin, flux_oracle, cron, replique, attendu):
    flux_oracle.source.configuration = {**flux_oracle.source.configuration, "replique": replique}
    flux_oracle.source.save()
    r = admin.patch(f"/api/v1/admin/flux-etl/{flux_oracle.pk}/", {"planification_cron": cron}, format="json")
    assert r.status_code == attendu, r.data
    if attendu == 400:
        assert "18:30" in str(r.data)
        assert not PeriodicTask.objects.filter(name=f"flux-etl-{flux_oracle.pk}").exists()


def test_flux_expose_prochaine_execution(admin, flux):
    url = f"/api/v1/admin/flux-etl/{flux.pk}/"
    assert admin.get(url).data["prochaine_execution"] is None
    admin.patch(url, {"planification_cron": "15 3 * * *"}, format="json")
    prochaine = admin.get(url).data["prochaine_execution"]
    assert prochaine and "T03:15:00" in prochaine


def heure_conakry(jour, heure, minute, seconde=0):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    return datetime(2026, 11, jour, heure, minute, seconde, tzinfo=ZoneInfo("Africa/Conakry"))


def test_planificateur_lance_le_flux_a_echeance_une_seule_fois(admin, flux, extraction):
    from etl.planificateur import Planificateur

    admin.patch(f"/api/v1/admin/flux-etl/{flux.pk}/", {"planification_cron": "0 2 * * *"}, format="json")
    PeriodicTask.objects.exclude(name=f"flux-etl-{flux.pk}").update(enabled=False)  # relève du dépôt, etc.
    planificateur = Planificateur(synchrone=True)
    try:
        assert planificateur.tour(heure_conakry(17, 1, 59)) == []
        assert planificateur.tour(heure_conakry(17, 2, 0, 10)) == [f"flux-etl-{flux.pk}"]
        assert planificateur.tour(heure_conakry(17, 2, 0, 40)) == []  # même minute : pas de doublon
        assert planificateur.tour(heure_conakry(17, 3, 0)) == []  # pas de rattrapage hors échéance
        assert admin.get("/api/v1/admin/flux-etl/planificateur/").data == {"actif": True}
    finally:
        planificateur.liberer()
    assert admin.get("/api/v1/admin/flux-etl/planificateur/").data == {"actif": False}
    ch = Chargement.objects.get(detail__declenchement="planification")
    assert ch.statut == "succes" and ch.detail["flux_etl"] == flux.code
    planifiee = admin.get(f"/api/v1/admin/flux-etl/{flux.pk}/").data["derniere_execution_planifiee"]
    assert planifiee["id"] == ch.pk
    tache = PeriodicTask.objects.get(name=f"flux-etl-{flux.pk}")
    assert tache.total_run_count == 1 and tache.last_run_at is not None


def test_un_seul_planificateur_par_base():
    from etl.planificateur import DejaActif, Planificateur

    premier = Planificateur(synchrone=True)
    premier.verrouiller()
    try:
        with patch("etl.planificateur.connection.cursor") as curseur:
            curseur.return_value.__enter__.return_value.fetchone.return_value = [False]
            with pytest.raises(DejaActif):
                Planificateur(synchrone=True).tour()
    finally:
        premier.liberer()


def test_echec_programme_leve_une_alerte_retiree_au_succes(flux, extraction):
    from apps.core.models import Alerte
    from etl.tasks import executer_flux_task

    invalides = donnees_test()
    invalides["resultats"] = pd.concat([invalides["resultats"]] * 2)
    with patch.object(SysopPortefeuilleConnector, "extract", return_value=invalides):
        assert executer_flux_task(flux.pk)["statut"] == "echec"
        executer_flux_task(flux.pk)
    alerte = Alerte.objects.get(titre__startswith="Chargement programmé en échec")
    assert alerte.source == flux.source and alerte.domaine == flux.source.domaine
    assert alerte.chargement.statut == "echec"
    assert "Aucune donnée" in alerte.message and ".." not in alerte.message
    assert executer_flux_task(flux.pk)["statut"] == "succes"
    assert not Alerte.objects.filter(titre__startswith="Chargement programmé en échec").exists()


def test_execution_programmee_refusee_leve_une_alerte(flux):
    from apps.core.models import Alerte
    from etl.tasks import executer_flux_task

    flux.actif = False
    flux.save()
    assert executer_flux_task(flux.pk) == {"statut": "refuse", "message": "Ce flux est désactivé."}
    alerte = Alerte.objects.get(titre__startswith="Chargement programmé en échec")
    assert "Ce flux est désactivé" in alerte.message and alerte.chargement is None


@pytest.mark.parametrize("saisie, attendu", [("11 h 30", "30 11 * * *"), ("2:05", "5 2 * * *"), ("3h", "0 3 * * *")])
def test_une_heure_simple_vaut_un_chargement_quotidien(admin, flux, saisie, attendu):
    r = admin.patch(f"/api/v1/admin/flux-etl/{flux.pk}/", {"planification_cron": saisie}, format="json")
    assert r.status_code == 200 and r.data["planification_cron"] == attendu


def test_programmation_illisible_explique_le_format(admin, flux):
    r = admin.patch(f"/api/v1/admin/flux-etl/{flux.pk}/", {"planification_cron": "demain matin"}, format="json")
    assert r.status_code == 400 and "2 h 30" in str(r.data)


def test_heure_simple_oracle_en_journee_refusee(admin, flux_oracle):
    r = admin.patch(f"/api/v1/admin/flux-etl/{flux_oracle.pk}/", {"planification_cron": "11 h 30"}, format="json")
    assert r.status_code == 400 and "18:30" in str(r.data)
