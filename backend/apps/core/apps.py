from django.apps import AppConfig
from django.db.models.signals import pre_migrate

SCHEMAS_ENTREPOT = ("staging", "ref", "dw", "mart")


def creer_schemas(using="default", **kwargs):
    """Crée les schémas de l'entrepôt avant toute migration (y compris base de test)."""
    from django.db import connections

    connection = connections[using]
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        for schema in SCHEMAS_ENTREPOT:
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")


class CoreConfig(AppConfig):
    name = "apps.core"
    verbose_name = "Socle"

    def ready(self):
        pre_migrate.connect(creer_schemas, sender=self, dispatch_uid="tdb_creer_schemas")
        from . import signals  # noqa: F401
