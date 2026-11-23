"""Connecteurs de la Chaîne Dépense : extraction Excel (lot 1) et Oracle (lecture seule)."""

from __future__ import annotations

import hashlib
import logging
from datetime import date, datetime
from datetime import time as dtime
from decimal import Decimal
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import pandas as pd
from django.conf import settings

from apps.core import regles
from apps.depense.models import FaitAPAD, FaitEngagement, FaitOperation, FaitRegie, FaitSituationLigne
from apps.referentiels.models import (
    TITRES,
    RefBailleur,
    RefBeneficiaire,
    RefBeneficiaireAlias,
    RefEtatDossier,
    RefExercice,
    RefGroupeBailleur,
    RefNatureEconomique,
    RefRegulation,
    RefSection,
    RefSourceFinancement,
    RefSousSection,
    RefTypeBudget,
    RefTypeProcedure,
)
from etl import nettoyage as n

from .base import BaseConnector, ErreurChargement, RapportValidation

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- mappings
# champ canonique -> en-têtes acceptés (comparés après cle_entete : minuscules, sans accents).

ONGLET_SITUATION = "situation"
ONGLET_ENGAGEMENTS = "engagements"
ONGLET_OPERATIONS = "operations"
ONGLET_REGIE = "regie"
ONGLET_APAD = "apad"

NOMS_ONGLETS = {
    ONGLET_SITUATION: ["situation courante"],
    ONGLET_ENGAGEMENTS: ["liste des engagements"],
    ONGLET_OPERATIONS: ["details des operations", "detail des operations"],
    ONGLET_REGIE: ["regie", "regies"],
    ONGLET_APAD: ["apad"],
}

IMPUTATION = {
    "type_budget": ["type budget"],
    "section": ["section"],
    "sous_section": ["sous section"],
    "titre": ["code titre", "titre"],
    "chapitre": ["code chapitre", "chapitre"],
    "article": ["code article", "article"],
    "paragraphe": ["code paragraphe", "paragraphe"],
    "sous_paragraphe": ["code sous paragraphe", "sous paragraphe"],
    "source_financement": ["code source financement", "source fin"],
    "groupe_bailleur": ["code groupe bailleur", "groupe fin", "groupe bailleur"],
    "bailleur": ["code bailleur", "bailleur", "bailleurs"],
}

COLONNES = {
    ONGLET_APAD: {
        **IMPUTATION,
        "exercice": ["exercice"],
        "gestionnaire": ["gradm"],
        "numero_apad": ["numero apad"],
        "numero_marche": ["numero marche"],
        "libelle_sous_section": ["libelle sous section"],
        "nature_flux": ["nature flux"],
        "avance_demarrage": ["avance de demarrage"],
        "date_creation": ["date creation"],
    },
    ONGLET_SITUATION: {
        **IMPUTATION,
        "libelle_section": ["libelle section"],
        "libelle_sous_section": ["libelle sous section"],
        "libelle_titre": ["libelle titre"],
        "libelle_chapitre": ["libelle chapitre"],
        "libelle_article": ["libelle article"],
        "libelle_paragraphe": ["libelle paragraphe"],
        "libelle_sous_paragraphe": ["libelle sous paragraphe"],
        "regulation": ["code regulation"],
        "credit_initial_lfi": ["credit initial lfi"],
        "credit_lfr": ["credit lfr"],
        "credit_douzieme_provisoire": ["credit 12eme prov"],
        "credit_actuel": ["credit actuel"],
        "credit_disponible": ["credits disponible", "credit disponible", "credits disponibles"],
        "credit_reserve": ["credit reserve"],
        "credit_engage": ["credits engages", "credit engage"],
        "credit_engage_projet": ["credits engages en projet"],
        "credit_engage_cf": ["credits engages cf"],
        "montant_liquide": ["montant liquide"],
        "montant_ordonnance": ["montant ordonnance"],
        "montant_vbp": ["montant vue bon pour paiement"],
        "montant_encours_paiement": ["montant encours de paiement"],
        "montant_paye": ["montant paye"],
        "montant_bloque": ["montant bloque"],
        "montant_delegation": ["montant delegation"],
        "avance_demarrage": ["avance de demarrage"],
        "montant_regie": ["montant regie"],
        "exercice": ["exercice"],
    },
    ONGLET_ENGAGEMENTS: {
        **IMPUTATION,
        "titre": ["titre"],
        "chapitre": ["chapitre"],
        "article": ["article"],
        "paragraphe": ["paragraphe"],
        "sous_paragraphe": ["sous paragraphe"],
        "exercice": ["exercice"],
        "numero": ["numero engagement"],
        "libelle_section": ["libelle section"],
        "objet": ["objet"],
        "beneficiaire": ["beneficiaire"],
        "type_procedure": ["type engagement"],
        "etat_dossier": ["etat dossier"],
        "montant_initial": ["montant initial eng"],
        "montant_engage": ["montant engage"],
        "montant_devise": ["montant devise"],
        "devise": ["devise"],
        "montant_engage_cf": ["montant eng cf"],
        "montant_retenu": ["montant retenu"],
        "montant_liquide": ["montant liq"],
        "montant_ordonnance": ["montant ord"],
        "montant_vbp": ["montant vbp"],
        "montant_ecp": ["montant ecp"],
        "montant_paye": ["montant paye"],
        "date_creation": ["date creation"],
        "date_visa_cf": ["date visa cf"],
        "date_visa_ministre": ["date visa ministre"],
        "date_etat": ["date etat"],
        "date_maj": ["date maj"],
    },
    ONGLET_OPERATIONS: {
        **IMPUTATION,
        "titre": ["titre"],
        "chapitre": ["chapitre"],
        "article": ["article"],
        "paragraphe": ["paragraphe"],
        "sous_paragraphe": ["sous paragraphe"],
        "exercice": ["numero exercice", "exercice"],
        "libelle_section": ["libelle section"],
        "beneficiaire": ["beneficiaire"],
        "objet": ["object", "objet"],
        "numero_engagement": ["numero engagement"],
        "type_procedure": ["type engagement"],
        "etat_dossier": ["etat dossier"],
        "type_origine": ["type origine"],
        "montant": ["montant"],
        "montant_engage": ["montant engage"],
        "montant_engage_cf": ["montant engage cf"],
        "montant_liquide": ["montant liquide"],
        "montant_devise": ["montant devise"],
        "code_devise": ["code devise"],
        "montant_vbp": ["montant vbp"],
        "date_visa_vbp": ["date visa vbp"],
        "montant_ordonnance": ["montant ordonnance"],
        "montant_paye": ["montant paye"],
    },
    ONGLET_REGIE: {
        **IMPUTATION,
        "titre": ["titre"],
        "chapitre": ["chapitre"],
        "article": ["article"],
        "paragraphe": ["paragraphe"],
        "sous_paragraphe": ["sous paragraphe"],
        "source_financement": ["source fin"],
        "exercice": ["numero exercice", "exercice"],
        "gestionnaire": ["gradm"],
        "numero_regie": ["numero regie"],
        "libelle_sous_section": ["libelle sous section"],
        "nature_flux": ["nature flux"],
        "montant_regie": ["montant regie"],
        "date_creation": ["date creation"],
        "etat_dossier": ["etat dossier"],
    },
}

OBLIGATOIRES = {
    ONGLET_SITUATION: [
        "section",
        "sous_section",
        "titre",
        "credit_actuel",
        "credit_engage",
        "montant_ordonnance",
        "montant_paye",
    ],
    ONGLET_ENGAGEMENTS: [
        "numero",
        "section",
        "titre",
        "montant_engage",
        "montant_ordonnance",
        "montant_paye",
        "type_procedure",
        "etat_dossier",
    ],
    ONGLET_OPERATIONS: [],
    ONGLET_REGIE: [],
}

MESURES_SITUATION = [
    "credit_initial_lfi",
    "credit_lfr",
    "credit_douzieme_provisoire",
    "credit_actuel",
    "credit_disponible",
    "credit_reserve",
    "credit_engage",
    "credit_engage_projet",
    "credit_engage_cf",
    "montant_liquide",
    "montant_ordonnance",
    "montant_vbp",
    "montant_encours_paiement",
    "montant_paye",
    "montant_bloque",
    "montant_delegation",
    "avance_demarrage",
    "montant_regie",
]
MESURES_ENGAGEMENT = [
    "montant_initial",
    "montant_engage",
    "montant_engage_cf",
    "montant_retenu",
    "montant_liquide",
    "montant_ordonnance",
    "montant_vbp",
    "montant_ecp",
    "montant_paye",
    "montant_devise",
]
MESURES_OPERATION = [
    "montant",
    "montant_engage",
    "montant_engage_cf",
    "montant_liquide",
    "montant_devise",
    "montant_vbp",
    "montant_ordonnance",
    "montant_paye",
]
CLE_LIGNE = [
    "type_budget",
    "sous_section",
    "titre",
    "chapitre",
    "article",
    "paragraphe",
    "sous_paragraphe",
    "source_financement",
    "bailleur",
    "regulation",
]
NIVEAUX_NATURE = ["titre", "chapitre", "article", "paragraphe", "sous_paragraphe"]

# Procédures payées hors de la chaîne (salaires, dette) — voir fixtures/referentiels.
PROCEDURES_HORS_CHAINE = {"Procedure Solde", "Debit d'office - NE PAS PAYER", "Regul.PCT - NE PAS PAYER"}
ETATS_ENGAGEMENT_VALIDE = {"Depense engagee"}

TAILLE_LOT = 2000


def _hash(valeurs) -> str:
    return hashlib.sha1("|".join(valeurs).encode("utf-8")).hexdigest()


def _renommer(df: pd.DataFrame, onglet: str) -> tuple[pd.DataFrame, list[str]]:
    """Renomme les colonnes vers les champs canoniques ; renvoie aussi les colonnes inconnues."""
    correspondances = {}
    for champ, alias in COLONNES[onglet].items():
        for col in df.columns:
            if n.cle_entete(col) in alias and col not in correspondances:
                correspondances[col] = champ
                break
    inconnues = [c for c in df.columns if c not in correspondances]
    return df.rename(columns=correspondances), inconnues


class ChaineDepenseMixin:
    """Validation et chargement communs aux connecteurs Excel et Oracle."""

    source_code = "chaine_depense"
    cle_ligne = CLE_LIGNE
    niveau_concordance = "bloquant"
    # Faux pour une source qui ne fournit que la situation budgétaire (ex. SIDOF, vue vm_lbudg) : pas de liste
    # des engagements, donc ni contrôle de concordance ni dossiers, délais, procédures ou bénéficiaires.
    avec_engagements = True

    # ----------------------------------------------------------------- validation

    def validate(self) -> RapportValidation:
        self.informations_chargement["colonnes_extraites"] = {
            onglet: [str(c) for c in df.columns] for onglet, df in self.donnees.items()
        }
        rapport = RapportValidation()
        sc = self.donnees.get(ONGLET_SITUATION)
        eng = self.donnees.get(ONGLET_ENGAGEMENTS)
        for onglet, requis in OBLIGATOIRES.items():
            if onglet == ONGLET_ENGAGEMENTS and not self.avec_engagements:
                continue
            df = self.donnees.get(onglet)
            if df is None:
                if requis:
                    rapport.ajouter(
                        f"onglet_{onglet}",
                        f"Onglet « {onglet} » présent",
                        "bloquant",
                        False,
                        detail={"message": "onglet introuvable"},
                    )
                continue
            manquantes = [c for c in requis if c not in df.columns]
            rapport.ajouter(
                f"colonnes_{onglet}",
                f"Colonnes obligatoires de l'onglet « {onglet} »",
                "bloquant",
                not manquantes,
                detail={"message": ", ".join(manquantes) or "ok"},
            )
        if not rapport.valide:
            return rapport

        if self.exercice is None:
            rapport.ajouter(
                "exercice",
                "Exercice déterminé",
                "bloquant",
                False,
                detail={"message": "exercice introuvable (nom de fichier ou colonne Exercice)"},
            )
        if self.date_situation is None:
            rapport.ajouter(
                "date_situation",
                "Date de situation déterminée",
                "bloquant",
                False,
                detail={"message": "date de situation introuvable, à saisir à l'import"},
            )

        apad = self.donnees.get(ONGLET_APAD)
        if apad is not None:
            try:
                self.preparer_apad(apad)
            except (ValueError, KeyError) as exc:
                rapport.ajouter(
                    "structure_apad", "Structure et valeurs APAD", "bloquant", False, detail={"message": str(exc)}
                )

        if not self.avec_engagements:
            rapport.ajouter(
                "liste_engagements",
                "Liste des engagements",
                "info",
                True,
                detail={
                    "message": "non fournie par cette source : délais de visa, procédures, bénéficiaires et "
                    "dossiers d'arbitrage ne sont pas alimentés par ce chargement"
                },
            )
            return self._controles_situation(rapport, sc, None)

        # Concordance bloquante : total engagé « Situation courante » = « Liste des engagements ».
        total_sc = sum((n.montant_ou_zero(v) for v in sc["credit_engage"]), Decimal(0))
        eng_comparables = getattr(self, "_engagements_concordance", eng)
        total_eng = sum((n.montant_ou_zero(v) for v in eng_comparables["montant_engage"]), Decimal(0))
        ok = regles.concordance_ok(total_sc, total_eng)
        rapport.ajouter(
            "concordance_engage",
            "Concordance du total engagé entre onglets",
            self.niveau_concordance,
            ok,
            valeur=total_sc - total_eng,
            detail={
                "situation_courante": str(total_sc),
                "liste_engagements": str(total_eng),
                "perimetre": getattr(self, "_perimetre_concordance", "Tous les engagements reçus"),
                "tolerance_gnf_par_million": regles.parametre("concordance_tolerance_par_million"),
                "message": f"écart de {total_sc - total_eng:,.0f} GNF".replace(",", " "),
            },
        )

        return self._controles_situation(rapport, sc, eng)

    def _controles_situation(self, rapport: RapportValidation, sc, eng) -> RapportValidation:
        """Contrôles non bloquants ; ceux portant sur les engagements seulement si la liste est fournie."""
        cles = sc[self.cle_ligne].apply(lambda r: _hash(n.code(v) for v in r), axis=1)
        doublons = int(cles.duplicated(keep=False).sum())
        rapport.ajouter(
            "doublons_cle_ligne",
            "Doublons sur la clé de ligne budgétaire",
            "avertissement",
            doublons == 0,
            nombre=doublons,
        )
        for champ in ("credit_initial_lfi", "credit_lfr"):
            if champ in sc.columns:
                absents = int(sc[champ].map(n.est_vide).sum())
                rapport.ajouter(
                    f"absents_{champ}", f"Valeurs absentes dans « {champ} » (comptées 0)", "info", True, nombre=absents
                )
        dispo = sc["credit_disponible"].map(n.montant_ou_zero) if "credit_disponible" in sc else pd.Series([])
        depassements = int(sum(regles.est_ligne_en_depassement(v) for v in dispo))
        rapport.ajouter(
            "lignes_depassement",
            "Lignes en dépassement (disponible < 0)",
            "avertissement",
            depassements == 0,
            nombre=depassements,
        )
        liq = sc["montant_liquide"].map(n.montant_ou_zero)
        engs = sc["credit_engage"].map(n.montant_ou_zero)
        liq_sup = int(sum(regles.liquide_depasse_engage(a, b) for a, b in zip(liq, engs)))
        rapport.ajouter(
            "liquide_sup_engage", "Lignes où le liquidé dépasse l'engagé", "avertissement", liq_sup == 0, nombre=liq_sup
        )
        sans_section = int(sc["section"].map(n.est_vide).sum())
        rapport.ajouter(
            "lignes_sans_section",
            "Lignes sans code section (rejetées)",
            "avertissement",
            sans_section == 0,
            nombre=sans_section,
        )
        if eng is not None:
            doublons_num = int(
                eng.assign(_s=eng["section"].map(n.code), _n=eng["numero"].map(n.code))
                .duplicated(["_s", "_n"], keep=False)
                .sum()
            )
            rapport.ajouter(
                "numero_engagement_non_unique",
                "Engagements partageant numéro et section",
                "info",
                True,
                nombre=doublons_num,
                detail={"message": "clé technique utilisée ; clé métier à confirmer"},
            )
        codes_numeriques = sum(
            int(df[c].map(lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)).sum())
            for df in (sc, eng)
            if df is not None
            for c in ("section", "sous_section", "titre")
            if c in df.columns
        )
        rapport.ajouter(
            "codes_numeriques",
            "Codes stockés comme nombres dans Excel (zéros initiaux perdus)",
            "avertissement",
            codes_numeriques == 0,
            nombre=codes_numeriques,
        )
        return rapport

    # ------------------------------------------------------------------ chargement

    def load(self, chargement) -> int:
        self._source = chargement.source
        RefExercice.objects.get_or_create(annee=self.exercice, defaults={"libelle": str(self.exercice)})
        self._charger_referentiels()
        total = 0
        total += self._charger_situation(chargement)
        if self.avec_engagements:
            total += self._charger_engagements(chargement, ONGLET_ENGAGEMENTS, FaitEngagement)
        if ONGLET_OPERATIONS in self.donnees:
            total += self._charger_engagements(chargement, ONGLET_OPERATIONS, FaitOperation)
        if ONGLET_REGIE in self.donnees:
            total += self._charger_regie(chargement)
        if ONGLET_APAD in self.donnees:
            total += self.charger_apad(chargement)
        return total

    def preparer_apad(self, df):
        requis = ["exercice", "section", "sous_section", "titre", "gestionnaire", "numero_apad", "avance_demarrage"]
        if any(c not in df.columns for c in requis):
            raise ValueError("Colonnes APAD incomplètes.")
        lignes = []
        for index, r in df.iterrows():
            if not n.code(r.get("section")) or not n.code(r.get("numero_apad")):
                raise ValueError("Section ou numéro APAD absent.")
            if n.code(r.get("exercice")) != str(self.exercice):
                raise ValueError("Exercice APAD différent de l'exercice importé.")
            montant, absent = n.montant(r.get("avance_demarrage"))
            if montant < 0:
                raise ValueError("Montant APAD négatif à rapprocher avant import.")
            creation = n.date_(r.get("date_creation"))
            if creation and self.date_situation and creation > self.date_situation:
                raise ValueError("Date APAD postérieure à la situation.")
            lignes.append(
                {
                    **self._imputation(r),
                    "gestionnaire": n.code(r.get("gestionnaire")),
                    "numero_apad": n.code(r.get("numero_apad")),
                    "numero_marche": n.code(r.get("numero_marche")),
                    "libelle_projet": n.libelle(r.get("libelle_sous_section")),
                    "nature_flux": n.code(r.get("nature_flux")),
                    "avance_demarrage": montant,
                    "montant_absent": absent,
                    "date_creation": creation,
                    "ligne_source": int(index) + 2,
                }
            )
        return lignes

    def charger_apad(self, chargement):
        lignes = self.preparer_apad(self.donnees[ONGLET_APAD])
        FaitAPAD.objects.bulk_create(
            [FaitAPAD(**self._technique(chargement), **r) for r in lignes], batch_size=TAILLE_LOT
        )
        self.comptes[ONGLET_APAD] = {"lues": len(lignes), "chargees": len(lignes), "rejetees": 0}
        return len(lignes)

    def _charger_referentiels(self) -> None:
        sc = self.donnees[ONGLET_SITUATION]
        frames = [df for df in self.donnees.values() if "section" in df.columns]

        # Sections : libellé titre-casé et accentué ; libellé court conservé s'il existe déjà.
        sections = {}
        for df in frames:
            if "libelle_section" not in df.columns:
                continue
            for c, l in zip(df["section"].map(n.code), df["libelle_section"].map(n.libelle)):
                if c and l and c not in sections:
                    sections[c] = l
        for df in frames:
            for c in df["section"].map(n.code):
                if c and c not in sections:
                    sections[c] = ""
        existantes = {s.code: s for s in RefSection.objects.filter(code__in=sections)}
        for c, brut in sections.items():
            s = existantes.get(c)
            affiche = n.titre_francais(brut) if brut else f"Section {c}"
            if s is None:
                RefSection.objects.create(
                    code=c,
                    libelle=affiche,
                    libelle_source=brut,
                    libelle_court=n.libelle_court_section(affiche),
                    type=n.type_section(c, brut),
                )
            elif brut and s.libelle_source != brut:
                s.libelle_source = brut
                if not s.libelle:
                    s.libelle = affiche
                s.save()

        # Sous-sections.
        sous = {}
        for df in frames:
            if "sous_section" not in df.columns:
                continue
            lib = df["libelle_sous_section"].map(n.libelle) if "libelle_sous_section" in df.columns else None
            for i, (c, s) in enumerate(zip(df["sous_section"].map(n.code), df["section"].map(n.code))):
                if c and (c not in sous or (lib is not None and not sous[c][1])):
                    sous[c] = (s, lib.iat[i] if lib is not None else "")
        existantes = set(RefSousSection.objects.filter(code__in=sous).values_list("code", flat=True))
        RefSousSection.objects.bulk_create(
            [RefSousSection(code=c, section_id=s, libelle=l) for c, (s, l) in sous.items() if c not in existantes],
            batch_size=TAILLE_LOT,
        )

        # Nature économique : les 5 niveaux, avec libellés de « Situation courante ».
        natures: dict[str, tuple[int, str, str, Optional[str]]] = {}
        for df in frames:
            if not all(c in df.columns for c in NIVEAUX_NATURE):
                continue
            codes = df[NIVEAUX_NATURE].apply(lambda col: col.map(n.code))
            libs = {
                niv: (df[f"libelle_{niv}"].map(n.libelle) if f"libelle_{niv}" in df.columns else None)
                for niv in NIVEAUX_NATURE
            }
            for i, row in enumerate(codes.itertuples(index=False)):
                parent = None
                for k, niv in enumerate(NIVEAUX_NATURE):
                    code_nat = ".".join(row[: k + 1])
                    lib = libs[niv].iat[i] if libs[niv] is not None else ""
                    if niv == "titre":
                        lib = TITRES.get(row[0], lib)
                    if code_nat not in natures or (lib and not natures[code_nat][1]):
                        natures[code_nat] = (k + 1, lib, row[0], parent)
                    parent = code_nat
        existantes = set(RefNatureEconomique.objects.filter(code__in=natures).values_list("code", flat=True))
        # Création niveau par niveau pour respecter la clé parent.
        for niveau in range(1, 6):
            a_creer = [(c, v) for c, v in natures.items() if v[0] == niveau and c not in existantes]
            ids = dict(
                RefNatureEconomique.objects.filter(code__in={v[3] for _, v in a_creer if v[3]}).values_list(
                    "code", "id"
                )
            )
            RefNatureEconomique.objects.bulk_create(
                [
                    RefNatureEconomique(code=c, niveau=v[0], libelle=v[1], titre=v[2], parent_id=ids.get(v[3]))
                    for c, v in a_creer
                ],
                batch_size=TAILLE_LOT,
            )

        # Petits référentiels à codes.
        for modele, champ in (
            (RefSourceFinancement, "source_financement"),
            (RefGroupeBailleur, "groupe_bailleur"),
            (RefBailleur, "bailleur"),
            (RefTypeBudget, "type_budget"),
        ):
            codes = set()
            for df in frames:
                if champ in df.columns:
                    codes |= set(df[champ].map(n.code)) - {""}
            existants = set(modele.objects.filter(code__in=codes).values_list("code", flat=True))
            modele.objects.bulk_create([modele(code=c) for c in codes - existants])
        if "regulation" in sc.columns:
            codes = set(sc["regulation"].map(n.code)) - {""}
            existants = set(RefRegulation.objects.filter(code__in=codes).values_list("code", flat=True))
            RefRegulation.objects.bulk_create([RefRegulation(code=c) for c in codes - existants])

        # Procédures et états de dossier.
        procedures, etats = set(), set()
        for onglet in (ONGLET_ENGAGEMENTS, ONGLET_OPERATIONS):
            df = self.donnees.get(onglet)
            if df is not None and "type_procedure" in df.columns:
                procedures |= set(df["type_procedure"].map(n.libelle)) - {""}
            if df is not None and "etat_dossier" in df.columns:
                etats |= set(df["etat_dossier"].map(n.libelle)) - {""}
        for p in procedures:
            RefTypeProcedure.objects.get_or_create(
                libelle=p,
                defaults={"paiement_hors_chaine": n.cle_entete(p) in {n.cle_entete(v) for v in PROCEDURES_HORS_CHAINE}},
            )
        for e in etats:
            RefEtatDossier.objects.get_or_create(
                libelle=e,
                defaults={"engagement_valide": n.cle_entete(e) in {n.cle_entete(v) for v in ETATS_ENGAGEMENT_VALIDE}},
            )
        self._procedures = dict(RefTypeProcedure.objects.values_list("libelle", "id"))
        self._etats = dict(RefEtatDossier.objects.values_list("libelle", "id"))

        # Bénéficiaires : rapprochement par clé normalisée, variantes en alias.
        noms = set()
        for onglet in (ONGLET_ENGAGEMENTS, ONGLET_OPERATIONS):
            df = self.donnees.get(onglet)
            if df is not None and "beneficiaire" in df.columns:
                noms |= set(df["beneficiaire"].map(n.beneficiaire_affiche)) - {""}
        self._beneficiaires = self._rapprocher_beneficiaires(noms)

    def _rapprocher_beneficiaires(self, noms: set[str]) -> dict[str, int]:
        alias_connus = dict(RefBeneficiaireAlias.objects.values_list("alias", "beneficiaire_id"))
        cles_connues = dict(RefBeneficiaire.objects.values_list("nom_normalise", "id"))
        # À clé égale, on affiche la variante qui contient le plus d'espaces (« TRAORE Gassimou »).
        par_cle: dict[str, list[str]] = {}
        for nom in noms:
            par_cle.setdefault(n.beneficiaire_cle(nom), []).append(nom)
        nouveaux = [
            RefBeneficiaire(nom_normalise=cle, nom_affiche=max(variantes, key=lambda v: (v.count(" "), v))[:255])
            for cle, variantes in par_cle.items()
            if cle and cle not in cles_connues
        ]
        RefBeneficiaire.objects.bulk_create(nouveaux, batch_size=TAILLE_LOT)
        cles_connues = dict(
            RefBeneficiaire.objects.filter(nom_normalise__in=par_cle).values_list("nom_normalise", "id")
        )
        resultat, alias_nouveaux = {}, {}
        for nom in noms:
            alias = n.beneficiaire_alias(nom)
            bid = alias_connus.get(alias) or cles_connues.get(n.beneficiaire_cle(nom))
            if bid:
                resultat[nom] = bid
                if alias and alias not in alias_connus:
                    alias_nouveaux[alias] = bid
        RefBeneficiaireAlias.objects.bulk_create(
            [RefBeneficiaireAlias(alias=a[:255], beneficiaire_id=b) for a, b in alias_nouveaux.items()],
            batch_size=TAILLE_LOT,
            ignore_conflicts=True,
        )
        return resultat

    def _imputation(self, r: dict) -> dict:
        codes = {k: n.code(r.get(k)) for k in IMPUTATION}
        nature = ".".join(codes[k] for k in NIVEAUX_NATURE) if all(codes[k] for k in NIVEAUX_NATURE) else None
        return {
            "type_budget": codes["type_budget"],
            "section_id": codes["section"],
            "sous_section_id": codes["sous_section"] or None,
            "titre": codes["titre"],
            "chapitre": codes["chapitre"],
            "article": codes["article"],
            "paragraphe": codes["paragraphe"],
            "sous_paragraphe": codes["sous_paragraphe"],
            "nature_id": nature,
            "source_financement": codes["source_financement"],
            "groupe_bailleur": codes["groupe_bailleur"],
            "bailleur": codes["bailleur"],
        }

    def _technique(self, chargement) -> dict:
        return {
            "exercice": self.exercice,
            "date_situation": self.date_situation,
            "source_id": chargement.source_id,
            "chargement_id": chargement.id,
        }

    def _charger_situation(self, chargement) -> int:
        df = self.donnees[ONGLET_SITUATION]
        connus = set(COLONNES[ONGLET_SITUATION])
        extras = [c for c in df.columns if c not in connus and not str(c).startswith("_")]
        objets, rejetees = [], 0
        tech = self._technique(chargement)
        for r in df.to_dict("records"):
            if not n.code(r.get("section")):
                rejetees += 1
                continue
            mesures = {m: n.montant(r.get(m)) for m in MESURES_SITUATION}
            objets.append(
                FaitSituationLigne(
                    **tech,
                    **self._imputation(r),
                    regulation=n.code(r.get("regulation")),
                    cle_ligne=_hash(n.code(r.get(k)) for k in self.cle_ligne),
                    lfi_absent=mesures["credit_initial_lfi"][1],
                    lfr_absent=mesures["credit_lfr"][1],
                    attributs={str(c): n.libelle(r.get(c)) for c in extras if not n.est_vide(r.get(c))}
                    | {"_mesures_absentes": [m for m, (_, absent) in mesures.items() if absent]},
                    **{m: v[0] for m, v in mesures.items()},
                )
            )
        FaitSituationLigne.objects.bulk_create(objets, batch_size=TAILLE_LOT)
        self.comptes[ONGLET_SITUATION] = {"lues": len(df), "chargees": len(objets), "rejetees": rejetees}
        return len(objets)

    def _charger_engagements(self, chargement, onglet: str, modele) -> int:
        df = self.donnees[onglet]
        objets, rejetees = [], 0
        tech = self._technique(chargement)
        mesures = MESURES_ENGAGEMENT if modele is FaitEngagement else MESURES_OPERATION
        for r in df.to_dict("records"):
            if not n.code(r.get("section")):
                rejetees += 1
                continue
            imput = self._imputation(r)
            benef = n.beneficiaire_affiche(r.get("beneficiaire"))
            commun = dict(
                **tech,
                **imput,
                type_procedure_id=self._procedures.get(n.libelle(r.get("type_procedure"))),
                etat_dossier_id=self._etats.get(n.libelle(r.get("etat_dossier"))),
                beneficiaire_id=self._beneficiaires.get(benef),
                beneficiaire_brut=benef[:255],
                objet=n.libelle(r.get("objet")),
                **{m: n.montant_ou_zero(r.get(m)) for m in mesures},
            )
            if modele is FaitEngagement:
                extras = [c for c in df.columns if c not in COLONNES[onglet] and not str(c).startswith("_")]
                obj = FaitEngagement(
                    **commun,
                    numero=n.code(r.get("numero")),
                    cle_imputation=_hash(str(imput[k] or "") for k in sorted(imput)),
                    devise=n.code(r.get("devise")),
                    date_creation=n.date_(r.get("date_creation")),
                    date_visa_cf=n.date_(r.get("date_visa_cf")),
                    date_visa_ministre=n.date_(r.get("date_visa_ministre")),
                    date_etat=n.date_(r.get("date_etat")),
                    date_maj=n.date_(r.get("date_maj")),
                    attributs={str(c): n.libelle(r.get(c)) for c in extras if not n.est_vide(r.get(c))},
                )
            else:
                obj = FaitOperation(
                    **commun,
                    numero_engagement=n.code(r.get("numero_engagement")),
                    type_origine=n.libelle(r.get("type_origine")),
                    code_devise=n.code(r.get("code_devise")),
                    date_visa_vbp=n.date_(r.get("date_visa_vbp")),
                )
            objets.append(obj)
        modele.objects.bulk_create(objets, batch_size=TAILLE_LOT)
        self.comptes[onglet] = {"lues": len(df), "chargees": len(objets), "rejetees": rejetees}
        return len(objets)

    def _charger_regie(self, chargement) -> int:
        df = self.donnees[ONGLET_REGIE]
        objets, rejetees = [], 0
        tech = self._technique(chargement)
        for r in df.to_dict("records"):
            if not n.code(r.get("section")):
                rejetees += 1
                continue
            objets.append(
                FaitRegie(
                    **tech,
                    **self._imputation(r),
                    gestionnaire=n.code(r.get("gestionnaire")),
                    numero_regie=n.code(r.get("numero_regie")),
                    nature_flux=n.code(r.get("nature_flux")),
                    montant_regie=n.montant_ou_zero(r.get("montant_regie")),
                    date_creation=n.date_(r.get("date_creation")),
                    etat_dossier_brut=n.libelle(r.get("etat_dossier")),
                )
            )
        FaitRegie.objects.bulk_create(objets, batch_size=TAILLE_LOT)
        self.comptes[ONGLET_REGIE] = {"lues": len(df), "chargees": len(objets), "rejetees": rejetees}
        return len(objets)


class ExcelChaineDepenseConnector(ChaineDepenseMixin, BaseConnector):
    """Fichier « SC de AAAA-AAAA en date du JJ-MM-AAAA.xlsx » (quatre onglets)."""

    def __init__(self, fichier, nom_fichier: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.fichier = fichier
        self._nom = nom_fichier or Path(str(fichier)).name

    @property
    def nom_fichier(self) -> str:
        return self._nom

    def extract(self) -> dict[str, pd.DataFrame]:
        donnees, ignores = {}, []
        # Le classeur est refermé dès la lecture : le fichier déposé peut alors être rangé ou supprimé.
        with pd.ExcelFile(self.fichier, engine="openpyxl") as classeur:
            for feuille in classeur.sheet_names:
                cle = n.cle_entete(feuille)
                onglet = next((o for o, noms in NOMS_ONGLETS.items() if cle in noms), None)
                if onglet is None:
                    ignores.append(feuille)
                    continue
                # dtype=object : texte reste texte (zéros initiaux conservés), montants restent numériques.
                df = classeur.parse(feuille, dtype=object)
                df = df.dropna(how="all")
                df, inconnues = _renommer(df, onglet)
                # Certains anciens exports comportent une feuille APAD vide et tronquée.
                # Elle ne prouve pas un montant nul et ne doit pas bloquer les dépenses.
                if onglet == ONGLET_APAD and df.empty and "avance_demarrage" not in df.columns:
                    ignores.append(feuille)
                    continue
                if onglet != ONGLET_SITUATION:
                    df = df.drop(columns=inconnues)
                donnees[onglet] = df
        self.comptes["_onglets_ignores"] = {"noms": len(ignores)}
        self.onglets_ignores = ignores

        exercice_nom, date_nom = n.infos_nom_fichier(self._nom)
        if self.date_situation is None:
            self.date_situation = date_nom
        if self.exercice is None:
            self.exercice = exercice_nom or _exercice_colonne(donnees)
        return donnees


def _exercice_colonne(donnees: dict[str, pd.DataFrame]) -> Optional[int]:
    for df in donnees.values():
        if "exercice" in df.columns:
            valeurs = df["exercice"].map(n.code)
            valeurs = valeurs[valeurs != ""]
            if len(valeurs):
                return int(valeurs.mode().iat[0])
    return None


def libelles_oracle(donnees: dict[str, pd.DataFrame]) -> dict:
    """Libellés de la situation importée : aucun renommage local ni mélange d'exercices."""
    sections, sous_sections = {}, {}
    for df in donnees.values():
        if "libelle_section" not in df.columns:
            continue
        champs = [
            c
            for c in ("section", "libelle_section", "libelle_court_section", "sous_section", "libelle_sous_section")
            if c in df.columns
        ]
        for r in df[champs].drop_duplicates().to_dict("records"):
            code = n.code(r.get("section"))
            if not code:
                continue
            nom = n.libelle(r.get("libelle_section")) or f"Section {code}"
            sections[code] = {
                "libelle": nom,
                "libelle_court": n.libelle(r.get("libelle_court_section")) or nom,
                "type": n.type_section(code, nom),
            }
            sous = n.code(r.get("sous_section"))
            if sous:
                sous_sections.setdefault(code, {})[sous] = n.libelle(r.get("libelle_sous_section")) or sous
    return {"sections": sections, "sous_sections": sous_sections}


class OracleChaineDepenseConnector(ChaineDepenseMixin, BaseConnector):
    """Lecture seule de la Chaîne Dépense sur une réplique ou des vues dédiées.

    Les requêtes (vues exposant les mêmes colonnes que l'extraction Excel) sont
    configurées dans Source.configuration["requetes"]. L'exécution est refusée
    pendant les heures ouvrées si la cible n'est pas une réplique.
    """

    HEURES_OUVREES = (dtime(7, 30), dtime(18, 30))
    cle_ligne = [
        "exercice",
        "section",
        "programme",
        "sous_section",
        "nature_flux",
        "titre",
        "chapitre",
        "article",
        "paragraphe",
        "sous_paragraphe",
        "source_financement",
        "groupe_bailleur",
        "bailleur",
        "type_budget",
    ]

    def __init__(
        self,
        configuration: Optional[dict] = None,
        maintenant: Optional[datetime] = None,
        exception_ponctuelle: bool = False,
        accepter_ecart_test: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.configuration = configuration or {}
        self.maintenant = maintenant
        self.exception_ponctuelle = exception_ponctuelle
        self.niveau_concordance = "avertissement" if accepter_ecart_test else "bloquant"
        self.informations_chargement = {
            "exception_horaire_ponctuelle": exception_ponctuelle,
            "test_non_reconcilie": accepter_ecart_test,
        }

    @property
    def nom_fichier(self) -> str:
        return "oracle://chaine_depense"

    @classmethod
    def programmation_en_heures_ouvrees(cls, expression: str) -> bool:
        """Vrai si l'expression cron déclenche au moins une exécution en semaine aux heures ouvrées."""
        from etl.planificateur import analyser

        c = analyser(expression)
        debut, fin = cls.HEURES_OUVREES
        # Jours de semaine cron : 1 = lundi … 5 = vendredi.
        return bool(c.day_of_week & {1, 2, 3, 4, 5}) and any(
            debut <= dtime(h, m) <= fin for h in c.hour for m in c.minute
        )

    def verifier_creneau(self) -> None:
        if not settings.ORACLE_RESTRICTION_HEURES_OUVREES or self.exception_ponctuelle:
            return
        if self.configuration.get("replique", False):
            return
        tz = ZoneInfo(settings.TIME_ZONE)
        maintenant = self.maintenant or datetime.now(tz)
        debut, fin = self.HEURES_OUVREES
        if maintenant.weekday() < 5 and debut <= maintenant.time() <= fin:
            raise ErreurChargement(
                "Interrogation de la base de production interdite aux heures ouvrées "
                "(configurer une réplique ou planifier la nuit)."
            )

    def extract(self) -> dict[str, pd.DataFrame]:
        from .oracle import connexion_lecture_seule

        self.verifier_creneau()
        conf = settings.SOURCES_EXTERNES["chaine_depense_oracle"]
        if not conf["dsn"]:
            raise ErreurChargement("Connexion Oracle non configurée (CHAINE_DEPENSE_ORACLE_DSN).")
        requetes = self.configuration.get("requetes", {})
        if not self.exercice:
            raise ErreurChargement("Un exercice explicite est requis pour l'extraction Oracle.")
        if not {ONGLET_SITUATION, ONGLET_ENGAGEMENTS}.issubset(requetes):
            raise ErreurChargement("Requêtes Oracle situation et engagements requises.")
        donnees = {}
        with connexion_lecture_seule() as cnx:
            for onglet, sql in requetes.items():
                with cnx.cursor() as cursor:
                    cursor.arraysize = 1000
                    cursor.execute(sql, exercice=self.exercice)
                    df = pd.DataFrame(cursor.fetchall(), columns=[c[0] for c in cursor.description], dtype=object)
                df, _ = _renommer(df.astype(object), onglet)
                donnees[onglet] = df
        self.informations_chargement["indicateurs_indisponibles"] = (
            [] if "credit_disponible" in donnees[ONGLET_SITUATION].columns else ["credit_disponible"]
        )
        self.informations_chargement["referentiels_libelles"] = libelles_oracle(donnees)
        if self.date_situation is None:
            self.date_situation = date.today()
        return donnees

    def validate(self) -> RapportValidation:
        # Une validation répétée ne doit pas réutiliser le périmètre d'une extraction précédente.
        self.__dict__.pop("_engagements_concordance", None)
        self.__dict__.pop("_perimetre_concordance", None)
        self.informations_chargement.pop("rapprochement_engage", None)
        for onglet, champs in (
            (ONGLET_SITUATION, self.cle_ligne),
            (ONGLET_ENGAGEMENTS, ["exercice", "groupe_administratif", "numero"]),
        ):
            df = self.donnees.get(onglet)
            if df is None or any(c not in df.columns for c in champs):
                raise ErreurChargement(f"Clé source Oracle incomplète pour {onglet}.")
            if df.empty:
                raise ErreurChargement(f"Aucune donnée Oracle pour {onglet} et l'exercice demandé.")
            if df[champs].isna().any().any() or df[champs].duplicated().any():
                raise ErreurChargement(f"Clé source Oracle nulle ou dupliquée pour {onglet}.")
        sc = self.donnees[ONGLET_SITUATION]
        eng = self.donnees[ONGLET_ENGAGEMENTS]
        rapprochement = None
        if {"code_etat_dossier", "code_type_procedure"}.issubset(eng.columns):
            # Périmètre constaté dans l'analyse LBUDG/ENGAGEMENT 2025. Il n'est accepté
            # pour une extraction que si l'égalité est vérifiée sur CHAQUE clé complète.
            comparables = eng.loc[
                (eng["code_etat_dossier"].map(n.code) != "E9N") & (eng["code_type_procedure"].map(n.code) != "52")
            ]

            def totaux_par_cle(df, mesure):
                totaux = {}
                for row in df[self.cle_ligne + [mesure]].itertuples(index=False, name=None):
                    cle = tuple(n.code(v) for v in row[:-1])
                    totaux[cle] = totaux.get(cle, Decimal(0)) + n.montant_ou_zero(row[-1])
                return totaux

            budget = totaux_par_cle(sc, "credit_engage")
            engagements = totaux_par_cle(comparables, "montant_engage")
            ecarts = sum(budget.get(k, 0) != engagements.get(k, 0) for k in budget.keys() | engagements.keys())
            rapprochement = {"cles_en_ecart": ecarts, "lignes_ecartees_du_controle": len(eng) - len(comparables)}
            if not ecarts:
                self._engagements_concordance = comparables
                self._perimetre_concordance = "Hors dossiers abandonnés E9N et procédure 52 (Dégagement)"
                self.informations_chargement["rapprochement_engage"] = {
                    **rapprochement,
                    "perimetre": self._perimetre_concordance,
                    "donnees_source_conservees": True,
                }
        rapport = super().validate()
        if rapprochement is not None:
            rapport.ajouter(
                "concordance_engage_par_cle",
                "Rapprochement Oracle sur chaque clé budgétaire complète",
                self.niveau_concordance,
                rapprochement["cles_en_ecart"] == 0,
                nombre=rapprochement["cles_en_ecart"],
                detail=rapprochement,
            )
        return rapport
