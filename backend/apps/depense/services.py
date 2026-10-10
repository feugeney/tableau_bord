"""Calculs de la page Dépenses, servis depuis la couche mart.

Les montants renvoyés sont en GNF (Decimal) ; la conversion en milliards est
faite par l'affichage. Les taux sont des ratios (0,71 = 71 %).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from django.db import connection

from apps.core import regles
from apps.core.filtres import Filtres
from apps.referentiels.models import TITRES, RefSection

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
    select = ", ".join(f"coalesce(sum({m}), 0) AS {m}" for m in MESURES)
    if group_by:
        return _entiers(
            _requete(
                f"SELECT {group_by}, {select} FROM mart.mv_depense_par_section_titre WHERE {where} "
                f"GROUP BY {group_by} ORDER BY {group_by}",
                params,
            )
        )
    return _entiers(_requete(f"SELECT {select} FROM mart.mv_depense_par_section_titre WHERE {where}", params))


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
    return {
        "credit_initial_lfi": t["credit_initial_lfi"],
        "credit_actuel": t["credit_actuel"],
        "variation_lfi": regles.taux(t["credit_actuel"] - t["credit_initial_lfi"], t["credit_initial_lfi"]),
        "credit_engage": t["credit_engage"],
        "taux_engagement": regles.taux_engagement(t["credit_engage"], t["credit_actuel"]),
        "montant_liquide": t["montant_liquide"],
        "montant_ordonnance": t["montant_ordonnance"],
        "taux_ordonnancement": regles.taux_ordonnancement(t["montant_ordonnance"], t["credit_actuel"]),
        "montant_paye": t["montant_paye"],
        "taux_paiement": regles.taux_paiement(t["montant_paye"], t["credit_actuel"]),
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
    lignes = _totaux(Filtres(f.exercice, f.date_situation, None, f.section, f.paiement), group_by="titre")
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


def _libelles_sections() -> dict[str, dict]:
    return {
        s.code: {"libelle": s.libelle, "libelle_court": s.libelle_affiche, "type": s.type}
        for s in RefSection.objects.all()
    }


def sections(f: Filtres, surcharges=None) -> list[dict]:
    lignes = _totaux(Filtres(f.exercice, f.date_situation, f.nature, None, f.paiement), group_by="section_code")
    libelles = _libelles_sections()
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
                "montant_ordonnance": pay.ordonnance,
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
    fs = Filtres(f.exercice, f.date_situation, f.nature, code, f.paiement)
    where, params = fs.where("l", avec_titre=False)
    titre_sql, titre_params = ("AND l.titre = %s", [fs.titre]) if fs.titre else ("", [])
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
    lib = _libelles_sections().get(code, {})
    return {
        "code": code,
        "libelle": lib.get("libelle", code),
        "libelle_court": lib.get("libelle_court", code),
        "natures": natures(fs),
        "top_sous_sections": top,
        "lignes_depassement": depassement,
    }


def compter_lignes(f: Filtres, condition: str, params_condition: Optional[list] = None) -> int:
    where, params = f.where()
    rows = _requete(
        f"""SELECT count(*) AS n FROM dw.fait_situation_ligne
            WHERE chargement_id IN (SELECT id FROM mart.v_chargements_actifs) AND {where} AND {condition}""",
        params + (params_condition or []),
    )
    return rows[0]["n"]


def compter_lignes_par_section(f: Filtres) -> dict[str, int]:
    where, params = Filtres(f.exercice, f.date_situation, f.nature, None).where()
    rows = _requete(
        f"""SELECT section_code, count(*) AS n FROM dw.fait_situation_ligne
            WHERE chargement_id IN (SELECT id FROM mart.v_chargements_actifs) AND {where}
              AND credit_disponible < %s GROUP BY 1""",
        params + [regles.parametre("depassement_disponible_max")],
    )
    return {r["section_code"]: r["n"] for r in rows}


def lignes_en_depassement(f: Filtres) -> int:
    return compter_lignes(f, "credit_disponible < %s", [regles.parametre("depassement_disponible_max")])


def mensuel(f: Filtres) -> dict:
    where, params = f.where()
    rows = _requete(
        f"""SELECT mois, sum(montant_engage) AS montant_engage, sum(nb_engagements)::int AS nb_engagements
            FROM mart.mv_depense_mensuelle WHERE {where} GROUP BY mois ORDER BY mois""",
        params,
    )
    for r in rows:
        r["periode_complementaire"] = bool(f.exercice and r["mois"].year > f.exercice)
        r["decembre"] = r["mois"].month == 12 and r["mois"].year == f.exercice
    return {
        "mois": rows,
        "engage_periode_complementaire": sum((r["montant_engage"] for r in rows if r["periode_complementaire"]), D0),
    }


def restes_a_payer_anciennete(f: Filtres) -> dict:
    where, params = f.where()
    hors = "" if f.paiement == "brut" else "AND NOT hors_chaine"
    rows = _requete(
        f"""SELECT mois_creation, sum(reste_a_payer) AS reste_a_payer, sum(nb_engagements)::int AS nb_engagements
            FROM mart.mv_restes_a_payer_anciennete WHERE {where} {hors}
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
    rows = _requete(
        f"""SELECT procedure, hors_chaine, sum(nb_engagements)::int AS nb_engagements,
                   sum(montant_engage) AS montant_engage, sum(montant_ordonnance) AS montant_ordonnance,
                   sum(montant_paye) AS montant_paye
            FROM mart.mv_depense_procedures WHERE {where}
            GROUP BY 1, 2 ORDER BY 4 DESC""",
        params,
    )
    for r in rows:
        r["paye_sur_ordonnance"] = regles.taux(r["montant_paye"], r["montant_ordonnance"])
    return rows


def beneficiaires(f: Filtres, top: int = 10) -> dict:
    where, params = f.where()
    total = _requete(
        f"SELECT coalesce(sum(montant_engage), 0) AS t FROM mart.mv_depense_beneficiaires WHERE {where}", params
    )[0]["t"]
    rows = _requete(
        f"""SELECT beneficiaire_id, beneficiaire, sum(nb_engagements)::int AS nb_engagements,
                   sum(montant_engage) AS montant_engage, sum(montant_paye) AS montant_paye
            FROM mart.mv_depense_beneficiaires WHERE {where}
            GROUP BY 1, 2 ORDER BY 4 DESC LIMIT %s""",
        params + [top],
    )
    for r in rows:
        r["part"] = regles.taux(r["montant_engage"], total)
    return {"total_engage": total, "beneficiaires": rows}


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
    libelles = _libelles_sections()
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
