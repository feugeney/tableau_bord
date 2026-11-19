"""Règles de gestion du tableau de bord — module unique et testé.

Tous les seuils sont paramétrables en base (table core_parametre). Les valeurs
ci-dessous sont les valeurs par défaut. Les montants sont exprimés en GNF.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Optional, Union

Nombre = Union[int, float, Decimal]

MILLIARD = Decimal("1000000000")

# code -> (valeur par défaut, libellé, unité)
PARAMETRES_DEFAUT: dict[str, tuple[Any, str, str]] = {
    "sous_execution_credits_min": (20 * 10**9, "Crédits actuels minimum pour le statut « Sous-exécution »", "GNF"),
    "sous_execution_taux_engagement_max": (
        0.50,
        "Taux d'engagement sous lequel un ministère est en sous-exécution",
        "taux",
    ),
    "retard_paiement_ordonnance_min": (20 * 10**9, "Ordonnancé minimum pour le statut « Paiements en retard »", "GNF"),
    "retard_paiement_taux_max": (0.35, "Payé / ordonnancé ajusté sous lequel les paiements sont en retard", "taux"),
    "a_suivre_taux_engagement_max": (0.75, "Taux d'engagement sous lequel un ministère est « À suivre »", "taux"),
    "projet_sans_engagement_credits_min": (
        1 * 10**9,
        "Crédits actuels minimum d'un projet d'investissement suivi",
        "GNF",
    ),
    "titre_investissement": ("5", "Code titre de la nature « Investissement »", "code"),
    "restes_a_payer_mois_risque": (
        12,
        "Ancienneté au-delà de laquelle le reste à payer est un risque d'arriérés",
        "mois",
    ),
    "depassement_disponible_max": (-1, "Crédits disponibles sous lesquels une ligne est en dépassement", "GNF"),
    "tresorerie_mois_seuil": (1, "Seuil de trésorerie en mois de décaissements moyens", "mois"),
    "recouvrement_taux_min": (0.80, "Réalisé / objectif sous lequel le recouvrement est en retard", "taux"),
    "dette_pib_seuil_cedeao": (0.70, "Seuil de convergence CEDEAO du ratio dette / PIB", "taux"),
    "concordance_tolerance_par_million": (1, "Écart toléré entre onglets (GNF par million)", "GNF/M"),
    "paiement_affichage_defaut": ("ajuste", "Affichage des paiements par défaut (ajuste | brut)", ""),
    "entente_directe_part_max": (
        0.10,
        "Part maximale des marchés passés par entente directe, en montant (à confirmer : code des marchés publics)",
        "taux",
    ),
    "delai_passation_max_jours": (90, "Délai de passation au-delà duquel un marché est signalé", "jours"),
    "projection_engagement_min": (
        0.80,
        "Taux d'engagement projeté au 31 décembre sous lequel une alerte est levée (à confirmer : DGB)",
        "taux",
    ),
}


def parametre(code: str, surcharges: Optional[Mapping[str, Any]] = None) -> Any:
    """Valeur d'un paramètre : surcharge explicite > base de données > défaut."""
    if surcharges and code in surcharges:
        return surcharges[code]
    if code not in PARAMETRES_DEFAUT:
        raise KeyError(f"Paramètre inconnu : {code}")
    return _parametres_base().get(code, PARAMETRES_DEFAUT[code][0])


def _parametres_base() -> dict[str, Any]:
    from django.core.cache import cache

    valeurs = cache.get("tdb:parametres")
    if valeurs is None:
        try:
            from .models import Parametre

            valeurs = dict(Parametre.objects.values_list("code", "valeur"))
        except Exception:  # base indisponible (tests purs, migrations) : défauts
            return {}
        cache.set("tdb:parametres", valeurs, 300)
    return valeurs


def invalider_cache_parametres() -> None:
    from django.core.cache import cache

    cache.delete("tdb:parametres")


def _dec(x: Optional[Nombre]) -> Decimal:
    if x is None:
        return Decimal(0)
    return x if isinstance(x, Decimal) else Decimal(str(x))


# --------------------------------------------------------------------------- taux


def taux(numerateur: Optional[Nombre], denominateur: Optional[Nombre]) -> Optional[Decimal]:
    """Ratio sûr : None si le dénominateur est nul ou absent."""
    d = _dec(denominateur)
    if d == 0:
        return None
    return _dec(numerateur) / d


# Taux de la chaîne de la dépense (décision du 18/11/2026) : chaque étape est rapportée
# à l'étape qui la précède — crédits → engagé → liquidé → ordonnancé → VBP / payé.
# Montants bruts de la situation ; les rapports aux crédits portent le suffixe « _sur_credits ».


def taux_engagement(engage, credits_actuels):
    """Engagé / crédits actuels."""
    return taux(engage, credits_actuels)


def taux_liquidation(liquide, engage):
    """Liquidé / engagé."""
    return taux(liquide, engage)


def taux_ordonnancement(ordonnance, liquide):
    """Ordonnancé / liquidé."""
    return taux(ordonnance, liquide)


def taux_vbp(vbp, ordonnance):
    """Vu bon à payer / ordonnancé."""
    return taux(vbp, ordonnance)


def taux_paiement(paye, ordonnance):
    """Payé / ordonnancé."""
    return taux(paye, ordonnance)


# --------------------------------------------------------------- paiement ajusté


@dataclass(frozen=True)
class Paiement:
    ordonnance: Decimal
    paye: Decimal
    reste_a_payer: Decimal
    paye_sur_ordonnance: Optional[Decimal]
    mode: str


def paiement(
    ordonnance_total: Nombre,
    paye_total: Nombre,
    ordonnance_hors_chaine: Nombre = 0,
    paye_hors_chaine: Nombre = 0,
    mode: str = "ajuste",
) -> Paiement:
    """Paiement « ajusté » (procédures payées hors chaîne exclues) ou « brut ».

    Les salaires (procédure Solde) et la dette (débit d'office) sont payés hors
    de la chaîne : les inclure fait apparaître un faux reste à payer.
    """
    if mode not in ("ajuste", "brut"):
        raise ValueError("mode doit valoir 'ajuste' ou 'brut'")
    o, p = _dec(ordonnance_total), _dec(paye_total)
    if mode == "ajuste":
        o -= _dec(ordonnance_hors_chaine)
        p -= _dec(paye_hors_chaine)
    return Paiement(o, p, o - p, taux(p, o), mode)


# ------------------------------------------------------------ statut ministère


@dataclass(frozen=True)
class Statut:
    code: str
    libelle: str
    severite: str  # critique | serieux | vigilance | bon


STATUT_SOUS_EXECUTION = Statut("sous_execution", "Sous-exécution", "critique")
STATUT_PAIEMENTS_RETARD = Statut("paiements_retard", "Paiements en retard", "serieux")
STATUT_A_SUIVRE = Statut("a_suivre", "À suivre", "vigilance")
STATUT_BON_RYTHME = Statut("bon_rythme", "Bon rythme", "bon")


def statut_ministere(
    credits_actuels: Nombre,
    engage: Nombre,
    ordonnance_ajuste: Nombre,
    paye_ajuste: Nombre,
    surcharges: Optional[Mapping[str, Any]] = None,
) -> Statut:
    """Statut appliqué dans l'ordre : sous-exécution, paiements en retard, à suivre, bon rythme."""
    ca, ordo = _dec(credits_actuels), _dec(ordonnance_ajuste)
    t_eng = taux(engage, ca)
    if (
        ca >= _dec(parametre("sous_execution_credits_min", surcharges))
        and t_eng is not None
        and t_eng < _dec(parametre("sous_execution_taux_engagement_max", surcharges))
    ):
        return STATUT_SOUS_EXECUTION
    t_pay = taux(paye_ajuste, ordo)
    if (
        ordo >= _dec(parametre("retard_paiement_ordonnance_min", surcharges))
        and t_pay is not None
        and t_pay < _dec(parametre("retard_paiement_taux_max", surcharges))
    ):
        return STATUT_PAIEMENTS_RETARD
    if t_eng is not None and t_eng < _dec(parametre("a_suivre_taux_engagement_max", surcharges)):
        return STATUT_A_SUIVRE
    return STATUT_BON_RYTHME


# ------------------------------------------------------------------ lignes


def est_projet_sans_engagement(
    code_titre: str, credits_actuels: Nombre, engage: Nombre, surcharges: Optional[Mapping[str, Any]] = None
) -> bool:
    """Sous-section du titre 5 dont les crédits actuels dépassent le seuil et l'engagé est nul."""
    return (
        str(code_titre).strip() == str(parametre("titre_investissement", surcharges))
        and _dec(credits_actuels) > _dec(parametre("projet_sans_engagement_credits_min", surcharges))
        and _dec(engage) == 0
    )


def est_ligne_en_depassement(credit_disponible: Nombre, surcharges: Optional[Mapping[str, Any]] = None) -> bool:
    return _dec(credit_disponible) < _dec(parametre("depassement_disponible_max", surcharges))


def liquide_depasse_engage(liquide: Nombre, engage: Nombre) -> bool:
    return _dec(liquide) > _dec(engage)


# ----------------------------------------------------------- restes à payer


def anciennete_mois(date_creation: Optional[date], date_situation: date) -> Optional[int]:
    """Nombre de mois calendaires entre la création de l'engagement et la situation."""
    if date_creation is None:
        return None
    return max(0, (date_situation.year - date_creation.year) * 12 + (date_situation.month - date_creation.month))


def est_risque_arriere(mois: Optional[int], surcharges: Optional[Mapping[str, Any]] = None) -> bool:
    return mois is not None and mois > int(parametre("restes_a_payer_mois_risque", surcharges))


# ------------------------------------------------------------- trésorerie


def jours_de_decaissements(solde: Nombre, decaissements_periode: Nombre, jours_periode: int) -> Optional[Decimal]:
    """Solde exprimé en jours de décaissements moyens de la période."""
    if jours_periode <= 0:
        return None
    moyen_jour = _dec(decaissements_periode) / jours_periode
    return taux(solde, moyen_jour)


def tresorerie_sous_seuil(
    solde: Nombre, decaissements_mensuels_moyens: Nombre, surcharges: Optional[Mapping[str, Any]] = None
) -> bool:
    seuil = _dec(decaissements_mensuels_moyens) * _dec(parametre("tresorerie_mois_seuil", surcharges))
    return _dec(solde) < seuil


# ------------------------------------------------------------- recettes


def recouvrement_en_retard(realise: Nombre, objectif: Nombre, surcharges: Optional[Mapping[str, Any]] = None) -> bool:
    t = taux(realise, objectif)
    return t is not None and t < _dec(parametre("recouvrement_taux_min", surcharges))


# ------------------------------------------------------------------ dette


@dataclass(frozen=True)
class RatioDette:
    ratio: Optional[Decimal]
    seuil: Decimal
    depasse: bool


def ratio_dette_pib(encours: Nombre, pib: Nombre, surcharges: Optional[Mapping[str, Any]] = None) -> RatioDette:
    seuil = _dec(parametre("dette_pib_seuil_cedeao", surcharges))
    r = taux(encours, pib)
    return RatioDette(r, seuil, r is not None and r > seuil)


# ----------------------------------------------------------- concordance


def concordance_ok(total_a: Nombre, total_b: Nombre, surcharges: Optional[Mapping[str, Any]] = None) -> bool:
    """Deux totaux concordent à `tolerance` GNF près par million (sur le plus grand)."""
    a, b = _dec(total_a), _dec(total_b)
    tolerance = _dec(parametre("concordance_tolerance_par_million", surcharges))
    reference = max(abs(a), abs(b))
    return abs(a - b) <= max(tolerance, reference / Decimal(1_000_000) * tolerance)


# -------------------------------------------------------------- affichage


def en_milliards(montant: Optional[Nombre], decimales: int = 2) -> Optional[Decimal]:
    if montant is None:
        return None
    return round(_dec(montant) / MILLIARD, decimales)


# --------------------------------------------------------------- marchés publics


def entente_directe_excessive(part: Nombre | None, surcharges: Optional[Mapping[str, Any]] = None) -> bool:
    """Part (en montant) des marchés passés par entente directe au-delà du seuil."""
    return part is not None and _dec(part) > _dec(parametre("entente_directe_part_max", surcharges))


def delai_passation_excessif(jours: Nombre | None, surcharges: Optional[Mapping[str, Any]] = None) -> bool:
    return jours is not None and _dec(jours) > _dec(parametre("delai_passation_max_jours", surcharges))


def projection_engagement_faible(taux_haut: Nombre | None, surcharges: Optional[Mapping[str, Any]] = None) -> bool:
    """Même dans l'hypothèse haute, l'engagement projeté en fin d'exercice reste sous le seuil."""
    return taux_haut is not None and _dec(taux_haut) < _dec(parametre("projection_engagement_min", surcharges))
