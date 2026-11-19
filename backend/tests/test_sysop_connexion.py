from io import StringIO
from unittest.mock import MagicMock, patch

import psycopg
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

PILOTE = "apps.core.management.commands.diagnostiquer_sysop.psycopg.connect"
URL_FICTIVE = "postgresql://lecteur:secret-fictif@serveur:5432/sysop"


@override_settings(SOURCES_EXTERNES={"sysop": {"url": ""}})
def test_configuration_absente_sans_connexion():
    with patch(PILOTE) as connect:
        with pytest.raises(CommandError, match="SYSOP_DATABASE_URL"):
            call_command("diagnostiquer_sysop")
        connect.assert_not_called()


@override_settings(SOURCES_EXTERNES={"sysop": {"url": URL_FICTIVE}})
def test_diagnostic_lecture_seule_sans_extraction():
    cnx = MagicMock()
    cursor = cnx.cursor.return_value.__enter__.return_value
    cursor.fetchone.side_effect = [("on",), (1,)]
    sortie = StringIO()
    with patch(PILOTE) as connect:
        connect.return_value.__enter__.return_value = cnx
        call_command("diagnostiquer_sysop", stdout=sortie)
        connect.assert_called_once_with(
            URL_FICTIVE,
            connect_timeout=10,
            options="-c default_transaction_read_only=on -c statement_timeout=5000",
        )
        assert [c.args[0] for c in cursor.execute.call_args_list] == ["SHOW transaction_read_only", "SELECT 1"]
        connect.return_value.__exit__.assert_called_once()
    assert "Connexion SYSOP OK" in sortie.getvalue()
    assert "secret-fictif" not in sortie.getvalue()


@pytest.mark.parametrize("reponses", [[("off",)], [("on",), (0,)]])
@override_settings(SOURCES_EXTERNES={"sysop": {"url": URL_FICTIVE}})
def test_reponse_inattendue_ou_transaction_non_protegee(reponses):
    with patch(PILOTE) as connect:
        cursor = connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = reponses
        with pytest.raises(CommandError):
            call_command("diagnostiquer_sysop")
        if reponses == [("off",)]:
            cursor.execute.assert_called_once_with("SHOW transaction_read_only")


@pytest.mark.parametrize(
    "erreur", [psycopg.OperationalError(URL_FICTIVE), psycopg.ProgrammingError(URL_FICTIVE), ValueError(URL_FICTIVE)]
)
@override_settings(SOURCES_EXTERNES={"sysop": {"url": URL_FICTIVE}})
def test_echec_sans_divulgation_des_parametres(erreur):
    sortie = StringIO()
    with patch(PILOTE, side_effect=erreur):
        with pytest.raises(CommandError) as exc:
            call_command("diagnostiquer_sysop", stdout=sortie)
    assert "secret-fictif" not in str(exc.value) + sortie.getvalue()
    assert "serveur" not in str(exc.value) + sortie.getvalue()
    assert "Connexion SYSOP impossible" in str(exc.value)
