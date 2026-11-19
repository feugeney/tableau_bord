"""Connexion partagée Oracle, sans écriture sur la source."""

from contextlib import contextmanager

import oracledb
from django.conf import settings

from .base import ErreurChargement


@contextmanager
def connexion_lecture_seule():
    conf = settings.SOURCES_EXTERNES["chaine_depense_oracle"]
    if not all(conf.get(k) for k in ("dsn", "user", "password")):
        raise ErreurChargement("Connexion Oracle incomplète (CHAINE_DEPENSE_ORACLE_DSN, USER, PASSWORD).")
    if conf.get("thick") and oracledb.is_thin_mode():
        options = {"lib_dir": conf["client_lib_dir"]} if conf.get("client_lib_dir") else {}
        oracledb.init_oracle_client(**options)
    params = oracledb.ConnectParams()
    params.parse_connect_string(conf["dsn"])
    params.set(tcp_connect_timeout=conf.get("connect_timeout", 10), retry_count=0)
    # Passer le descripteur complet pour que le client natif conserve les délais.
    with oracledb.connect(user=conf["user"], password=conf["password"], dsn=params.get_connect_string()) as cnx:
        cnx.call_timeout = conf.get("call_timeout_ms", 30000)
        with cnx.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")
        yield cnx
