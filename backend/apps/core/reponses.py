"""Enveloppe commune des réponses : { meta: {...}, data: ... } et cache Redis versionné."""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from decimal import Decimal
from functools import wraps
from typing import Any, Optional

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from .audit import journaliser
from .filtres import Filtres, resoudre_filtres, statut_source
from .models import JournalAudit, Source
from .permissions import PERMISSIONS_DONNEES

PARAMETRES_COMMUNS = [
    OpenApiParameter("exercice", int, description="Exercice budgétaire (défaut : dernier chargé)"),
    OpenApiParameter("date_situation", OpenApiTypes.DATE, description="Défaut : dernière date chargée"),
    OpenApiParameter("nature", str, enum=["personnel", "biens_services", "transferts", "investissement", "dette"]),
    OpenApiParameter("section", str, description="Code section (ex. 14)"),
    OpenApiParameter("paiement", str, enum=["ajuste", "brut"], description="Défaut : ajuste"),
]
SCHEMA_DONNEES = extend_schema(
    parameters=PARAMETRES_COMMUNS,
    responses={200: OpenApiTypes.OBJECT},
    description="Réponse : { meta: { source, date_situation, statut_source, genere_le }, data }",
)


def jsonable(v: Any) -> Any:
    """Decimal → float (montants GNF à 2 décimales, taux) ; dates ISO."""
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, dict):
        return {k: jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [jsonable(x) for x in v]
    return v


def meta(source_code: str, f: Optional[Filtres] = None, **extra) -> dict:
    src = Source.objects.filter(code=source_code).first()
    return {
        "source": source_code,
        "application": src.application if src else source_code,
        "date_situation": f.date_situation.isoformat() if f and f.date_situation else None,
        "exercice": f.exercice if f else None,
        "statut_source": statut_source(source_code),
        "genere_le": timezone.now().isoformat(),
        **extra,
    }


def en_cache(fonction):
    """Met en cache la réponse d'une méthode GET (15 min), clé = chemin + requête + version des données."""

    @wraps(fonction)
    def enveloppe(self, request, *args, **kwargs):
        from etl.mart import version_donnees

        brut = f"{request.path}?{request.META.get('QUERY_STRING', '')}|v{version_donnees()}"
        if getattr(self, "cache_par_perimetre", False):
            from .models import Domaine

            brut += "|" + ",".join(d for d in Domaine.values if request.user.peut_voir(d))
        cle = "tdb:api:" + hashlib.sha1(brut.encode()).hexdigest()
        donnees = cache.get(cle)
        if donnees is None:
            donnees = jsonable(fonction(self, request, *args, **kwargs))
            cache.set(cle, donnees, getattr(settings, "API_CACHE_SECONDES", 900))
        return Response(donnees)

    return enveloppe


class VueDomaine(APIView):
    """Vue de données : permissions par domaine, filtres communs, enveloppe meta, cache."""

    domaine: str = ""
    source_code: str = ""
    page: Optional[str] = None  # si défini : la consultation est journalisée
    permission_classes = PERMISSIONS_DONNEES

    def filtres(self, request) -> Filtres:
        return resoudre_filtres(request.query_params, self.source_code)

    def calculer(self, request, f: Filtres, **kwargs) -> Any:
        raise NotImplementedError

    @SCHEMA_DONNEES
    def get(self, request, **kwargs):
        if self.page:
            journaliser(request, JournalAudit.Action.CONSULTATION, objet=self.page)
        return self._get(request, **kwargs)

    @en_cache
    def _get(self, request, **kwargs):
        f = self.filtres(request)
        if f.date_situation is None:
            return {"meta": meta(self.source_code, f), "data": None}
        return {"meta": meta(self.source_code, f, paiement=f.paiement), "data": self.calculer(request, f, **kwargs)}
