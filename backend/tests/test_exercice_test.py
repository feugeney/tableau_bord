from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from rest_framework.exceptions import ValidationError

from apps.core.etl_admin import FluxSerializer
from apps.core.filtres import dernieres_situations, resoudre_filtres
from etl.connecteurs.base import BaseConnector, ErreurChargement


@override_settings(TDB_EXERCICE_TEST=2025)
def test_situations_limitees_a_exercice_et_non_annee_de_situation():
    with patch("apps.core.filtres.connection") as connexion:
        curseur = connexion.cursor.return_value.__enter__.return_value
        curseur.fetchall.return_value = [(2026, date(2026, 11, 23)), (2025, date(2026, 9, 15))]
        assert dernieres_situations("chaine_depense") == [(2025, date(2026, 9, 15))]


@override_settings(TDB_EXERCICE_TEST=2025)
def test_source_sans_donnees_2025_ne_retombe_pas_sur_autre_exercice():
    with patch("apps.core.filtres.dernieres_situations", return_value=[]):
        filtres = resoudre_filtres({}, "sysop")
        assert (filtres.exercice, filtres.date_situation) == (2025, None)
        with pytest.raises(ValidationError):
            resoudre_filtres({"exercice": "2026"}, "sysop")


@override_settings(TDB_EXERCICE_TEST=2025)
def test_refus_import_et_configuration_autre_exercice():
    connecteur = MagicMock(exercice=2026)
    with pytest.raises(ErreurChargement):
        BaseConnector._verifier_exercice_test(connecteur)
    with pytest.raises(ValidationError):
        FluxSerializer().validate_exercice(2026)
    connecteur.exercice = 2025
    BaseConnector._verifier_exercice_test(connecteur)
    assert FluxSerializer().validate_exercice(2025) == 2025


@override_settings(TDB_EXERCICE_TEST=None)
def test_retrait_restriction_retablit_les_autres_exercices():
    BaseConnector._verifier_exercice_test(MagicMock(exercice=2026))
    with patch("apps.core.filtres.dernieres_situations", return_value=[(2026, date(2026, 11, 23))]):
        assert resoudre_filtres({}, "sysop").exercice == 2026
