"""Tâches Celery : un chargement par source, planifiés par Celery beat."""

import logging

from celery import shared_task

from apps.core.models import Source, TypeConnecteur

logger = logging.getLogger(__name__)


@shared_task(name="etl.executer_flux")
def executer_flux_task(flux_id):
    """Exécution programmée : un échec, même refusé avant l'extraction, lève une alerte."""
    from rest_framework.exceptions import ValidationError

    from apps.core.etl_admin import executer_flux, suivre_execution_planifiee
    from apps.core.models import FluxETL

    flux = FluxETL.objects.select_related("source").get(pk=flux_id)
    try:
        ch = executer_flux(flux, declenchement="planification")
    except ValidationError as exc:
        details = exc.detail if isinstance(exc.detail, list) else [exc.detail]
        message = " ".join(str(d) for d in details)
        suivre_execution_planifiee(flux, message=message)
        return {"statut": "refuse", "message": message}
    except Exception as exc:
        suivre_execution_planifiee(flux, message=f"erreur inattendue ({type(exc).__name__})")
        raise
    suivre_execution_planifiee(flux, ch)
    return {"chargement": ch.pk, "statut": ch.statut}


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
