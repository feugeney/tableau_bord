"""Contrats d'alimentation et administration des flux de la base centrale."""

import json
import re
from zoneinfo import ZoneInfo

from celery.schedules import crontab
from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone
from django_celery_beat.models import CrontabSchedule, PeriodicTask
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .admin_api import PERMISSIONS_ADMIN, connexion_configuree
from .audit import journaliser
from .models import (
    Alerte,
    Chargement,
    FluxETL,
    JournalAudit,
    Severite,
    Source,
    StatutAlerte,
    StatutChargement,
)

# Contrat fonctionnel : les noms physiques existants sont conservés pour assurer la continuité.
CONTRATS = [
    (
        "Synthèse",
        ["chaine_depense", "safig", "sydonia", "scie", "dette"],
        "Indicateurs consolidés",
        ["fait_situation_ligne", "fait_recouvrement_fiscal"],
        "Agrégats par périmètre autorisé",
    ),
    (
        "Dépenses",
        ["chaine_depense"],
        "Crédits et étapes de la dépense",
        ["fait_situation_ligne", "fait_engagement"],
        "Clé budgétaire, exercice et situation",
    ),
    (
        "Investissements",
        ["chaine_depense", "sigpip"],
        "Exécution des projets",
        ["fait_situation_ligne", "fait_engagement", "fait_avancement_projet"],
        "Projet, exercice et situation ; volet physique à raccorder",
    ),
    (
        "Recettes fiscales",
        ["safig"],
        "Objectifs et recouvrements",
        ["fait_recouvrement_fiscal"],
        "Impôt, centre, exercice et situation",
    ),
    (
        "Recettes douanières",
        ["sydonia"],
        "Droits, déclarations et recettes",
        ["fait_recette_douane", "fait_declaration", "fait_exoneration"],
        "Bureau, droit, exercice et situation",
    ),
    (
        "Trésorerie",
        ["scie", "chaine_depense"],
        "Encaissements et décaissements",
        ["fait_flux_tresorerie"],
        "Période et catégorie de flux",
    ),
    (
        "Dette publique",
        ["dette", "chaine_depense"],
        "Encours et service de dette",
        ["fait_encours_dette", "fait_echeancier_dette", "fait_indicateur_macro"],
        "Créancier et période",
    ),
    (
        "Masse salariale",
        ["fugas", "chaine_depense"],
        "Effectifs et dépenses de personnel",
        ["fait_paie", "fait_situation_ligne"],
        "Période et structure",
    ),
    ("Patrimoine", ["sicom"], "Biens et valeurs comptables", ["fait_patrimoine"], "Catégorie, structure et situation"),
    (
        "Portefeuille de l'État",
        ["sysop", "chaine_depense"],
        "Organismes, subventions, dividendes et validations",
        ["fait_subvention_epa", "fait_dividende", "fait_sante_financiere", "fait_gouvernance"],
        "Identifiant organisme SYSOP, exercice et situation",
    ),
    (
        "Marchés publics",
        ["telemo"],
        "Réservations, marchés et paiements",
        ["fait_reservation_credit", "fait_marche", "fait_paiement_marche"],
        "Identifiant du marché et référence de paiement",
    ),
    (
        "TOFE",
        ["tofe"],
        "Recettes, dépenses, soldes et financement",
        ["core_chargement.detail.scenario"],
        "Scénario fictif autonome ; contrat réel à valider",
    ),
]


FUSEAU_PLANIFICATION = "Africa/Conakry"


def synchroniser_flux(flux):
    nom = f"flux-etl-{flux.pk}"
    if not flux.actif or not flux.planification_cron:
        PeriodicTask.objects.filter(name=nom).delete()
        return
    minute, heure, jour, mois, semaine = flux.planification_cron.split()
    calendrier, _ = CrontabSchedule.objects.get_or_create(
        minute=minute,
        hour=heure,
        day_of_month=jour,
        month_of_year=mois,
        day_of_week=semaine,
        timezone=FUSEAU_PLANIFICATION,
    )
    PeriodicTask.objects.update_or_create(
        name=nom,
        defaults={
            "task": "etl.executer_flux",
            "crontab": calendrier,
            "args": "[]",
            "kwargs": json.dumps({"flux_id": flux.pk}),
            "enabled": True,
        },
    )


PROFILS_ORACLE = ("oracle_chaine_depense", "oracle_plan_engagement")


def executer_flux(flux, apercu=False, utilisateur=None, exception_horaire_ponctuelle=False, declenchement="manuel"):
    from etl.connecteurs.chaine_depense import OracleChaineDepenseConnector
    from etl.connecteurs.plan_engagement import PlanEngagementConnector
    from etl.connecteurs.sidof import SidofLignesBudgetairesConnector
    from etl.connecteurs.sysop import SysopPortefeuilleConnector

    if not apercu and not flux.actif:
        raise ValidationError("Ce flux est désactivé.")
    # Profil → (source attendue, connecteur attendu de la source). Le plan d'engagement lit la même base
    # Oracle que la Chaîne Dépense (connexion de backend/.env) : sa source n'a pas de connecteur propre, pour
    # qu'aucune planification nocturne « par source » ne lui applique le connecteur de la Chaîne Dépense.
    profils = {
        "sysop_portefeuille": ("sysop", "postgres"),
        "oracle_chaine_depense": ("chaine_depense", "oracle_chaine_depense"),
        "oracle_plan_engagement": ("plan_engagement", None),
        # Lignes budgétaires de la Chaîne Dépense par l'API SIDOF : chargées dans la source Chaîne Dépense
        # (pages Dépenses), quel que soit le connecteur Oracle ou Excel configuré pour cette source.
        "sidof_lignes_budgetaires": ("chaine_depense", None),
    }
    if flux.profil not in profils or flux.source.code != profils[flux.profil][0]:
        raise ValidationError("Ce profil ne dispose pas encore d'un connecteur validé.")
    attendu = profils[flux.profil][1]
    if attendu is not None and flux.source.connecteur != attendu:
        raise ValidationError("Le connecteur de la source ne correspond pas au profil ETL. Vérifier la connexion.")
    if flux.profil == "oracle_plan_engagement" and not settings.SOURCES_EXTERNES["chaine_depense_oracle"]["dsn"]:
        raise ValidationError(
            "Connexion Oracle de la Chaîne Dépense non configurée (CHAINE_DEPENSE_ORACLE_DSN dans backend/.env)."
        )
    if flux.profil == "sidof_lignes_budgetaires" and not settings.SOURCES_EXTERNES["sidof"]["cle"]:
        raise ValidationError("Clé de l'API SIDOF non configurée (SIDOF_API_KEY dans backend/.env).")
    if exception_horaire_ponctuelle and flux.profil not in PROFILS_ORACLE:
        raise ValidationError("L'exception horaire ne concerne que les flux Oracle de la Chaîne Dépense.")
    # Verrou partagé entre processus et flux visant la même source et le même exercice.
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s, %s)", [flux.source_id, flux.exercice])
        if not cursor.fetchone()[0]:
            raise ValidationError("Une exécution est déjà en cours pour cette source et cet exercice.")
    try:
        commun = dict(exercice=flux.exercice, date_situation=timezone.localdate(), utilisateur=utilisateur)
        if flux.profil == "oracle_chaine_depense":
            connecteur = OracleChaineDepenseConnector(
                configuration=flux.source.configuration,
                exception_ponctuelle=exception_horaire_ponctuelle,
                **commun,
            )
        elif flux.profil == "sidof_lignes_budgetaires":
            # Date de situation : dernière mise à jour des lignes dans SIDOF, pas la date du jour.
            connecteur = SidofLignesBudgetairesConnector(exercice=flux.exercice, utilisateur=utilisateur)
        elif flux.profil == "oracle_plan_engagement":
            connecteur = PlanEngagementConnector(
                replique=bool((flux.source.configuration or {}).get("replique", False)),
                exception_ponctuelle=exception_horaire_ponctuelle,
                **commun,
            )
        else:
            connecteur = SysopPortefeuilleConnector(**commun)
        ch = connecteur.executer(apercu=apercu)
        ch.detail = {**ch.detail, "flux_etl": flux.code, "declenchement": declenchement}
        ch.save(update_fields=["detail"])
        return ch
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s, %s)", [flux.source_id, flux.exercice])


TITRE_ECHEC_PROGRAMME = "Chargement programmé en échec : {nom}"


def suivre_execution_planifiee(flux, chargement=None, message=""):
    """Alerte sur l'échec d'un chargement programmé ; un succès retire l'alerte non encore vue."""
    titre = TITRE_ECHEC_PROGRAMME.format(nom=flux.nom)[:255]
    ouvertes = Alerte.objects.filter(regle__isnull=True, source=flux.source, titre=titre, statut=StatutAlerte.NOUVELLE)
    if chargement is not None and chargement.statut != StatutChargement.ECHEC:
        ouvertes.delete()
        return None
    reussi = (
        Chargement.objects.filter(source=flux.source, statut=StatutChargement.SUCCES)
        .exclude(date_situation=None)
        .first()
    )
    instant = timezone.localtime().strftime("%d/%m/%Y à %H:%M")
    cause = (message or (chargement.message_erreur if chargement else "") or "erreur non précisée").rstrip(". ")
    ouvertes.delete()
    return Alerte.objects.create(
        domaine=flux.source.domaine,
        source=flux.source,
        chargement=chargement,
        severite=Severite.SERIEUX,
        titre=titre,
        message=(
            f"Exécution programmée du {instant} (exercice {flux.exercice}) : "
            f"{cause}. "
            + (
                f"Les indicateurs restent ceux de la situation au {reussi.date_situation:%d/%m/%Y}."
                if reussi
                else "Aucune donnée n'a encore été chargée par ce flux."
            )
        ),
        valeur="Échec",
        action_recommandee="Vérifier la connexion à la source, puis relancer le flux depuis Administration → Flux ETL.",
        lien="/administration/flux-etl",
    )


class FluxSerializer(serializers.ModelSerializer):
    source = serializers.SlugRelatedField(slug_field="code", read_only=True)
    derniere_execution = serializers.SerializerMethodField()
    derniere_execution_planifiee = serializers.SerializerMethodField()
    prochaine_execution = serializers.SerializerMethodField()
    requetes = serializers.SerializerMethodField()

    class Meta:
        model = FluxETL
        fields = [
            "id",
            "code",
            "nom",
            "source",
            "profil",
            "exercice",
            "actif",
            "planification_cron",
            "derniere_execution",
            "derniere_execution_planifiee",
            "prochaine_execution",
            "requetes",
        ]
        read_only_fields = ["code", "source", "profil"]

    def get_requetes(self, flux):
        if flux.profil != "oracle_chaine_depense":
            return []
        return [
            {"table": table, "sql": sql, "champs": re.findall(r'\bAS\s+"([a-z_]+)"', sql, re.I)}
            for table, sql in (flux.source.configuration or {}).get("requetes", {}).items()
        ]

    def get_derniere_execution(self, flux):
        return (
            Chargement.objects.filter(detail__flux_etl=flux.code)
            .values("id", "statut", "fin", "lignes_chargees", "message_erreur")
            .first()
        )

    def get_derniere_execution_planifiee(self, flux):
        return (
            Chargement.objects.filter(detail__flux_etl=flux.code, detail__declenchement="planification")
            .values("id", "statut", "debut", "lignes_chargees", "message_erreur")
            .first()
        )

    def get_prochaine_execution(self, flux):
        from etl.planificateur import analyser, prochaine_occurrence

        if not flux.actif or not flux.planification_cron:
            return None
        maintenant = timezone.localtime(timezone=ZoneInfo(FUSEAU_PLANIFICATION))
        prochaine = prochaine_occurrence(analyser(flux.planification_cron), maintenant)
        return prochaine.isoformat() if prochaine else None

    def validate(self, attrs):
        from etl.connecteurs.chaine_depense import OracleChaineDepenseConnector

        flux = self.instance
        cron = attrs.get("planification_cron", flux.planification_cron if flux else "")
        if (
            settings.ORACLE_RESTRICTION_HEURES_OUVREES
            and flux is not None
            and cron
            and flux.profil in PROFILS_ORACLE
            and not (flux.source.configuration or {}).get("replique", False)
            and OracleChaineDepenseConnector.programmation_en_heures_ouvrees(cron)
        ):
            debut, fin = OracleChaineDepenseConnector.HEURES_OUVREES
            raise ValidationError(
                f"La Chaîne Dépense ne peut pas être interrogée en semaine entre {debut:%H:%M} et {fin:%H:%M} : "
                "choisir un horaire de nuit (ex. 2 h) ou le week-end. Une réplique déclarée lève cette restriction."
            )
        return attrs

    def validate_exercice(self, valeur):
        if settings.TDB_EXERCICE_TEST and valeur != settings.TDB_EXERCICE_TEST:
            raise ValidationError(f"Test limité à l'exercice {settings.TDB_EXERCICE_TEST}.")
        if not 2000 <= valeur <= timezone.localdate().year:
            raise ValidationError("Exercice compris entre 2000 et l'année courante attendu.")
        return valeur

    def validate_planification_cron(self, valeur):
        valeur = valeur.strip()
        # Une simple heure (« 11 h 30 », « 11:30 », « 2h ») vaut un chargement quotidien à cette heure.
        heure_seule = re.fullmatch(r"(\d{1,2})\s*(?:h|:)\s*(\d{2})?", valeur, re.I)
        if heure_seule and int(heure_seule[1]) < 24 and int(heure_seule[2] or 0) < 60:
            valeur = f"{int(heure_seule[2] or 0)} {int(heure_seule[1])} * * *"
        if valeur:
            try:
                minute, heure, jour, mois, semaine = valeur.split()
                crontab(minute=minute, hour=heure, day_of_month=jour, month_of_year=mois, day_of_week=semaine)
            except (ValueError, TypeError, KeyError) as exc:
                raise ValidationError(
                    "Programmation non reconnue. Indiquer une heure (ex. « 2 h 30 ») ou une expression cron à cinq "
                    "champs : minute heure jour mois jour-de-semaine (ex. « 30 2 * * * » chaque jour à 2 h 30)."
                ) from exc
        return valeur


class FluxViewSet(mixins.UpdateModelMixin, viewsets.ReadOnlyModelViewSet):
    queryset = FluxETL.objects.select_related("source")
    serializer_class = FluxSerializer
    permission_classes = PERMISSIONS_ADMIN
    pagination_class = None
    http_method_names = ["get", "patch", "post", "head", "options"]

    @transaction.atomic
    def perform_update(self, serializer):
        flux = serializer.save()
        synchroniser_flux(flux)
        journaliser(
            self.request,
            JournalAudit.Action.PARAMETRE,
            objet=f"configuration flux {flux.code}",
            detail=serializer.validated_data,
        )

    @action(detail=False, methods=["get"])
    def planificateur(self, request):
        from etl.planificateur import planificateur_actif

        return Response({"actif": planificateur_actif()})

    @action(detail=True, methods=["post"])
    def lancer(self, request, pk=None):
        apercu = serializers.BooleanField().run_validation(request.data.get("apercu", True))
        exception = serializers.BooleanField().run_validation(request.data.get("exception_horaire_ponctuelle", False))
        flux = self.get_object()
        ch = executer_flux(flux, apercu, request.user, exception_horaire_ponctuelle=exception)
        journaliser(
            request,
            JournalAudit.Action.PARAMETRE,
            objet=f"exécution flux {flux.code}",
            detail={"chargement": ch.pk, "apercu": apercu, "exception_horaire_ponctuelle": exception},
        )
        return Response(
            {
                "id": ch.pk,
                "statut": ch.statut,
                "lignes_lues": ch.lignes_lues,
                "lignes_chargees": ch.lignes_chargees,
                "message": ch.message_erreur,
                "detail": ch.detail,
            }
        )


class CatalogueView(APIView):
    permission_classes = PERMISSIONS_ADMIN

    def get(self, request):
        from .api import SourceSerializer

        sources = {s.code: s for s in Source.objects.all()}
        lignes = []
        for onglet, codes, donnees, tables, cle in CONTRATS:
            lignes.append(
                {
                    "onglet": onglet,
                    "donnees": donnees,
                    "tables": tables,
                    "cle": cle,
                    "sources": [
                        {**SourceSerializer(sources[c]).data, "connexion_configuree": connexion_configuree(sources[c])}
                        for c in codes
                        if c in sources
                    ],
                }
            )
        return Response(
            {
                "onglets": lignes,
                "flux": FluxSerializer(FluxETL.objects.all(), many=True).data,
                "note": (
                    "Les onglets lisent la base centrale. Une connexion configurée ne garantit "
                    "ni son accessibilité ni la fraîcheur des données."
                ),
            }
        )
