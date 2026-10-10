"""Patrimoine de l'État (SICOM) : valeurs, catégories, parc automobile, contrôles, déploiement."""

from __future__ import annotations

from django.db.models import Sum

from apps.core import regles
from apps.core.domaines import chargements_actifs, somme, ventiler
from apps.core.filtres import Filtres

from .models import FaitControlePatrimoine, FaitDeploiementSicom, FaitParcVehicules, FaitPatrimoine

LIBELLES_CONTROLES = dict(FaitControlePatrimoine.CONTROLES)
LIBELLES_ETATS = dict(FaitParcVehicules.ETATS)


def page(f: Filtres) -> dict:
    ids = chargements_actifs("sicom", f)
    pat = FaitPatrimoine.objects.filter(chargement_id__in=ids)
    tot = somme(pat, "valeur_brute", "valeur_nette", "nombre_biens", "biens_immatricules")
    parc = list(FaitParcVehicules.objects.filter(chargement_id__in=ids).values("etat").annotate(nombre=Sum("nombre")))
    nb_vehicules = sum(p["nombre"] for p in parc)
    en_service = sum(p["nombre"] for p in parc if p["etat"] == "en_service")
    for p in parc:
        p["libelle"] = LIBELLES_ETATS[p["etat"]]
        p["part"] = regles.taux(p["nombre"], nb_vehicules)
    dep = FaitDeploiementSicom.objects.filter(chargement_id__in=ids).first()
    par_ministere = ventiler(pat, "section__libelle_court", "valeur_nette", "valeur_brute")
    return {
        "indicateurs": {
            "valeur_nette": tot["valeur_nette"],
            "valeur_brute": tot["valeur_brute"],
            "taux_amortissement": regles.taux(tot["valeur_brute"] - tot["valeur_nette"], tot["valeur_brute"]),
            "nombre_biens": tot["nombre_biens"],
            "biens_immatricules": tot["biens_immatricules"],
            "taux_immatriculation": regles.taux(tot["biens_immatricules"], tot["nombre_biens"]),
            "vehicules": nb_vehicules,
            "taux_en_service": regles.taux(en_service, nb_vehicules),
            "institutions_actives": dep.institutions_actives if dep else None,
            "institutions_prevues": dep.institutions_prevues if dep else None,
        },
        "par_categorie": ventiler(pat, "categorie__libelle", "valeur_nette", "valeur_brute", "nombre_biens"),
        "par_ministere": par_ministere,
        "parc": sorted(parc, key=lambda p: list(LIBELLES_ETATS).index(p["etat"])),
        "controles": [
            {
                "controle": c.controle,
                "libelle": LIBELLES_CONTROLES[c.controle],
                "nombre": c.nombre,
                "montant": c.montant,
            }
            for c in FaitControlePatrimoine.objects.filter(chargement_id__in=ids).order_by("controle")
        ],
    }


def biens_non_inventories(f: Filtres):
    return FaitControlePatrimoine.objects.filter(
        chargement_id__in=chargements_actifs("sicom", f), controle="non_inventories_2ans"
    ).first()
