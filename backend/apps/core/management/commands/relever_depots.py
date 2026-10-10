from django.core.management.base import BaseCommand

from etl.depots import racine, relever


class Command(BaseCommand):
    help = "Charge les fichiers déposés par les partenaires dans le dépôt (SFTP), un dossier par source."

    def handle(self, **options):
        resultats = relever()
        for r in resultats:
            self.stdout.write(f"  {r['source']:<16} {r['fichier']} : {r['statut']} (chargement {r['chargement']})")
        self.stdout.write(self.style.SUCCESS(f"{len(resultats)} fichier(s) relevé(s) dans {racine()}."))
