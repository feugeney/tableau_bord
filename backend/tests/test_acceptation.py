"""Critères d'acceptation (section 12) sur l'extraction réelle.

Le fichier n'est pas versionné (données sensibles). Pour lancer ces tests :

    TDB_FICHIER_ACCEPTATION="/chemin/SC de 2025-2025 en date du 15-09-2026.xlsx" pytest tests/test_acceptation.py
"""

import os
from decimal import Decimal

import pytest

from apps.core import regles
from apps.core.filtres import resoudre_filtres
from apps.depense import services

FICHIER = os.environ.get("TDB_FICHIER_ACCEPTATION")

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.skipif(not FICHIER, reason="TDB_FICHIER_ACCEPTATION non défini"),
]


def mds(v):
    return regles.en_milliards(v, 2)


@pytest.fixture
def f(db):
    from etl.connecteurs.chaine_depense import ExcelChaineDepenseConnector

    ch = ExcelChaineDepenseConnector(FICHIER).executer()
    assert ch.statut == "succes", ch.message_erreur
    return resoudre_filtres({}, "chaine_depense"), ch


def test_nombre_de_lignes(f):
    _, ch = f
    comptes = ch.detail["comptes"]
    assert comptes["situation"]["chargees"] == 13_426
    assert comptes["engagements"]["chargees"] == 25_149
    assert comptes["operations"]["chargees"] == 16_220


def test_indicateurs_globaux(f):
    i = services.indicateurs(f[0])
    assert mds(i["credit_initial_lfi"]) == Decimal("36444.68")
    assert mds(i["credit_actuel"]) == Decimal("50657.15")
    assert mds(i["credit_engage"]) == Decimal("35944.63")
    assert round(i["taux_engagement"] * 100) == 71
    assert mds(i["montant_ordonnance"]) == Decimal("35250.45")
    assert mds(i["montant_paye"]) == Decimal("19790.62")
    assert mds(i["credit_disponible"]) == Decimal("12583.63")


def test_paiement_ajuste(f):
    p = services.indicateurs(f[0])["paiement"]
    assert mds(p["ordonnance"]) == Decimal("27286.96")
    assert mds(p["paye"]) == Decimal("19786.09")
    assert mds(p["reste_a_payer"]) == Decimal("7500.87")
    assert round(p["paye_sur_ordonnance"] * 100, 1) == Decimal("72.5")


def test_investissement(f):
    inv = services.synthese_investissement(f[0])
    assert regles.en_milliards(inv["credit_actuel"], 1) == Decimal("15674.9")
    assert regles.en_milliards(inv["credit_engage"], 1) == Decimal("4853.0")
    assert round(inv["taux_engagement"] * 100) == 31
    assert inv["nb_projets_sans_engagement"] == 145
    assert inv["nb_projets"] == 413  # « 145 sur 413 » : dénominateur à confirmer
    assert regles.en_milliards(inv["credits_projets_sans_engagement"], 1) == Decimal("8842.4")


def test_controles_de_lignes(f):
    assert services.lignes_en_depassement(f[0]) == 350
    assert services.chaine(f[0])["nb_lignes_liquide_sup_engage"] == 109


def test_infrastructures_sous_execution(f):
    infra = next(s for s in services.sections(f[0]) if s["libelle_court"] == "Infrastructures")
    assert regles.en_milliards(infra["credit_actuel"], 1) == Decimal("5774.2")
    assert round(infra["taux_engagement"] * 100) == 13
    assert infra["statut"]["libelle"] == "Sous-exécution"
