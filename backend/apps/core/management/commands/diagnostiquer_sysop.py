"""Vérifie l'accès PostgreSQL à SYSOP sans extraction ni chargement."""

import psycopg
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Teste SYSOP en lecture seule (SELECT 1), sans importer de données."
    requires_system_checks = []

    def handle(self, **options):
        url = settings.SOURCES_EXTERNES.get("sysop", {}).get("url")
        if not url:
            raise CommandError("Connexion SYSOP non configurée : renseigner SYSOP_DATABASE_URL dans backend/.env.")

        try:
            with psycopg.connect(
                url,
                connect_timeout=10,
                options="-c default_transaction_read_only=on -c statement_timeout=5000",
            ) as cnx:
                with cnx.cursor() as cursor:
                    cursor.execute("SHOW transaction_read_only")
                    if cursor.fetchone() != ("on",):
                        raise CommandError("Diagnostic arrêté : la transaction SYSOP n'est pas en lecture seule.")
                    cursor.execute("SELECT 1")
                    if cursor.fetchone() != (1,):
                        raise CommandError("Réponse inattendue du serveur SYSOP.")
                self.stdout.write(self.style.SUCCESS("Connexion SYSOP OK ; transaction en lecture seule confirmée."))
                self.stdout.write("Aucune donnée métier extraite ; aucun chargement dans le dashboard.")
        except (psycopg.Error, ValueError):
            # Les messages du pilote peuvent contenir l'URL, les identifiants ou le serveur.
            raise CommandError(
                "Connexion SYSOP impossible. Vérifier SYSOP_DATABASE_URL, le réseau/VPN, "
                "le port PostgreSQL, les identifiants et les paramètres SSL."
            ) from None
