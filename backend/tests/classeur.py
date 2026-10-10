"""Générateur d'extraction Chaîne Dépense synthétique, aux valeurs connues (en GNF)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from openpyxl import Workbook

MD = 10**9

EN_TETES_SC = [
    "type budget",
    "Section",
    "libelle section",
    "Sous section",
    "libelle sous section",
    "Code Titre",
    "libelle titre",
    "Code chapitre",
    "libelle chapitre",
    "Code article",
    "libelle article",
    "Code paragraphe",
    "libelle paragraphe",
    "Code Sous paragraphe",
    "libelle sous paragraphe",
    "code source financement",
    "code groupe bailleur",
    "code bailleur",
    "code regulation",
    "crédit initial LFI",
    "crédit LFR",
    "crédit actuel",
    "crédits disponible",
    "crédit reservé",
    "crédits engagés",
    "Credits engagés en projet",
    "Credits engagés CF",
    "montant liquidé",
    "montant ordonnancé",
    "montant vue bon pour paiement",
    "montant encours de paiement",
    "montant payé",
    "montant bloque",
    "montant delegation",
    "Avance de demarrage",
    "montant regie",
    "Exercice",
    "pillier simandou",
]
EN_TETES_ENG = [
    "Exercice",
    "type budget",
    "Numéro engagement",
    "Section",
    "Sous Section",
    "Titre",
    "Chapitre",
    "Article",
    "Paragraphe",
    "Sous Paragraphe",
    "source fin",
    "groupe fin",
    "bailleur",
    "Libelle Section",
    "Objet",
    "Bénéficiaire",
    "Type engagement",
    "Etat dossier",
    "Montant initial eng",
    "Montant engagé",
    "Montant devise",
    "Devise",
    "Montant Eng CF",
    "Montant retenu",
    "Montant Liq",
    "Montant Ord",
    "Montant VBP",
    "Montant ECP",
    "Montant Payé",
    "Date creation",
    "Date Visa CF",
    "Date Visa Ministre",
    "Date etat",
    "Date Maj",
]
EN_TETES_OP = [
    "numéro Exercice",
    "Section",
    "Sous Section",
    "Titre",
    "Chapitre",
    "Article",
    "Paragraphe",
    "Sous Paragraphe",
    "libelle section",
    "Bénéficiaire",
    "Object",
    "Numéro engagement",
    "Type engagement",
    "Etat dossier",
    "Type Origine",
    "Montant",
    "Montant engagé",
    "Montant Engagé CF",
    "Montant Liquidé",
    "Montant devise",
    "code devise",
    "Montant VBP",
    "Date Visa VBP",
    "Montant Ordonnancé",
    "Montant Payé",
]
EN_TETES_REGIE = [
    "numéro Exercice",
    "type budget",
    "gradm",
    "numero régie",
    "Section",
    "Sous Section",
    "Libelle Sous Section",
    "Nature flux",
    "Titre",
    "Chapitre",
    "Article",
    "Paragraphe",
    "Sous Paragraphe",
    "Source fin",
    "Groupe bailleur",
    "Bailleurs",
    "Montant Régie",
    "Date Création",
    "Etat Dossier",
]

LIB = {
    "14": "MINISTERES DES INFRASTRUCTURES",
    "09": "MINISTERE DE L'ECONOMIE, DES FINANCES ET DU BUDGET",
    "99": "DEPENSES COMMUNES",
}
TITRES = {
    "1": "Depenses De La Dette",
    "2": "Depenses De Personnel",
    "3": "Depenses De Biens Et Services",
    "5": "Depenses D'Investissement",
}


def _ligne(
    section,
    sous_section,
    titre,
    lfi,
    actuel,
    engage,
    liquide,
    ordonnance,
    paye,
    *,
    dispo=None,
    paragraphe="10",
    regul="00 ",
    lfr=None,
):
    dispo = actuel - engage if dispo is None else dispo
    return [
        "000",
        section,
        LIB[section] + "   ",
        sous_section,
        f"Service {sous_section}",
        titre,
        TITRES[titre],
        "1",
        "Chapitre",
        "1",
        "Article",
        paragraphe,
        "Paragraphe",
        "01",
        "Sous-paragraphe",
        "2",
        "0",
        "000",
        regul,
        lfi,
        lfr,
        actuel,
        dispo,
        0,
        engage,
        0,
        engage,
        liquide,
        ordonnance,
        ordonnance,
        0,
        paye,
        0,
        0,
        0,
        0,
        "2025",
        "Infrastructures",
    ]


# Situation courante : 7 lignes.
LIGNES_SC = [
    # Infrastructures : 30 Md de crédits, 3 Md engagés → sous-exécution.
    _ligne("14", "140100000000", "5", 25 * MD, 28 * MD, 3 * MD, 3 * MD, 2 * MD, 1 * MD),
    # Projet d'investissement de 2 Md sans engagement.
    _ligne("14", "140200000000", "5", 2 * MD, 2 * MD, 0, 0, 0, 0),
    # Ligne en dépassement (disponible < 0) et liquidé > engagé ; LFI vide.
    _ligne("09", "090100000000", "3", None, 10 * MD, 9 * MD, 9_500_000_000, 9 * MD, 8 * MD, dispo=-5_000_000),
    _ligne("09", "090100000000", "2", 5 * MD, 5 * MD, 5 * MD, 5 * MD, 5 * MD, 5 * MD, lfr=0),
    # Dépenses communes : salaires (Solde) et dette (débit d'office) payés hors chaîne.
    _ligne("99", "990100000000", "2", 40 * MD, 40 * MD, 40 * MD, 40 * MD, 40 * MD, 0),
    _ligne("99", "990200000000", "1", 20 * MD, 20 * MD, 20 * MD, 20 * MD, 20 * MD, 0),
    # Doublon de clé : même imputation que la ligne précédente, régulation identique.
    _ligne("99", "990200000000", "1", 0, 0, 0, 0, 0, 0),
]


def _eng(num, section, sous_section, titre, benef, procedure, etat, engage, ordonnance, paye, creation):
    return [
        "2025",
        "000",
        f"{num}      ",
        section,
        sous_section,
        titre,
        "1",
        "1",
        "10",
        "01",
        "2",
        "0",
        "000",
        LIB[section] + "  ",
        "Objet",
        benef,
        procedure + "   ",
        etat + "   ",
        engage,
        engage,
        0,
        None,
        engage,
        0,
        ordonnance,
        ordonnance,
        ordonnance,
        0,
        paye,
        creation,
        creation,
        creation,
        creation,
        creation,
    ]


LIGNES_ENG = [
    _eng(
        "1",
        "14",
        "140100000000",
        "5",
        "GAL BGD TRAORE Gassimou",
        "Procedure normale",
        "Depense engagee",
        2 * MD,
        2 * MD,
        1 * MD,
        datetime(2025, 3, 10),
    ),
    _eng(
        "2",
        "14",
        "140100000000",
        "5",
        "GAL BGD TRAOREGassimou",
        "Procedure normale",
        "Nouvel engagement",
        1 * MD,
        0,
        0,
        datetime(2025, 12, 5),
    ),
    # Même numéro et même section qu'un autre engagement : clé technique.
    _eng(
        "1",
        "09",
        "090100000000",
        "3",
        "ENTREPRISE ALPHA",
        "Procedure Normale MP",
        "Depense engagee",
        9 * MD,
        9 * MD,
        8 * MD,
        datetime(2024, 6, 1),
    ),
    _eng(
        "3",
        "09",
        "090100000000",
        "2",
        "ENTREPRISE ALPHA",
        "Procedure normale",
        "Depense engagee",
        5 * MD,
        5 * MD,
        5 * MD,
        datetime(2025, 1, 15),
    ),
    _eng(
        "4",
        "99",
        "990100000000",
        "2",
        "SOLDE DES AGENTS",
        "Procedure Solde",
        "Depense engagee",
        40 * MD,
        40 * MD,
        0,
        datetime(2025, 2, 1),
    ),
    _eng(
        "5",
        "99",
        "990200000000",
        "1",
        "BCRG",
        "Debit d'office - NE PAS PAYER",
        "Depense engagee",
        20 * MD,
        20 * MD,
        0,
        datetime(2026, 1, 20),
    ),  # période complémentaire
]

TOTAL_ENGAGE = 77 * MD


def ecrire_classeur(
    dossier: Path,
    nom: str = "SC de 2025-2025 en date du 15-09-2026.xlsx",
    *,
    engagements=None,
    sans_onglet_regie: bool = False,
) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "Situation courante"
    ws.append(EN_TETES_SC)
    for r in LIGNES_SC:
        ws.append(r)
    ws = wb.create_sheet("Liste des engagements")
    ws.append(EN_TETES_ENG)
    for r in engagements if engagements is not None else LIGNES_ENG:
        ws.append(r)
    ws = wb.create_sheet("Détails des opérations")
    ws.append(EN_TETES_OP)
    ws.append(
        [
            "2025",
            "14",
            "140100000000",
            "5",
            "1",
            "1",
            "10",
            "01",
            LIB["14"],
            "GAL BGD TRAORE Gassimou",
            "Objet",
            "1",
            "Procedure normale",
            "Depense engagee",
            "Liquidation",
            1 * MD,
            2 * MD,
            2 * MD,
            1 * MD,
            0,
            None,
            1 * MD,
            datetime(2025, 4, 1),
            1 * MD,
            1 * MD,
        ]
    )
    if not sans_onglet_regie:
        ws = wb.create_sheet("Régie")
        ws.append(EN_TETES_REGIE)  # onglet vide : la structure doit suffire
    ws = wb.create_sheet("APAD")  # onglet non géré : ignoré
    ws.append(["Exercice", "numero APAD"])
    chemin = dossier / nom
    wb.save(chemin)
    return chemin
