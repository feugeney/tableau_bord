"""Synthèse révisée (19/11/2026) : bandes de lecture, alertes visibles, sources sur leur propre situation."""

from datetime import date
from decimal import Decimal

import pytest

from apps.core.models import Alerte, Chargement, Source
from apps.core.synthese import BANDES
from apps.portefeuille.models import FaitDividende
from apps.referentiels.models import RefOrganisme, TypeOrganisme


@pytest.fixture
def cabinet(db):
    from tests.test_api import client_pour, utilisateur

    return client_pour(utilisateur("cabinet", "ministre_cabinet"))


def test_bandes_libelles_et_execution(charge, cabinet):
    d = cabinet.get("/api/v1/synthese/").json()["data"]
    assert [k["code"] for k in d["indicateurs"]] == list(BANDES)
    assert all(k["bande"] == BANDES[k["code"]] for k in d["indicateurs"])
    reste = next(k for k in d["indicateurs"] if k["code"] == "reste_a_payer")
    assert reste["libelle"] == "Reste à payer"  # même libellé que la page Dépenses
    assert d["execution"]["indicateurs"]["credit_actuel"] > 0
    assert d["execution"]["comparaison_n1"]["disponible"] is False  # un seul exercice chargé
    assert set(d["alertes_compte"]) == {"critique", "serieux", "vigilance"}


def test_alertes_sans_chargement_affichees(charge, cabinet):
    Alerte.objects.create(
        domaine="depense",
        source=Source.objects.get(code="chaine_depense"),
        severite="critique",
        titre="Alerte évaluée hors import",
        message="Sans chargement rattaché.",
    )
    d = cabinet.get("/api/v1/synthese/", {"exercice": charge.exercice}).json()["data"]
    assert "Alerte évaluée hors import" in [a["titre"] for a in d["alertes"]]
    assert d["alertes_compte"]["critique"] >= 1


def test_chaque_source_garde_sa_situation(charge, cabinet):
    """Sans exercice demandé, une source d'un autre exercice n'est plus vidée par celui de la Chaîne Dépense."""
    src = Source.objects.get(code="sysop")
    ch = Chargement.objects.create(
        source=src, exercice=charge.exercice - 1, date_situation=date(2026, 1, 31), statut="succes"
    )
    src.statut = "reel"
    src.save(update_fields=["statut"])
    o = RefOrganisme.objects.create(identifiant_etat="S1", nom="Société publique", type=TypeOrganisme.SOCIETE)
    FaitDividende.objects.create(
        organisme=o,
        vote=Decimal(4e9),
        encaisse=Decimal(3e9),
        exercice=ch.exercice,
        date_situation=ch.date_situation,
        source=src,
        chargement=ch,
    )
    d = cabinet.get("/api/v1/synthese/").json()["data"]
    k = next(k for k in d["indicateurs"] if k["code"] == "recettes_administratives")
    assert k["valeur"] == 3e9 and k["meta"]["exercice"] == charge.exercice - 1
    assert d["avertissements"]  # dates de situation différentes signalées
