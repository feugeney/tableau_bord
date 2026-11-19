"""Planificateur intégré : exécute les tâches programmées sans Celery beat ni courtier de messages.

Les programmations saisies dans l'administration (flux ETL, sources, relève du dépôt) sont
enregistrées dans django-celery-beat (PeriodicTask). Sur un poste sans Redis ni RabbitMQ,
aucun service beat ne les lit : ce planificateur, lancé par Lancer.cmd ou par
`manage.py planificateur`, les relit toutes les 30 secondes et exécute dans le processus
celles dont l'échéance est atteinte.

Une échéance manquée (poste éteint, application arrêtée) n'est pas rattrapée : un rattrapage au
démarrage tomberait souvent en heures ouvrées, où la Chaîne Dépense refuse d'être interrogée.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import date, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from celery.schedules import crontab
from django.db import connection
from django.db.models import F
from django.utils import timezone

logger = logging.getLogger(__name__)

# Verrou consultatif à deux clés : une seule instance par base. La première clé est hors de la
# plage des identifiants de source, utilisés comme première clé par le verrou des flux ETL.
VERROU = (1_952_736_112, 1)
PAS_SECONDES = 30


class DejaActif(Exception):
    """Un autre planificateur détient déjà le verrou de cette base."""


def analyser(expression: str) -> crontab:
    """Expression cron à cinq champs → ensembles de valeurs (jours de semaine : 0 = dimanche)."""
    minute, heure, jour, mois, semaine = expression.split()
    return crontab(minute=minute, hour=heure, day_of_month=jour, month_of_year=mois, day_of_week=semaine)


def _jour_correspond(c: crontab, jour: date) -> bool:
    return jour.month in c.month_of_year and jour.day in c.day_of_month and jour.isoweekday() % 7 in c.day_of_week


def correspond(c: crontab, instant: datetime) -> bool:
    return _jour_correspond(c, instant.date()) and instant.hour in c.hour and instant.minute in c.minute


def prochaine_occurrence(c: crontab, apres: datetime, jours_max: int = 400) -> Optional[datetime]:
    """Première minute strictement postérieure à `apres`, dans le fuseau de `apres`."""
    debut = apres.replace(second=0, microsecond=0) + timedelta(minutes=1)
    heures, minutes = sorted(c.hour), sorted(c.minute)
    for n in range(jours_max):
        jour = debut.date() + timedelta(days=n)
        if not _jour_correspond(c, jour):
            continue
        for h in heures:
            for m in minutes:
                candidat = datetime(jour.year, jour.month, jour.day, h, m, tzinfo=debut.tzinfo)
                if candidat >= debut:
                    return candidat
    return None


def _crontab_modele(modele) -> crontab:
    return crontab(
        minute=modele.minute,
        hour=modele.hour,
        day_of_month=modele.day_of_month,
        month_of_year=modele.month_of_year,
        day_of_week=modele.day_of_week,
    )


def est_due(tache, maintenant: datetime) -> bool:
    if tache.start_time and tache.start_time > maintenant:
        return False
    if tache.expires and tache.expires <= maintenant:
        return False
    if tache.crontab_id:
        fuseau = ZoneInfo(str(tache.crontab.timezone))
        local = maintenant.astimezone(fuseau)
        if not correspond(_crontab_modele(tache.crontab), local):
            return False
        # Une seule exécution par minute programmée, même si le passage a lieu deux fois.
        return tache.last_run_at is None or tache.last_run_at.astimezone(fuseau) < local.replace(
            second=0, microsecond=0
        )
    if tache.interval_id:
        pas = timedelta(**{tache.interval.period: tache.interval.every})
        return tache.last_run_at is None or maintenant - tache.last_run_at >= pas
    return False


def _taches_celery() -> dict:
    from config.celery import app

    app.loader.import_default_modules()
    return app.tasks


def _executer(tache_nom: str, nom: str, args: list, kwargs: dict, fermer_connexion: bool) -> None:
    try:
        resultat = _taches_celery()[tache_nom](*args, **kwargs)
        logger.info("Tâche programmée %s terminée : %s", nom, resultat)
    except Exception:
        logger.exception("Tâche programmée %s en échec", nom)
    finally:
        if fermer_connexion:
            connection.close()


def planificateur_actif() -> bool:
    """Vrai si un planificateur détient le verrou sur la base courante."""
    with connection.cursor() as curseur:
        curseur.execute(
            "SELECT EXISTS (SELECT 1 FROM pg_locks WHERE locktype = 'advisory' AND granted"
            " AND classid::bigint = %s AND objid::bigint = %s AND objsubid = 2"
            " AND database = (SELECT oid FROM pg_database WHERE datname = current_database()))",
            list(VERROU),
        )
        return bool(curseur.fetchone()[0])


class Planificateur:
    def __init__(self, synchrone: bool = False):
        # En mode synchrone (contrôle, tests), les tâches s'exécutent l'une après l'autre.
        self.synchrone = synchrone
        self.en_cours: dict[int, threading.Thread] = {}
        self.verrou = False

    def verrouiller(self) -> None:
        if self.verrou and connection.connection is not None:
            return
        with connection.cursor() as curseur:
            curseur.execute("SELECT pg_try_advisory_lock(%s, %s)", list(VERROU))
            self.verrou = bool(curseur.fetchone()[0])
        if not self.verrou:
            raise DejaActif

    def liberer(self) -> None:
        if self.verrou and connection.connection is not None:
            with connection.cursor() as curseur:
                curseur.execute("SELECT pg_advisory_unlock(%s, %s)", list(VERROU))
        self.verrou = False

    def tour(self, maintenant: Optional[datetime] = None) -> list[str]:
        """Lance les tâches arrivées à échéance ; renvoie leurs noms."""
        from django_celery_beat.models import PeriodicTask

        self.verrouiller()
        maintenant = maintenant or timezone.now()
        lancees = []
        for tache in PeriodicTask.objects.filter(enabled=True).select_related("crontab", "interval"):
            fil = self.en_cours.get(tache.pk)
            if fil is not None and fil.is_alive():
                continue
            if not est_due(tache, maintenant):
                continue
            # Échéance consommée avant l'exécution : une tâche longue n'est pas relancée en boucle.
            PeriodicTask.objects.filter(pk=tache.pk).update(
                last_run_at=maintenant,
                total_run_count=F("total_run_count") + 1,
                enabled=not tache.one_off,
            )
            parametres = (tache.task, tache.name, json.loads(tache.args or "[]"), json.loads(tache.kwargs or "{}"))
            logger.info("Tâche programmée %s lancée", tache.name)
            lancees.append(tache.name)
            if self.synchrone:
                _executer(*parametres, fermer_connexion=False)
            else:
                fil = threading.Thread(target=_executer, args=(*parametres, True), name=tache.name)
                fil.start()
                self.en_cours[tache.pk] = fil
        return lancees

    def boucle(self, arret: Optional[threading.Event] = None) -> None:
        arret = arret or threading.Event()
        self.verrouiller()
        logger.info("Planificateur démarré (passage toutes les %s s).", PAS_SECONDES)
        try:
            while not arret.is_set():
                try:
                    self.tour()
                except DejaActif:
                    raise
                except Exception:
                    # Base redémarrée ou indisponible : reconnexion et reprise du verrou au passage suivant.
                    logger.exception("Passage du planificateur en échec")
                    connection.close()
                    self.verrou = False
                arret.wait(PAS_SECONDES)
        finally:
            for fil in self.en_cours.values():
                fil.join()
            self.liberer()
