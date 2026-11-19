"""Complète un ancien import depuis le même fichier brut, sans réimporter ses dépenses."""

import hashlib
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.models import Chargement, JournalAudit
from apps.depense.models import FaitAPAD, FaitEngagement, FaitSituationLigne
from etl.connecteurs.chaine_depense import CLE_LIGNE, MESURES_SITUATION, ExcelChaineDepenseConnector, _hash
from etl.nettoyage import code, montant


class Command(BaseCommand):
    help = "Complète les APAD et la couverture des champs d'un import Excel existant, par empreinte identique."

    def add_arguments(self, parser):
        parser.add_argument("--chargement", type=int, required=True)
        parser.add_argument("--fichier")
        parser.add_argument("--apercu", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        ch = (
            Chargement.objects.select_for_update()
            .filter(pk=options["chargement"], statut="succes", source__code="chaine_depense")
            .first()
        )
        if not ch:
            raise CommandError("Chargement réussi de la Chaîne Dépense introuvable.")
        if ch.fichier.startswith(("oracle://", "postgresql://")):
            raise CommandError("Cette commande complète uniquement un import Excel.")
        fichier = Path(options["fichier"]) if options["fichier"] else Path(settings.MEDIA_ROOT) / ch.fichier_archive
        if not fichier.is_file() or not ch.empreinte_sha256:
            raise CommandError("Fichier brut ou empreinte de contrôle absent.")
        if hashlib.sha256(fichier.read_bytes()).hexdigest() != ch.empreinte_sha256:
            raise CommandError("Empreinte différente : les données historiques ne sont pas modifiées.")
        connecteur = ExcelChaineDepenseConnector(fichier, exercice=ch.exercice, date_situation=ch.date_situation)
        connecteur.donnees = connecteur.extract()
        sc = connecteur.donnees.get("situation")
        eng = connecteur.donnees.get("engagements")
        if (
            sc is None
            or eng is None
            or len(sc) != FaitSituationLigne.objects.filter(chargement=ch).count()
            or len(eng) != FaitEngagement.objects.filter(chargement=ch).count()
        ):
            raise CommandError("Le contenu du fichier ne correspond pas aux effectifs historiques.")
        manquants = {}
        for row in sc.to_dict("records"):
            cle = _hash(code(row.get(k)) for k in CLE_LIGNE)
            if cle in manquants:
                raise CommandError("Clés budgétaires ambiguës : complément refusé.")
            manquants[cle] = [m for m in MESURES_SITUATION if montant(row.get(m))[1]]
        faits = list(FaitSituationLigne.objects.filter(chargement=ch))
        if {r.cle_ligne for r in faits} != set(manquants):
            raise CommandError("Les clés budgétaires ne correspondent pas à l'import historique.")
        apad = connecteur.donnees.get("apad")
        nouvelles = connecteur.preparer_apad(apad) if apad is not None else []
        existantes = FaitAPAD.objects.filter(chargement=ch).count()
        if existantes and existantes != len(nouvelles):
            raise CommandError("Des APAD différentes existent déjà pour cet import.")
        if options["apercu"]:
            self.stdout.write(f"Empreinte et clés vérifiées ; {len(nouvelles)} lignes APAD ; aucune écriture.")
            return
        if apad is not None and not existantes:
            connecteur.charger_apad(ch)
        for fait in faits:
            fait.attributs = {**fait.attributs, "_mesures_absentes": manquants[fait.cle_ligne]}
        FaitSituationLigne.objects.bulk_update(faits, ["attributs"], batch_size=500)
        ch.detail = {**ch.detail, "colonnes_extraites": {k: list(df.columns) for k, df in connecteur.donnees.items()}}
        if apad is not None:
            ch.detail.setdefault("comptes", {})["apad"] = {
                "lues": len(nouvelles),
                "chargees": len(nouvelles),
                "rejetees": 0,
            }
        ch.lignes_chargees = sum(v.get("chargees", 0) for v in ch.detail.get("comptes", {}).values())
        ch.lignes_lues = sum(v.get("lues", 0) for v in ch.detail.get("comptes", {}).values())
        ch.save(update_fields=["detail", "lignes_chargees", "lignes_lues"])
        JournalAudit.objects.create(
            action=JournalAudit.Action.IMPORT,
            objet=f"complément-dépense:{ch.pk}",
            detail={"apad": len(nouvelles), "empreinte_verifiee": True},
        )
        transaction.on_commit(cache.clear)
        self.stdout.write(self.style.SUCCESS("Complément enregistré ; montants historiques de dépense conservés."))
