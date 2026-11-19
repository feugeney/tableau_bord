"""Outils communs aux services de domaine (SAFIG, SYDONIA, SCIE, dette, FUGAS, SICOM, SYSOP)."""

from __future__ import annotations

from typing import Optional

from django.db import connection
from django.db.models import Sum

from .filtres import Filtres, dernieres_situations
from .reponses import meta


def chargements_actifs(source_code: str, f: Filtres) -> list[int]:
    """Dernier chargement réussi de la source pour (exercice, date de situation)."""
    with connection.cursor() as c:
        c.execute(
            """SELECT a.id FROM mart.v_chargements_actifs a JOIN public.core_source s ON s.id = a.source_id
               WHERE s.code = %s AND a.exercice = %s AND a.date_situation = %s""",
            [source_code, f.exercice, f.date_situation],
        )
        return [r[0] for r in c.fetchall()]


def filtres_source(source_code: str, exercice: Optional[int] = None) -> Optional[Filtres]:
    """Dernière situation de l'exercice demandé, sans substitution d'un autre exercice."""
    situations = dernieres_situations(source_code)
    if not situations:
        return None
    if exercice is not None:
        for e, d in situations:
            if e == exercice:
                return Filtres(e, d)
        return None
    e, d = situations[0]
    return Filtres(e, d)


def bloc(source_code: str, f: Optional[Filtres], donnees) -> dict:
    """Bloc de page avec sa propre pastille de source (pages mêlant réel et illustration)."""
    return {"meta": meta(source_code, f), "donnees": donnees}


def somme(qs, *champs) -> dict:
    agg = qs.aggregate(**{c: Sum(c) for c in champs})
    return {c: agg[c] or 0 for c in champs}


def ventiler(qs, cle: str, *champs, ordre: Optional[str] = None, limite: Optional[int] = None) -> list[dict]:
    lignes = qs.values(cle).annotate(**{c: Sum(c) for c in champs}).order_by(ordre or f"-{champs[0]}")
    lignes = list(lignes[:limite] if limite else lignes)
    for ligne in lignes:
        ligne["libelle"] = ligne.pop(cle)
    return lignes


def depense(f_exercice: Optional[int], titre: Optional[str] = None):
    """Indicateurs réels de la Chaîne Dépense (pages mixtes)."""
    from apps.depense import services

    fc = filtres_source("chaine_depense", f_exercice)
    if fc is None:
        return None, None
    if titre:
        from apps.referentiels.models import NATURE_VERS_TITRE

        fc.nature = next(n for n, t in NATURE_VERS_TITRE.items() if t == titre)
    return fc, services.indicateurs(fc)


def projection_recettes(lignes: list[dict], f: Filtres) -> dict:
    """Recettes projetées au 31 décembre, à partir des lignes mensuelles (mois, objectif, recouvre).

    La cible n'est renseignée que si les objectifs des douze mois sont chargés ; sinon l'objectif annuel
    n'est pas connu de l'entrepôt.
    """
    from datetime import date

    from .projections import projeter

    serie = {date(f.exercice, int(x["mois"]), 1): x["recouvre"] for x in lignes}
    annuel = len({int(x["mois"]) for x in lignes if x["objectif"]}) == 12
    cible = sum(x["objectif"] for x in lignes) if annuel else None
    return projeter(serie, f.date_situation, cible=cible, exercice=f.exercice)
