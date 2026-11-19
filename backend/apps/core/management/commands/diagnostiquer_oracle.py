"""Teste uniquement la connexion, sans extraction métier ni chargement."""

import oracledb
from django.core.management.base import BaseCommand, CommandError

from etl.connecteurs.base import ErreurChargement
from etl.connecteurs.oracle import connexion_lecture_seule


class Command(BaseCommand):
    help = "Teste Oracle en lecture seule (SELECT 1 FROM DUAL), sans importer de données."

    def handle(self, **options):
        try:
            with connexion_lecture_seule() as cnx:
                with cnx.cursor() as cursor:
                    cursor.execute("SELECT 1 FROM DUAL")
                    if cursor.fetchone() != (1,):
                        raise CommandError("Réponse inattendue du serveur Oracle.")
                self.stdout.write(self.style.SUCCESS(f"Connexion Oracle OK ; serveur {cnx.version}."))
                self.stdout.write("Mode : " + ("Thin" if oracledb.is_thin_mode() else "Thick"))
        except oracledb.Error as exc:
            # Ne pas journaliser les paramètres ni le message contenant des détails de connexion.
            error = exc.args[0] if exc.args else None
            code = getattr(error, "full_code", None) or "erreur pilote"
            raise CommandError(
                f"Connexion Oracle impossible ({code}). Vérifier le client, le réseau, le service et les identifiants."
            ) from None
        except ErreurChargement as exc:
            raise CommandError(str(exc)) from None
