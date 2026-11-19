from django.core.management.base import BaseCommand, CommandError

from etl.connecteurs.plan_engagement import PlanEngagementConnector, exercices_disponibles


class Command(BaseCommand):
    help = (
        "Charge le plan d'engagement de la Chaîne Dépense (GDEP.TD_PLAN_ENG*, lecture seule). "
        "Un chargement par exercice ; sans --exercice, tous les exercices ouverts dans Oracle."
    )

    def add_arguments(self, parser):
        parser.add_argument("--exercice", type=int, action="append", help="Répétable ; défaut : tous")
        parser.add_argument(
            "--replique", action="store_true", help="La base interrogée n'est pas la production (ex. devdep)"
        )
        parser.add_argument(
            "--exception-ponctuelle",
            action="store_true",
            help="Autorise une lecture aux heures ouvrées ; tracé dans le chargement",
        )
        parser.add_argument("--apercu", action="store_true", help="Valide sans charger")

    def handle(self, exercice=None, replique=False, exception_ponctuelle=False, apercu=False, **options):
        exercices = exercice or exercices_disponibles()
        if not exercices:
            raise CommandError("Aucun plan d'engagement dans la Chaîne Dépense.")
        echecs = 0
        for ex in exercices:
            ch = PlanEngagementConnector(ex, replique=replique, exception_ponctuelle=exception_ponctuelle).executer(
                apercu=apercu
            )
            for c in ch.detail.get("controles", []):
                if not c["reussi"]:
                    marque = "ÉCHEC" if c["niveau"] == "bloquant" else "ATTN"
                    self.stdout.write(f"  [{marque}] {c['libelle']} {c['nombre'] if c['nombre'] is not None else ''}")
            if ch.statut == "echec":
                echecs += 1
                self.stderr.write(f"Exercice {ex} : échec — {ch.message_erreur}")
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Exercice {ex} : chargement {ch.pk} ({ch.get_statut_display()}), "
                        f"{ch.lignes_chargees} lignes en {ch.duree_secondes} s."
                    )
                )
        if echecs == len(exercices):
            raise CommandError("Aucun exercice chargé.")
