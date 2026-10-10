"""Journal d'audit : connexions, consultations, exports, imports, paramètres."""

import logging

from .models import JournalAudit

logger = logging.getLogger(__name__)


def _ip(request):
    if request is None:
        return None
    transmis = request.META.get("HTTP_X_FORWARDED_FOR")
    if transmis:
        return transmis.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def journaliser(request, action, objet="", detail=None, utilisateur=None, identifiant=""):
    if utilisateur is None and request is not None:
        u = getattr(request, "user", None)
        utilisateur = u if (u is not None and u.is_authenticated) else None
    try:
        JournalAudit.objects.create(
            utilisateur=utilisateur,
            identifiant=identifiant or (utilisateur.get_username() if utilisateur else ""),
            action=action,
            objet=objet[:255],
            detail=detail or {},
            adresse_ip=_ip(request),
        )
    except Exception:  # l'audit ne doit jamais faire échouer la requête
        logger.exception("Échec d'écriture du journal d'audit")
