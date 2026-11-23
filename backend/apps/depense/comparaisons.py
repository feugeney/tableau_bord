"""Comparaisons dans le temps de la page Dépenses : exercice précédent à la même date et courbe cumulée.

Seul l'engagement est daté dans l'extraction (date de création de l'engagement) : l'engagé N−1
« à la même date » se reconstitue à partir des engagements N−1. Les autres phases (liquidation,
ordonnancement, paiement) ne portent pas de date ; pour elles, la référence N−1 est la clôture
de l'exercice précédent, présentée comme telle.

Le dénominateur N−1 est celui de la dernière situation N−1 (crédits de clôture, LFR comprise) :
c'est une approximation des crédits ouverts à la même date, indiquée dans la méthode.
"""

from __future__ import annotations

import calendar
from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import Optional

from apps.core import regles
from apps.core.domaines import chargements_actifs
from apps.core.filtres import Filtres, dernieres_situations
from apps.core.models import Chargement

from . import criteres
from .services import _requete, indicateurs, sections

D0 = Decimal(0)
MOIS = range(1, 13)


def _filtres_n1(f: Filtres) -> Optional[Filtres]:
    jour = next((d for e, d in dernieres_situations("chaine_depense") if e == f.exercice - 1), None)
    return replace(f, exercice=f.exercice - 1, date_situation=jour) if jour else None


def _meme_jour(d: date, annee: int) -> date:
    return date(annee, d.month, min(d.day, calendar.monthrange(annee, d.month)[1]))


def _engage_par_mois(f: Filtres, par_section: bool = False, jusqu_au: Optional[date] = None) -> list[dict]:
    """Engagé par mois de création, même périmètre que le graphique mensuel (rapproché à l'import)."""
    ids = chargements_actifs("chaine_depense", f)
    ch = Chargement.objects.filter(pk__in=ids).order_by("-fin", "-id").first()
    filtre = ""
    if ch and ch.detail.get("rapprochement_engage", {}).get("cles_en_ecart") == 0:
        filtre = """AND COALESCE(e.attributs->>'code_etat_dossier', '') <> 'E9N'
                    AND COALESCE(e.attributs->>'code_type_procedure', '') <> '52'"""
    where, params = f.where("e")
    ce, pe = criteres.clause_engagement(f, "e")
    borne, pb = ("AND e.date_creation <= %s", [jusqu_au]) if jusqu_au else ("", [])
    section = "e.section_code, " if par_section else ""
    return _requete(
        f"""SELECT {section}extract(month FROM e.date_creation)::int AS mois, SUM(e.montant_engage) AS engage
            FROM dw.fait_engagement e
            WHERE e.chargement_id = ANY(%s) AND {where} AND {ce} AND e.date_creation IS NOT NULL
              AND extract(year FROM e.date_creation) = %s {borne} {filtre}
            GROUP BY {section}extract(month FROM e.date_creation)""",
        [ids, *params, *pe, f.exercice, *pb],
    )


def comparaison_n1(f: Filtres) -> dict:
    """Engagement à la même date de l'exercice précédent (global et par ministère) et taux de clôture N−1."""
    fp = _filtres_n1(f)
    if fp is None or f.date_situation is None:
        return {"disponible": False, "motif": f"Exercice {f.exercice - 1} non chargé."}
    jour = _meme_jour(f.date_situation, fp.exercice)
    cloture = indicateurs(fp)
    engage = sum((r["engage"] for r in _engage_par_mois(fp, jusqu_au=jour)), D0)
    par_section_engage: dict[str, Decimal] = {}
    for r in _engage_par_mois(fp, par_section=True, jusqu_au=jour):
        par_section_engage[r["section_code"]] = par_section_engage.get(r["section_code"], D0) + r["engage"]
    credits_sections = {s["code"]: s["credit_actuel"] for s in sections(fp)}
    return {
        "disponible": True,
        "exercice": fp.exercice,
        "date": jour,
        "taux_engagement": regles.taux(engage, cloture["credit_actuel"]),
        "engage": engage,
        "par_section": {
            code: regles.taux(par_section_engage.get(code, D0), credit) for code, credit in credits_sections.items()
        },
        "cloture": {
            k: cloture[k]
            for k in ("taux_engagement", "taux_liquidation", "taux_ordonnancement", "taux_vbp", "taux_paiement")
        },
        "methode": (
            f"Engagements {fp.exercice} créés jusqu'au {jour:%d/%m/%Y}, rapportés aux crédits de la dernière "
            f"situation {fp.exercice} (clôture, LFR comprise). Les autres phases ne sont pas datées : "
            f"leur référence est la clôture {fp.exercice}."
        ),
    }


def courbe(f: Filtres) -> dict:
    """Engagé cumulé en % des crédits, mois par mois : exercice courant, exercice précédent, prorata temporel."""
    i = indicateurs(f)
    mois_n = {r["mois"]: r["engage"] for r in _engage_par_mois(f, jusqu_au=f.date_situation)}
    fp = _filtres_n1(f)
    mois_n1, credit_n1 = {}, None
    if fp:
        mois_n1 = {r["mois"]: r["engage"] for r in _engage_par_mois(fp, jusqu_au=fp.date_situation)}
        credit_n1 = indicateurs(fp)["credit_actuel"]
    dernier = f.date_situation.month if f.date_situation and f.date_situation.year == f.exercice else 12
    if f.date_situation and f.date_situation.year < f.exercice:
        dernier = 0
    dernier_n1 = fp.date_situation.month if fp and fp.date_situation and fp.date_situation.year == fp.exercice else 12
    points, cumul_n, cumul_n1 = [], D0, D0
    for m in MOIS:
        cumul_n += mois_n.get(m, D0)
        cumul_n1 += mois_n1.get(m, D0)
        points.append(
            {
                "mois": m,
                # Au-delà du mois de situation, l'exercice courant n'est pas encore connu.
                "n": regles.taux(cumul_n, i["credit_actuel"]) if mois_n and m <= dernier else None,
                "n1": regles.taux(cumul_n1, credit_n1) if mois_n1 and m <= dernier_n1 else None,
                "prorata": Decimal(m) / 12,
            }
        )
    return {
        "exercice": f.exercice,
        "exercice_precedent": fp.exercice if fp else None,
        "date_situation": f.date_situation,
        "points": points,
        "concordant": sum(mois_n.values(), D0) == i["credit_engage"],
        "engage_serie": sum(mois_n.values(), D0),
        "engage_situation": i["credit_engage"],
        "methode": (
            "Engagements cumulés par mois de création, rapportés aux crédits actuels de chaque exercice. "
            "Le dernier mois est arrêté à la date de situation ; les mois futurs restent vides. "
            "La série précédente est bornée à sa propre date de situation. "
            "Les dossiers sans date ou créés hors exercice sont exclus de la courbe. "
            "Le prorata temporel est un simple repère visuel, pas un objectif."
        ),
    }
