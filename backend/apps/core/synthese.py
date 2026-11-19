"""Page Synthèse : indicateurs consolidés, alertes prioritaires, série mensuelle, état des sources."""

from __future__ import annotations

from django.db.models import Q
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView

from .audit import journaliser
from .filtres import Filtres, resoudre_filtres
from .models import SEVERITE_ORDRE, Alerte, Domaine, JournalAudit, Source, StatutAlerte
from .permissions import PERMISSIONS_DONNEES
from .reponses import SCHEMA_DONNEES, en_cache, meta


def _filtres(source_code: str, params) -> Filtres | None:
    f = resoudre_filtres(params, source_code)
    return f if f.date_situation else None


def _autorise(source, f, params):
    return params.get("mode_synthese", "decision") == "demonstration" or meta(source, f)["statut_source"] == "reel"


def _kpi(code, libelle, source_code, f, valeur=None, **champs):
    return {"code": code, "libelle": libelle, "valeur": valeur, "meta": meta(source_code, f), **champs}


def indicateurs_depense(params) -> list[dict]:
    from apps.depense import services

    f = _filtres("chaine_depense", params)
    if f is None:
        return [
            _kpi("depenses_engagees", "Dépenses engagées", "chaine_depense", None),
            _kpi("reste_a_payer", "Reste à payer", "chaine_depense", None),
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
            "Reste à payer",
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
            taux=perso["taux_ordonnancement_sur_credits"],
            reference=perso["credit_actuel"],
        ),
    ]


def indicateurs_recettes_detail(params) -> list[dict]:
    """Recettes par nature : fiscales (SAFIG), douanières (SYDONIA), administratives (dividendes SYSOP)."""
    from apps.douanes.services import totaux as douanes
    from apps.portefeuille.services import recettes_administratives
    from apps.recettes_fiscales.services import _recouvrement, somme

    from .regles import taux

    sortie = []
    f = _filtres("safig", params)
    kpi = {}
    if f and _autorise("safig", f, params):
        t = somme(_recouvrement(f), "recouvre", "objectif")
        kpi = {"valeur": t["recouvre"], "reference": t["objectif"], "taux": taux(t["recouvre"], t["objectif"])}
    sortie.append(_kpi("recettes_fiscales", "Recettes fiscales", "safig", f, **kpi))
    f = _filtres("sydonia", params)
    kpi = {}
    if f and _autorise("sydonia", f, params):
        t = douanes(f)
        kpi = {"valeur": t["recouvre"], "reference": t["objectif"], "taux": taux(t["recouvre"], t["objectif"])}
    sortie.append(_kpi("recettes_douanieres", "Recettes douanières", "sydonia", f, **kpi))
    f = _filtres("sysop", params)
    kpi = {}
    if f and _autorise("sysop", f, params):
        i = recettes_administratives(f)["indicateurs"]
        if i["nb_societes"]:
            kpi = {
                "valeur": i["dividendes_encaisses"],
                "reference": i["dividendes_votes"],
                "taux": i["taux_recouvrement"],
                "nombre": i["nb_societes"],
            }
    sortie.append(_kpi("recettes_administratives", "Recettes administratives (dividendes)", "sysop", f, **kpi))
    return sortie


def execution(params) -> dict | None:
    """Chaîne des montants de la dépense et comparaison avec l'exercice précédent à la même date."""
    from apps.depense import services
    from apps.depense.comparaisons import comparaison_n1

    f = _filtres("chaine_depense", params)
    if f is None or not _autorise("chaine_depense", f, params):
        return None
    return {"indicateurs": services.indicateurs(f), "comparaison_n1": comparaison_n1(f)}


def plan_engagement(params) -> dict | None:
    """Consommation du plafond du trimestre, seulement si le plan de l'exercice de la Chaîne Dépense est chargé."""
    from apps.depense.plan_engagement import page

    from .filtres import dernieres_situations

    f = _filtres("chaine_depense", params)
    if f is None:
        return None
    jour = next((d for e, d in dernieres_situations("plan_engagement") if e == f.exercice), None)
    if jour is None:
        return None
    d = page(Filtres(f.exercice, jour))
    if not d or not d["indicateurs"]["plafond"]:
        return None
    return {
        "exercice": f.exercice,
        "periode": d["libelle_periode"],
        "etat": d["entete"]["etat_libelle"],
        "plafond": d["indicateurs"]["plafond"],
        "engage_periode": d["indicateurs"]["engage_periode"],
        "taux": d["indicateurs"]["taux"],
        "nb_depassements": d["indicateurs"]["nb_depassements"],
    }


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
        if code == "recettes":
            from apps.douanes.services import totaux as douanes
            from apps.recettes_fiscales.services import _recouvrement, somme

            fd = _filtres("sydonia", params)
            composantes = [meta(source, f), meta("sydonia", fd)]
            if (
                f
                and fd
                and f.date_situation == fd.date_situation
                and _autorise(source, f, params)
                and _autorise("sydonia", fd, params)
            ):
                a, b = somme(_recouvrement(f), "recouvre", "objectif"), douanes(fd)
                from .regles import taux

                kpi = {"valeur": a["recouvre"] + b["recouvre"], "reference": a["objectif"] + b["objectif"]}
                kpi["taux"] = taux(kpi["valeur"], kpi["reference"])
            x = _kpi(code, libelle, source, f, **(kpi or {}))
            x["meta"]["composantes"] = composantes
            if not kpi:
                x["raison_indisponibilite"] = "SAFIG et SYDONIA : données autorisées et même période requises."
            sortie.append(x)
            continue
        if f is not None and _autorise(source, f, params):
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
        if f is None or not _autorise(source, f, params):
            continue
        if source == "chaine_depense":
            from apps.depense.services import mensuel

            for r in mensuel(f)["mois"]:
                lignes.append(
                    {
                        "indicateur": indicateur,
                        "source": source,
                        "mois": r["mois"],
                        "realise": r["montant_engage"],
                        "objectif": None,
                    }
                )
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


# Bandes de lecture de la page : trésorerie, recettes, exécution, dette.
BANDES = {
    "tresorerie": "tresorerie",
    "recettes_fiscales": "recettes",
    "recettes_douanieres": "recettes",
    "recettes_administratives": "recettes",
    "recettes": "recettes",
    "depenses_engagees": "execution",
    "reste_a_payer": "execution",
    "personnel_ordonnance": "execution",
    "dette": "dette",
}
DOMAINE_KPI = {
    "recettes_fiscales": Domaine.RECETTES_FISCALES,
    "recettes_douanieres": Domaine.DOUANES,
    "recettes_administratives": Domaine.PORTEFEUILLE,
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
        params = request.query_params.copy()
        mode = params.get("mode_synthese", "decision")
        if mode not in ("decision", "demonstration"):
            raise ValidationError({"mode_synthese": "Valeurs admises : decision, demonstration."})
        # Sans exercice demandé, chaque source garde sa dernière situation propre : imposer l'exercice de la
        # Chaîne Dépense à toutes vidait les autres blocs. Les dates de chaque source sont affichées.
        exercice_demande = params.get("exercice")
        kpis = indicateurs_autres(params) + indicateurs_recettes_detail(params) + indicateurs_depense(params)
        for k in kpis:
            if mode == "decision" and k["meta"]["statut_source"] != "reel":
                for champ in ("taux", "reference", "jours", "sous_seuil", "depasse"):
                    k.pop(champ, None)
                k["valeur"] = None
                k["raison_indisponibilite"] = "Données réelles non disponibles pour cette période."
            elif k.get("valeur") is None:
                k.setdefault("raison_indisponibilite", "Aucune donnée pour l'exercice et la situation choisis.")
        # Logique de lecture : trésorerie, puis recettes, puis exécution de la dépense, enfin dette.
        ordre = list(BANDES)
        kpis.sort(key=lambda k: ordre.index(k["code"]))
        for k in kpis:
            k["bande"] = BANDES[k["code"]]
        # Blocs hors du périmètre de l'utilisateur : masqués (valeurs non transmises).
        kpis = [
            (
                k
                if u.peut_voir(DOMAINE_KPI[k["code"]]) and (k["code"] != "recettes" or u.peut_voir(Domaine.DOUANES))
                else {
                    "code": k["code"],
                    "libelle": k["libelle"],
                    "masque": True,
                    "meta": k["meta"],
                    "bande": k["bande"],
                }
            )
            for k in kpis
        ]
        alertes = Alerte.objects.exclude(statut=StatutAlerte.TRAITEE).select_related("source")
        if mode == "decision":
            alertes = alertes.filter(source__statut="reel")
        if exercice_demande:
            alertes = alertes.filter(Q(chargement__exercice=int(exercice_demande)) | Q(chargement__isnull=True))
        if params.get("date_situation"):
            alertes = alertes.filter(date_situation=params["date_situation"])
        if not u.voit_tout():
            alertes = alertes.filter(domaine__in=[d for d in Domaine.values if u.peut_voir(d)])
        toutes = list(alertes[:500])
        compte = {sev: sum(1 for a in toutes if a.severite == sev) for sev in SEVERITE_ORDRE}
        alertes = sorted(toutes, key=lambda a: (SEVERITE_ORDRE.get(a.severite, 9), -a.id))[:12]
        from apps.depense.services import mensuel

        from .api import AlerteSerializer

        f_depense = _filtres("chaine_depense", params)
        rapprochement = (
            mensuel(f_depense)["rapprochement"]
            if f_depense and u.peut_voir(Domaine.DEPENSE) and _autorise("chaine_depense", f_depense, params)
            else None
        )
        dates = {k["meta"]["date_situation"] for k in kpis if not k.get("masque") and k.get("valeur") is not None}

        return {
            "meta": meta("chaine_depense", f_depense),
            "data": {
                "indicateurs": kpis,
                "alertes": AlerteSerializer(alertes, many=True).data,
                "serie_mensuelle": [l for l in serie_mensuelle(params) if u.peut_voir(DOMAINE_SERIE[l["indicateur"]])],
                "mode_synthese": mode,
                "avertissements": (
                    ["Les sources présentent des dates de situation différentes ; consulter chaque pastille."]
                    if len(dates) > 1
                    else []
                ),
                "rapprochement_mensuel": rapprochement,
                "alertes_compte": compte,
                "execution": execution(params) if u.peut_voir(Domaine.DEPENSE) else None,
                "plan_engagement": plan_engagement(params) if u.peut_voir(Domaine.TOFE) else None,
                "sources": etat_sources(),
            },
        }
