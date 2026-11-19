"""Couche de restitution : rafraîchissement des vues matérialisées et du cache après chargement."""

from __future__ import annotations

import logging

from django.core.cache import cache
from django.db import connection

logger = logging.getLogger(__name__)

# Ordre de rafraîchissement (les vues dépendantes en dernier).
VUES_MART = [
    "mv_depense_par_section_titre",
    "mv_depense_synthese",
    "mv_depense_mensuelle",
    "mv_restes_a_payer_anciennete",
    "mv_depense_procedures",
    "mv_depense_beneficiaires",
    "mv_investissement_projets",
    "mv_synthese_globale",
]

CLE_VERSION = "tdb:version_donnees"


def rafraichir_vues() -> None:
    with connection.cursor() as cursor:
        for vue in VUES_MART:
            cursor.execute(f"REFRESH MATERIALIZED VIEW mart.{vue}")


def version_donnees() -> str:
    # Le marqueur en base rend les imports d'un autre processus visibles même sans Redis.
    from django.db.models import Count, Max

    from apps.core.models import Chargement

    etat = Chargement.objects.filter(statut="succes").aggregate(dernier=Max("id"), nombre=Count("id"))
    return f"{cache.get_or_set(CLE_VERSION, 1, None)}:{etat['dernier']}:{etat['nombre']}"


def invalider_cache_api() -> None:
    """Toutes les clés de l'API incluent la version : l'incrémenter invalide le cache."""
    try:
        cache.incr(CLE_VERSION)
    except ValueError:
        cache.set(CLE_VERSION, 2, None)


def apres_chargement(chargement) -> None:
    rafraichir_vues()
    try:
        from apps.core.alertes import evaluer_alertes

        evaluer_alertes(chargement=chargement)
    except Exception:  # une règle défaillante ne doit pas annuler le chargement
        logger.exception("Évaluation des alertes en échec après le chargement %s", chargement.pk)
    invalider_cache_api()
