from datetime import date, datetime
from decimal import Decimal

import pytest

from etl import nettoyage as n


def test_codes_en_texte():
    assert n.code("01") == "01"
    assert n.code(" 000 ") == "000"
    assert n.code("00 ") == "00"
    assert n.code(5.0) == "5"
    assert n.code(None) == ""
    assert n.code(float("nan")) == ""


def test_montants():
    assert n.montant(517080000) == (Decimal(517080000), False)
    assert n.montant(None) == (Decimal(0), True)
    assert n.montant("") == (Decimal(0), True)
    assert n.montant("1 234,5") == (Decimal("1234.5"), False)
    assert n.montant(1.5) == (Decimal("1.5"), False)
    with pytest.raises(ValueError):
        n.montant("abc")


def test_dates():
    assert n.date_(datetime(2026, 8, 4)) == date(2026, 8, 4)
    assert n.date_("2026-08-04 00:00:00") == date(2026, 8, 4)
    assert n.date_("04/08/2026") == date(2026, 8, 4)
    assert n.date_(None) is None
    with pytest.raises(ValueError):
        n.date_("pas une date")


def test_entetes():
    assert n.cle_entete("crédits  engagés ") == "credits engages"
    assert n.cle_entete("Numéro engagement") == "numero engagement"


@pytest.mark.parametrize(
    "brut, attendu, court",
    [
        (
            "MINISTERE DE L'ECONOMIE, DES FINANCES ET DU BUDGET",
            "Ministère de l'Économie, des Finances et du Budget",
            "Économie, Finances et Budget",
        ),
        ("MINISTERES DES INFRASTRUCTURES", "Ministères des Infrastructures", "Infrastructures"),
        (
            "MINISTERE DE L ADMINISTRATION DU TERRITOIRE ET DE LA DECENTRALISATION",
            "Ministère de l'Administration du Territoire et de la Décentralisation",
            "Administration du Territoire et Décentralisation",
        ),
        ("MINISTERE DE LA DEFENSE NATIONALE", "Ministère de la Défense Nationale", "Défense Nationale"),
        ("COUR DES COMPTES", "Cour des Comptes", "Cour des Comptes"),
    ],
)
def test_libelles_sections(brut, attendu, court):
    assert n.titre_francais(brut) == attendu
    assert n.libelle_court_section(attendu) == court


def test_type_section():
    assert n.type_section("99", "DEPENSES COMMUNES") == "depenses_communes"
    assert n.type_section("14", "MINISTERES DES INFRASTRUCTURES") == "ministere"
    assert n.type_section("73", "COUR DES COMPTES") == "institution"


def test_beneficiaires_rapproches():
    a, b = "GAL BGD TRAORE Gassimou", "GAL BGD TRAOREGassimou"
    assert n.beneficiaire_cle(a) == n.beneficiaire_cle(b)
    assert n.beneficiaire_cle("Société  Généralé") == n.beneficiaire_cle("SOCIETE GENERALE")
    assert n.beneficiaire_alias("GAL  BGD  TRAORE Gassimou ") == "GAL BGD TRAORE GASSIMOU"
    assert n.beneficiaire_affiche("  GROUPE   LOUNADEV   ") == "GROUPE LOUNADEV"


def test_nom_fichier():
    assert n.infos_nom_fichier("SC de 2025-2025 en date du 15-09-2026.xlsx") == (2025, date(2026, 9, 15))
    assert n.infos_nom_fichier("SC des pp_du_dimanche 16 août 2026 22_10_49.xlsx") == (None, date(2026, 8, 16))
    assert n.infos_nom_fichier("export.xlsx") == (None, None)
