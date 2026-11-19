"""Filtres à critères multiples de la page Dépenses.

Chaque critère accepte plusieurs valeurs (OU à l'intérieur d'un critère, ET entre critères).
Ministère et titre existent dans les vues « mart » ; les autres critères n'existent qu'au niveau
de la ligne budgétaire. Dès qu'un de ces critères est actif, les calculs repartent des tables
de faits (`source()`), avec la même définition que les vues mart.

Les engagements portent le ministère, le titre, le type de budget, la source et le bailleur ;
le programme, la fonction, le pilier et la zone se lisent sur la ligne budgétaire de même
imputation, dans le même chargement.
"""

from __future__ import annotations

from typing import Optional

from apps.core.filtres import CRITERES, Filtres

ACTIFS = "chargement_id IN (SELECT id FROM mart.v_chargements_actifs)"


def _fonction(a: str) -> str:
    """Code de fonction : fourni par Oracle, ou déduit du libellé de l'extraction Excel."""
    from .services import FONCTIONS, _cle_libelle

    # Libellés constants du référentiel (pas de saisie utilisateur) ; apostrophes doublées pour SQL.
    cas = " ".join(f"WHEN '{_cle_libelle(v).replace(chr(39), chr(39) * 2)}' THEN '{k}'" for k, v in FONCTIONS.items())
    return (
        f"coalesce(nullif({a}.attributs->>'code_fonction', ''), "
        f"CASE lower(trim(translate({a}.attributs->>'fonctionnelle', 'éèêàâîôûç', 'eeeaaiouc'))) {cas} END)"
    )


# GDEP.TC_PILLIER_SIMANDOU (relevé le 19/11/2026) → libellé de l'extraction Excel, forme de référence.
PILIERS_ORACLE = {
    "1": "Agriculture, Industrie alimentaire et Commerce",
    "2": "Education et Culture",
    "3": "Infrastructures, Technologie et Transport",
    "4": "Economie, Finances et Assurances",
    "5": "Sante et Bien-etre",
}


def pilier_sql(a: str) -> str:
    """Pilier Simandou sous sa forme de référence, quelle que soit l'extraction.

    Excel : libellé sans accents (« pillier simandou ») ; Oracle : identifiant 1 à 5 (ancienne clé
    « pilier_simandou ») ou libellé accentué de TC_PILLIER_SIMANDOU.
    """
    brut = f"coalesce(nullif({a}.attributs->>'pillier simandou', ''), nullif({a}.attributs->>'pilier_simandou', ''))"
    cle = f"lower(translate(trim({brut}), 'éèêàâîôûçÉ', 'eeeaaioucE'))"
    cas = " ".join(f"WHEN '{k}' THEN '{v}' WHEN '{v.lower()}' THEN '{v}'" for k, v in PILIERS_ORACLE.items())
    return f"(CASE {cle} {cas} ELSE {brut} END)"


def zone_sql(a: str) -> str:
    """Zone d'exécution : fournie par Oracle, sinon 6e chiffre du code de sous-section.

    Règle vérifiée le 18/11/2026 sur GDEP.TC_SOUS_SECTION 2024 à 2026 : le 6e chiffre du code
    est toujours le CODE_ZONE_GEOGRAPHIQUE (0 à 6), sans exception.
    """
    return (
        f"coalesce(nullif({a}.attributs->>'code_zone_geographique', ''), "
        f"CASE WHEN substr({a}.sous_section_code, 6, 1) BETWEEN '0' AND '6' "
        f"THEN substr({a}.sous_section_code, 6, 1) END)"
    )


# Expression SQL du critère sur une ligne budgétaire (alias a) ; colonne directe de l'engagement si elle existe.
LIGNE = {
    "ministeres": lambda a: f"{a}.section_code",
    "programmes": lambda a: f"{a}.attributs->>'programme'",
    "titres": lambda a: f"{a}.titre",
    "fonctions": _fonction,
    "piliers": lambda a: pilier_sql(a),
    "types_budget": lambda a: f"{a}.type_budget",
    "zones": lambda a: zone_sql(a),
    "sources": lambda a: f"{a}.source_financement",
    "bailleurs": lambda a: f"{a}.bailleur",
}
ENGAGEMENT_DIRECT = {"ministeres", "titres", "types_budget", "sources", "bailleurs"}
# Colonnes d'imputation partagées par la ligne budgétaire et l'engagement.
IMPUTATION = (
    "section_code",
    "titre",
    "chapitre",
    "article",
    "paragraphe",
    "sous_paragraphe",
    "source_financement",
    "groupe_bailleur",
    "bailleur",
    "type_budget",
)
MART = {"ministeres", "titres"}


def actifs(f: Filtres) -> dict[str, tuple[str, ...]]:
    return {k: v for k, v in (f.criteres or {}).items() if v}


def hors_mart(f: Filtres) -> bool:
    """Vrai si un critère n'existe pas dans les vues mart (calcul depuis les tables de faits)."""
    return any(k not in MART for k in actifs(f))


def _in(expr: str, valeurs: tuple[str, ...], params: list) -> str:
    params.extend(valeurs)
    return f"{expr} IN ({', '.join(['%s'] * len(valeurs))})"


def clause_ligne(f: Filtres, a: str = "l", sauf: tuple[str, ...] = ()) -> tuple[str, list]:
    """Conditions sur une ligne budgétaire (alias a). Renvoie « TRUE » sans critère."""
    params: list = []
    conditions = [_in(LIGNE[k](a), v, params) for k, v in actifs(f).items() if k not in sauf]
    return (" AND ".join(conditions) or "TRUE"), params


def clause_engagement(f: Filtres, a: str = "e", sauf: tuple[str, ...] = ()) -> tuple[str, list]:
    """Conditions sur un engagement (alias a) : directes, ou via la ligne budgétaire de même imputation."""
    params: list = []
    criteres = {k: v for k, v in actifs(f).items() if k not in sauf}
    conditions = [_in(LIGNE[k](a), v, params) for k, v in criteres.items() if k in ENGAGEMENT_DIRECT]
    indirects = {k: v for k, v in criteres.items() if k not in ENGAGEMENT_DIRECT}
    if indirects:
        jointure = " AND ".join(
            [
                f"l2.chargement_id = {a}.chargement_id",
                f"l2.sous_section_code IS NOT DISTINCT FROM {a}.sous_section_code",
            ]
            + [f"l2.{c} = {a}.{c}" for c in IMPUTATION]
        )
        sous: list = []
        filtres = " AND ".join(_in(LIGNE[k]("l2"), v, sous) for k, v in indirects.items())
        conditions.append(f"EXISTS (SELECT 1 FROM dw.fait_situation_ligne l2 WHERE {jointure} AND {filtres})")
        params.extend(sous)
    return (" AND ".join(conditions) or "TRUE"), params


def source(nom: str, f: Filtres) -> tuple[str, list]:
    """Vue mart, ou sa définition recalculée sur les tables de faits avec les critères de la ligne."""
    if not hors_mart(f):
        return f"mart.{nom}", []
    cl, pl = clause_ligne(f, "l")
    ce, pe = clause_engagement(f, "e")

    def periode(a: str) -> str:
        return f"{a}.exercice = %s AND {a}.date_situation = %s"

    per = [f.exercice, f.date_situation]
    if nom == "mv_depense_par_section_titre":
        sql = f"""(
            WITH sit AS (
                SELECT l.exercice, l.date_situation, l.section_code, l.titre, count(*) AS nb_lignes,
                       sum(l.credit_initial_lfi) AS credit_initial_lfi, sum(l.credit_lfr) AS credit_lfr,
                       sum(l.credit_actuel) AS credit_actuel, sum(l.credit_disponible) AS credit_disponible,
                       sum(l.credit_engage) AS credit_engage, sum(l.montant_liquide) AS montant_liquide,
                       sum(l.montant_ordonnance) AS montant_ordonnance, sum(l.montant_vbp) AS montant_vbp,
                       sum(l.montant_paye) AS montant_paye,
                       count(*) FILTER (WHERE l.lfi_absent) AS nb_lfi_absent
                FROM dw.fait_situation_ligne l
                WHERE l.{ACTIFS} AND {periode("l")} AND {cl}
                GROUP BY 1, 2, 3, 4
            ), eng AS (
                SELECT e.exercice, e.date_situation, e.section_code, e.titre, count(*) AS nb_engagements,
                       coalesce(sum(e.montant_ordonnance) FILTER (WHERE p.paiement_hors_chaine), 0)
                           AS ordonnance_hors_chaine,
                       coalesce(sum(e.montant_paye) FILTER (WHERE p.paiement_hors_chaine), 0) AS paye_hors_chaine
                FROM dw.fait_engagement e
                LEFT JOIN ref.ref_type_procedure p ON p.id = e.type_procedure_id
                WHERE e.{ACTIFS} AND {periode("e")} AND {ce}
                GROUP BY 1, 2, 3, 4
            )
            SELECT coalesce(s.exercice, e.exercice) AS exercice,
                   coalesce(s.date_situation, e.date_situation) AS date_situation,
                   coalesce(s.section_code, e.section_code) AS section_code,
                   coalesce(s.titre, e.titre) AS titre,
                   coalesce(s.nb_lignes, 0) AS nb_lignes,
                   coalesce(s.credit_initial_lfi, 0) AS credit_initial_lfi,
                   coalesce(s.credit_lfr, 0) AS credit_lfr, coalesce(s.credit_actuel, 0) AS credit_actuel,
                   coalesce(s.credit_disponible, 0) AS credit_disponible,
                   coalesce(s.credit_engage, 0) AS credit_engage,
                   coalesce(s.montant_liquide, 0) AS montant_liquide,
                   coalesce(s.montant_ordonnance, 0) AS montant_ordonnance,
                   coalesce(s.montant_vbp, 0) AS montant_vbp, coalesce(s.montant_paye, 0) AS montant_paye,
                   coalesce(s.nb_lfi_absent, 0) AS nb_lfi_absent,
                   coalesce(e.nb_engagements, 0) AS nb_engagements,
                   coalesce(e.ordonnance_hors_chaine, 0) AS ordonnance_hors_chaine,
                   coalesce(e.paye_hors_chaine, 0) AS paye_hors_chaine
            FROM sit s
            FULL OUTER JOIN eng e
              ON e.exercice = s.exercice AND e.date_situation = s.date_situation
             AND e.section_code = s.section_code AND e.titre = s.titre
        ) m"""
        return sql, [*per, *pl, *per, *pe]
    if nom == "mv_restes_a_payer_anciennete":
        sql = f"""(
            SELECT e.exercice, e.date_situation, e.section_code, e.titre,
                   date_trunc('month', e.date_creation)::date AS mois_creation,
                   coalesce(p.paiement_hors_chaine, false) AS hors_chaine,
                   count(*) AS nb_engagements, sum(e.montant_ordonnance - e.montant_paye) AS reste_a_payer
            FROM dw.fait_engagement e
            LEFT JOIN ref.ref_type_procedure p ON p.id = e.type_procedure_id
            WHERE e.{ACTIFS} AND {periode("e")} AND e.montant_ordonnance > e.montant_paye AND {ce}
            GROUP BY 1, 2, 3, 4, 5, 6
        ) m"""
        return sql, [*per, *pe]
    if nom == "mv_depense_procedures":
        sql = f"""(
            SELECT e.exercice, e.date_situation, e.section_code, e.titre,
                   p.id AS type_procedure_id, coalesce(p.libelle, '(non renseigné)') AS procedure,
                   coalesce(p.paiement_hors_chaine, false) AS hors_chaine,
                   count(*) AS nb_engagements, sum(e.montant_engage) AS montant_engage,
                   sum(e.montant_ordonnance) AS montant_ordonnance, sum(e.montant_paye) AS montant_paye
            FROM dw.fait_engagement e
            LEFT JOIN ref.ref_type_procedure p ON p.id = e.type_procedure_id
            WHERE e.{ACTIFS} AND {periode("e")} AND {ce}
            GROUP BY 1, 2, 3, 4, 5, 6, 7
        ) m"""
        return sql, [*per, *pe]
    if nom == "mv_depense_beneficiaires":
        sql = f"""(
            SELECT e.exercice, e.date_situation, e.section_code, e.titre,
                   e.beneficiaire_id, coalesce(b.nom_affiche, '(non renseigné)') AS beneficiaire,
                   count(*) AS nb_engagements, sum(e.montant_engage) AS montant_engage,
                   sum(e.montant_paye) AS montant_paye
            FROM dw.fait_engagement e
            LEFT JOIN ref.ref_beneficiaire b ON b.id = e.beneficiaire_id
            WHERE e.{ACTIFS} AND {periode("e")} AND {ce}
            GROUP BY 1, 2, 3, 4, 5, 6
        ) m"""
        return sql, [*per, *pe]
    raise ValueError(f"Vue sans équivalent filtrable : {nom}")


def extra_orm(f: Filtres, table: str, engagement: bool = False) -> Optional[tuple[list[str], list]]:
    """Conditions pour QuerySet.extra(where=…) sur une table de faits (nom SQL entre guillemets)."""
    if not actifs(f):
        return None
    clause, params = clause_engagement(f, table) if engagement else clause_ligne(f, table)
    return [clause], params


__all__ = ["CRITERES", "actifs", "clause_engagement", "clause_ligne", "extra_orm", "hors_mart", "source"]


LIBELLES_CRITERES = {
    "ministeres": "Ministère / institution",
    "programmes": "Programme",
    "titres": "Titre",
    "fonctions": "Fonction",
    "piliers": "Pilier Simandou 2040",
    "types_budget": "Type de budget (BAS)",
    "zones": "Zone d'exécution",
    "sources": "Source de financement",
    "bailleurs": "Bailleur",
}
SOURCES_FINANCEMENT = {"1": "Source extérieure de financement", "2": "Source intérieure de financement"}
# Libellé fourni par l'extraction Oracle, quand il existe, pour les codes qui n'ont pas de référentiel local.
LIBELLE_EXTRAIT = {"programmes": "libelle_programme", "bailleurs": "libelle_bailleur"}


def options(f: Filtres) -> dict:
    """Valeurs proposées pour chaque critère : situation courante entière, sans les critères eux-mêmes."""
    from django.db import connection

    from apps.referentiels.models import TITRES, RefBailleur, RefSourceFinancement

    from .services import FONCTIONS, LIBELLES_PILIERS, TYPES_BUDGET, ZONES, _libelles_sections

    sections = _libelles_sections(f)
    referentiels = {
        "titres": TITRES,
        "fonctions": FONCTIONS,
        "piliers": LIBELLES_PILIERS,
        "types_budget": TYPES_BUDGET,
        "zones": ZONES,
        "sources": {
            **dict(RefSourceFinancement.objects.exclude(libelle="").values_list("code", "libelle")),
            **SOURCES_FINANCEMENT,  # libellés accentués prioritaires
        },
        "bailleurs": dict(RefBailleur.objects.exclude(libelle="").values_list("code", "libelle")),
    }
    sortie = []
    with connection.cursor() as c:
        for cle in CRITERES:
            extrait = LIBELLE_EXTRAIT.get(cle)
            libelle_sql = f"max(l.attributs->>'{extrait}')" if extrait else "NULL"
            c.execute(
                f"""SELECT {LIGNE[cle]("l")} AS code, {libelle_sql} AS libelle, count(*) AS n,
                           coalesce(sum(l.credit_actuel), 0) AS credit
                    FROM dw.fait_situation_ligne l
                    WHERE l.{ACTIFS} AND l.exercice = %s AND l.date_situation = %s
                    GROUP BY 1 ORDER BY 4 DESC""",
                [f.exercice, f.date_situation],
            )
            valeurs = []
            for code, libelle, n, credit in c.fetchall():
                if code in (None, ""):
                    continue
                if cle == "ministeres":
                    nom = sections.get(code, {}).get("libelle_court") or f"Section {code}"
                else:
                    nom = (
                        referentiels.get(cle, {}).get(code)
                        or (libelle or "").strip().title()
                        or f"{LIBELLES_CRITERES[cle].split(' ')[0]} {code}"
                    )
                valeurs.append({"code": code, "libelle": nom, "nb_lignes": n, "credit": credit})
            if cle in ("titres", "fonctions", "zones", "types_budget", "sources"):
                valeurs.sort(key=lambda v: v["code"])
            raison = None
            if not valeurs:
                raison = "Absent de la situation chargée (fourni par l'extraction Oracle)."
            elif len(valeurs) == 1:
                raison = f"Une seule valeur dans la situation chargée ({valeurs[0]['libelle']})."
            sortie.append(
                {
                    "cle": cle,
                    "libelle": LIBELLES_CRITERES[cle],
                    "valeurs": valeurs,
                    "disponible": raison is None,
                    "raison": raison,
                    "selection": list(f.criteres.get(cle, ())),
                }
            )
    return {"criteres": sortie}
