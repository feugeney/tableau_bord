"""Page Synthèse : indicateurs consolidés, alertes prioritaires, série mensuelle, état des sources."""

from __future__ import annotations

from rest_framework.views import APIView

from .audit import journaliser
from .filtres import Filtres, dernieres_situations
from .models import SEVERITE_ORDRE, Alerte, Domaine, JournalAudit, Source, StatutAlerte
from .permissions import PERMISSIONS_DONNEES
from .reponses import SCHEMA_DONNEES, en_cache, meta


def _filtres(source_code: str, params) -> Filtres | None:
    situations = dernieres_situations(source_code)
    if not situations:
        return None
    exercice = int(params["exercice"]) if params.get("exercice") else situations[0][0]
    d = next((d for e, d in situations if e == exercice), None)
    return Filtres(exercice, d) if d else None


def _kpi(code, libelle, source_code, f, valeur=None, **champs):
    return {"code": code, "libelle": libelle, "valeur": valeur, "meta": meta(source_code, f), **champs}


def indicateurs_depense(params) -> list[dict]:
    from apps.depense import services

    f = _filtres("chaine_depense", params)
    if f is None:
        return [
            _kpi("depenses_engagees", "Dépenses engagées", "chaine_depense", None),
            _kpi("reste_a_payer", "Reste à payer ajusté", "chaine_depense", None),
            _kpi("personnel_ordonnance", "Dépenses de personnel ordonnancées", "chaine_depense", None),
        ]
    i = services.indicateurs(f)
    perso = services.indicateurs(Filtres(f.exercice, f.date_situation, "personnel"))
    return [
        _kpi(
            "depenses_engagees",
            "Dépenses engagées",
            "chaine_depense",
            f,
            i["credit_engage"],
            taux=i["taux_engagement"],
            reference=i["credit_actuel"],
        ),
        _kpi(
            "reste_a_payer",
            "Reste à payer ajusté",
            "chaine_depense",
            f,
            i["paiement"]["reste_a_payer"],
            taux=i["paiement"]["paye_sur_ordonnance"],
        ),
        _kpi(
            "personnel_ordonnance",
            "Dépenses de personnel ordonnancées",
            "chaine_depense",
            f,
            perso["montant_ordonnance"],
            taux=perso["taux_ordonnancement"],
            reference=perso["credit_actuel"],
        ),
    ]


def indicateurs_autres(params) -> list[dict]:
    """Recettes, trésorerie et dette : calculés par leurs services dès qu'ils sont raccordés."""
    from importlib import import_module

    sortie = []
    for code, libelle, source, module in (
        ("recettes", "Recettes fiscales et douanières", "safig", "apps.recettes_fiscales.services"),
        ("tresorerie", "Trésorerie fin de période", "scie", "apps.tresor.services"),
        ("dette", "Encours de la dette", "dette", "apps.dette.services"),
    ):
        f = _filtres(source, params)
        kpi = None
        if f is not None:
            try:
                kpi = import_module(module).kpi_synthese(f)
            except (ImportError, AttributeError):
                kpi = None
        sortie.append(_kpi(code, libelle, source, f, **(kpi or {})))
    return sortie


def serie_mensuelle(params) -> list[dict]:
    from django.db import connection

    lignes = []
    for indicateur, source in (
        ("depense_engagee", "chaine_depense"),
        ("recettes_fiscales", "safig"),
        ("recettes_douanieres", "sydonia"),
    ):
        f = _filtres(source, params)
        if f is None:
            continue
        with connection.cursor() as c:
            c.execute(
                """SELECT mois, realise, objectif FROM mart.mv_synthese_globale
                   WHERE indicateur = %s AND exercice = %s AND date_situation = %s ORDER BY mois""",
                [indicateur, f.exercice, f.date_situation],
            )
            for mois, realise, objectif in c.fetchall():
                lignes.append(
                    {"indicateur": indicateur, "source": source, "mois": mois, "realise": realise, "objectif": objectif}
                )
    return lignes


def etat_sources() -> list[dict]:
    from .api import SourceSerializer

    return (
        SourceSerializer(Source.objects.exclude(domaine=Domaine.PREPARATION), many=True).data
        + SourceSerializer(Source.objects.filter(domaine=Domaine.PREPARATION), many=True).data
    )


DOMAINE_KPI = {
    "recettes": Domaine.RECETTES_FISCALES,
    "depenses_engagees": Domaine.DEPENSE,
    "reste_a_payer": Domaine.DEPENSE,
    "tresorerie": Domaine.TRESOR,
    "dette": Domaine.DETTE,
    "personnel_ordonnance": Domaine.DEPENSE,
}
DOMAINE_SERIE = {
    "depense_engagee": Domaine.DEPENSE,
    "recettes_fiscales": Domaine.RECETTES_FISCALES,
    "recettes_douanieres": Domaine.DOUANES,
}


class SyntheseView(APIView):
    permission_classes = PERMISSIONS_DONNEES
    cache_par_perimetre = True

    @SCHEMA_DONNEES
    def get(self, request):
        journaliser(request, JournalAudit.Action.CONSULTATION, objet="synthese")
        return self._get(request)

    @en_cache
    def _get(self, request):
        u = request.user
        kpis = indicateurs_autres(request.query_params) + indicateurs_depense(request.query_params)
        ordre = ["recettes", "depenses_engagees", "reste_a_payer", "tresorerie", "dette", "personnel_ordonnance"]
        kpis.sort(key=lambda k: ordre.index(k["code"]))
        # Blocs hors du périmètre de l'utilisateur : masqués (valeurs non transmises).
        kpis = [
            (
                k
                if u.peut_voir(DOMAINE_KPI[k["code"]])
                else {"code": k["code"], "libelle": k["libelle"], "masque": True, "meta": k["meta"]}
            )
            for k in kpis
        ]
        alertes = Alerte.objects.exclude(statut=StatutAlerte.TRAITEE).select_related("source")
        if not u.voit_tout():
            alertes = alertes.filter(domaine__in=[d for d in Domaine.values if u.peut_voir(d)])
        alertes = sorted(alertes[:200], key=lambda a: (SEVERITE_ORDRE.get(a.severite, 9), -a.id))[:12]
        from .api import AlerteSerializer

        return {
            "meta": meta("chaine_depense", _filtres("chaine_depense", request.query_params)),
            "data": {
                "indicateurs": kpis,
                "alertes": AlerteSerializer(alertes, many=True).data,
                "serie_mensuelle": [
                    l for l in serie_mensuelle(request.query_params) if u.peut_voir(DOMAINE_SERIE[l["indicateur"]])
                ],
                "sources": etat_sources(),
            },
        }
