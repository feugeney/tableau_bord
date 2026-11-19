from datetime import datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from django.test import override_settings

from apps.core.reponses import masquer_disponible
from etl.connecteurs.base import ErreurChargement
from etl.connecteurs.chaine_depense import OracleChaineDepenseConnector
from etl.connecteurs.oracle import connexion_lecture_seule


@override_settings(SOURCES_EXTERNES={"chaine_depense_oracle": {"dsn": "serveur:1526/service"}})
def test_configuration_incomplete_avant_toute_connexion():
    with patch("etl.connecteurs.oracle.oracledb.connect") as connect:
        with pytest.raises(ErreurChargement, match="incomplète"):
            with connexion_lecture_seule():
                pass
        connect.assert_not_called()


@override_settings(
    SOURCES_EXTERNES={
        "chaine_depense_oracle": {
            "dsn": "serveur:1526/service",
            "user": "lecture",
            "password": "secret-fictif",
            "thick": True,
            "client_lib_dir": "client19",
            "call_timeout_ms": 1234,
        }
    }
)
def test_client_thick_et_transaction_lecture_seule_avant_utilisation():
    cnx = MagicMock()
    with (
        patch("etl.connecteurs.oracle.oracledb.is_thin_mode", return_value=True),
        patch("etl.connecteurs.oracle.oracledb.init_oracle_client") as init,
        patch("etl.connecteurs.oracle.oracledb.connect") as connect,
    ):
        connect.return_value.__enter__.return_value = cnx
        with connexion_lecture_seule() as result:
            init.assert_called_once_with(lib_dir="client19")
            assert result is cnx
            assert cnx.call_timeout == 1234
            cnx.cursor.return_value.__enter__.return_value.execute.assert_called_once_with("SET TRANSACTION READ ONLY")
            assert "CONNECT_TIMEOUT" in connect.call_args.kwargs["dsn"]
        connect.return_value.__exit__.assert_called_once()


def test_exceptions_oracle_ne_sont_pas_persistantes():
    heure = datetime(2026, 11, 12, 14, 0, tzinfo=ZoneInfo("Africa/Conakry"))
    autorise = OracleChaineDepenseConnector(maintenant=heure, exception_ponctuelle=True, accepter_ecart_test=True)
    autorise.verifier_creneau()
    assert autorise.niveau_concordance == "avertissement"
    normal = OracleChaineDepenseConnector(maintenant=heure)
    assert normal.niveau_concordance == "bloquant"
    with pytest.raises(ErreurChargement, match="heures ouvrées"):
        normal.verifier_creneau()


def test_indicateur_absent_et_depassements_ne_sont_pas_affiches_comme_zero():
    brut = {"credit_actuel": 100, "credit_disponible": 0, "sections": [{"nb_lignes_depassement": 0}]}
    resultat = masquer_disponible(brut)
    assert resultat == {"credit_actuel": 100, "credit_disponible": None, "sections": [{"nb_lignes_depassement": None}]}
    assert brut["credit_disponible"] == 0
