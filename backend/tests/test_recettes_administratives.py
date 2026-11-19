"""Recettes › Recettes administratives : dividendes SYSOP versés par les sociétés publiques."""

from datetime import date
from decimal import Decimal

import pytest

from apps.core.filtres import resoudre_filtres
from apps.core.models import Chargement, Source
from apps.portefeuille.models import FaitDividende
from apps.portefeuille.services import recettes_administratives
from apps.referentiels.models import RefOrganisme, TypeOrganisme

MD = Decimal(10**9)


@pytest.fixture
def dividendes(db):
    src = Source.objects.get(code="sysop")
    ch = Chargement.objects.create(source=src, exercice=2025, date_situation=date(2026, 11, 13), statut="succes")
    commun = dict(exercice=2025, date_situation=date(2026, 11, 13), source=src, chargement=ch)
    for i, (vote, encaisse) in enumerate([(5, 5), (4, 1), (3, 0), (0, 0)]):
        o = RefOrganisme.objects.create(identifiant_etat=f"S{i}", nom=f"Société {i}", type=TypeOrganisme.SOCIETE)
        FaitDividende.objects.create(organisme=o, vote=vote * MD, encaisse=encaisse * MD, **commun)
    return ch


def test_dividendes_votes_et_encaisses(dividendes):
    d = recettes_administratives(resoudre_filtres({}, "sysop"))
    i = d["indicateurs"]
    assert i["dividendes_votes"] == 12 * MD
    assert i["dividendes_encaisses"] == 6 * MD
    assert i["taux_recouvrement"] == Decimal("0.5")
    assert i["reste_a_encaisser"] == 6 * MD
    # La société sans dividende renseigné n'est pas comptée comme débitrice.
    assert i["nb_societes"] == 3
    assert [s["statut"] for s in d["societes"]] == ["verse", "partiel", "non_verse"]


def test_acces_reserve_au_domaine_portefeuille(dividendes):
    from tests.test_api import client_pour, utilisateur

    douanes = client_pour(utilisateur("douanes", "directeur", ["douanes"]))
    assert douanes.get("/api/v1/recettes-administratives/").status_code == 403
    portefeuille = client_pour(utilisateur("pf", "directeur", ["portefeuille"]))
    r = portefeuille.get("/api/v1/recettes-administratives/")
    assert r.status_code == 200 and r.json()["data"]["indicateurs"]["nb_societes"] == 3
