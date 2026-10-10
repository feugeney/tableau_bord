"""Dette publique : encours, ratio dette / PIB (seuil CEDEAO), composition, échéancier."""

from __future__ import annotations

from apps.core import regles
from apps.core.domaines import bloc, chargements_actifs, depense, somme, ventiler
from apps.core.filtres import Filtres

from .models import FaitEcheancierDette, FaitEncoursDette, FaitIndicateurMacro


def _encours(f: Filtres) -> dict:
    ids = chargements_actifs("dette", f)
    enc = FaitEncoursDette.objects.filter(chargement_id__in=ids)
    total = somme(enc, "encours")["encours"]
    ext = somme(enc.filter(exterieure=True), "encours")["encours"]
    pib = (
        FaitIndicateurMacro.objects.filter(chargement_id__in=ids, indicateur="pib", annee=f.exercice)
        .values_list("valeur", flat=True)
        .first()
    )
    ratio = regles.ratio_dette_pib(total, pib)
    return {
        "encours": total,
        "exterieure": ext,
        "interieure": total - ext,
        "pib": pib,
        "ratio": ratio.ratio,
        "seuil": ratio.seuil,
        "depasse": ratio.depasse,
    }


def page(f: Filtres) -> dict:
    ids = chargements_actifs("dette", f)
    e = _encours(f)
    fc, titre1 = depense(f.exercice, titre="1")
    ech = list(
        FaitEcheancierDette.objects.filter(chargement_id__in=ids).values("annee", "exterieure", "principal", "interets")
    )
    annees: dict[int, dict] = {}
    for x in ech:
        a = annees.setdefault(x["annee"], {"annee": x["annee"], "principal": 0, "interets": 0})
        a["principal"] += x["principal"]
        a["interets"] += x["interets"]
    return {
        "indicateurs": e,
        "interets_engages": bloc("chaine_depense", fc, titre1["credit_engage"] if titre1 else None),
        "composition": ventiler(
            FaitEncoursDette.objects.filter(chargement_id__in=ids), "type_creancier__libelle", "encours"
        ),
        "echeancier": sorted(annees.values(), key=lambda a: a["annee"]),
    }


def kpi_synthese(f: Filtres) -> dict:
    e = _encours(f)
    return {"valeur": e["encours"], "taux": e["ratio"], "reference": e["seuil"], "depasse": e["depasse"]}
