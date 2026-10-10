from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from openpyxl import Workbook

from apps.core.models import MappingColonnes, Source
from apps.paie.models import FaitPaie
from apps.referentiels.models import RefSection
from etl.connecteurs import fabrique
from etl.connecteurs.base import ErreurChargement
from etl.connecteurs.chaine_depense import ExcelChaineDepenseConnector, OracleChaineDepenseConnector
from etl.connecteurs.generique import ExcelGenericConnector, PostgresConnector, modele_fait

pytestmark = pytest.mark.django_db

TZ = ZoneInfo("Africa/Conakry")


def _mapping_fugas():
    src = Source.objects.get(code="fugas")
    for col, champ, typ, obl in [
        ("Mois", "mois", "entier", True),
        ("Code ministère", "section", "code", True),
        ("Effectif", "effectif", "entier", True),
        ("Masse brute", "masse_brute", "montant", True),
        ("Masse nette", "masse_nette", "montant", False),
    ]:
        MappingColonnes.objects.create(
            source=src, table_cible="fait_paie", colonne_source=col, champ_cible=champ, type_donnee=typ, obligatoire=obl
        )


def _fichier_paie(tmp_path, lignes, nom="paie en date du 31-08-2026.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.append(["Mois", "Code ministère", "Effectif", "Masse brute", "Masse nette", "Colonne ignorée"])
    for r in lignes:
        ws.append(r)
    chemin = tmp_path / nom
    wb.save(chemin)
    return chemin


def test_excel_generique_avec_mapping(tmp_path):
    _mapping_fugas()
    RefSection.objects.get_or_create(code="09", defaults={"libelle": "Économie"})
    chemin = _fichier_paie(
        tmp_path, [[8, "09", 1200, 15_000_000_000, 12_000_000_000, "x"], [8, "ZZ", 10, 1, 1, "x"]]
    )  # ministère inconnu : rejeté
    ch = ExcelGenericConnector("fugas", "fait_paie", chemin).executer()
    assert ch.statut == "succes", ch.message_erreur
    assert ch.date_situation == date(2026, 8, 31) and ch.exercice == 2026
    assert ch.lignes_chargees == 1 and ch.lignes_rejetees == 1
    p = FaitPaie.objects.get()
    assert p.section_id == "09" and p.effectif == 1200 and p.masse_brute == Decimal(15_000_000_000)
    assert Source.objects.get(code="fugas").statut == "reel"


def test_excel_generique_sans_mapping(tmp_path):
    chemin = _fichier_paie(tmp_path, [[8, "09", 1, 1, 1, ""]])
    ch = ExcelGenericConnector("fugas", "fait_paie", chemin).executer()
    assert ch.statut == "echec" and "mapping" in ch.message_erreur


def test_excel_generique_colonne_obligatoire(tmp_path):
    _mapping_fugas()
    wb = Workbook()
    wb.active.append(["Mois", "Effectif"])
    wb.active.append([8, 3])
    chemin = tmp_path / "paie en date du 31-08-2026.xlsx"
    wb.save(chemin)
    ch = ExcelGenericConnector("fugas", "fait_paie", chemin).executer()
    assert ch.statut == "echec" and "section" in ch.message_erreur


def test_csv_generique(tmp_path):
    _mapping_fugas()
    RefSection.objects.get_or_create(code="09")
    chemin = tmp_path / "paie en date du 31-08-2026.csv"
    chemin.write_text("Mois;Code ministère;Effectif;Masse brute\n8;09;5;1000\n", encoding="utf-8")
    ch = ExcelGenericConnector("fugas", "fait_paie", chemin).executer()
    assert ch.statut == "succes", ch.message_erreur


def test_modele_fait():
    assert modele_fait("fait_paie") is FaitPaie
    with pytest.raises(ErreurChargement):
        modele_fait("inconnue")


def test_postgres_non_configure():
    ch = PostgresConnector("sicom", "fait_patrimoine", "SELECT 1", date_situation=date(2026, 9, 1)).executer()
    assert ch.statut == "echec" and "non configurée" in ch.message_erreur
    assert Source.objects.get(code="sicom").statut == "non_raccorde"  # une source en échec ne change pas


def test_oracle_refuse_heures_ouvrees():
    c = OracleChaineDepenseConnector(maintenant=datetime(2026, 9, 28, 10, 0, tzinfo=TZ))
    with pytest.raises(ErreurChargement, match="heures ouvrées"):
        c.verifier_creneau()
    OracleChaineDepenseConnector(maintenant=datetime(2026, 9, 28, 23, 0, tzinfo=TZ)).verifier_creneau()
    OracleChaineDepenseConnector(maintenant=datetime(2026, 9, 27, 10, 0, tzinfo=TZ)).verifier_creneau()  # dimanche
    OracleChaineDepenseConnector(
        configuration={"replique": True}, maintenant=datetime(2026, 9, 28, 10, 0, tzinfo=TZ)
    ).verifier_creneau()


def test_oracle_non_configure():
    c = OracleChaineDepenseConnector(maintenant=datetime(2026, 9, 28, 23, 0, tzinfo=TZ))
    ch = c.executer()
    assert ch.statut == "echec" and "Oracle" in ch.message_erreur


def test_fabrique(tmp_path, classeur):
    cd = Source.objects.get(code="chaine_depense")
    assert isinstance(fabrique.connecteur_pour(cd, fichier=classeur), ExcelChaineDepenseConnector)
    fugas = Source.objects.get(code="fugas")
    assert isinstance(fabrique.connecteur_pour(fugas, fichier=classeur, table_cible="fait_paie"), ExcelGenericConnector)
    # Sans table cible : mode multi-onglets, qui échoue si aucun onglet du classeur n'est mappé.
    multi = fabrique.connecteur_pour(fugas, fichier=classeur)
    assert multi.table_cible is None
    ch = multi.executer()
    assert ch.statut == "echec" and "Au moins une table reconnue" in ch.message_erreur
    with pytest.raises(ErreurChargement):
        fabrique.connecteur_pour(Source.objects.get(code="pleb"))
    cd.connecteur = "oracle_chaine_depense"
    assert isinstance(fabrique.connecteur_pour(cd), OracleChaineDepenseConnector)


def test_tache_celery_source_non_raccordee():
    from etl.tasks import charger_source

    assert charger_source("pleb")["statut"] == "ignore"


def test_planification_suit_la_source():
    from django_celery_beat.models import PeriodicTask

    s = Source.objects.get(code="sicom")
    s.planification_cron = "30 1 * * *"
    s.save()
    t = PeriodicTask.objects.get(name="chargement-sicom")
    assert t.task == "etl.charger_source" and t.crontab.hour == "1"
    s.connecteur = "excel_generique"  # import manuel : plus de planification
    s.save()
    assert not PeriodicTask.objects.filter(name="chargement-sicom").exists()
