"""Données initiales idempotentes : sources, paramètres, référentiels de base, règles d'alerte."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from django.conf import settings
from django.db import transaction

from . import regles
from .models import Domaine, Parametre, Source, StatutSource, TypeConnecteur

FIXTURES = Path(settings.BASE_DIR) / "fixtures" / "referentiels"

REMARQUE_PLAN_ENGAGEMENT = "GDEP.TD_PLAN_ENG* en lecture seule : Administration → Flux ETL → Oracle · Plan d'engagement"
# Ancien texte, remplacé à l'initialisation s'il n'a pas été modifié par l'administrateur.
REMARQUE_PLAN_ENGAGEMENT_ANCIENNE = "GDEP.TD_PLAN_ENG* en lecture seule : commande import_plan_engagement"

SOURCES = [
    (
        "tofe",
        Domaine.TOFE,
        "TOFE — scénario d'illustration",
        "Cadre TOFE guinéen · démonstration",
        StatutSource.NON_RACCORDE,
        TypeConnecteur.AUCUN,
        None,
        "Scénario fictif autonome, sans consolidation des sources réelles",
    ),
    # code, domaine, application, structure, statut, connecteur, en production depuis, remarque
    (
        "chaine_depense",
        Domaine.DEPENSE,
        "Chaîne Dépense (Oracle)",
        "DNSI / DGB",
        StatutSource.NON_RACCORDE,
        TypeConnecteur.EXCEL_CHAINE_DEPENSE,
        None,
        "Extraction Excel (lot 1)",
    ),
    (
        # Page Pilotage : la permission est celle du domaine Pilotage (code « tofe »).
        "plan_engagement",
        Domaine.TOFE,
        "Chaîne Dépense — plan d'engagement (Oracle)",
        "DGB / DNB",
        StatutSource.NON_RACCORDE,
        TypeConnecteur.AUCUN,
        None,
        REMARQUE_PLAN_ENGAGEMENT,
    ),
    (
        "safig",
        Domaine.RECETTES_FISCALES,
        "SAFIG",
        "Direction générale des impôts",
        StatutSource.NON_RACCORDE,
        TypeConnecteur.EXCEL_GENERIQUE,
        None,
        "À raccorder",
    ),
    (
        "sydonia",
        Domaine.DOUANES,
        "SYDONIA",
        "Direction générale des douanes",
        StatutSource.NON_RACCORDE,
        TypeConnecteur.EXCEL_GENERIQUE,
        None,
        "À raccorder",
    ),
    (
        "scie",
        Domaine.TRESOR,
        "SCIE (Système comptable intégré de l'État)",
        "Trésor public",
        StatutSource.NON_RACCORDE,
        TypeConnecteur.EXCEL_GENERIQUE,
        None,
        "À raccorder",
    ),
    (
        "dette",
        Domaine.DETTE,
        "SIGAD",
        "Direction de la dette",
        StatutSource.NON_RACCORDE,
        TypeConnecteur.EXCEL_GENERIQUE,
        None,
        "À raccorder",
    ),
    (
        "sigpip",
        Domaine.INVESTISSEMENT,
        "SIGPIP",
        "Investissements publics",
        StatutSource.NON_RACCORDE,
        TypeConnecteur.EXCEL_GENERIQUE,
        None,
        "À raccorder (volet physique)",
    ),
    (
        "fugas",
        Domaine.PAIE,
        "FUGAS",
        "Gestion de la paie",
        StatutSource.NON_RACCORDE,
        TypeConnecteur.EXCEL_GENERIQUE,
        None,
        "À raccorder",
    ),
    (
        "sicom",
        Domaine.PATRIMOINE,
        "SICOM (comptabilité matière)",
        "DNSI / DNCM",
        StatutSource.NON_RACCORDE,
        TypeConnecteur.POSTGRES,
        date(2026, 5, 20),
        "En production depuis le 20/05/2026",
    ),
    (
        "sysop",
        Domaine.PORTEFEUILLE,
        "SYSOP (EPA et sociétés publiques)",
        "DGPEIP",
        StatutSource.NON_RACCORDE,
        TypeConnecteur.POSTGRES,
        date(2026, 8, 14),
        "En production depuis le 14/08/2026",
    ),
    (
        "telemo",
        Domaine.MARCHES_PUBLICS,
        "Telemo (marchés publics)",
        "Structure propriétaire à confirmer",
        StatutSource.NON_RACCORDE,
        TypeConnecteur.EXCEL_GENERIQUE,
        None,
        "À raccorder",
    ),
    (
        "sgpip",
        Domaine.INVESTISSEMENT,
        "SGPIP (projets d'investissement public)",
        "DGIP",
        StatutSource.NON_RACCORDE,
        TypeConnecteur.AUCUN,
        None,
        "À raccorder : décaissements, entrée en vigueur et clôture des projets (ex-Finex)",
    ),
    (
        "pleb",
        Domaine.PREPARATION,
        "PLEB",
        "À confirmer",
        StatutSource.NON_RACCORDE,
        TypeConnecteur.AUCUN,
        None,
        "Périmètre à préciser",
    ),
]


@transaction.atomic
def initialiser_sources() -> None:
    for ordre, (code, domaine, app, structure, statut, connecteur, depuis, remarque) in enumerate(SOURCES):
        Source.objects.get_or_create(
            code=code,
            defaults=dict(
                domaine=domaine,
                application=app,
                structure=structure,
                statut=statut,
                connecteur=connecteur,
                en_production_depuis=depuis,
                remarque=remarque,
                ordre=ordre,
                planification_cron="0 2 * * *" if connecteur != TypeConnecteur.AUCUN else "",
            ),
        )


@transaction.atomic
def initialiser_parametres() -> None:
    for code, (valeur, libelle, unite) in regles.PARAMETRES_DEFAUT.items():
        Parametre.objects.get_or_create(code=code, defaults={"valeur": valeur, "libelle": libelle, "unite": unite})
    regles.invalider_cache_parametres()


@transaction.atomic
def charger_referentiels() -> None:
    from apps.referentiels.models import (
        RefEtatDossier,
        RefNatureEconomique,
        RefRegulation,
        RefSection,
        RefTypeBudget,
        RefTypeProcedure,
    )

    nomenclature = json.loads((FIXTURES / "nomenclature.json").read_text(encoding="utf-8"))
    for t in nomenclature["titres"]:
        RefNatureEconomique.objects.update_or_create(
            code=t["code"], defaults={"libelle": t["libelle"], "niveau": 1, "titre": t["code"]}
        )
    for p in nomenclature["types_procedure"]:
        RefTypeProcedure.objects.update_or_create(
            libelle=p["libelle"],
            defaults={"paiement_hors_chaine": p["paiement_hors_chaine"], "description": p.get("description", "")},
        )
    for e in nomenclature["etats_dossier"]:
        RefEtatDossier.objects.update_or_create(
            libelle=e["libelle"], defaults={"engagement_valide": e["engagement_valide"]}
        )
    for c in nomenclature["regulations"]:
        RefRegulation.objects.get_or_create(code=c)
    for tb in nomenclature["types_budget"]:
        objet, _ = RefTypeBudget.objects.get_or_create(code=tb["code"], defaults={"libelle": tb["libelle"]})
        if not objet.libelle and tb["libelle"]:  # libellé laissé vide par une initialisation antérieure
            objet.libelle = tb["libelle"]
            objet.save(update_fields=["libelle"])

    sections = json.loads((FIXTURES / "sections.json").read_text(encoding="utf-8"))["sections"]
    for s in sections:
        RefSection.objects.update_or_create(
            code=s["code"],
            defaults={"libelle": s["libelle"], "libelle_court": s["libelle_court"], "type": s["type"]},
        )


# Pays et régions administratives, codes ISO 3166-2:GN. Les préfectures s'ajoutent avec les données réelles.
ZONES = [
    ("GN", "Guinée", "pays", None),
    ("GN-C", "Conakry", "region", "GN"),
    ("GN-B", "Boké", "region", "GN"),
    ("GN-D", "Kindia", "region", "GN"),
    ("GN-M", "Mamou", "region", "GN"),
    ("GN-L", "Labé", "region", "GN"),
    ("GN-F", "Faranah", "region", "GN"),
    ("GN-K", "Kankan", "region", "GN"),
    ("GN-N", "Nzérékoré", "region", "GN"),
]


def initialiser_dimensions() -> None:
    """Dimension temps et zones géographiques."""
    from apps.referentiels.models import RefZoneGeographique
    from apps.referentiels.temps import initialiser_calendrier

    initialiser_calendrier()
    for code, libelle, type_zone, parent in ZONES:
        RefZoneGeographique.objects.get_or_create(
            code=code, defaults={"libelle": libelle, "type": type_zone, "parent_id": parent}
        )


def initialiser_tout() -> None:
    initialiser_sources()
    initialiser_flux()
    initialiser_parametres()
    charger_referentiels()
    initialiser_dimensions()
    initialiser_telemo()
    from .alertes import initialiser_regles_alerte

    initialiser_regles_alerte()
    from etl.depots import preparer_dossiers
    from etl.planification import planifier_notification_alertes, planifier_releve_depots

    preparer_dossiers()
    planifier_releve_depots()
    planifier_notification_alertes()


@transaction.atomic
def initialiser_flux() -> None:
    """Installe le pilote sans activer de collecte ni modifier un flux déjà configuré."""
    from django.utils import timezone
    from django_celery_beat.models import PeriodicTask

    from .models import Chargement, FluxETL

    source = Source.objects.get(code="sysop")
    exercice = (
        Chargement.objects.filter(source=source, statut="succes", exercice__isnull=False)
        .exclude(detail__contains={"demo": True})
        .values_list("exercice", flat=True)
        .first()
    )
    _, cree = FluxETL.objects.get_or_create(
        code="sysop-portefeuille",
        defaults={
            "nom": "SYSOP · Portefeuille de l'État",
            "source": source,
            "profil": "sysop_portefeuille",
            "exercice": exercice or timezone.localdate().year,
        },
    )
    if cree:
        # L'ancien job ne fixait pas l'exercice. Le pilote reste manuel par défaut.
        source.planification_cron = ""
        source.save(update_fields=["planification_cron"])
        PeriodicTask.objects.filter(name="chargement-sysop").delete()

    source = Source.objects.get(code="chaine_depense")
    exercice = (
        Chargement.objects.filter(source=source, statut="succes", fichier="oracle://chaine_depense")
        .values_list("exercice", flat=True)
        .first()
    )
    _, cree = FluxETL.objects.get_or_create(
        code="oracle-chaine-depense",
        defaults={
            "nom": "Oracle · Chaîne Dépense",
            "source": source,
            "profil": "oracle_chaine_depense",
            "exercice": exercice or timezone.localdate().year,
        },
    )
    if cree:
        source.planification_cron = ""
        source.save(update_fields=["planification_cron"])
        PeriodicTask.objects.filter(name="chargement-chaine_depense").delete()

    # Plan d'engagement (GDEP.TD_PLAN_ENG*) : même connexion Oracle que la Chaîne Dépense, pilote manuel.
    source = Source.objects.get(code="plan_engagement")
    if source.remarque == REMARQUE_PLAN_ENGAGEMENT_ANCIENNE:
        source.remarque = REMARQUE_PLAN_ENGAGEMENT
        source.save(update_fields=["remarque"])
    exercice = (
        Chargement.objects.filter(source=source, statut="succes", exercice__isnull=False)
        .values_list("exercice", flat=True)
        .first()
    )
    # Lignes budgétaires de la Chaîne Dépense par l'API SIDOF-ENTREPOT (clé dans backend/.env), pilote manuel.
    FluxETL.objects.get_or_create(
        code="sidof-lignes-budgetaires",
        defaults={
            "nom": "SIDOF · Lignes budgétaires",
            "source": Source.objects.get(code="chaine_depense"),
            "profil": "sidof_lignes_budgetaires",
            "exercice": timezone.localdate().year,
        },
    )

    FluxETL.objects.get_or_create(
        code="oracle-plan-engagement",
        defaults={
            "nom": "Oracle · Plan d'engagement",
            "source": source,
            "profil": "oracle_plan_engagement",
            "exercice": exercice or timezone.localdate().year,
        },
    )


def requetes_oracle_preparees() -> dict[str, str]:
    """Correspondances SQL existantes, sans modifier les requêtes déjà configurées."""
    import sqlparse

    dossier = Path(settings.BASE_DIR) / "etl" / "sql" / "chaine_depense"
    return {
        nom: sqlparse.format((dossier / f"{nom}.sql").read_text(encoding="utf-8"), strip_comments=True).strip()
        for nom in ("situation", "engagements")
    }


# ---------------------------------------------------------------- Telemo (flux F3, F4, F5)
# Libellés des champs tels qu'ils figurent dans la description des flux Chaîne de dépenses ↔ Telemo.
# Non repris (minimisation) : RCCM, adresse et coordonnées bancaires (RIB/IBAN) du titulaire.
MAPPINGS_TELEMO = {
    ("fait_reservation_credit", "F3 Réservations"): [
        ("Numéro de la réservation de crédit", "numero_reservation", "code", True),
        ("Date création de la réservation", "date_creation", "date", False),
        ("Date validation de la réservation", "date_validation", "date", False),
        ("Identifiant de la ligne budgétaire (clé d'imputation complète)", "ligne_budgetaire", "code", False),
        ("Objet de la réservation", "objet", "texte", False),
        ("Autorité contractante", "autorite_contractante", "texte", False),
        ("Montant réservé", "montant_reserve", "montant", True),
        ("Devise", "devise", "code", False),
        ("Date du visa", "date_visa", "date", False),
    ],
    ("fait_marche", "F4 Marchés"): [
        ("Numéro d'immatriculation du marché", "numero_immatriculation", "code", True),
        ("Date d'immatriculation", "date_immatriculation", "date", False),
        ("Numéro de la réservation de crédit associée", "numero_reservation", "code", False),
        ("Objet du marché", "objet", "texte", False),
        ("Type de marché", "type_marche", "texte", True),
        ("Mode de passation", "mode_passation", "texte", True),
        ("Autorité contractante", "autorite_contractante", "texte", True),
        ("Titulaire : NIF", "titulaire_nif", "code", False),
        ("Titulaire : raison sociale", "titulaire", "texte", False),
        ("Montant du marché HT", "montant_ht", "montant", False),
        ("Montant du marché TTC", "montant_ttc", "montant", True),
        ("Montant de la TVA et autres taxes", "montant_taxes", "montant", False),
        ("Devise", "devise", "code", False),
        ("Date de signature du marché", "date_signature", "date", False),
        ("Date d'approbation", "date_approbation", "date", False),
        ("Délai / durée d'exécution", "delai_execution_jours", "entier", False),
        ("Modalités de paiement", "modalites_paiement", "texte", False),
    ],
    ("fait_paiement_marche", "F5 Paiements"): [
        ("Numéro d'immatriculation du marché", "numero_immatriculation", "code", True),
        ("Date paiement", "date_paiement", "date", True),
        ("Référence paiement", "reference_paiement", "code", False),
        ("Montant paiement", "montant_paiement", "montant", True),
    ],
}

CONFIGURATION_TELEMO = {
    "_note": "Mode d'échange à confirmer. Flux F1 (LFI/LFR) et F2 (mouvements) : couverts par la Chaîne Dépense.",
    "flux": [
        {"code": "F3", "chemin": "/reservations-credit", "table_cible": "fait_reservation_credit"},
        {"code": "F4", "chemin": "/marches-immatricules", "table_cible": "fait_marche"},
        {"code": "F5", "chemin": "/paiements", "table_cible": "fait_paiement_marche"},
    ],
}


@transaction.atomic
def initialiser_telemo() -> None:
    """Mappings des flux Telemo (sans écraser les réglages de l'administrateur) et configuration par défaut."""
    from .models import MappingColonnes

    source = Source.objects.get(code="telemo")
    if not source.configuration:
        source.configuration = CONFIGURATION_TELEMO
        source.save(update_fields=["configuration"])
    for (table, onglet), champs in MAPPINGS_TELEMO.items():
        for colonne, champ, type_donnee, obligatoire in champs:
            MappingColonnes.objects.get_or_create(
                source=source,
                table_cible=table,
                champ_cible=champ,
                defaults={
                    "onglet": onglet,
                    "colonne_source": colonne,
                    "type_donnee": type_donnee,
                    "obligatoire": obligatoire,
                },
            )
