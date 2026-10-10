"""Événements publiés sur la messagerie AMQP 0.9.1 (RabbitMQ) pour les systèmes partenaires.

Échange durable de type « topic » : un partenaire lie sa file à la clé qui l'intéresse, par exemple
`chargement.telemo.succes` ou `chargement.#`. Les messages sont persistants. La messagerie est facultative :
sans adresse configurée, rien n'est publié ; une panne de la messagerie ne fait jamais échouer un chargement.
"""

from __future__ import annotations

import logging

from django.conf import settings
from kombu import Connection, Exchange

logger = logging.getLogger(__name__)

ECHANGE = Exchange("tdb.evenements", type="topic", durable=True)


def publier(cle: str, corps: dict) -> bool:
    url = settings.EVENEMENTS_AMQP_URL
    if not url:
        return False
    try:
        with Connection(url, connect_timeout=5) as connexion:
            connexion.Producer(serializer="json").publish(
                corps,
                exchange=ECHANGE,
                routing_key=cle,
                declare=[ECHANGE],
                delivery_mode=2,  # persistant
                retry=True,
                retry_policy={"max_retries": 2, "interval_start": 0, "interval_step": 1},
            )
        return True
    except Exception:
        logger.exception("Publication AMQP impossible (%s)", cle)
        return False


def chargement_termine(chargement) -> bool:
    """Annonce la fin d'un chargement (réussi ou en échec) ; aucun montant ni donnée métier dans le message."""
    return publier(
        f"chargement.{chargement.source.code}.{chargement.statut}",
        {
            "uuid": str(chargement.uuid),
            "source": chargement.source.code,
            "statut": chargement.statut,
            "exercice": chargement.exercice,
            "date_situation": chargement.date_situation.isoformat() if chargement.date_situation else None,
            "lignes_chargees": chargement.lignes_chargees,
            "lignes_rejetees": chargement.lignes_rejetees,
            "empreinte_sha256": chargement.empreinte_sha256,
            "fin": chargement.fin.isoformat() if chargement.fin else None,
        },
    )
