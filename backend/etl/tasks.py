"""Tâches Celery : un chargement par source, planifiés par Celery beat."""

import logging

from celery import shared_task

from apps.core.models import Source, TypeConnecteur

logger = logging.getLogger(__name__)


@shared_task(name="etl.charger_source")
def charger_source(
    code_source: str,
    fichier: str | None = None,
    date_situation: str | None = None,
    exercice: int | None = None,
    utilisateur_id: int | None = None,
) -> dict:
    from datetime import date

    from etl.connecteurs import fabrique

    source = Source.objects.get(code=code_source)
    if source.connecteur == TypeConnecteur.AUCUN:
        return {"statut": "ignore", "raison": "source non raccordée"}
    connecteur = fabrique.connecteur_pour(
        source,
        fichier=fichier,
        exercice=exercice,
        date_situation=date.fromisoformat(date_situation) if date_situation else None,
        utilisateur_id=utilisateur_id,
    )
    ch = connecteur.executer()
    return {"chargement": ch.pk, "statut": ch.statut, "message": ch.message_erreur}


@shared_task(name="etl.relever_depots")
def relever_depots() -> list[dict]:
    """Charge les fichiers déposés par les partenaires (SFTP)."""
    from etl.depots import relever

    return relever()


@shared_task(name="etl.evaluer_alertes")
def evaluer_alertes_task(domaine: str | None = None) -> int:
    from apps.core.alertes import evaluer_alertes

    return len(evaluer_alertes(domaine=domaine))
