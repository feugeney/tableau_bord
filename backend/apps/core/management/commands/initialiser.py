from django.core.management.base import BaseCommand

from apps.core.initialisation import initialiser_tout


class Command(BaseCommand):
    help = "Crée ou complète les sources, paramètres, référentiels de base et règles d'alerte (idempotent)."

    def handle(self, *args, **options):
        initialiser_tout()
        self.stdout.write(self.style.SUCCESS("Initialisation terminée."))
