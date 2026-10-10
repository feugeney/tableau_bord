"""Chantier 2 de la mise en conformité : dépôt de fichiers (SFTP), schémas JSON, XML, événements AMQP."""

import json
import os
import shutil
import time
from datetime import date
from pathlib import Path

import pytest
from django.conf import settings as reglages

from apps.core.models import Chargement, Source
from apps.marches_publics.models import FaitMarche, FaitPaiementMarche, FaitReservationCredit
from etl import depots, evenements, schemas
from etl.connecteurs.generique import ExcelGenericConnector

from .test_api import client_pour, utilisateur

pytestmark = pytest.mark.django_db
MD = 10**9


@pytest.fixture
def admin(db):
    return client_pour(utilisateur("dnsi", "dnsi_admin"))


@pytest.fixture
def depot(db):
    """Dépôt vidé avant et après chaque test."""
    shutil.rmtree(reglages.DEPOT_ROOT, ignore_errors=True)
    depots.preparer_dossiers()
    yield Path(reglages.DEPOT_ROOT)
    shutil.rmtree(reglages.DEPOT_ROOT, ignore_errors=True)


def deposer(dossier: Path, origine: Path, nom: str | None = None, age: int = 3600) -> Path:
    cible = dossier / (nom or origine.name)
    shutil.copyfile(origine, cible)
    ancien = time.time() - age
    os.utime(cible, (ancien, ancien))
    return cible


# ------------------------------------------------------------------ dépôt de fichiers


def test_un_dossier_par_source(depot):
    assert {d.name for d in depot.iterdir()} == set(Source.objects.values_list("code", flat=True))


def test_releve_charge_puis_retire_le_fichier(depot, classeur):
    f = deposer(depot / "chaine_depense", classeur)
    resultats = depots.relever()
    assert [(r["source"], r["statut"]) for r in resultats] == [("chaine_depense", "succes")]
    ch = Chargement.objects.get(pk=resultats[0]["chargement"])
    assert ch.detail["origine"] == "depot" and ch.fichier == classeur.name and ch.utilisateur is None
    assert (Path(reglages.MEDIA_ROOT) / ch.fichier_archive).is_file()  # la copie conservée est en zone brute
    assert not f.exists() and not list((depot / "chaine_depense" / ".encours").iterdir())
    assert depots.relever() == []  # rien n'est traité deux fois


def test_transfert_en_cours_et_fichiers_ignores(depot, classeur):
    recent = deposer(depot / "chaine_depense", classeur, age=5)
    cache = deposer(depot / "chaine_depense", classeur, nom=".partiel.xlsx")
    autre = depot / "chaine_depense" / "note.txt"
    autre.write_text("à ne pas charger")
    ancien = time.time() - 3600
    os.utime(autre, (ancien, ancien))
    assert depots.relever() == []
    assert recent.exists() and cache.exists() and autre.exists()
    assert depots.relever(maintenant=time.time() + 120) and not recent.exists()  # délai de stabilité écoulé


def test_fichier_illisible_trace_et_retire(depot, tmp_path):
    mauvais = tmp_path / "Telemo en date du 30-06-2026.xlsx"
    mauvais.write_bytes(b"pas un classeur")
    f = deposer(depot / "telemo", mauvais)
    (r,) = depots.relever()
    assert r["statut"] == "echec" and not f.exists()
    assert Chargement.objects.get(pk=r["chargement"]).empreinte_sha256  # consultable pour le diagnostic


def test_fichier_trop_volumineux(depot, classeur, settings):
    settings.IMPORT_TAILLE_MAX = 10
    deposer(depot / "chaine_depense", classeur)
    (r,) = depots.relever()
    ch = Chargement.objects.get(pk=r["chargement"])
    assert ch.statut == "echec" and "volumineux" in ch.message_erreur and not ch.fichier_archive


def test_releve_planifiee_et_tache():
    from django_celery_beat.models import PeriodicTask

    from etl.tasks import relever_depots

    t = PeriodicTask.objects.get(name="releve-depots")
    assert t.task == "etl.relever_depots" and t.enabled and t.interval.every == reglages.DEPOT_RELEVE_MINUTES
    assert relever_depots() == []


def test_releve_depuis_l_administration(admin, depot, classeur):
    deposer(depot / "chaine_depense", classeur)
    e = admin.get("/api/v1/admin/entrepot/").data
    assert e["depot"]["en_attente"] == [
        {"source": "chaine_depense", "fichier": classeur.name, "octets": classeur.stat().st_size}
    ]
    r = admin.post("/api/v1/admin/entrepot/", {"action": "relever"}, format="json")
    assert r.status_code == 200 and "1 fichier" in r.data["detail"]
    assert admin.get("/api/v1/admin/entrepot/").data["depot"]["en_attente"] == []


# ------------------------------------------------------------------ schémas JSON, JSON et XML


def test_schema_json_d_un_flux():
    s = schemas.schema_flux("telemo", "fait_marche")
    assert s["$schema"].endswith("2020-12/schema") and s["type"] == "object"
    assert "Numéro d'immatriculation du marché" in s["required"] and "Montant du marché TTC" in s["required"]
    assert "null" in s["properties"]["Date d'immatriculation"]["type"]
    assert s["properties"]["Date d'immatriculation"]["format"] == "date"
    assert "entente_directe" in s["properties"]["Mode de passation"]["description"]
    assert not any("bancaire" in c or "RCCM" in c for c in s["properties"])  # champs non repris
    assert set(schemas.schemas_source("telemo")) == {"fait_reservation_credit", "fait_marche", "fait_paiement_marche"}


def test_schemas_telechargeables(admin):
    r = admin.get("/api/v1/admin/sources/telemo/schemas/")
    assert r.status_code == 200 and "schemas-telemo.json" in r["Content-Disposition"]
    assert r.data["fait_paiement_marche"]["required"]


def test_fichier_json_multi_tables_et_lignes_hors_schema(tmp_path):
    """Un JSON {flux: lignes} se charge en un chargement ; les lignes non conformes sont écartées et comptées."""
    contenu = {
        "/reservations-credit": [{"Numéro de la réservation de crédit": "R1", "Montant réservé": 5 * MD}],
        "F4 Marchés": [
            {
                "Numéro d'immatriculation du marché": "M1",
                "Type de marché": "travaux",
                "Mode de passation": "aoo",
                "Autorité contractante": "A",
                "Montant du marché TTC": 4 * MD,
                "Titulaire : coordonnées bancaires (banque, RIB / IBAN)": "à ignorer",
            },
            {"Numéro d'immatriculation du marché": "M2", "Type de marché": "travaux"},  # clés obligatoires absentes
            {
                "Numéro d'immatriculation du marché": "M3",
                "Type de marché": "travaux",
                "Mode de passation": "aoo",
                "Autorité contractante": "A",
                "Montant du marché TTC": {"valeur": 1},  # type inattendu
            },
        ],
        "fait_paiement_marche": [
            {"Numéro d'immatriculation du marché": "M1", "Date paiement": "2026-05-02", "Montant paiement": MD}
        ],
        "inconnu": [{"x": 1}],
    }
    f = tmp_path / "Telemo en date du 30-06-2026.json"
    f.write_text(json.dumps(contenu), encoding="utf-8")
    ch = ExcelGenericConnector("telemo", None, f).executer()
    assert ch.statut == "succes", ch.message_erreur
    assert (FaitReservationCredit.objects.count(), FaitMarche.objects.count(), FaitPaiementMarche.objects.count()) == (
        1,
        1,
        1,
    )
    assert ch.detail["comptes"]["fait_marche"] == {"lues": 3, "chargees": 1, "rejetees": 2}
    assert ch.lignes_rejetees == 2
    controle = next(c for c in ch.detail["controles"] if c["code"] == "schema_json_fait_marche")
    assert controle["niveau"] == "avertissement" and not controle["reussi"] and controle["nombre"] == 2
    assert ch.fichier_archive.endswith(".json")


def test_fichier_xml(tmp_path):
    f = tmp_path / "Telemo en date du 30-06-2026.xml"
    f.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<paiements>
  <paiement><numero>M1</numero><date>2026-05-02</date><reference>BCRG-1</reference><montant>1000000000</montant></paiement>
  <paiement><numero>M2</numero><date>2026-05-09</date><reference>BCRG-2</reference><montant>250000000</montant></paiement>
</paiements>""",
        encoding="utf-8",
    )
    from apps.core.models import MappingColonnes

    telemo = Source.objects.get(code="telemo")
    for colonne, champ in (
        ("numero", "numero_immatriculation"),
        ("date", "date_paiement"),
        ("reference", "reference_paiement"),
        ("montant", "montant_paiement"),
    ):
        MappingColonnes.objects.filter(source=telemo, table_cible="fait_paiement_marche", champ_cible=champ).update(
            colonne_source=colonne
        )
    ch = ExcelGenericConnector("telemo", "fait_paiement_marche", f).executer()
    assert ch.statut == "succes", ch.message_erreur
    assert list(
        FaitPaiementMarche.objects.order_by("reference_paiement").values_list("montant_paiement", flat=True)
    ) == [
        1_000_000_000,
        250_000_000,
    ]
    assert FaitPaiementMarche.objects.first().date_paiement in (date(2026, 5, 2), date(2026, 5, 9))


def test_formats_acceptes_a_l_import(admin, tmp_path):
    f = tmp_path / "Telemo en date du 30-06-2026.json"
    f.write_text(json.dumps({"F5 Paiements": []}), encoding="utf-8")
    with open(f, "rb") as fh:
        r = admin.post("/api/v1/sources/telemo/import/", {"fichier": fh, "apercu": True}, format="multipart")
    assert r.status_code == 201 and r.data["statut"] == "apercu", r.data


# ------------------------------------------------------------------ événements AMQP


def test_evenement_publie_a_la_fin_d_un_chargement(settings, classeur):
    from kombu import Connection, Queue

    from etl.connecteurs.chaine_depense import ExcelChaineDepenseConnector

    settings.EVENEMENTS_AMQP_URL = "memory://"
    file_partenaire = Queue("partenaire", exchange=evenements.ECHANGE, routing_key="chargement.chaine_depense.*")
    with Connection("memory://") as connexion:
        file_partenaire(connexion.default_channel).declare()
        ch = ExcelChaineDepenseConnector(classeur).executer()
        ExcelChaineDepenseConnector(classeur).executer(apercu=True)  # un aperçu n'est pas annoncé
        recus = []
        with connexion.Consumer(file_partenaire, callbacks=[lambda corps, message: recus.append((corps, message))]):
            connexion.drain_events(timeout=2)
            with pytest.raises(TimeoutError):  # un seul message : rien d'autre dans la file
                connexion.drain_events(timeout=0.2)
    ((corps, message),) = recus
    assert message.delivery_info["routing_key"] == "chargement.chaine_depense.succes"
    assert corps["uuid"] == str(ch.uuid) and corps["empreinte_sha256"] == ch.empreinte_sha256
    assert corps["date_situation"] == ch.date_situation.isoformat() and corps["lignes_chargees"] == ch.lignes_chargees
    assert not any("montant" in cle for cle in corps)  # aucune donnée métier dans le message


def test_messagerie_absente_ou_en_panne_sans_effet(settings, classeur):
    from etl.connecteurs.chaine_depense import ExcelChaineDepenseConnector

    assert evenements.publier("chargement.x.succes", {}) is False  # non configurée
    settings.EVENEMENTS_AMQP_URL = "amqp://invite:invite@127.0.0.1:1//"  # port fermé
    assert ExcelChaineDepenseConnector(classeur).executer().statut == "succes"
