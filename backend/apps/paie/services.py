"""Masse salariale : crédits de personnel (Chaîne Dépense, titre 2, réel) et paie (FUGAS)."""

from __future__ import annotations

from django.db.models import Max, Sum

from apps.core import regles
from apps.core.domaines import bloc, chargements_actifs, depense, somme
from apps.core.filtres import Filtres

from .models import FaitControlePaie, FaitPaie

LIBELLES_CONTROLES = dict(FaitControlePaie.CONTROLES)


def _paie(f: Filtres) -> dict:
    ids = chargements_actifs("fugas", f)
    paie = FaitPaie.objects.filter(chargement_id__in=ids)
    mensuel = list(
        paie.values("mois")
        .annotate(effectif=Sum("effectif"), masse_brute=Sum("masse_brute"), masse_nette=Sum("masse_nette"))
        .order_by("mois")
    )
    dernier = mensuel[-1] if mensuel else None
    total = somme(paie, "masse_brute")["masse_brute"]
    return {
        "mensuel": mensuel,
        "masse_mensuelle_moyenne": total / len(mensuel) if mensuel else None,
        "agents": dernier["effectif"] if dernier else None,
        "cout_moyen": regles.taux(dernier["masse_brute"], dernier["effectif"]) if dernier else None,
        "controles": [
            {
                "controle": c.controle,
                "libelle": LIBELLES_CONTROLES[c.controle],
                "nombre_agents": c.nombre_agents,
                "montant": c.montant,
            }
            for c in FaitControlePaie.objects.filter(chargement_id__in=ids).order_by("controle")
        ],
        "dernier_mois": paie.aggregate(m=Max("mois"))["m"],
    }


def page(f: Filtres | None, exercice: int | None = None) -> dict:
    """Page mixte : la Chaîne Dépense est réelle, FUGAS peut être en illustration."""
    from apps.depense import services as dep

    fc, perso = depense(exercice or (f.exercice if f else None), titre="2")
    _, total = depense(exercice or (f.exercice if f else None))
    par_ministere = []
    if fc:
        for s in dep.sections(fc)[:12]:
            par_ministere.append(
                {
                    "libelle": s["libelle_court"],
                    "credit_actuel": s["credit_actuel"],
                    "credit_engage": s["credit_engage"],
                    "montant_ordonnance": s["montant_ordonnance"],
                }
            )
    p = _paie(f) if f else None
    return {
        "credits": bloc(
            "chaine_depense",
            fc,
            (
                None
                if not perso
                else {
                    "credit_actuel": perso["credit_actuel"],
                    "part_budget": regles.taux(perso["credit_actuel"], total["credit_actuel"]) if total else None,
                    "montant_ordonnance": perso["montant_ordonnance"],
                    "taux_ordonnancement": perso["taux_ordonnancement"],
                }
            ),
        ),
        "par_ministere": bloc("chaine_depense", fc, par_ministere),
        "fugas": bloc("fugas", f, p),
    }
