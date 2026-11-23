"""SIDOF-ENTREPOT : lignes budgétaires de la Chaîne Dépense (vue vm_lbudg) par l'API, en lecture seule.

L'API (en-tête X-API-Key) renvoie la situation budgétaire par ligne : crédits, engagé, liquidé,
ordonnancé, payé, bloqué, réservé, disponible, avec l'imputation complète et les libellés de service,
région, préfecture et pilier Simandou. Elle ne fournit pas la liste des engagements : les chargements
SIDOF alimentent les indicateurs par ligne, pas les dossiers, délais de visa, procédures ni bénéficiaires.

Défaut constaté le 23/11/2026 sur vm_lbudg : chaque ligne est renvoyée deux fois, la seconde avec la
source de financement, le groupe de bailleurs et le bailleur décalés (« 0 / 000 / 2 » au lieu de
« 2 / 0 / 000 »). Ces copies, reconnaissables au groupe de bailleurs sur 3 caractères et au bailleur sur 1,
sont écartées et comptées dans le chargement ; sans cela, tous les montants seraient doublés.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo

import pandas as pd
from django.conf import settings

from .base import BaseConnector, ErreurChargement, RapportValidation
from .chaine_depense import CLE_LIGNE, ONGLET_SITUATION, ChaineDepenseMixin, libelles_oracle

CHEMIN = "/api/v1/lignes-budgetaires/"
TAILLE_PAGE = 1000

# Champ SIDOF → colonne canonique de la situation (mêmes noms que l'extraction Excel et Oracle).
CORRESPONDANCES = {
    "no_ex": "exercice",
    "cd_type_budget": "type_budget",
    "cd_section": "section",
    "libelle_court_section": "libelle_section",
    "cd_ss_section": "sous_section",
    "libelle_long_service": "libelle_sous_section",
    "cd_titre": "titre",
    "cd_chap": "chapitre",
    "cd_art": "article",
    "cd_paragraphe": "paragraphe",
    "cd_ss_paragraphe": "sous_paragraphe",
    "cd_source_fin": "source_financement",
    "cd_groupe_bail": "groupe_bailleur",
    "cd_bailleur": "bailleur",
    "cd_regul": "regulation",
    "mt_cred_init": "credit_initial_lfi",
    "mt_cred": "credit_actuel",
    "mt_dispo": "credit_disponible",
    "mt_resrv": "credit_reserve",
    "mt_eng": "credit_engage",
    "mt_eng_cf": "credit_engage_cf",
    "mt_liq": "montant_liquide",
    "mt_ord": "montant_ordonnance",
    "mt_vbp": "montant_vbp",
    "mt_paye": "montant_paye",
    "mt_bloque": "montant_bloque",
    "mt_delegation": "montant_delegation",
    "mt_apad": "avance_demarrage",
    "mt_regie": "montant_regie",
    # Conservés dans les attributs de la ligne (filtres et répartitions de la page Dépenses).
    "libelle_pillier_simandou": "pillier simandou",
    "code_zone_geographique": "code_zone_geographique",
    "code_region": "code_region",
    "libelle_region": "libelle_region",
    "code_prefecture": "code_prefecture",
    "libelle_prefecture": "libelle_prefecture",
    "code_sous_prefecture": "code_sous_prefecture",
    "code_service": "code_service",
}


def est_copie_decalee(ligne: dict) -> bool:
    """Copie défectueuse de vm_lbudg : groupe de bailleurs sur 3 caractères, bailleur sur 1."""
    groupe = str(ligne.get("cd_groupe_bail") or "").strip()
    bailleur = str(ligne.get("cd_bailleur") or "").strip()
    return len(groupe) == 3 and len(bailleur) == 1


class SidofLignesBudgetairesConnector(ChaineDepenseMixin, BaseConnector):
    """Situation budgétaire d'un exercice depuis SIDOF ; chargée comme une situation de la Chaîne Dépense."""

    avec_engagements = False
    # Des sous-sections portent le même code dans deux sections : la section fait partie de la clé.
    cle_ligne = [*CLE_LIGNE, "section", "groupe_bailleur"]

    def __init__(self, lignes: Optional[list[dict]] = None, **kwargs):
        super().__init__(**kwargs)
        self._fournies = lignes  # jeu de lignes fourni (essais) au lieu de l'appel à l'API
        self.informations_chargement = {}

    @property
    def nom_fichier(self) -> str:
        return "sidof://lignes_budgetaires"

    # ------------------------------------------------------------------ lecture de l'API

    def _lire_pages(self) -> list[dict]:
        conf = settings.SOURCES_EXTERNES["sidof"]
        if not conf.get("cle"):
            raise ErreurChargement("Clé SIDOF non configurée (SIDOF_API_KEY dans backend/.env).")
        base = conf["url"].rstrip("/")
        hote = urllib.parse.urlsplit(base).netloc
        url = f"{base}{CHEMIN}?{urllib.parse.urlencode({'no_ex': self.exercice, 'taille': TAILLE_PAGE})}"
        lignes: list[dict] = []
        while url:
            # La clé n'est jamais envoyée à un autre hôte que celui configuré (pagination incluse).
            if urllib.parse.urlsplit(url).netloc != hote:
                raise ErreurChargement("Pagination SIDOF vers un autre hôte : lecture interrompue.")
            requete = urllib.request.Request(url, headers={"X-API-Key": conf["cle"], "Accept": "application/json"})
            try:
                with urllib.request.urlopen(requete, timeout=conf.get("timeout", 120)) as reponse:
                    page = json.load(reponse)
            except urllib.error.HTTPError as exc:
                motif = "clé refusée" if exc.code in (401, 403) else f"erreur HTTP {exc.code}"
                raise ErreurChargement(f"API SIDOF : {motif}.") from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                raise ErreurChargement(f"API SIDOF injoignable ({base}).") from exc
            lignes += page.get("results") or []
            url = page.get("next")
        return lignes

    def extract(self) -> dict[str, pd.DataFrame]:
        if not self.exercice:
            raise ErreurChargement("Un exercice explicite est requis pour la lecture SIDOF.")
        brutes = self._fournies if self._fournies is not None else self._lire_pages()
        decalees = [r for r in brutes if est_copie_decalee(r)]
        lignes = [r for r in brutes if not est_copie_decalee(r)]
        renommees = pd.DataFrame(lignes, dtype=object).rename(columns=CORRESPONDANCES)
        df = renommees[[c for c in CORRESPONDANCES.values() if c in renommees.columns]]
        # Date de situation : dernière mise à jour des lignes dans l'entrepôt (pas la date d'appel).
        majs = [r.get("dt_maj") for r in lignes if r.get("dt_maj")]
        if self.date_situation is None:
            self.date_situation = (
                max(datetime.fromisoformat(m.replace("Z", "+00:00")) for m in majs)
                .astimezone(ZoneInfo(settings.TIME_ZONE))
                .date()
                if majs
                else date.today()
            )
        self.informations_chargement = {
            "origine": "sidof",
            "date_extraction": date.today().isoformat(),
            "sidof": {
                "lignes_recues": len(brutes),
                "copies_decalees_ecartees": len(decalees),
                "lignes_retenues": len(lignes),
                "derniere_mise_a_jour": max(majs) if majs else None,
            },
            "indicateurs_indisponibles": ["liste_engagements"],
            "referentiels_libelles": libelles_oracle({ONGLET_SITUATION: df}),
        }
        return {ONGLET_SITUATION: df}

    # ------------------------------------------------------------------ contrôles

    def validate(self) -> RapportValidation:
        df = self.donnees.get(ONGLET_SITUATION)
        if df is None or df.empty:
            raise ErreurChargement(f"Aucune ligne budgétaire SIDOF pour l'exercice {self.exercice}.")
        rapport = super().validate()
        info = self.informations_chargement.get("sidof", {})
        recues, ecartees = info.get("lignes_recues", 0), info.get("copies_decalees_ecartees", 0)
        # Le défaut double chaque ligne : environ une ligne reçue sur deux est écartée. Un autre rapport
        # signale un changement de la vue (corrigée, ou décalage différent) à faire vérifier.
        proportion = ecartees / recues if recues else 0
        rapport.ajouter(
            "sidof_copies_decalees",
            "Copies décalées de vm_lbudg écartées (source, groupe et bailleur décalés)",
            "avertissement",
            ecartees == 0 or 0.4 <= proportion <= 0.6,
            nombre=ecartees,
            detail={
                "message": f"{ecartees} sur {recues} lignes reçues ({proportion:.0%})",
                "lignes_retenues": info.get("lignes_retenues"),
            },
        )
        return rapport
