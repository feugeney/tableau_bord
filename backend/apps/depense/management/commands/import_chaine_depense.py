from datetime import date

from django.core.management.base import BaseCommand, CommandError

from etl.connecteurs.chaine_depense import ExcelChaineDepenseConnector


class Command(BaseCommand):
    help = "Charge une extraction Excel de la Chaîne Dépense (« SC de AAAA-AAAA en date du JJ-MM-AAAA.xlsx »)."

    def add_arguments(self, parser):
        parser.add_argument("fichier")
        parser.add_argument("--date-situation", type=date.fromisoformat, help="AAAA-MM-JJ (sinon : nom du fichier)")
        parser.add_argument("--exercice", type=int, help="Sinon : nom du fichier ou colonne Exercice")
        parser.add_argument("--apercu", action="store_true", help="Valide sans charger")

    def handle(self, fichier, date_situation=None, exercice=None, apercu=False, **options):
        connecteur = ExcelChaineDepenseConnector(fichier, exercice=exercice, date_situation=date_situation)
        ch = connecteur.executer(apercu=apercu)
        for c in ch.detail.get("controles", []):
            marque = "OK " if c["reussi"] else ("ÉCHEC" if c["niveau"] == "bloquant" else "ATTN")
            valeur = c["nombre"] if c["nombre"] is not None else (c["valeur"] or "")
            self.stdout.write(f"  [{marque}] {c['libelle']} {valeur}")
        self.stdout.write(
            f"Exercice {ch.exercice}, situation du {ch.date_situation} : {ch.lignes_lues} lues, "
            f"{ch.lignes_chargees} chargées, {ch.lignes_rejetees} rejetées en {ch.duree_secondes} s."
        )
        if ch.statut == "echec":
            raise CommandError(ch.message_erreur)
        self.stdout.write(self.style.SUCCESS(f"Chargement {ch.pk} : {ch.get_statut_display()}"))
