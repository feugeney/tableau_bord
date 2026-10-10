"""Recettes fiscales (SAFIG) : recouvrement, restes à recouvrer, contentieux, contribuables."""

from __future__ import annotations

from django.db.models import Max, Sum

from apps.core import regles
from apps.core.domaines import chargements_actifs, filtres_source, somme, ventiler
from apps.core.filtres import Filtres

from .models import FaitContentieux, FaitContribuables, FaitRecouvrementFiscal, FaitResteARecouvrer


def _recouvrement(f: Filtres):
    return FaitRecouvrementFiscal.objects.filter(chargement_id__in=chargements_actifs("safig", f))


def page(f: Filtres) -> dict:
    ids = chargements_actifs("safig", f)
    rec = FaitRecouvrementFiscal.objects.filter(chargement_id__in=ids)
    tot = somme(rec, "objectif", "recouvre")
    restes = FaitResteARecouvrer.objects.filter(chargement_id__in=ids)
    contentieux = FaitContentieux.objects.filter(chargement_id__in=ids)
    contrib = FaitContribuables.objects.filter(chargement_id__in=ids)
    dernier_mois = contrib.aggregate(m=Max("mois"))["m"]
    c = somme(contrib.filter(mois=dernier_mois), "actifs", "teledeclarants")

    par_impot = ventiler(rec, "impot__libelle", "objectif", "recouvre")
    for ligne in par_impot:
        ligne["taux"] = regles.taux(ligne["recouvre"], ligne["objectif"])
        ligne["en_retard"] = regles.recouvrement_en_retard(ligne["recouvre"], ligne["objectif"])
    return {
        "indicateurs": {
            "recouvre": tot["recouvre"],
            "objectif": tot["objectif"],
            "taux": regles.taux(tot["recouvre"], tot["objectif"]),
            "restes_a_recouvrer": somme(restes, "montant")["montant"],
            "contentieux": somme(contentieux, "montant")["montant"],
            "dossiers_contentieux": contentieux.aggregate(n=Sum("nombre_dossiers"))["n"] or 0,
            "contribuables_actifs": c["actifs"],
            "taux_teledeclaration": regles.taux(c["teledeclarants"], c["actifs"]),
        },
        "par_impot": par_impot,
        "mensuel": [
            {"mois": ligne["libelle"], "objectif": ligne["objectif"], "recouvre": ligne["recouvre"]}
            for ligne in ventiler(rec, "mois", "objectif", "recouvre", ordre="mois")
        ],
        "par_centre": ventiler(rec, "centre__libelle", "objectif", "recouvre"),
        "par_secteur": ventiler(rec, "secteur__libelle", "recouvre"),
        "restes_par_anciennete": ventiler(restes, "anciennete", "montant"),
        "contentieux_par_stade": ventiler(contentieux, "stade", "montant", "nombre_dossiers"),
        "seuil_retard": regles.parametre("recouvrement_taux_min"),
    }


def kpi_synthese(f: Filtres) -> dict:
    """Recettes fiscales et douanières réunies (chacune sur sa dernière situation)."""
    from apps.douanes.services import totaux as totaux_douanes

    tot = somme(_recouvrement(f), "objectif", "recouvre")
    fd = filtres_source("sydonia", f.exercice)
    d = totaux_douanes(fd) if fd else {"objectif": 0, "recouvre": 0}
    recouvre, objectif = tot["recouvre"] + d["recouvre"], tot["objectif"] + d["objectif"]
    return {"valeur": recouvre, "taux": regles.taux(recouvre, objectif), "reference": objectif}
