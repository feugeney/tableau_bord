"""Exécute les chargements programmés dans l'administration, sans Celery beat ni courtier."""

from django.core.management.base import BaseCommand

from etl.planificateur import DejaActif, Planificateur


class Command(BaseCommand):
    help = "Planificateur intégré : lance les flux ETL et tâches programmés à leur échéance."

    def add_arguments(self, parser):
        parser.add_argument(
            "--une-fois",
            action="store_true",
            help="Un seul passage (tâches exécutées l'une après l'autre), puis arrêt.",
        )

    def handle(self, une_fois, **options):
        planificateur = Planificateur(synchrone=une_fois)
        try:
            if une_fois:
                lancees = planificateur.tour()
                planificateur.liberer()
                self.stdout.write(f"Tâches lancées : {', '.join(lancees) or 'aucune'}.")
            else:
                self.stdout.write("Planificateur démarré. Ctrl+C pour arrêter.")
                planificateur.boucle()
        except DejaActif:
            self.stdout.write("Un planificateur est déjà actif sur cette base : rien à faire.")
        except KeyboardInterrupt:
            self.stdout.write("Planificateur arrêté.")
