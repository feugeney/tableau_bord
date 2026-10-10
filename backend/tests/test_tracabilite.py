"""Chantier 1 de la mise en conformité : dimension temps, zones géographiques, UUID des flux, zone brute."""

import hashlib
import json
import uuid
from datetime import date
from pathlib import Path

import pytest
from django.conf import settings

from apps.core.models import Chargement, JournalAudit
from apps.referentiels.models import DimTemps, RefZoneGeographique
from apps.referentiels.temps import assurer_calendrier
from etl import zone_brute
from etl.connecteurs.chaine_depense import ExcelChaineDepenseConnector

from .test_api import client_pour, utilisateur

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(db):
    return client_pour(utilisateur("dnsi", "dnsi_admin"))


# ------------------------------------------------------------------ dimensions


def test_dimension_temps():
    assert DimTemps.objects.filter(annee=2024).count() == 366  # année bissextile
    d = DimTemps.objects.get(date=date(2026, 8, 31))
    assert (d.annee, d.semestre, d.trimestre, d.mois, d.jour) == (2026, 2, 3, 8, 31)
    assert d.libelle_mois == "août 2026" and d.libelle_trimestre == "T3 2026"
    assert d.jour_semaine == 1 and d.semaine_iso == 36 and d.fin_de_mois
    assert not DimTemps.objects.get(date=date(2026, 8, 30)).fin_de_mois
    assert DimTemps.objects.filter(date__year=date.today().year + 5).exists()


def test_calendrier_etendu_sans_doublon():
    assert not DimTemps.objects.filter(annee=2040).exists()
    assert assurer_calendrier(2040, 2040) == 366
    assert assurer_calendrier(2040, 2040) == 0
    assert DimTemps.objects.filter(annee=2040).count() == 366


def test_zones_geographiques():
    regions = RefZoneGeographique.objects.filter(type="region")
    assert regions.count() == 8 and set(regions.values_list("parent_id", flat=True)) == {"GN"}
    assert RefZoneGeographique.objects.get(code="GN-K").libelle == "Kankan"


def test_zone_inconnue_rejetee_par_le_connecteur():
    """Référentiel commun fermé : un code de zone inconnu n'est pas créé à la volée."""
    from django.db import models

    from apps.referentiels.models import RefBureauDouane
    from etl.connecteurs.generique import MappingMixin

    champ = RefBureauDouane._meta.get_field("zone")
    assert isinstance(champ, models.ForeignKey)
    assert MappingMixin._resoudre_ref(champ, "GN-C", {}) == "GN-C"
    with pytest.raises(ValueError):
        MappingMixin._resoudre_ref(champ, "XX-9", {})
    assert not RefZoneGeographique.objects.filter(code="XX-9").exists()


# ------------------------------------------------------------------ identifiant et zone brute


def test_chargement_identifie_et_archive(charge, classeur):
    assert isinstance(charge.uuid, uuid.UUID) and charge.uuid.version == 4
    sha = hashlib.sha256(Path(classeur).read_bytes()).hexdigest()
    assert charge.empreinte_sha256 == sha
    assert charge.fichier_archive == f"brut/chaine_depense/{sha}.xlsx"
    archive = Path(settings.MEDIA_ROOT) / charge.fichier_archive
    assert archive.read_bytes() == Path(classeur).read_bytes()
    assert "deja_charge" not in charge.detail


def test_fichier_deja_charge_signale_et_stocke_une_fois(charge, classeur):
    second = ExcelChaineDepenseConnector(classeur).executer()
    assert second.statut == "succes" and second.uuid != charge.uuid
    assert second.detail["deja_charge"] == charge.id
    assert second.fichier_archive == charge.fichier_archive
    assert len(list((Path(settings.MEDIA_ROOT) / "brut" / "chaine_depense").glob(f"{charge.empreinte_sha256}*"))) == 1


def test_fichier_en_echec_conserve(tmp_path):
    """Un fichier rejeté reste consultable pour le diagnostic."""
    mauvais = tmp_path / "SC du 01-01-2026.xlsx"
    mauvais.write_bytes(b"ceci n'est pas un classeur")
    ch = ExcelChaineDepenseConnector(mauvais).executer()
    assert ch.statut == "echec" and ch.empreinte_sha256 == hashlib.sha256(mauvais.read_bytes()).hexdigest()
    assert (Path(settings.MEDIA_ROOT) / ch.fichier_archive).is_file()


def test_import_par_api_archive_et_journalise(admin, classeur):
    with open(classeur, "rb") as f:
        r = admin.post("/api/v1/sources/chaine_depense/import/", {"fichier": f}, format="multipart")
    assert r.status_code == 201, r.data
    ch = Chargement.objects.get(pk=r.data["id"])
    assert r.data["uuid"] == str(ch.uuid) and r.data["empreinte_sha256"] == ch.empreinte_sha256
    assert (Path(settings.MEDIA_ROOT) / ch.fichier_archive).is_file()
    assert not list((Path(settings.MEDIA_ROOT) / "depot" / "chaine_depense").glob("*"))  # dépôt provisoire purgé
    j = JournalAudit.objects.filter(action="import").latest("id")
    assert j.detail["uuid"] == str(ch.uuid) and j.detail["empreinte_sha256"] == ch.empreinte_sha256


def test_telechargement_du_fichier_brut(admin, charge, classeur):
    r = admin.get(f"/api/v1/admin/chargements/{charge.id}/fichier/")
    assert r.status_code == 200
    assert b"".join(r.streaming_content) == Path(classeur).read_bytes()
    assert Path(classeur).name in r["Content-Disposition"]
    assert JournalAudit.objects.filter(objet__contains="fichier brut").exists()
    # Réservé à l'administrateur.
    cabinet = client_pour(utilisateur("cab", "ministre_cabinet"))
    assert cabinet.get(f"/api/v1/admin/chargements/{charge.id}/fichier/").status_code == 403


def test_telechargement_sans_fichier(admin, charge):
    Chargement.objects.filter(pk=charge.pk).update(fichier_archive="")
    assert admin.get(f"/api/v1/admin/chargements/{charge.id}/fichier/").status_code == 404


def test_chemin_hors_zone_brute_refuse():
    with pytest.raises(ValueError):
        zone_brute.chemin_absolu("../config/settings/base.py")
    with pytest.raises(ValueError):
        zone_brute.chemin_absolu("depot/chaine_depense/x.xlsx")


def test_reponses_api_archivees(monkeypatch, settings):
    """Connecteur API : les réponses reçues sont conservées en JSON."""
    import io

    from apps.core.models import Source
    from etl.connecteurs.generique import ApiConnector

    class Reponse(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    settings.SOURCES_EXTERNES = {**settings.SOURCES_EXTERNES, "telemo": {"url": "https://telemo.test/api", "jeton": ""}}
    lignes = {
        "/reservations-credit": [{"Numéro de la réservation de crédit": "R1", "Montant réservé": 5}],
        "/marches-immatricules": [],
        "/paiements": [],
    }
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda r, timeout=0: Reponse(json.dumps(next(v for k, v in lignes.items() if k in r.full_url)).encode()),
    )
    ch = ApiConnector(
        "telemo", Source.objects.get(code="telemo").configuration, date_situation=date(2026, 6, 30)
    ).executer()
    assert ch.statut == "succes", ch.message_erreur
    assert ch.fichier_archive.endswith(".json")
    assert json.loads((Path(settings.MEDIA_ROOT) / ch.fichier_archive).read_text(encoding="utf-8")) == lignes
