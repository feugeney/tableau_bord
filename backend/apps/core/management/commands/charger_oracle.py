"""Chargement Oracle manuel avec options explicites pour les exceptions de test."""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.core.models import Source, TypeConnecteur
from etl.connecteurs.chaine_depense import OracleChaineDepenseConnector


class Command(BaseCommand):
    help = "Charge un exercice Oracle en lecture seule sur la source ; écrit uniquement dans l'entrepôt local."

    def add_arguments(self, parser):
        parser.add_argument("--exercice", type=int, required=True)
        parser.add_argument("--apercu", action="store_true")
        parser.add_argument("--exception-horaire-ponctuelle", action="store_true")
        parser.add_argument("--accepter-ecart-test", action="store_true")

    def handle(self, exercice, apercu, exception_horaire_ponctuelle, accepter_ecart_test, **options):
        dossier = Path(settings.BASE_DIR) / "etl" / "sql" / "chaine_depense"
        requetes = {nom: (dossier / f"{nom}.sql").read_text(encoding="utf-8") for nom in ("situation", "engagements")}
        connecteur = OracleChaineDepenseConnector(
            configuration={"requetes": requetes},
            exercice=exercice,
            date_situation=timezone.localdate(),
            exception_ponctuelle=exception_horaire_ponctuelle,
            accepter_ecart_test=accepter_ecart_test,
        )
        chargement = connecteur.executer(apercu=apercu)
        self.stdout.write(
            f"Chargement {chargement.pk} : {chargement.statut} ; "
            f"{chargement.lignes_lues} lignes lues ; {chargement.lignes_chargees} chargées."
        )
        if chargement.statut == "echec":
            raise CommandError(chargement.message_erreur)
        if not apercu:
            source = Source.objects.get(code="chaine_depense")
            source.connecteur = TypeConnecteur.ORACLE_CHAINE_DEPENSE
            source.configuration = {**source.configuration, "requetes": requetes}
            # Une connexion manuelle ne crée pas de planification automatique.
            source.planification_cron = ""
            source.save(update_fields=["connecteur", "configuration", "planification_cron"])
