"""Fonctions de nettoyage communes à tous les connecteurs."""

from __future__ import annotations

import math
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

import pandas as pd

_ESPACES = re.compile(r"\s+")


def est_vide(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    if v is pd.NaT:
        return True
    if isinstance(v, str) and v.strip() == "":
        return True
    return False


def sans_accents(texte: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn")


def cle_entete(entete: Any) -> str:
    """Clé de comparaison d'un en-tête : minuscules, sans accents, espaces réduits."""
    return _ESPACES.sub(" ", sans_accents(str(entete)).lower()).strip()


def code(v: Any) -> str:
    """Code lu en texte, zéros initiaux conservés, espaces supprimés.

    Si Excel a stocké le code comme nombre, 1.0 devient « 1 » (le zéro initial
    ne peut alors pas être reconstitué : c'est signalé par le contrôle qualité).
    """
    if est_vide(v):
        return ""
    if isinstance(v, bool):
        return str(int(v))
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def libelle(v: Any) -> str:
    if est_vide(v):
        return ""
    return _ESPACES.sub(" ", str(v)).strip()


def montant(v: Any) -> tuple[Decimal, bool]:
    """Montant décimal et indicateur « valeur absente » (la valeur vaut alors 0)."""
    if est_vide(v):
        return Decimal(0), True
    if isinstance(v, Decimal):
        return v, False
    if isinstance(v, (int, float)):
        return Decimal(str(v)), False
    texte = str(v).strip().replace(" ", "").replace("\xa0", "").replace(" ", "")
    if "," in texte and "." not in texte:
        texte = texte.replace(",", ".")
    try:
        return Decimal(texte), False
    except InvalidOperation as exc:
        raise ValueError(f"Montant illisible : {v!r}") from exc


def montant_ou_zero(v: Any) -> Decimal:
    return montant(v)[0]


def date_(v: Any) -> Optional[date]:
    if est_vide(v):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, pd.Timestamp):
        return v.date()
    texte = str(v).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%Y %H:%M:%S"):
        try:
            return datetime.strptime(texte, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Date illisible : {v!r}")


# ------------------------------------------------------------ libellés affichés

# Mots dont l'extraction a perdu les accents (en majuscules, sans accents).
ACCENTS = {
    "MINISTERE": "Ministère",
    "MINISTERES": "Ministères",
    "ECONOMIE": "Économie",
    "DEFENSE": "Défense",
    "SECURITE": "Sécurité",
    "ETRANGERES": "Étrangères",
    "ETRANGER": "Étranger",
    "INTEGRATION": "Intégration",
    "GUINEENS": "Guinéens",
    "GUINEE": "Guinée",
    "ETABLIS": "Établis",
    "COOPERATION": "Coopération",
    "DEVELOPPEMENT": "Développement",
    "PECHE": "Pêche",
    "GEOLOGIE": "Géologie",
    "AMENAGEMENT": "Aménagement",
    "SANTE": "Santé",
    "HYGIENE": "Hygiène",
    "SOLIDARITE": "Solidarité",
    "EDUCATION": "Éducation",
    "NUMERIQUE": "Numérique",
    "SUPREME": "Suprême",
    "AUTORITE": "Autorité",
    "SECRETARIAT": "Secrétariat",
    "GENERAL": "Général",
    "GENERALE": "Générale",
    "PRESIDENCE": "Présidence",
    "REPUBLIQUE": "République",
    "SUPERIEUR": "Supérieur",
    "ENERGIE": "Énergie",
    "ELEVAGE": "Élevage",
    "SPECIAUX": "Spéciaux",
    "CONTROLE": "Contrôle",
    "DEPENSES": "Dépenses",
    "DEPENSE": "Dépense",
    "ETAT": "État",
    "DECENTRALISATION": "Décentralisation",
    "ORGANISE": "Organisé",
    "CHARGE": "Chargé",
    "ASSEMBLEE": "Assemblée",
    "ELECTORALE": "Électorale",
    "MEDIATEUR": "Médiateur",
    "REFORME": "Réforme",
    "ENERGIES": "Énergies",
    "ELECTRICITE": "Électricité",
    "COMMUNAUTE": "Communauté",
    "ECONOMIQUE": "Économique",
    "PREVOYANCE": "Prévoyance",
    "SOCIETE": "Société",
    "ENTREPRISES": "Entreprises",
    "INTERIEUR": "Intérieur",
    "PROMOTION": "Promotion",
    "FEMININE": "Féminine",
    "HOTELLERIE": "Hôtellerie",
    "PRIMATURE": "Primature",
    "TRESOR": "Trésor",
    "PUBLIQUE": "Publique",
    "DETTE": "Dette",
    "ETUDES": "Études",
    "EGALITE": "Égalité",
}
MOTS_MINUSCULES = {"de", "du", "des", "la", "le", "les", "et", "a", "à", "aux", "au", "en", "contre", "pour", "sur"}


def titre_francais(texte: str) -> str:
    """Titre-case un libellé en majuscules et rétablit les accents usuels.

    « MINISTERE DE L'ECONOMIE, DES FINANCES ET DU BUDGET »
    → « Ministère de l'Économie, des Finances et du Budget »
    """
    texte = libelle(texte)
    # « DE L ADMINISTRATION » : apostrophe perdue dans l'extraction.
    texte = re.sub(r"\b([LD]) (?=[AEIOUYH])", r"\1'", texte.upper())
    mots = re.split(r"(\s+|,|-|/|\()", texte)
    sortie = []
    premier = True
    for mot in mots:
        if not mot or not re.search(r"\w", mot):
            sortie.append(mot)
            continue
        if "'" in mot:
            prefixe, _, reste = mot.partition("'")
            p = prefixe.lower() if not premier else prefixe.capitalize()
            sortie.append(f"{p}'{_mot(reste, False)}")
        else:
            sortie.append(_mot(mot, premier))
        premier = False
    return "".join(sortie)


def _mot(mot: str, premier: bool) -> str:
    cle = sans_accents(mot).upper()
    if cle in ACCENTS:
        return ACCENTS[cle]
    if not premier and mot.lower() in MOTS_MINUSCULES:
        return "à" if mot.lower() == "a" else mot.lower()
    if len(mot) <= 4 and mot.isupper() and cle in {"CNT", "DNSI", "DGB", "EPA", "BCRG", "PME", "ONG", "TIC"}:
        return mot
    return mot.capitalize()


_ARTICLES = re.compile(r"(^|, | et )(?:de la |de l'|des |du |de |d')", re.IGNORECASE)


def libelle_court_section(libelle_affiche: str) -> str:
    """Libellé court d'un ministère : « Ministère de l'Économie, des Finances et du Budget »
    → « Économie, Finances et Budget ». Les institutions gardent leur libellé."""
    m = re.match(r"^Ministères? (.*)$", libelle_affiche)
    if not m:
        return libelle_affiche
    reste = _ARTICLES.sub(lambda x: x.group(1), m.group(1))
    return reste[:1].upper() + reste[1:]


def type_section(code_section: str, libelle_source: str) -> str:
    brut = sans_accents(libelle_source).upper()
    if code_section == "99" or brut.startswith("DEPENSES COMMUNES"):
        return "depenses_communes"
    if brut.startswith("MINISTERE"):
        return "ministere"
    return "institution"


# ----------------------------------------------------------------- bénéficiaires


def beneficiaire_affiche(nom: Any) -> str:
    """Nom d'affichage : espaces multiples réduits."""
    return libelle(nom)


def beneficiaire_cle(nom: Any) -> str:
    """Clé de rapprochement : sans accents, majuscules, sans espaces ni ponctuation.

    « GAL BGD TRAORE Gassimou » et « GAL BGD TRAOREGassimou » → « GALBGDTRAOREGASSIMOU ».
    """
    return re.sub(r"[^0-9A-Z]", "", sans_accents(libelle(nom)).upper())


def beneficiaire_alias(nom: Any) -> str:
    """Variante normalisée (espaces conservés) enregistrée comme alias."""
    return _ESPACES.sub(" ", re.sub(r"[^0-9A-Z ]", " ", sans_accents(libelle(nom)).upper())).strip()


# ----------------------------------------------------------- nom de fichier

MOIS_FR = {
    "janvier": 1,
    "fevrier": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "aout": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "decembre": 12,
}


def infos_nom_fichier(nom: str) -> tuple[Optional[int], Optional[date]]:
    """Exercice et date de situation déduits du nom de fichier.

    « SC de 2025-2025 en date du 15-09-2026.xlsx » → (2025, 2026-09-15)
    « SC des pp_du_dimanche 16 août 2026 22_10_49.xlsx » → (None, 2026-08-16)
    """
    base = sans_accents(nom).lower()
    exercice = None
    m = re.search(r"sc de (\d{4})-(\d{4})", base)
    if m:
        exercice = int(m.group(1))
    date_situation = None
    m = re.search(r"en date du (\d{1,2})[-_/.](\d{1,2})[-_/.](\d{4})", base)
    if m:
        date_situation = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    else:
        m = re.search(r"(\d{1,2}) (" + "|".join(MOIS_FR) + r") (\d{4})", base)
        if m:
            date_situation = date(int(m.group(3)), MOIS_FR[m.group(2)], int(m.group(1)))
    return exercice, date_situation
