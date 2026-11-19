"""Export décideurs du tableau « Ministères et institutions » (page Dépenses), en Excel et en PDF.

Mêmes données, filtres et droits que la page : une ligne par ministère ou institution, triée sur les
crédits non engagés, avec le total, une synthèse en tête, la comparaison avec l'exercice précédent
et une note de méthode. Montants en milliards de GNF.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from io import BytesIO
from typing import Optional

from django.utils import timezone

from apps.core import regles
from apps.core.filtres import Filtres
from apps.core.reponses import meta
from apps.referentiels.models import NATURE_VERS_TITRE, TITRES

from .comparaisons import comparaison_n1
from .criteres import actifs, options
from .services import sections

D0 = Decimal(0)
MILLIARD = Decimal(10**9)
TITRE = "Exécution budgétaire par ministère et institution"


@dataclass
class Colonne:
    cle: str
    libelle: str
    genre: str  # texte | montant | taux | ecart | entier
    largeur_xlsx: int
    largeur_pdf: float  # part de la largeur utile


# Toutes les colonnes possibles, dans l'ordre ; l'export ne retient que celles choisies à l'écran.
TOUTES = [
    Colonne("rang", "N°", "entier", 5, 0.03),
    Colonne("libelle", "Ministère / institution", "texte", 44, 0.18),
    Colonne("credit_actuel", "Crédits actuels", "montant", 14, 0.075),
    Colonne("credit_engage", "Engagé", "montant", 13, 0.065),
    Colonne("taux_engagement", "Taux d'engagement", "taux", 12, 0.08),
    Colonne("ecart_n1", "Écart N−1 (pts)", "ecart", 12, 0.06),
    Colonne("non_engage", "Non engagé", "montant", 13, 0.07),
    Colonne("montant_liquide", "Liquidé", "montant", 13, 0.065),
    Colonne("montant_ordonnance", "Ordonnancé", "montant", 13, 0.075),
    Colonne("montant_vbp", "Vu bon à payer", "montant", 13, 0.07),
    Colonne("montant_paye", "Payé", "montant", 13, 0.06),
    Colonne("paye_sur_ordonnance", "Payé / ordonnancé", "taux", 12, 0.07),
    Colonne("credit_disponible", "Disponible", "montant", 13, 0.07),
    Colonne("reste_a_payer", "Reste à payer", "montant", 13, 0.07),
    Colonne("nb_lignes_depassement", "Lignes en dépassement", "entier", 12, 0.075),
    Colonne("statut", "Statut", "texte", 24, 0.09),
]
# Jeu par défaut (aucun choix transmis) : celui de la première version de l'export.
COLONNES = [c for c in TOUTES if c.cle not in ("montant_liquide", "montant_vbp", "credit_disponible")]
# Colonne de l'écran → colonnes de l'export (« Engagé » affiche à l'écran le montant et le taux).
CHOIX = {
    "credit_actuel": ("credit_actuel",),
    "taux_engagement": ("credit_engage", "taux_engagement"),
    "ecart_n1": ("ecart_n1",),
    "non_engage": ("non_engage",),
    "montant_liquide": ("montant_liquide",),
    "montant_ordonnance": ("montant_ordonnance",),
    "montant_vbp": ("montant_vbp",),
    "montant_paye": ("montant_paye",),
    "paye_sur_ordonnance": ("paye_sur_ordonnance",),
    "credit_disponible": ("credit_disponible",),
    "reste_a_payer": ("reste_a_payer",),
    "nb_lignes_depassement": ("nb_lignes_depassement",),
    "statut": ("statut",),
}


def colonnes_choisies(choix: Optional[str]) -> list[Colonne]:
    """Colonnes de l'export d'après le paramètre « colonnes » (identifiants de l'écran séparés par des virgules).

    Le rang et le libellé sont toujours présents ; un identifiant inconnu est ignoré ; sans choix, jeu par défaut.
    """
    if not choix:
        return list(COLONNES)
    retenues = {"rang", "libelle"}
    for cle in choix.split(",")[:30]:
        retenues.update(CHOIX.get(cle.strip(), ()))
    return [c for c in TOUTES if c.cle in retenues]


@dataclass
class Donnees:
    f: Filtres
    meta: dict
    lignes: list[dict]
    total: dict
    n1: dict
    filtres: str
    synthese: list[tuple[str, str]] = field(default_factory=list)
    colonnes: list[Colonne] = field(default_factory=lambda: list(COLONNES))


def _mds(v) -> Optional[float]:
    return None if v is None else float(Decimal(v) / MILLIARD)


def _description_filtres(f: Filtres) -> str:
    parties = []
    if f.nature:
        parties.append(f"Nature : {TITRES.get(NATURE_VERS_TITRE.get(f.nature, ''), f.nature)}")
    if f.paiement == "brut":
        parties.append("Paiements bruts (procédures hors chaîne incluses)")
    criteres = actifs(f)
    if criteres:
        libelles = {
            c["cle"]: (c["libelle"], {v["code"]: v["libelle"] for v in c["valeurs"]}) for c in options(f)["criteres"]
        }
        for cle, valeurs in criteres.items():
            nom, valeurs_lib = libelles.get(cle, (cle, {}))
            parties.append(f"{nom} : " + ", ".join(valeurs_lib.get(v, v) for v in valeurs))
    return " · ".join(parties) or "Aucun : tous ministères, toutes natures"


def preparer(f: Filtres, colonnes: Optional[list[Colonne]] = None) -> Donnees:
    n1 = comparaison_n1(f)
    par_section = n1.get("par_section", {}) if n1.get("disponible") else {}
    lignes = []
    for s in sections(f):
        ref = par_section.get(s["code"])
        lignes.append(
            s
            | {
                "non_engage": max(s["credit_actuel"] - s["credit_engage"], D0),
                "ecart_n1": (
                    None if ref is None or s["taux_engagement"] is None else round((s["taux_engagement"] - ref) * 100)
                ),
                "statut": s["statut"]["libelle"],
            }
        )
    lignes.sort(key=lambda s: s["non_engage"], reverse=True)
    for rang, s in enumerate(lignes, start=1):
        s["rang"] = rang
    total = {
        k: sum((s[k] or D0 for s in lignes), D0)
        for k in (
            "credit_actuel",
            "credit_engage",
            "non_engage",
            "montant_liquide",
            "montant_ordonnance",
            "montant_vbp",
            "montant_paye",
            "reste_a_payer",
        )
    }
    disponibles = [s["credit_disponible"] for s in lignes if s.get("credit_disponible") is not None]
    total["credit_disponible"] = sum(disponibles, D0) if disponibles else None
    total["nb_lignes_depassement"] = sum(s["nb_lignes_depassement"] or 0 for s in lignes)
    total["taux_engagement"] = regles.taux(total["credit_engage"], total["credit_actuel"])
    total["paye_sur_ordonnance"] = regles.taux(total["montant_paye"], total["montant_ordonnance"])
    total["libelle"] = f"Total ({len(lignes)} ministères et institutions)"
    if n1.get("disponible") and total["taux_engagement"] is not None and n1.get("taux_engagement") is not None:
        total["ecart_n1"] = round((total["taux_engagement"] - n1["taux_engagement"]) * 100)
    trois = sum((s["non_engage"] for s in lignes[:3]), D0)
    synthese = [
        ("Crédits actuels", _mds_txt(total["credit_actuel"])),
        (
            "Engagé",
            f"{_mds_txt(total['credit_engage'])} · {_pct(total['taux_engagement'])}",
        ),
        ("Non engagé", _mds_txt(total["non_engage"])),
        (
            "Concentration",
            f"Les 3 premiers ministères portent {_pct(regles.taux(trois, total['non_engage']))} du non-engagé",
        ),
    ]
    if n1.get("disponible"):
        synthese.append(
            (
                f"Repère {n1['exercice']}",
                f"{_pct(n1['taux_engagement'])} engagés au {n1['date']:%d/%m/%Y} (même date de l'exercice précédent)",
            )
        )
    return Donnees(
        f, meta("chaine_depense", f), lignes, total, n1, _description_filtres(f), synthese, colonnes or list(COLONNES)
    )


def _mds_txt(v) -> str:
    return f"{_mds(v):,.1f}".replace(",", " ").replace(".", ",") + " Mds"


def _pct(v) -> str:
    return "—" if v is None else f"{float(v) * 100:.0f} %"


def _valeur_brute(c: Colonne, ligne: dict):
    v = ligne.get(c.cle)
    if c.genre == "montant":
        return _mds(v)
    if c.genre == "taux":
        return None if v is None else float(v)
    return v


def _texte(c: Colonne, ligne: dict) -> str:
    v = ligne.get(c.cle)
    if v is None or v == "":
        return "" if c.genre == "texte" or c.cle == "rang" else "—"
    if c.genre == "montant":
        return f"{_mds(v):,.1f}".replace(",", " ").replace(".", ",")
    if c.genre == "taux":
        return _pct(v)
    if c.genre == "ecart":
        return f"{'+' if v > 0 else ''}{v}"
    return str(v)


# (colonne concernée, libellé, définition) : seules les définitions des colonnes exportées sont reprises.
_METHODE = [
    ("taux_engagement", "Taux d'engagement", "Engagé / crédits actuels."),
    ("ecart_n1", "Écart N−1", "Taux d'engagement moins celui de l'exercice précédent à la même date, en points."),
    ("non_engage", "Non engagé", "Crédits actuels − engagé (zéro si l'engagé dépasse les crédits). Ordre du tableau."),
    ("montant_liquide", "Liquidé", "Montants liquidés (service fait constaté), bruts de la situation."),
    ("montant_vbp", "Vu bon à payer", "Montants visés bon à payer, bruts de la situation."),
    (
        "paye_sur_ordonnance",
        "Payé / ordonnancé",
        "Part de l'ordonnancé effectivement payée, selon le mode de paiement choisi.",
    ),
    ("credit_disponible", "Disponible", "Crédit disponible de la situation (négatif en cas de dépassement)."),
    (
        "reste_a_payer",
        "Reste à payer",
        "Ordonnancé − payé ; à rapprocher avec le Trésor, ne certifie pas un stock d'arriérés.",
    ),
    ("nb_lignes_depassement", "Lignes en dépassement", "Lignes budgétaires dont le crédit disponible est négatif."),
    ("statut", "Statut", "Statut de suivi calculé par l'application (règles paramétrables en administration)."),
]
METHODE = [(lib, txt) for _, lib, txt in _METHODE]


def _methode(d: Donnees) -> list[tuple[str, str]]:
    cles = {c.cle for c in d.colonnes}
    return [(lib, txt) for cle, lib, txt in _METHODE if cle in cles]


# ------------------------------------------------------------------------------------------- Excel


def classeur(d: Donnees, utilisateur: str) -> bytes:
    from openpyxl import Workbook
    from openpyxl.formatting.rule import DataBarRule
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    marine, or_, gris = "16314E", "B8860B", "F3F5F8"
    fin = Side(style="thin", color="DCE2EA")
    wb = Workbook()
    ws = wb.active
    ws.title = "Ministères"
    COLONNES = d.colonnes  # noqa: N806 (colonnes choisies à l'écran)
    n = len(COLONNES)
    der = get_column_letter(n)

    def ligne_titre(texte, **police):
        ws.append([texte])
        ws.merge_cells(start_row=ws.max_row, start_column=1, end_row=ws.max_row, end_column=n)
        ws.cell(ws.max_row, 1).font = Font(**police)

    ligne_titre("RÉPUBLIQUE DE GUINÉE · Ministère de l'Économie, des Finances et du Budget", bold=True, color=marine)
    ligne_titre(TITRE, bold=True, size=16, color=marine)
    m = d.meta
    ligne_titre(
        f"Exercice {m.get('exercice')} · situation au {_date(m.get('date_situation'))} · source : "
        f"{m.get('application') or 'Chaîne Dépense'} · montants en milliards de GNF",
        color="4A5668",
    )
    ligne_titre(f"Filtres : {d.filtres}", color="4A5668")
    ligne_titre(
        f"Exporté le {timezone.localtime():%d/%m/%Y à %H:%M} par {utilisateur} · "
        "Document de travail – diffusion restreinte",
        italic=True,
        color="4A5668",
    )
    ws.append([])
    # Synthèse en tête : libellé / valeur sur deux colonnes fusionnées.
    for libelle, valeur in d.synthese:
        ws.append([libelle, None, valeur])
        r = ws.max_row
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=2)
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=n)
        ws.cell(r, 1).font = Font(bold=True, color=marine)
        ws.cell(r, 1).fill = PatternFill("solid", fgColor=gris)
    ws.append([])

    ws.append([c.libelle for c in COLONNES])
    entete = ws.max_row  # après l'ajout : une ligne vide n'est pas comptée par max_row
    for i, c in enumerate(COLONNES, start=1):
        cell = ws.cell(entete, i)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=marine)
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        ws.column_dimensions[get_column_letter(i)].width = c.largeur_xlsx
    ws.row_dimensions[entete].height = 32

    formats = {"montant": "#,##0.0", "taux": "0%", "ecart": "+0;-0;0", "entier": "0"}
    for k, ligne in enumerate(d.lignes):
        ws.append([_valeur_brute(c, ligne) for c in COLONNES])
        r = ws.max_row
        for i, c in enumerate(COLONNES, start=1):
            cell = ws.cell(r, i)
            cell.border = Border(bottom=fin)
            if c.genre in formats:
                cell.number_format = formats[c.genre]
                cell.alignment = Alignment(horizontal="right")
            if k % 2:
                cell.fill = PatternFill("solid", fgColor="F8F9FB")
    premiere, derniere = entete + 1, ws.max_row
    ws.append([_valeur_brute(c, d.total | {"rang": None}) for c in COLONNES])
    r = ws.max_row
    for i, c in enumerate(COLONNES, start=1):
        cell = ws.cell(r, i)
        cell.font = Font(bold=True, color=marine)
        cell.border = Border(top=Side(style="medium", color=marine))
        if c.genre in formats:
            cell.number_format = formats[c.genre]
            cell.alignment = Alignment(horizontal="right")
    # Barres proportionnelles discrètes : taux d'engagement et non engagé.
    for cle, couleur in (("taux_engagement", "2A78D6"), ("non_engage", or_)):
        if cle not in {c.cle for c in COLONNES}:
            continue
        col = get_column_letter([c.cle for c in COLONNES].index(cle) + 1)
        ws.conditional_formatting.add(
            f"{col}{premiere}:{col}{derniere}", DataBarRule(start_type="min", end_type="max", color=couleur)
        )
    ws.freeze_panes = ws.cell(entete + 1, 3)
    ws.auto_filter.ref = f"A{entete}:{der}{derniere}"
    ws.print_title_rows = f"{entete}:{entete}"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.oddFooter.left.text = "Document de travail – diffusion restreinte"
    ws.oddFooter.right.text = "Page &P / &N"

    meth = wb.create_sheet("Méthode")
    meth.append(["Indicateur", "Définition"])
    for c in meth[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=marine)
    for ligne in _methode(d):
        meth.append(list(ligne))
    if d.n1.get("disponible"):
        meth.append(["Repère N−1", d.n1["methode"]])
    else:
        meth.append(["Repère N−1", d.n1.get("motif", "Non disponible.")])
    meth.column_dimensions["A"].width = 26
    meth.column_dimensions["B"].width = 110
    for row in meth.iter_rows(min_row=2):
        row[1].alignment = Alignment(wrap_text=True, vertical="top")

    tampon = BytesIO()
    wb.save(tampon)
    return tampon.getvalue()


def _date(v) -> str:
    if not v:
        return "—"
    s = str(v)
    return f"{s[8:10]}/{s[5:7]}/{s[:4]}" if len(s) >= 10 else s


# --------------------------------------------------------------------------------------------- PDF


def pdf(d: Donnees, utilisateur: str) -> bytes:
    from xml.sax.saxutils import escape

    from reportlab.platypus import KeepTogether, LongTable, Paragraph, Spacer, Table, TableStyle

    from apps.core.export_pdf import BORDER, MUTED, NAVY, TINT, WHITE, WIDTH, DocumentPdf, _p, _polices, _style
    from apps.core.export_pdf import _texte as texte_pdf

    _polices()
    COLONNES = d.colonnes  # noqa: N806 (colonnes choisies à l'écran)
    # Largeurs ramenées à la largeur utile, quel que soit le nombre de colonnes retenues.
    somme = sum(c.largeur_pdf for c in COLONNES)
    largeurs = [WIDTH * c.largeur_pdf / somme for c in COLONNES]
    flux = BytesIO()
    doc = DocumentPdf(flux, TITRE, utilisateur)
    m = d.meta
    contenu = [
        _p(TITRE, fontName="Tdb-Bold", fontSize=18, leading=23, textColor=NAVY, spaceAfter=4),
        _p(
            f"Exercice {m.get('exercice')} · situation au {_date(m.get('date_situation'))} · source : "
            f"{m.get('application') or 'Chaîne Dépense'} · montants en milliards de GNF",
            fontSize=8.5,
            textColor=MUTED,
        ),
        _p(f"Filtres : {d.filtres} · exporté par {utilisateur}", fontSize=8.5, textColor=MUTED),
        Spacer(1, 8),
    ]
    # Synthèse : une cellule par chiffre clé.
    cellules = [
        [
            _p(lib, fontSize=7.5, spaceAfter=2, textColor=MUTED),
            _p(val, fontName="Tdb-Bold", fontSize=10, leading=13, spaceAfter=0, textColor=NAVY),
        ]
        for lib, val in d.synthese
    ]
    resume = Table([cellules], colWidths=[WIDTH / len(cellules)] * len(cellules))
    resume.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("BACKGROUND", (0, 0), (-1, -1), TINT),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    contenu += [KeepTogether([resume]), Spacer(1, 10)]

    def cellule(c: Colonne, ligne: dict, gras=False):
        style = dict(fontSize=7.2, leading=9, spaceAfter=0, alignment=0 if c.genre == "texte" else 2)
        if gras:
            style |= dict(fontName="Tdb-Bold", textColor=NAVY)
        return _p(_texte(c, ligne), **style)

    entete = [
        _p(c.libelle, fontName="Tdb-Bold", fontSize=6.8, leading=8.5, spaceAfter=0, textColor=WHITE) for c in COLONNES
    ]
    corps = [[cellule(c, ligne) for c in COLONNES] for ligne in d.lignes]
    total = [cellule(c, d.total | {"rang": ""}, gras=True) for c in COLONNES]
    tableau = LongTable([entete, *corps, total], colWidths=largeurs, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 1), (-1, -2), 0.3, BORDER),
        ("LINEABOVE", (0, -1), (-1, -1), 1, NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    style += [("BACKGROUND", (0, i), (-1, i), "#F8F9FB") for i in range(2, len(corps) + 1, 2)]
    tableau.setStyle(TableStyle(style))
    contenu += [tableau, Spacer(1, 10)]
    notes = [_p("Méthode", fontName="Tdb-Bold", fontSize=9, textColor=NAVY, spaceAfter=3)]
    repere = d.n1["methode"] if d.n1.get("disponible") else d.n1.get("motif", "Non disponible.")
    for lib, txt in [*_methode(d), ("Repère N−1", repere)]:
        # Libellé en gras : balise construite ici, textes échappés.
        notes.append(
            Paragraph(
                f"<b>{escape(texte_pdf(lib))}</b> : {escape(texte_pdf(txt))}",
                _style(fontSize=7.5, leading=10, textColor=MUTED, spaceAfter=2),
            )
        )
    contenu.append(KeepTogether(notes))
    doc.build(contenu)
    return flux.getvalue()
