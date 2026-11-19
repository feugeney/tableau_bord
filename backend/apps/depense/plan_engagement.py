"""Page Pilotage › Plan d'engagement : plafonds trimestriels et engagé constaté.

Montants en GNF (Decimal) ; taux en ratio (0,71 = 71 %).

Engagé du trimestre : le plan conserve l'engagé visé CF cumulé à chaque ouverture
de trimestre. L'engagé d'un trimestre clos est donc la différence entre l'ouverture
du trimestre suivant et la sienne (même source, même mesure). Pour le dernier trimestre
ouvert, on retient l'engagé visé CF de la dernière situation Chaîne Dépense de
l'exercice, postérieure à l'ouverture ; à défaut, l'engagé n'est pas présenté.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from django.db import connection

from apps.core.domaines import chargements_actifs
from apps.core.filtres import Filtres, dernieres_situations
from apps.referentiels.models import TITRES

from .models import FaitPlanEngagement, FaitPlanEngagementAjustement, PlanEngagementPeriode

D0 = Decimal(0)
SOURCE = "plan_engagement"
LIBELLES_PERIODES = {"T1": "1er trimestre", "T2": "2e trimestre", "T3": "3e trimestre", "T4": "4e trimestre"}
ORDRE = {"T1": 1, "T2": 2, "T3": 3, "T4": 4}

# Circuit vérifié dans les procédures GDEP.PLAN_ENG_* (PE7 n'est posé par aucune procédure).
CIRCUIT = [
    ("PE1", "Paramétrage", "Enveloppe mobilisable, imprévus et dépenses obligatoires"),
    ("PE2", "Plan généré", "Plafonds calculés par section et par titre"),
    ("PE3", "Saisie DAF", "Plafonds transmis aux ministères pour répartition"),
    ("PE8", "Transmis au CF", "Répartition soumise au contrôle financier"),
    ("PE4", "Projet validé", "Validé par le contrôle financier (un rejet renvoie en saisie DAF)"),
    ("PE5", "Arbitrage validé", "Arbitrage du ministère du Budget"),
    ("PE6", "Plan validé", "Plan arrêté : les régulations ne peuvent dépasser les plafonds"),
]
# PE7 « Saisie arbitrage » : projet validé, arbitrage en cours.
ETAPE = {code: i for i, (code, _, _) in enumerate(CIRCUIT)} | {"PE7": 4}

REFERENCES = [
    {
        "titre": "Décret D/2013/015/PRG/SGG du 15 janvier 2013 (RGGBCP), article 19",
        "usage": "Institue le plan d'engagement comme outil de régulation budgétaire.",
    },
    {
        "titre": "Arrêtés trimestriels du ministre du Budget portant plan d'engagement",
        "usage": "Référence de l'arrêté et date de validation reprises de la Chaîne Dépense.",
    },
]


DELAI_OUVERTURE_JOURS = 45


def fin_trimestre(exercice: int, periode: str) -> date:
    mois = ORDRE[periode] * 3
    return date(exercice, mois, 30 if mois in (6, 9) else 31)


def _date(d: Optional[date]) -> str:
    return d.strftime("%d/%m/%Y") if d else "date inconnue"


def _taux(num: Optional[Decimal], den: Optional[Decimal]) -> Optional[Decimal]:
    if num is None or not den:
        return None
    return num / den


def _engage_chaine_depense(exercice: int, apres) -> tuple[Optional[dict], Optional[str]]:
    """Engagé visé CF par (section, titre) de la dernière situation Chaîne Dépense de l'exercice."""
    situations = [d for e, d in dernieres_situations("chaine_depense") if e == exercice and (not apres or d >= apres)]
    if not situations:
        return None, None
    f = Filtres(exercice, situations[0])
    ids = chargements_actifs("chaine_depense", f)
    if not ids:
        return None, None
    with connection.cursor() as c:
        c.execute(
            """SELECT section_code, titre, coalesce(sum(credit_engage_cf), 0)
               FROM dw.fait_situation_ligne WHERE chargement_id = ANY(%s) GROUP BY section_code, titre""",
            [ids],
        )
        return {(s, t): v for s, t, v in c.fetchall()}, situations[0].isoformat()


def periodes_disponibles(chargement_id: int) -> list[PlanEngagementPeriode]:
    return sorted(
        PlanEngagementPeriode.objects.filter(chargement_id=chargement_id, periode__in=ORDRE),
        key=lambda p: ORDRE[p.periode],
    )


def page(f: Filtres, periode: Optional[str] = None) -> Optional[dict]:
    ids = chargements_actifs(SOURCE, f)
    if not ids:
        return None
    ch = ids[0]
    periodes = periodes_disponibles(ch)
    if not periodes:
        return None
    lignes = defaultdict(list)
    for l in FaitPlanEngagement.objects.filter(chargement_id=ch).order_by("section_code", "titre"):
        lignes[l.periode].append(l)
    avec_plan = [p for p in periodes if lignes.get(p.periode)]

    # Trimestre affiché : demandé, sinon trimestre courant, sinon dernier trimestre doté de plafonds.
    codes = {p.periode for p in periodes}
    if periode not in codes:
        courant = next((p.periode for p in periodes if p.periode_courante and lignes.get(p.periode)), None)
        periode = courant or (avec_plan[-1].periode if avec_plan else periodes[-1].periode)
    entete = next(p for p in periodes if p.periode == periode)

    engages, methodes = {}, {}
    for i, p in enumerate(avec_plan):
        suivant = avec_plan[i + 1] if i + 1 < len(avec_plan) else None
        ouverture = {(l.section_code, l.titre): l.engage_ouverture for l in lignes[p.periode]}
        if suivant:
            limite = fin_trimestre(f.exercice, p.periode) + timedelta(days=DELAI_OUVERTURE_JOURS)
            if suivant.date_ouverture and suivant.date_ouverture > limite:
                # L'écart entre deux ouvertures couvrirait d'autres trimestres : non comparable au plafond.
                methodes[p.periode] = {
                    "code": None,
                    "libelle": f"Engagé du trimestre non calculé : le {LIBELLES_PERIODES[suivant.periode]} "
                    f"n'a été ouvert que le {_date(suivant.date_ouverture)}, plus de {DELAI_OUVERTURE_JOURS} jours "
                    "après la fin du trimestre.",
                }
                continue
            fin = {(l.section_code, l.titre): l.engage_ouverture for l in lignes[suivant.periode]}
            methodes[p.periode] = {
                "code": "ouverture_suivante",
                "libelle": f"Engagé visé CF entre l'ouverture du {LIBELLES_PERIODES[p.periode]} "
                f"({_date(p.date_ouverture)}) et celle du {LIBELLES_PERIODES[suivant.periode]} "
                f"({_date(suivant.date_ouverture)})",
            }
        else:
            fin, date_cd = _engage_chaine_depense(f.exercice, p.date_ouverture)
            if fin is None:
                methodes[p.periode] = {
                    "code": None,
                    "libelle": "Engagé du trimestre non disponible : ni trimestre suivant ouvert, "
                    "ni situation Chaîne Dépense de l'exercice après l'ouverture.",
                }
                continue
            methodes[p.periode] = {
                "code": "chaine_depense",
                "libelle": f"Engagé visé CF de la situation Chaîne Dépense du {date_cd}, "
                "diminué de l'engagé à l'ouverture du trimestre",
                "date_situation": date_cd,
            }
        engages[p.periode] = {k: fin.get(k, D0) - v for k, v in ouverture.items()}

    def resume(code: str) -> dict:
        ls = lignes.get(code, [])
        plafond = sum((l.plafond for l in ls), D0)
        eng = engages.get(code)
        engage = sum(eng.values(), D0) if eng is not None else None
        return {"plafond": plafond, "engage_periode": engage, "taux": _taux(engage, plafond)}

    eng = engages.get(periode)
    sections: dict[str, dict] = {}
    titres: dict[str, dict] = {}
    for l in lignes.get(periode, []):
        e = eng.get((l.section_code, l.titre)) if eng is not None else None
        s = sections.setdefault(
            l.section_code,
            {
                "code": l.section_code,
                "libelle": l.section_libelle or f"Section {l.section_code}",
                "plafond": D0,
                "engage_periode": None if eng is None else D0,
                "credit": D0,
                "engage_ouverture": D0,
                "titres": [],
            },
        )
        s["plafond"] += l.plafond
        s["credit"] += l.credit
        s["engage_ouverture"] += l.engage_ouverture
        if e is not None:
            s["engage_periode"] += e
        s["titres"].append(
            {
                "titre": l.titre,
                "libelle": TITRES.get(l.titre, f"Titre {l.titre}"),
                "plafond": l.plafond,
                "engage_periode": e,
                "taux": _taux(e, l.plafond),
                "depassement": e is not None and e > l.plafond,
            }
        )
        t = titres.setdefault(
            l.titre,
            {
                "titre": l.titre,
                "libelle": TITRES.get(l.titre, f"Titre {l.titre}"),
                "plafond": D0,
                "engage_periode": None if eng is None else D0,
            },
        )
        t["plafond"] += l.plafond
        if e is not None:
            t["engage_periode"] += e
    for s in sections.values():
        s["taux"] = _taux(s["engage_periode"], s["plafond"])
        s["marge"] = None if s["engage_periode"] is None else s["plafond"] - s["engage_periode"]
        # Dépassement apprécié par titre : c'est la maille que contrôle la Chaîne Dépense.
        s["depassement"] = any(t["depassement"] for t in s["titres"])
    for t in titres.values():
        t["taux"] = _taux(t["engage_periode"], t["plafond"])

    total = resume(periode)
    libelles = {s["code"]: s["libelle"] for s in sections.values()}
    ajustements = [
        {
            "section_source": a.section_source,
            "libelle_source": libelles.get(a.section_source, f"Section {a.section_source}"),
            "titre_source": a.titre_source,
            "section_destination": a.section_destination,
            "libelle_destination": libelles.get(a.section_destination, f"Section {a.section_destination}"),
            "titre_destination": a.titre_destination,
            "montant": a.montant,
            "observation": a.observation,
            "date": a.date_ajustement,
        }
        for a in FaitPlanEngagementAjustement.objects.filter(chargement_id=ch, periode=periode).order_by(
            "date_ajustement", "id"
        )
    ]
    etape = ETAPE.get(entete.etat_code)
    return {
        "periode": periode,
        "libelle_periode": LIBELLES_PERIODES.get(periode, periode),
        "periodes": [
            {
                "code": p.periode,
                "libelle": LIBELLES_PERIODES[p.periode],
                "etat_code": p.etat_code,
                "etat_libelle": p.etat_libelle,
                "courante": p.periode_courante,
                "a_des_plafonds": bool(lignes.get(p.periode)),
                **resume(p.periode),
            }
            for p in periodes
        ],
        "entete": {
            "etat_code": entete.etat_code,
            "etat_libelle": entete.etat_libelle,
            "reference_arrete": entete.reference_arrete,
            "date_validation": entete.date_validation,
            "date_ouverture": entete.date_ouverture,
            "courante": entete.periode_courante,
            "montant_mobilisable": entete.montant_mobilisable,
            "montant_imprevu": entete.montant_imprevu,
            "montant_obligatoire_titre2": entete.montant_obligatoire_titre2,
            "montant_repartissable": entete.montant_repartissable,
        },
        "indicateurs": {
            **total,
            "marge": None if total["engage_periode"] is None else total["plafond"] - total["engage_periode"],
            "credit": sum((s["credit"] for s in sections.values()), D0),
            "engage_ouverture": sum((s["engage_ouverture"] for s in sections.values()), D0),
            "nb_sections": len(sections),
            "nb_depassements": sum(1 for s in sections.values() if s["depassement"]),
        },
        "methode_engage": methodes.get(periode, {"code": None, "libelle": "Aucun plafond pour ce trimestre."}),
        "titres": sorted(titres.values(), key=lambda t: t["titre"]),
        "sections": sorted(sections.values(), key=lambda s: -s["plafond"]),
        "ajustements": ajustements,
        "circuit": [
            {"code": c, "libelle": lib, "description": desc, "atteint": etape is not None and i <= etape}
            for i, (c, lib, desc) in enumerate(CIRCUIT)
        ],
        "references": REFERENCES,
    }
