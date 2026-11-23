"""Calculs de la page Dépenses, servis depuis la couche mart.

Les montants renvoyés sont en GNF (Decimal) ; la conversion en milliards est
faite par l'affichage. Les taux sont des ratios (0,71 = 71 %).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import Optional

from django.db import connection

from apps.core import regles
from apps.core.domaines import chargements_actifs
from apps.core.filtres import Filtres
from apps.core.models import Chargement
from apps.referentiels.models import TITRES, RefSection

from . import criteres

D0 = Decimal(0)

MESURES = [
    "credit_initial_lfi",
    "credit_lfr",
    "credit_actuel",
    "credit_disponible",
    "credit_engage",
    "montant_liquide",
    "montant_ordonnance",
    "montant_vbp",
    "montant_paye",
    "ordonnance_hors_chaine",
    "paye_hors_chaine",
    "nb_lignes",
    "nb_engagements",
    "nb_lfi_absent",
]


def _requete(sql: str, params: list) -> list[dict]:
    with connection.cursor() as c:
        c.execute(sql, params)
        cols = [d[0] for d in c.description]
        return [dict(zip(cols, r)) for r in c.fetchall()]


def _totaux(f: Filtres, group_by: Optional[str] = None) -> list[dict]:
    where, params = f.where()
    src, params_src = criteres.source("mv_depense_par_section_titre", f)
    params = params_src + params
    select = ", ".join(f"coalesce(sum({m}), 0) AS {m}" for m in MESURES)
    if group_by:
        return _entiers(
            _requete(
                f"SELECT {group_by}, {select} FROM {src} WHERE {where} GROUP BY {group_by} ORDER BY {group_by}",
                params,
            )
        )
    return _entiers(_requete(f"SELECT {select} FROM {src} WHERE {where}", params))


def _entiers(lignes: list[dict]) -> list[dict]:
    for t in lignes:
        for k in ("nb_lignes", "nb_engagements", "nb_lfi_absent"):
            if k in t:
                t[k] = int(t[k])
    return lignes


def _paiement(t: dict, mode: str) -> regles.Paiement:
    return regles.paiement(
        t["montant_ordonnance"], t["montant_paye"], t["ordonnance_hors_chaine"], t["paye_hors_chaine"], mode
    )


def indicateurs(f: Filtres) -> dict:
    t = _totaux(f)[0]
    pay = _paiement(t, f.paiement)
    soldes_negatifs = [
        {"section": r["section_code"], "montant": _paiement(r, f.paiement).reste_a_payer}
        for r in _totaux(f, group_by="section_code")
        if _paiement(r, f.paiement).reste_a_payer < 0
    ]
    return {
        "credit_initial_lfi": t["credit_initial_lfi"],
        "credit_actuel": t["credit_actuel"],
        "variation_lfi": regles.taux(t["credit_actuel"] - t["credit_initial_lfi"], t["credit_initial_lfi"]),
        "credit_engage": t["credit_engage"],
        "taux_engagement": regles.taux_engagement(t["credit_engage"], t["credit_actuel"]),
        "montant_liquide": t["montant_liquide"],
        "montant_ordonnance": t["montant_ordonnance"],
        "taux_liquidation": regles.taux_liquidation(t["montant_liquide"], t["credit_engage"]),
        "taux_liquidation_sur_credits": regles.taux(t["montant_liquide"], t["credit_actuel"]),
        "taux_ordonnancement": regles.taux_ordonnancement(t["montant_ordonnance"], t["montant_liquide"]),
        "taux_ordonnancement_sur_credits": regles.taux(t["montant_ordonnance"], t["credit_actuel"]),
        "montant_vbp": t["montant_vbp"],
        "taux_vbp": regles.taux_vbp(t["montant_vbp"], t["montant_ordonnance"]),
        "montant_paye": t["montant_paye"],
        "taux_paiement": regles.taux_paiement(t["montant_paye"], t["montant_ordonnance"]),
        "taux_paiement_sur_credits": regles.taux(t["montant_paye"], t["credit_actuel"]),
        "credit_disponible": t["credit_disponible"],
        "credits_non_engages": t["credit_actuel"] - t["credit_engage"],
        "paiement": {
            "mode": pay.mode,
            "ordonnance": pay.ordonnance,
            "paye": pay.paye,
            "reste_a_payer": pay.reste_a_payer,
            "paye_sur_ordonnance": pay.paye_sur_ordonnance,
        },
        "hors_chaine": {"ordonnance": t["ordonnance_hors_chaine"], "paye": t["paye_hors_chaine"]},
        "nb_lignes": t["nb_lignes"],
        "nb_engagements": t["nb_engagements"],
        "nb_lfi_absent": t["nb_lfi_absent"],
        "nb_lignes_depassement": lignes_en_depassement(f),
        "qualite": {
            "engage_sup_credits": compter_lignes(f, "credit_engage > credit_actuel"),
            "liquide_sup_engage": compter_lignes(f, "montant_liquide > credit_engage"),
            "soldes_negatifs": soldes_negatifs,
        },
    }


def chaine(f: Filtres) -> dict:
    t = _totaux(f)[0]
    ca = t["credit_actuel"]
    phases = [
        ("credits", "Crédits actuels", ca),
        ("engage", "Engagé", t["credit_engage"]),
        ("liquide", "Liquidé", t["montant_liquide"]),
        ("ordonnance", "Ordonnancé", t["montant_ordonnance"]),
        ("vbp", "Vu bon pour paiement", t["montant_vbp"]),
        ("paye", "Payé", t["montant_paye"]),
    ]
    return {
        "phases": [{"code": c, "libelle": l, "montant": m, "taux": regles.taux(m, ca)} for c, l, m in phases],
        "liquide_depasse_engage": t["montant_liquide"] > t["credit_engage"],
        "nb_lignes_liquide_sup_engage": compter_lignes(f, "montant_liquide > credit_engage"),
    }


def natures(f: Filtres) -> list[dict]:
    lignes = _totaux(replace(f, nature=None), group_by="titre")
    sortie = []
    for t in lignes:
        pay = _paiement(t, f.paiement)
        sortie.append(
            {
                "titre": t["titre"],
                "libelle": TITRES.get(t["titre"], t["titre"]),
                "credit_actuel": t["credit_actuel"],
                "credit_engage": t["credit_engage"],
                "montant_ordonnance": t["montant_ordonnance"],
                "montant_paye": t["montant_paye"],
                "credit_disponible": t["credit_disponible"],
                "taux_engagement": regles.taux(t["credit_engage"], t["credit_actuel"]),
                # Barres empilées : payé / ordonnancé non payé / engagé non ordonnancé / disponible.
                "empile": {
                    "paye": t["montant_paye"],
                    "ordonnance_non_paye": max(t["montant_ordonnance"] - t["montant_paye"], D0),
                    "engage_non_ordonnance": max(t["credit_engage"] - t["montant_ordonnance"], D0),
                    "disponible": max(t["credit_actuel"] - t["credit_engage"], D0),
                },
                "reste_a_payer": pay.reste_a_payer,
            }
        )
    return sortie


def _referentiels_libelles(f: Filtres) -> dict:
    return (
        Chargement.objects.filter(pk__in=chargements_actifs("chaine_depense", f))
        .order_by("-fin", "-id")
        .values_list("detail__referentiels_libelles", flat=True)
        .first()
    ) or {}


def _libelles_sections(f: Filtres) -> dict[str, dict]:
    libelles = {
        s.code: {"libelle": s.libelle, "libelle_court": s.libelle_affiche, "type": s.type}
        for s in RefSection.objects.all()
    }
    for code, noms in _referentiels_libelles(f).get("sections", {}).items():
        libelles.setdefault(code, {}).update({k: noms[k] for k in ("libelle", "libelle_court") if k in noms})
    return libelles


def sections(f: Filtres, surcharges=None) -> list[dict]:
    lignes = _totaux(replace(f, section=None), group_by="section_code")
    libelles = _libelles_sections(f)
    depassements = compter_lignes_par_section(f)
    sortie = []
    for t in lignes:
        pay_aj = _paiement(t, "ajuste")
        pay = _paiement(t, f.paiement)
        statut = regles.statut_ministere(
            t["credit_actuel"], t["credit_engage"], pay_aj.ordonnance, pay_aj.paye, surcharges
        )
        lib = libelles.get(t["section_code"], {})
        sortie.append(
            {
                "code": t["section_code"],
                "libelle": lib.get("libelle", t["section_code"]),
                "libelle_court": lib.get("libelle_court", t["section_code"]),
                "type": lib.get("type"),
                "credit_actuel": t["credit_actuel"],
                "credit_engage": t["credit_engage"],
                "taux_engagement": regles.taux(t["credit_engage"], t["credit_actuel"]),
                "montant_liquide": t["montant_liquide"],
                "montant_ordonnance": pay.ordonnance,
                "montant_vbp": t["montant_vbp"],
                "montant_paye": pay.paye,
                "paye_sur_ordonnance": pay.paye_sur_ordonnance,
                "credit_disponible": t["credit_disponible"],
                "reste_a_payer": pay.reste_a_payer,
                "nb_lignes_depassement": depassements.get(t["section_code"], 0),
                "statut": {"code": statut.code, "libelle": statut.libelle, "severite": statut.severite},
            }
        )
    sortie.sort(key=lambda s: s["credit_actuel"], reverse=True)
    return sortie


def section_detail(f: Filtres, code: str) -> dict:
    fs = replace(f, section=code)
    where, params = fs.where("l", avec_titre=False)
    titre_sql, titre_params = ("AND l.titre = %s", [fs.titre]) if fs.titre else ("", [])
    cl, pl = criteres.clause_ligne(fs, "l")
    titre_sql, titre_params = f"{titre_sql} AND {cl}", titre_params + pl
    top = _requete(
        f"""SELECT l.sous_section_code AS code, coalesce(ss.libelle, l.sous_section_code) AS libelle,
                   sum(l.credit_actuel) AS credit_actuel, sum(l.credit_engage) AS credit_engage,
                   sum(l.montant_ordonnance) AS montant_ordonnance, sum(l.montant_paye) AS montant_paye
            FROM dw.fait_situation_ligne l
            LEFT JOIN ref.ref_sous_section ss ON ss.code = l.sous_section_code
            WHERE l.chargement_id IN (SELECT id FROM mart.v_chargements_actifs) AND {where} {titre_sql}
            GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 8""",
        params + titre_params,
    )
    for t in top:
        t["taux_engagement"] = regles.taux(t["credit_engage"], t["credit_actuel"])
    noms_services = _referentiels_libelles(f).get("sous_sections", {}).get(code, {})
    for t in top:
        t["libelle"] = noms_services.get(t["code"], t["libelle"])
    seuil = regles.parametre("depassement_disponible_max")
    depassement = _requete(
        f"""SELECT l.sous_section_code, coalesce(ss.libelle, '') AS sous_section, l.nature_code,
                   coalesce(n.libelle, '') AS nature, l.credit_actuel, l.credit_engage, l.credit_disponible
            FROM dw.fait_situation_ligne l
            LEFT JOIN ref.ref_sous_section ss ON ss.code = l.sous_section_code
            LEFT JOIN ref.ref_nature_economique n ON n.code = l.nature_code
            WHERE l.chargement_id IN (SELECT id FROM mart.v_chargements_actifs) AND {where} {titre_sql}
              AND l.credit_disponible < %s
            ORDER BY l.credit_disponible LIMIT 100""",
        params + titre_params + [seuil],
    )
    for ligne in depassement:
        ligne["sous_section"] = noms_services.get(ligne["sous_section_code"], ligne["sous_section"])
    lib = _libelles_sections(f).get(code, {})
    return {
        "code": code,
        "libelle": lib.get("libelle", code),
        "libelle_court": lib.get("libelle_court", code),
        "natures": natures(fs),
        "top_sous_sections": top,
        "lignes_depassement": depassement,
    }


def compter_lignes(f: Filtres, condition: str, params_condition: Optional[list] = None) -> int:
    where, params = f.where("l")
    cl, pl = criteres.clause_ligne(f, "l")
    rows = _requete(
        f"""SELECT count(*) AS n FROM dw.fait_situation_ligne l
            WHERE l.chargement_id IN (SELECT id FROM mart.v_chargements_actifs) AND {where} AND {cl}
              AND {condition}""",
        params + pl + (params_condition or []),
    )
    return rows[0]["n"]


def compter_lignes_par_section(f: Filtres) -> dict[str, int]:
    where, params = replace(f, section=None).where("l")
    cl, pl = criteres.clause_ligne(f, "l")
    rows = _requete(
        f"""SELECT l.section_code, count(*) AS n FROM dw.fait_situation_ligne l
            WHERE l.chargement_id IN (SELECT id FROM mart.v_chargements_actifs) AND {where} AND {cl}
              AND l.credit_disponible < %s GROUP BY 1""",
        params + pl + [regles.parametre("depassement_disponible_max")],
    )
    return {r["section_code"]: r["n"] for r in rows}


def lignes_en_depassement(f: Filtres) -> int:
    return compter_lignes(f, "credit_disponible < %s", [regles.parametre("depassement_disponible_max")])


def _mensuel_engagements(f: Filtres, par_section: bool = False, comparable: bool = True) -> list[dict]:
    """Le périmètre Oracle n'est appliqué que s'il a été rapproché sur chaque clé à l'import."""
    ids = chargements_actifs("chaine_depense", f)
    ch = Chargement.objects.filter(pk__in=ids).order_by("-fin", "-id").first()
    rapprochement = ch.detail.get("rapprochement_engage", {}) if ch else {}
    filtre = ""
    if comparable and rapprochement.get("cles_en_ecart") == 0:
        filtre = """AND COALESCE(e.attributs->>'code_etat_dossier', '') <> 'E9N'
                    AND COALESCE(e.attributs->>'code_type_procedure', '') <> '52'"""
    where, params = f.where("e")
    ce, pe = criteres.clause_engagement(f, "e")
    where, params = f"{where} AND {ce}", params + pe
    section = "e.section_code, " if par_section else ""
    return _requete(
        f"""SELECT {section}date_trunc('month', e.date_creation)::date AS mois,
                   SUM(e.montant_engage) AS montant_engage, COUNT(*)::int AS nb_engagements
            FROM dw.fait_engagement e
            WHERE e.chargement_id = ANY(%s) AND {where} AND e.date_creation IS NOT NULL {filtre}
            GROUP BY {section}date_trunc('month', e.date_creation) ORDER BY {section}mois""",
        [ids, *params],
    )


def mensuel(f: Filtres) -> dict:
    rows = _mensuel_engagements(f)
    brut = _mensuel_engagements(f, comparable=False)
    par_mois = {r["mois"]: r["montant_engage"] for r in brut}
    mois_comparables = {r["mois"] for r in rows}
    rows.extend(
        {"mois": r["mois"], "montant_engage": D0, "nb_engagements": 0}
        for r in brut
        if r["mois"] not in mois_comparables
    )
    rows.sort(key=lambda r: r["mois"])
    total_brut = sum(par_mois.values(), D0)
    total = sum((r["montant_engage"] for r in rows), D0)
    reference = indicateurs(f)["credit_engage"]
    ch = Chargement.objects.filter(pk__in=chargements_actifs("chaine_depense", f)).first()
    rapprochement = ch.detail.get("rapprochement_engage", {}) if ch else {}
    for r in rows:
        r["montant_engage_brut"] = par_mois.get(r["mois"], D0)
        r["periode_complementaire"] = bool(f.exercice and r["mois"].year > f.exercice)
        r["decembre"] = r["mois"].month == 12 and r["mois"].year == f.exercice
    return {
        "mois": rows,
        "engage_periode_complementaire": sum((r["montant_engage"] for r in rows if r["periode_complementaire"]), D0),
        "rapprochement": {
            "perimetre": rapprochement.get("perimetre", "Engagements bruts par date de création"),
            "brut": total_brut,
            "comparable": total,
            "reference": reference,
            "ecart_perimetre": total_brut - total,
            "ecart_reference": total - reference,
            "concordant": total == reference,
        },
    }


def restes_a_payer_anciennete(f: Filtres) -> dict:
    where, params = f.where()
    src, params_src = criteres.source("mv_restes_a_payer_anciennete", f)
    params = params_src + params
    hors = "" if f.paiement == "brut" else "AND NOT hors_chaine"
    rows = _requete(
        f"""SELECT mois_creation, sum(reste_a_payer) AS reste_a_payer, sum(nb_engagements)::int AS nb_engagements
            FROM {src} WHERE {where} {hors}
            GROUP BY mois_creation ORDER BY mois_creation""",
        params,
    )
    risque = D0
    for r in rows:
        mois = regles.anciennete_mois(r["mois_creation"], f.date_situation) if f.date_situation else None
        r["anciennete_mois"] = mois
        r["risque_arriere"] = regles.est_risque_arriere(mois)
        if r["risque_arriere"]:
            risque += r["reste_a_payer"]
    return {
        "mois": rows,
        "reste_a_payer_risque_arriere": risque,
        "seuil_mois": regles.parametre("restes_a_payer_mois_risque"),
    }


def procedures(f: Filtres) -> list[dict]:
    where, params = f.where()
    src, params_src = criteres.source("mv_depense_procedures", f)
    params = params_src + params
    rows = _requete(
        f"""SELECT procedure, hors_chaine, sum(nb_engagements)::int AS nb_engagements,
                   sum(montant_engage) AS montant_engage, sum(montant_ordonnance) AS montant_ordonnance,
                   sum(montant_paye) AS montant_paye
            FROM {src} WHERE {where}
            GROUP BY 1, 2 ORDER BY 4 DESC""",
        params,
    )
    for r in rows:
        r["paye_sur_ordonnance"] = regles.taux(r["montant_paye"], r["montant_ordonnance"])
    return rows


def beneficiaires(f: Filtres, top: int = 10) -> dict:
    where, params = f.where()
    src, params_src = criteres.source("mv_depense_beneficiaires", f)
    params = params_src + params
    total = _requete(f"SELECT coalesce(sum(montant_engage), 0) AS t FROM {src} WHERE {where}", params)[0]["t"]
    rows = _requete(
        f"""SELECT beneficiaire_id, beneficiaire, sum(nb_engagements)::int AS nb_engagements,
                   sum(montant_engage) AS montant_engage, sum(montant_paye) AS montant_paye
            FROM {src} WHERE {where}
            GROUP BY 1, 2 ORDER BY 4 DESC LIMIT %s""",
        params + [top],
    )
    for r in rows:
        r["part"] = regles.taux(r["montant_engage"], total)
    return {"total_engage": total, "beneficiaires": rows}


# ------------------------------------------------------------- Simandou 2040

# En-têtes de colonnes de l'extraction, conservés tels quels dans `attributs` (orthographe de la source).
PILIER = "pillier simandou"
GREEN = "projet green"
LIBELLES_PILIERS = {
    "Sante et Bien-etre": "Santé et bien-être",
    "Education et Culture": "Éducation et culture",
    "Infrastructures, Technologie et Transport": "Infrastructures, technologie et transport",
    "Agriculture, Industrie alimentaire et Commerce": "Agriculture, industrie alimentaire et commerce",
    "Economie, Finances et Assurances": "Économie, finances et assurances",
}


def simandou(f: Filtres) -> dict:
    """Exécution par pilier du programme Simandou 2040 et des projets « green » (colonnes de l'extraction)."""
    where, params = f.where("l")
    cl, pl = criteres.clause_ligne(f, "l")
    where, params = f"{where} AND {cl}", params + pl
    actifs = "l.chargement_id IN (SELECT id FROM mart.v_chargements_actifs)"
    green = f"upper(l.attributs->>'{GREEN}') = 'OUI'"
    rows = _requete(
        f"""SELECT nullif({criteres.pilier_sql("l")}, '') AS pilier, l.section_code,
                   count(*) AS nb_lignes,
                   sum(l.credit_actuel) AS credit_actuel, sum(l.credit_engage) AS credit_engage,
                   sum(l.montant_ordonnance) AS montant_ordonnance, sum(l.montant_paye) AS montant_paye,
                   count(*) FILTER (WHERE {green}) AS nb_green,
                   coalesce(sum(l.credit_actuel) FILTER (WHERE {green}), 0) AS credit_green,
                   coalesce(sum(l.credit_engage) FILTER (WHERE {green}), 0) AS engage_green
            FROM dw.fait_situation_ligne l
            WHERE {actifs} AND {where}
            GROUP BY 1, 2""",
        params,
    )
    libelles = _libelles_sections(f)
    mesures = ("nb_lignes", "credit_actuel", "credit_engage", "montant_ordonnance", "montant_paye")
    piliers: dict[Optional[str], dict] = {}
    for r in rows:
        p = piliers.setdefault(r["pilier"], {m: D0 for m in mesures} | {"ministeres": []})
        for m in mesures:
            p[m] += r[m]
        p["ministeres"].append(
            {
                "code": r["section_code"],
                "libelle_court": libelles.get(r["section_code"], {}).get("libelle_court", r["section_code"]),
                "credit_actuel": r["credit_actuel"],
            }
        )
    total = sum((p["credit_actuel"] for p in piliers.values()), D0)

    def decrire(code: Optional[str], p: dict) -> dict:
        return {
            "pilier": code,
            "libelle": LIBELLES_PILIERS.get(code, code) if code else "Pilier non renseigné",
            "nb_lignes": int(p["nb_lignes"]),
            "nb_ministeres": len(p["ministeres"]),
            "credit_actuel": p["credit_actuel"],
            "credit_engage": p["credit_engage"],
            "montant_ordonnance": p["montant_ordonnance"],
            "montant_paye": p["montant_paye"],
            "part": regles.taux(p["credit_actuel"], total),
            "taux_engagement": regles.taux(p["credit_engage"], p["credit_actuel"]),
            "taux_paiement": regles.taux_paiement(p["montant_paye"], p["montant_ordonnance"]),
            "empile": {
                "paye": p["montant_paye"],
                "ordonnance_non_paye": max(p["montant_ordonnance"] - p["montant_paye"], D0),
                "engage_non_ordonnance": max(p["credit_engage"] - p["montant_ordonnance"], D0),
                "disponible": max(p["credit_actuel"] - p["credit_engage"], D0),
            },
            "principaux_ministeres": sorted(p["ministeres"], key=lambda m: m["credit_actuel"], reverse=True)[:3],
        }

    liste = sorted((decrire(c, p) for c, p in piliers.items() if c), key=lambda p: p["credit_actuel"], reverse=True)
    credit_simandou = sum((p["credit_actuel"] for p in liste), D0)
    engage_simandou = sum((p["credit_engage"] for p in liste), D0)
    credit_green = sum((r["credit_green"] for r in rows), D0)
    engage_green = sum((r["engage_green"] for r in rows), D0)
    return {
        "piliers": liste,
        "hors_pilier": decrire(None, piliers[None]) if None in piliers else None,
        "credit_simandou": credit_simandou,
        "part_simandou": regles.taux(credit_simandou, total),
        "taux_engagement_simandou": regles.taux(engage_simandou, credit_simandou),
        "green": {
            "nb_lignes": sum(int(r["nb_green"]) for r in rows),
            "credit_actuel": credit_green,
            "credit_engage": engage_green,
            "part": regles.taux(credit_green, total),
            "taux_engagement": regles.taux(engage_green, credit_green),
        },
    }


# ------------------------------------------------------------- investissement


def projets_investissement(f: Filtres) -> list[dict]:
    fi = Filtres(f.exercice, f.date_situation, None, f.section, f.paiement)
    where, params = fi.where(avec_titre=False)
    rows = _requete(
        f"""SELECT section_code, sous_section_code, projet, sum(credit_initial_lfi) AS credit_initial_lfi,
                   sum(credit_actuel) AS credit_actuel, sum(credit_engage) AS credit_engage,
                   sum(montant_ordonnance) AS montant_ordonnance, sum(montant_paye) AS montant_paye
            FROM mart.mv_investissement_projets WHERE {where}
            GROUP BY 1, 2, 3""",
        params,
    )
    for r in rows:
        r["sans_engagement"] = regles.est_projet_sans_engagement("5", r["credit_actuel"], r["credit_engage"])
        r["taux_engagement"] = regles.taux(r["credit_engage"], r["credit_actuel"])
    return rows


def synthese_investissement(f: Filtres) -> dict:
    projets = projets_investissement(f)
    sans = [p for p in projets if p["sans_engagement"]]
    libelles = _libelles_sections(f)
    par_min: dict[str, dict] = {}
    for p in projets:
        m = par_min.setdefault(p["section_code"], {"credit_actuel": D0, "credit_engage": D0})
        m["credit_actuel"] += p["credit_actuel"]
        m["credit_engage"] += p["credit_engage"]
    ministeres = sorted(
        (
            {
                "code": c,
                "libelle_court": libelles.get(c, {}).get("libelle_court", c),
                **v,
                "taux_engagement": regles.taux(v["credit_engage"], v["credit_actuel"]),
            }
            for c, v in par_min.items()
        ),
        key=lambda m: m["credit_actuel"],
        reverse=True,
    )
    total = {
        k: sum((p[k] for p in projets), D0)
        for k in ("credit_initial_lfi", "credit_actuel", "credit_engage", "montant_ordonnance", "montant_paye")
    }
    grands = sorted(projets, key=lambda p: p["credit_actuel"], reverse=True)[:12]
    for p in grands:
        p["ministere"] = libelles.get(p["section_code"], {}).get("libelle_court", p["section_code"])
    return {
        **total,
        "taux_engagement": regles.taux(total["credit_engage"], total["credit_actuel"]),
        "nb_projets": len(projets),
        "nb_projets_sans_engagement": len(sans),
        "credits_projets_sans_engagement": sum((p["credit_actuel"] for p in sans), D0),
        "grands_projets": grands,
        "top_ministeres": ministeres[:8],
    }


def date_reference(f: Filtres) -> Optional[date]:
    return f.date_situation


# ------------------------------------------------------------------ projection de fin d'exercice


def _serie_engagements(f: Filtres, par_section: bool = False) -> list[dict]:
    return [{**r, "montant": r["montant_engage"]} for r in _mensuel_engagements(f, par_section)]


def projection(f: Filtres) -> dict:
    """Engagement projeté au 31 décembre : ensemble, puis ministères les plus éloignés de leurs crédits."""
    from apps.core.filtres import dernieres_situations
    from apps.core.projections import projeter

    i = indicateurs(f)
    serie = {r["mois"]: r["montant"] for r in _serie_engagements(f)}
    # Exercice précédent, s'il est chargé : sa dernière situation donne le profil de fin d'année.
    precedent = None
    jour_precedent = next((d for e, d in dernieres_situations("chaine_depense") if e == f.exercice - 1), None)
    if jour_precedent:
        fp = replace(f, exercice=f.exercice - 1, date_situation=jour_precedent)
        precedent = {r["mois"]: r["montant"] for r in _serie_engagements(fp) if r["mois"].year == fp.exercice}
    ensemble = projeter(
        serie,
        f.date_situation,
        cible=i["credit_actuel"],
        realise=i["credit_engage"],
        precedent=precedent,
        plafonner=True,
        exercice=f.exercice,
    )
    if not mensuel(f)["rapprochement"]["concordant"]:
        ensemble.update(
            {
                "fiable": False,
                "central": None,
                "bas": None,
                "haut": None,
                "methodes": {},
                "trajectoire": [],
                "motif": "Projection suspendue : la série mensuelle n'est pas rapprochée avec la situation budgétaire.",
            }
        )

    ministeres = []
    if ensemble["fiable"] and not f.section:
        series: dict[str, dict] = {}
        for r in _serie_engagements(f, par_section=True):
            series.setdefault(r["section_code"], {})[r["mois"]] = r["montant"]
        minimum = regles.parametre("sous_execution_credits_min")
        for s in sections(f):
            if s["credit_actuel"] < minimum:
                continue
            p = projeter(
                series.get(s["code"], {}),
                f.date_situation,
                cible=s["credit_actuel"],
                realise=s["credit_engage"],
                plafonner=True,
                exercice=f.exercice,
            )
            ministeres.append(
                {
                    "code": s["code"],
                    "libelle": s["libelle_court"],
                    "credit_actuel": s["credit_actuel"],
                    "credit_engage": s["credit_engage"],
                    "taux_engagement": s["taux_engagement"],
                    "projete": p["central"] if p["fiable"] else s["credit_engage"],
                    "taux_projete": regles.taux(
                        p["central"] if p["fiable"] else s["credit_engage"], s["credit_actuel"]
                    ),
                    "fiable": p["fiable"],
                    "plafonne": p["plafonne"],
                }
            )
        ministeres.sort(key=lambda m: (m["taux_projete"] is None, m["taux_projete"]))
    seuil = regles.parametre("projection_engagement_min")
    return {
        "engagement": ensemble,
        "seuil": seuil,
        "sous_le_seuil": ensemble["fiable"] and regles.projection_engagement_faible(ensemble["taux_haut"]),
        "ministeres": ministeres,
        "nb_ministeres_sous_le_seuil": sum(
            1 for m in ministeres if m["taux_projete"] is not None and m["taux_projete"] < seuil
        ),
        "exercice_precedent": bool(precedent),
    }


# --------------------------------------------------------- répartitions de l'exécution

# Référentiels de la Chaîne Dépense (GDEP.TC_DIVISION, TC_ZONE_GEO, TC_TYPE_BUDGET), relevés le 18/11/2026.
# Ils servent de repli quand l'extraction (Excel) ne fournit que le code ou que le libellé.
FONCTIONS = {
    "700": "Non codifié",
    "701": "Services généraux des administrations publiques",
    "702": "Défense",
    "703": "Ordre et sécurité publics",
    "704": "Affaires économiques",
    "705": "Protection de l'environnement",
    "706": "Logement et équipements collectifs",
    "707": "Santé",
    "708": "Loisirs, culture et culte",
    "709": "Enseignement",
    "710": "Protection sociale",
}
ZONES = {
    "0": "Tout le territoire guinéen",
    "1": "Services centraux",
    "2": "Services déconcentrés · Conakry",
    "3": "Services déconcentrés · intérieur",
    "4": "Services déconcentrés · extérieur",
    "5": "Services décentralisés · Conakry",
    "6": "Services décentralisés · intérieur",
}
TYPES_BUDGET = {
    "000": "Budget général",
    "101": "BAS FNDL/ANAFIC",
    "102": "BAS FODECON/AFICON",
    "103": "BAS RSU",
    "104": "BAS FCE",
    "105": "BAS FIM",
}


def _cle_libelle(texte: str) -> str:
    import unicodedata

    t = unicodedata.normalize("NFD", texte or "")
    return " ".join("".join(c for c in t if unicodedata.category(c) != "Mn").lower().split())


_FONCTION_PAR_LIBELLE = {_cle_libelle(v): k for k, v in FONCTIONS.items()}


MESURES_REPARTIES = ("credit", "engage", "liquide", "ordonnance", "vbp", "paye")


def repartitions(f: Filtres) -> dict:
    """Crédits et étapes de dépense par pilier Simandou, titre, fonction, zone et type de budget.

    Montants bruts de la situation (même base que les taux). Un axe absent de l'extraction
    est signalé « non disponible » plutôt que présenté comme une seule catégorie.
    """
    # Le filtre de nature (titre) ne s'applique pas à l'axe « titre » lui-même : il resterait une seule part.
    where, params = f.where("l", avec_titre=False)
    cl, pl = criteres.clause_ligne(f, "l", sauf=("titres",))
    where, params = f"{where} AND {cl}", params + pl
    titres_retenus = set(f.criteres.get("titres", ())) | ({f.titre} if f.titre else set())
    rows = _requete(
        f"""SELECT l.titre, l.type_budget,
                   nullif(l.attributs->>'code_fonction', '') AS code_fonction,
                   nullif(l.attributs->>'fonctionnelle', '') AS fonction,
                   {criteres.zone_sql("l")} AS code_zone,
                   nullif(l.attributs->>'zone_geographique', '') AS zone,
                   nullif({criteres.pilier_sql("l")}, '') AS pilier,
                   sum(l.credit_actuel) AS credit,
                   sum(l.credit_engage) AS engage, sum(l.montant_liquide) AS liquide,
                   sum(l.montant_ordonnance) AS ordonnance, sum(l.montant_vbp) AS vbp,
                   sum(l.montant_paye) AS paye
            FROM dw.fait_situation_ligne l
            WHERE l.chargement_id IN (SELECT id FROM mart.v_chargements_actifs) AND {where}
            GROUP BY 1, 2, 3, 4, 5, 6, 7""",
        params,
    )

    axes: dict[str, dict[str, dict]] = {"pilier": {}, "titre": {}, "fonction": {}, "zone": {}, "type_budget": {}}
    renseignes = {"pilier": False, "fonction": False, "zone": False}

    def ajouter(axe: str, code: str, libelle: str, r: dict) -> None:
        p = axes[axe].setdefault(code, {"code": code, "libelle": libelle, **{m: D0 for m in MESURES_REPARTIES}})
        for m in MESURES_REPARTIES:
            p[m] += r[m] or D0

    for r in rows:
        ajouter("titre", r["titre"], f"{r['titre']} · {TITRES.get(r['titre'], 'Titre ' + r['titre'])}", r)
        if titres_retenus and r["titre"] not in titres_retenus:
            continue
        pilier = r["pilier"]
        if pilier:
            renseignes["pilier"] = True
        ajouter("pilier", pilier or "?", LIBELLES_PILIERS.get(pilier, pilier) if pilier else "Pilier non renseigné", r)
        code_f = r["code_fonction"] or _FONCTION_PAR_LIBELLE.get(_cle_libelle(r["fonction"] or ""))
        if code_f or r["fonction"]:
            renseignes["fonction"] = True
        code_f = code_f or "?"
        ajouter("fonction", code_f, f"{code_f} · {FONCTIONS.get(code_f, r['fonction'] or 'Non renseignée')}", r)
        if r["code_zone"]:
            renseignes["zone"] = True
        code_z = r["code_zone"] or "?"
        ajouter("zone", code_z, ZONES.get(code_z, r["zone"] or "Non renseignée"), r)
        tb = r["type_budget"] or "?"
        ajouter("type_budget", tb, TYPES_BUDGET.get(tb, f"Type de budget {tb}"), r)

    def sortie(axe: str, titre: str, disponible: bool = True) -> dict:
        parts = sorted(axes[axe].values(), key=lambda p: -p["engage"])
        return {"axe": axe, "titre": titre, "disponible": disponible and bool(parts), "parts": parts}

    return {
        "axes": [
            sortie("pilier", "Par pilier Simandou", renseignes["pilier"]),
            sortie("titre", "Par titre"),
            sortie("fonction", "Par fonction", renseignes["fonction"]),
            sortie("zone", "Par zone d'exécution", renseignes["zone"]),
            sortie("type_budget", "Par type de budget (BAS)"),
        ],
        "titre_filtre": ", ".join(sorted(titres_retenus)) or None,
        "indisponible": {
            "pilier": "Pilier Simandou absent de cette extraction.",
            "zone": "Code de sous-section absent : la zone d'exécution ne peut pas être déterminée.",
            "fonction": "Classification fonctionnelle absente de cette extraction.",
        },
    }
