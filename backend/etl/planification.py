"""Planification nocturne par source (Celery beat, django-celery-beat), configurable dans core_source."""

import json

from django_celery_beat.models import CrontabSchedule, PeriodicTask

from apps.core.models import Source, TypeConnecteur

# Seules les sources lues automatiquement (base ou API) sont planifiées ; les imports de fichiers sont manuels.
CONNECTEURS_AUTOMATIQUES = {TypeConnecteur.ORACLE_CHAINE_DEPENSE, TypeConnecteur.POSTGRES, TypeConnecteur.API}


def synchroniser_planification(source: Source) -> None:
    nom = f"chargement-{source.code}"
    if (
        source.code in ("sysop", "chaine_depense")
        or not source.planification_cron
        or source.connecteur not in CONNECTEURS_AUTOMATIQUES
    ):
        PeriodicTask.objects.filter(name=nom).delete()
        return
    minute, heure, jour, mois, jour_semaine = source.planification_cron.split()
    crontab, _ = CrontabSchedule.objects.get_or_create(
        minute=minute,
        hour=heure,
        day_of_month=jour,
        month_of_year=mois,
        day_of_week=jour_semaine,
        timezone="Africa/Conakry",
    )
    PeriodicTask.objects.update_or_create(
        name=nom,
        defaults={"task": "etl.charger_source", "crontab": crontab, "args": json.dumps([source.code]), "enabled": True},
    )


def planifier_releve_depots() -> None:
    """Relève périodique du dépôt de fichiers (SFTP)."""
    from django.conf import settings
    from django_celery_beat.models import IntervalSchedule

    intervalle, _ = IntervalSchedule.objects.get_or_create(
        every=settings.DEPOT_RELEVE_MINUTES, period=IntervalSchedule.MINUTES
    )
    PeriodicTask.objects.update_or_create(
        name="releve-depots",
        defaults={"task": "etl.relever_depots", "interval": intervalle, "crontab": None, "enabled": True},
    )


def synchroniser_tout() -> None:
    from apps.core.etl_admin import synchroniser_flux
    from apps.core.models import FluxETL

    for s in Source.objects.all():
        synchroniser_planification(s)
    for flux in FluxETL.objects.all():
        synchroniser_flux(flux)
    planifier_releve_depots()
