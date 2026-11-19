from datetime import date

from django.core.management.base import BaseCommand

from apps.core import demo


class Command(BaseCommand):
    help = (
        "Charge les données d'illustration (statut « demo ») des domaines non raccordés : SAFIG, SYDONIA, SCIE, "
        "dette, FUGAS, SICOM et SYSOP. Organismes et structures fictifs ; une source réelle n'est jamais écrasée."
    )

    def add_arguments(self, parser):
        parser.add_argument("--exercice", type=int, help="Défaut : exercice de la dernière situation Chaîne Dépense")
        parser.add_argument("--date-situation", type=date.fromisoformat, help="AAAA-MM-JJ")
        parser.add_argument(
            "--sources",
            nargs="*",
            choices=demo.SOURCES_DEMO + demo.SOURCES_DEMO_SUR_DEMANDE,
            help="Défaut : toutes sauf chaine_depense (raccordée en production), chargée seulement si nommée",
        )
        parser.add_argument("--supprimer", action="store_true", help="Retire toutes les données d'illustration")

    def handle(self, exercice=None, date_situation=None, sources=None, supprimer=False, **options):
        if supprimer:
            demo.supprimer()
            self.stdout.write(self.style.SUCCESS("Données d'illustration supprimées."))
            return
        for code, etat in demo.generer(exercice, date_situation, sources).items():
            self.stdout.write(f"  {code:<8} {etat}")
        self.stdout.write(self.style.SUCCESS("Données d'illustration chargées (statut « demo »)."))
