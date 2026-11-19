from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pandas as pd
import pytest

from apps.core.filtres import Filtres
from apps.core.models import Source
from apps.portefeuille.models import FaitDividende, FaitGouvernance, FaitSanteFinanciere, FaitSubventionEpa
from apps.portefeuille.services import page
from apps.referentiels.models import RefOrganisme
from etl.connecteurs.base import ErreurChargement
from etl.connecteurs.sysop import SysopPortefeuilleConnector, situation_organisme


@pytest.mark.parametrize("niveau", ["4", "6"])
def test_validation_et_resultat_net(niveau):
    validations = [{"validation_id": niveau, "date_rejet": None}]
    assert situation_organisme(validations, [{"mt_ligne_gnf": 0}]) == (True, 0, "equilibre")
    assert situation_organisme(validations, [{"mt_ligne_gnf": -1}]) == (True, -1, "deficitaire")
    assert situation_organisme(validations, [{"mt_ligne_gnf": 1}]) == (True, 1, "excedentaire")
    assert situation_organisme(validations, []) == (True, None, "indisponible")


def test_non_valide_ou_rejete_ne_produit_pas_un_equilibre():
    assert situation_organisme([], []) == (False, None, "non_transmis")
    assert situation_organisme([{"validation_id": "1", "date_rejet": None}], [])[0] is False
    assert situation_organisme([{"validation_id": "4", "date_rejet": date.today()}], [])[0] is False


def test_plusieurs_resultats_non_additionnes():
    with pytest.raises(ErreurChargement, match="Plusieurs résultats"):
        situation_organisme([], [{"mt_ligne_gnf": 10}, {"mt_ligne_gnf": 20}])


def donnees_test():
    return {
        "organismes": pd.DataFrame(
            [
                dict(no_op="SYS-EPA", sigle_op="EPA", lib_long_op="EPA réel", lib_court_op="EPA", type_op_id="EPA"),
                dict(no_op="SYS-SP", sigle_op="SP", lib_long_op="Société réelle", lib_court_op="SP", type_op_id="SP"),
            ],
            dtype=object,
        ),
        "subventions": pd.DataFrame([dict(organisme_id="SYS-EPA", prevu=0, paye=12)], dtype=object),
        "dividendes": pd.DataFrame([dict(organisme_id="SYS-SP", vote=100, encaisse=75)], dtype=object),
        "validations": pd.DataFrame(
            [
                dict(organisme_id="SYS-SP", type_etat="CPR", validation_id="6", date_rejet=None),
            ],
            dtype=object,
        ),
        "resultats": pd.DataFrame([dict(organisme_id="SYS-SP", mt_ligne_gnf=23)], dtype=object),
    }


@pytest.mark.django_db
def test_import_multitable_et_remplacement_sans_cumul():
    def extraire(connecteur):
        connecteur.informations_chargement = {"profil": "sysop_portefeuille"}
        return donnees_test()

    with (
        patch.object(SysopPortefeuilleConnector, "extract", extraire),
        patch.object(SysopPortefeuilleConnector, "apres_chargement"),
    ):
        for _ in range(2):
            ch = SysopPortefeuilleConnector(exercice=2025, date_situation=date(2026, 11, 13)).executer()
            assert ch.statut == "succes", ch.message_erreur
            assert ch.lignes_chargees == 6
    assert RefOrganisme.objects.filter(identifiant_etat__in=["SYS-EPA", "SYS-SP"]).count() == 2
    assert Source.objects.get(code="sysop").statut == "reel"
    assert FaitSubventionEpa.objects.get(chargement=ch).prevu == 0
    assert FaitDividende.objects.get(chargement=ch).encaisse == 75
    assert FaitSanteFinanciere.objects.get(chargement=ch, organisme__identifiant_etat="SYS-EPA").resultat is None
    assert FaitGouvernance.objects.get(chargement=ch, organisme__identifiant_etat="SYS-SP").etats_financiers_transmis
    d = page(Filtres(2025, date(2026, 11, 13)))
    assert d["indicateurs"]["epa"] == 1 and d["indicateurs"]["societes"] == 1
    assert d["indicateurs"]["dividendes_encaisses"] == Decimal(75)
    assert d["indicateurs"]["taux_transmission"] == Decimal("0.5")
    assert d["gouvernance"]["mandats_expires"] is None


@pytest.mark.django_db
def test_apercu_sans_creation_organismes_ni_faits():
    connecteur = SysopPortefeuilleConnector(exercice=2025, date_situation=date(2026, 11, 13))
    with patch.object(connecteur, "extract", return_value=donnees_test()):
        ch = connecteur.executer(apercu=True)
    assert ch.statut == "apercu"
    assert not RefOrganisme.objects.filter(identifiant_etat="SYS-EPA").exists()
    assert not FaitSanteFinanciere.objects.filter(chargement=ch).exists()


def test_resultats_ambigus_rejetes_avant_chargement():
    connecteur = SysopPortefeuilleConnector(exercice=2025)
    connecteur.donnees = donnees_test()
    connecteur.donnees["resultats"] = pd.concat([connecteur.donnees["resultats"]] * 2)
    assert not connecteur.validate().valide
