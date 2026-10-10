import os

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from psycopg import sql

SCHEMAS_AGREGES = ("mart", "ref")
SCHEMA_DETAIL = "dw"


class Command(BaseCommand):
    help = (
        "Crée ou met à jour un compte PostgreSQL en lecture seule pour un outil de BI (Power BI, Metabase…). "
        "Par défaut, il lit les vues agrégées (mart) et les dimensions (ref) ; --detail ajoute les tables de "
        "faits (dw). Le mot de passe est lu dans une variable d'environnement, jamais en argument."
    )

    def add_arguments(self, parser):
        parser.add_argument("--role", default="tdb_bi", help="Nom du compte (défaut : tdb_bi)")
        parser.add_argument("--variable", default="BI_MOT_DE_PASSE", help="Variable d'environnement du mot de passe")
        parser.add_argument("--detail", action="store_true", help="Donne aussi accès aux tables de faits (dw)")
        parser.add_argument("--supprimer", action="store_true", help="Retire le compte et ses droits")

    def handle(self, role, variable, detail, supprimer, **options):
        if not role.replace("_", "").isalnum():
            raise CommandError("Nom de compte invalide (lettres, chiffres et « _ »).")
        compte = sql.Identifier(role)
        base = sql.Identifier(connection.settings_dict["NAME"])
        with connection.cursor() as c:
            c.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [role])
            existe = c.fetchone() is not None
            if supprimer:
                if existe:
                    c.execute(sql.SQL("DROP OWNED BY {}").format(compte))
                    c.execute(sql.SQL("DROP ROLE {}").format(compte))
                self.stdout.write(self.style.SUCCESS(f"Compte {role} retiré."))
                return
            mot_de_passe = os.environ.get(variable, "")
            if len(mot_de_passe) < 16:
                raise CommandError(f"Définir la variable {variable} (16 caractères au moins).")
            c.execute(
                sql.SQL("{} ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE").format(
                    sql.SQL("ALTER" if existe else "CREATE"), compte, sql.Literal(mot_de_passe)
                )
            )
            # Lecture seule imposée au compte lui-même, en plus des droits.
            c.execute(sql.SQL("ALTER ROLE {} SET default_transaction_read_only = on").format(compte))
            c.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(base, compte))
            for schema in (*SCHEMAS_AGREGES, SCHEMA_DETAIL):
                s = sql.Identifier(schema)
                if schema == SCHEMA_DETAIL and not detail:
                    c.execute(sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA {} FROM {}").format(s, compte))
                    c.execute(sql.SQL("REVOKE ALL ON SCHEMA {} FROM {}").format(s, compte))
                    c.execute(
                        sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA {} REVOKE SELECT ON TABLES FROM {}").format(
                            s, compte
                        )
                    )
                    continue
                c.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(s, compte))
                c.execute(sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA {} TO {}").format(s, compte))
                c.execute(
                    sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA {} GRANT SELECT ON TABLES TO {}").format(s, compte)
                )
        perimetre = "mart, ref" + (", dw" if detail else "")
        self.stdout.write(self.style.SUCCESS(f"Compte {role} prêt, en lecture seule sur : {perimetre}."))
