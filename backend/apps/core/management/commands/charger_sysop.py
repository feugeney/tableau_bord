from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.core.models import Source, TypeConnecteur
from etl.connecteurs.sysop import SysopPortefeuilleConnector


class Command(BaseCommand):
    help = "Charge le portefeuille SYSOP dans le dashboard, sans écriture sur SYSOP."

    def add_arguments(self, parser):
        parser.add_argument("--exercice", type=int, required=True)
        parser.add_argument("--date-situation", type=date.fromisoformat)
        parser.add_argument("--apercu", action="store_true")

    def handle(self, exercice, date_situation, apercu, **options):
        ch = SysopPortefeuilleConnector(exercice=exercice, date_situation=date_situation).executer(apercu=apercu)
        self.stdout.write(f"Chargement {ch.pk} : {ch.statut} ; {ch.lignes_chargees} faits chargés.")
        if ch.statut == "echec":
            raise CommandError(ch.message_erreur)
        if not apercu:
            source = Source.objects.get(code="sysop")
            source.connecteur = TypeConnecteur.POSTGRES
            source.configuration = {**source.configuration, "profil": "sysop_portefeuille"}
            source.save(update_fields=["connecteur", "configuration"])
