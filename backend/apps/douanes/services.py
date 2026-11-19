"""Recettes douanières (SYDONIA) : recettes, exonérations, déclarations, dédouanement."""

from __future__ import annotations

from django.db.models import Sum

from apps.core import regles
from apps.core.domaines import chargements_actifs, projection_recettes, somme, ventiler
from apps.core.filtres import Filtres

from .models import FaitDeclaration, FaitExoneration, FaitRecetteDouane


def totaux(f: Filtres) -> dict:
    return somme(
        FaitRecetteDouane.objects.filter(chargement_id__in=chargements_actifs("sydonia", f)), "objectif", "recouvre"
    )


def page(f: Filtres) -> dict:
    ids = chargements_actifs("sydonia", f)
    rec = FaitRecetteDouane.objects.filter(chargement_id__in=ids)
    tot = somme(rec, "objectif", "recouvre")
    exo = FaitExoneration.objects.filter(chargement_id__in=ids)
    decl = FaitDeclaration.objects.filter(chargement_id__in=ids)
    nb_decl = decl.aggregate(n=Sum("nombre"))["n"] or 0
    # Délai moyen de dédouanement pondéré par le nombre de déclarations.
    jours = sum(
        ((d.date_mainlevee - d.date_enregistrement).days * d.nombre)
        for d in decl.exclude(date_mainlevee=None).only("date_enregistrement", "date_mainlevee", "nombre")
    )
    circuits = list(decl.values("circuit").annotate(nombre=Sum("nombre")).order_by("circuit"))
    for c in circuits:
        c["part"] = regles.taux(c["nombre"], nb_decl)
    par_nature = ventiler(rec, "nature_droit__libelle", "objectif", "recouvre")
    for ligne in par_nature:
        ligne["taux"] = regles.taux(ligne["recouvre"], ligne["objectif"])
    total_exo = somme(exo, "montant")["montant"]
    mensuel = [
        {"mois": ligne["libelle"], "objectif": ligne["objectif"], "recouvre": ligne["recouvre"]}
        for ligne in ventiler(rec, "mois", "objectif", "recouvre", ordre="mois")
    ]
    return {
        "indicateurs": {
            "recouvre": tot["recouvre"],
            "objectif": tot["objectif"],
            "taux": regles.taux(tot["recouvre"], tot["objectif"]),
            "exonerations": total_exo,
            "part_exonerations": regles.taux(total_exo, tot["recouvre"] + total_exo),
            "declarations": nb_decl,
            "delai_moyen_jours": round(jours / nb_decl, 1) if nb_decl else None,
        },
        "par_nature": par_nature,
        "mensuel": mensuel,
        "projection": projection_recettes(mensuel, f),
        "par_bureau": ventiler(rec, "bureau__libelle", "objectif", "recouvre"),
        "circuits": circuits,
        "exonerations_par_regime": ventiler(exo, "regime", "montant"),
        "seuil_retard": regles.parametre("recouvrement_taux_min"),
    }


def exonerations(f: Filtres) -> dict:
    ids = chargements_actifs("sydonia", f)
    total = somme(FaitExoneration.objects.filter(chargement_id__in=ids), "montant")["montant"]
    recettes = somme(FaitRecetteDouane.objects.filter(chargement_id__in=ids), "recouvre")["recouvre"]
    return {"montant": total, "part": regles.taux(total, recettes + total)}
