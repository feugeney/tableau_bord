"""Trésorerie (SCIE) : flux, solde en jours de décaissements, délai de paiement, TOFE simplifié."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db.models import Avg, Sum
from django.db.models.functions import ExtractMonth

from apps.core import regles
from apps.core.domaines import bloc, chargements_actifs, depense, filtres_source, somme
from apps.core.filtres import Filtres

from .models import FaitDelaiPaiement, FaitFluxTresorerie, FaitTofe


def _flux(f: Filtres):
    return FaitFluxTresorerie.objects.filter(chargement_id__in=chargements_actifs("scie", f))


def _solde(f: Filtres) -> dict:
    flux = _flux(f)
    dernier = flux.order_by("-jour").first()
    tot = somme(flux, "encaissements", "decaissements")
    # Jours calendaires de la période (le seuil est exprimé en mois calendaires de décaissements).
    nb_jours = (dernier.jour - date(dernier.jour.year, 1, 1)).days + 1 if dernier else 0
    mois = flux.annotate(m=ExtractMonth("jour")).values("m").distinct().count() or 1
    decaissement_mensuel = tot["decaissements"] / mois
    solde = dernier.solde if dernier else Decimal(0)
    return {
        "solde": solde,
        "jour": dernier.jour if dernier else None,
        "jours_de_decaissements": regles.jours_de_decaissements(solde, tot["decaissements"], nb_jours),
        "decaissement_mensuel_moyen": decaissement_mensuel,
        "sous_seuil": regles.tresorerie_sous_seuil(solde, decaissement_mensuel),
        **tot,
    }


def page(f: Filtres) -> dict:
    s = _solde(f)
    flux = _flux(f).annotate(m=ExtractMonth("jour"))
    mensuel = list(
        flux.values("m").annotate(encaissements=Sum("encaissements"), decaissements=Sum("decaissements")).order_by("m")
    )
    soldes = []
    for m in mensuel:
        fin = _flux(f).filter(jour__month=m["m"]).order_by("-jour").first()
        soldes.append({"mois": m["m"], "solde": fin.solde if fin else 0})
    delai = FaitDelaiPaiement.objects.filter(chargement_id__in=chargements_actifs("scie", f))
    return {
        "indicateurs": {
            "encaissements": s["encaissements"],
            "decaissements": s["decaissements"],
            "solde": s["solde"],
            "jour_solde": s["jour"],
            "jours_de_decaissements": s["jours_de_decaissements"],
            "sous_seuil": s["sous_seuil"],
            "delai_moyen_paiement": delai.aggregate(d=Avg("delai_moyen_jours"))["d"],
        },
        "flux_mensuels": [
            {"mois": m["m"], "encaissements": m["encaissements"], "decaissements": m["decaissements"]} for m in mensuel
        ],
        "solde_mensuel": soldes,
        "seuil": {"valeur": s["decaissement_mensuel_moyen"], "mois": regles.parametre("tresorerie_mois_seuil")},
        "tofe": tofe(f),
    }


def tofe(f: Filtres) -> list[dict]:
    """TOFE simplifié : recettes par source, puis dépenses de la Chaîne Dépense ; source ligne par ligne."""
    from apps.douanes.services import totaux as totaux_douanes
    from apps.recettes_fiscales.services import _recouvrement

    lignes = []
    fs = filtres_source("safig", f.exercice)
    if fs:
        lignes.append(
            {
                "poste": "Recettes fiscales",
                "sens": "recette",
                **bloc("safig", fs, somme(_recouvrement(fs), "recouvre")["recouvre"]),
            }
        )
    fd = filtres_source("sydonia", f.exercice)
    if fd:
        lignes.append(
            {"poste": "Recettes douanières", "sens": "recette", **bloc("sydonia", fd, totaux_douanes(fd)["recouvre"])}
        )
    for poste in FaitTofe.objects.filter(chargement_id__in=chargements_actifs("scie", f)).order_by("ordre"):
        lignes.append({"poste": poste.poste_libelle, "sens": "financement", **bloc("scie", f, poste.montant)})
    fc, i = depense(f.exercice)
    if i:
        lignes.append(
            {"poste": "Dépenses ordonnancées", "sens": "depense", **bloc("chaine_depense", fc, i["montant_ordonnance"])}
        )
        lignes.append({"poste": "Dépenses payées", "sens": "depense", **bloc("chaine_depense", fc, i["montant_paye"])})
    return lignes


def kpi_synthese(f: Filtres) -> dict:
    s = _solde(f)
    return {"valeur": s["solde"], "jours": s["jours_de_decaissements"], "sous_seuil": s["sous_seuil"]}
