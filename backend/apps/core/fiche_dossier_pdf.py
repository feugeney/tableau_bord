"""Fiche de suivi d'un dossier (alerte par dossier, ex. arbitrage de la Ministre) en PDF structuré.

A4 portrait, charte des rapports PDF (export_pdf.py) : bandeau officiel avec armoiries et filet tricolore,
rubriques numérotées en tableaux, cadre de décision à compléter, pied de page « diffusion restreinte »
paginé « Page n / N ».
"""

from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from pathlib import Path

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as canvas_pdf
from reportlab.platypus import BaseDocTemplate, Frame, KeepTogether, PageTemplate, Spacer, Table, TableStyle

from .export_pdf import (
    BACKGROUND,
    BORDER,
    CREDIT_ARMOIRIES,
    GOLD,
    INK,
    MUTED,
    NAVY,
    TINT,
    WHITE,
    _p,
    _polices,
    _texte,
    mention_droits,
)
from .models import Alerte

PAGE = A4
MARGE = 40
LARGEUR = PAGE[0] - 2 * MARGE
GRAVITES = {"critique": "Critique", "serieux": "Sérieux", "vigilance": "Vigilance"}
COULEURS_GRAVITE = {"critique": "#b42318", "serieux": "#b54708", "vigilance": "#8a6d00"}
STATUTS = {"nouvelle": "Nouvelle (non traitée)", "vue": "Vue (en cours)", "traitee": "Traitée"}


def _date(valeur) -> str | None:
    if not valeur:
        return None
    if isinstance(valeur, str):
        try:
            valeur = date.fromisoformat(valeur[:10]) if len(valeur) <= 10 else datetime.fromisoformat(valeur)
        except ValueError:
            return valeur
    if isinstance(valeur, datetime):
        return (
            timezone.localtime(valeur).strftime("%d/%m/%Y à %H:%M")
            if timezone.is_aware(valeur)
            else (valeur.strftime("%d/%m/%Y à %H:%M"))
        )
    return valeur.strftime("%d/%m/%Y")


def _jours(valeur) -> str | None:
    try:
        n = int(valeur)
    except (TypeError, ValueError):
        return None
    return None if n < 0 else f"{n} jour{'s' if n > 1 else ''}"


class _CanvasNumerote(canvas_pdf.Canvas):
    """Canvas en deux passes : chaque page connaît le nombre total de pages (« Page 1 / 2 »)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pages = []

    def showPage(self):
        self._pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._pages)
        for etat in self._pages:
            self.__dict__.update(etat)
            self.setFont("Tdb", 7)
            self.setFillColor(MUTED)
            self.drawRightString(PAGE[0] - MARGE, 31, f"Page {self._pageNumber} / {total}")
            super().showPage()
        super().save()


class _DocumentFiche(BaseDocTemplate):
    def __init__(self, flux, titre: str, utilisateur: str):
        self.titre_fiche = titre
        self.utilisateur = utilisateur
        self.genere_le = timezone.localtime().strftime("%d/%m/%Y à %H:%M")
        super().__init__(
            flux,
            pagesize=PAGE,
            leftMargin=MARGE,
            rightMargin=MARGE,
            topMargin=96,
            bottomMargin=56,
            title=_texte(titre),
            author="MEFB - République de Guinée",
            subject="Fiche de suivi d'un dossier - tableau de bord des finances publiques",
            keywords=CREDIT_ARMOIRIES,
        )
        cadre = Frame(MARGE, 56, LARGEUR, PAGE[1] - 152, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates(PageTemplate(id="fiche", frames=cadre, onPage=self._cadre))

    def _cadre(self, canvas, doc):
        w, h = PAGE
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, h - 71, w, 71, fill=1, stroke=0)
        image = Path(__file__).parent / "assets" / "armoiries.png"
        if image.is_file():
            canvas.drawImage(str(image), MARGE, h - 61, width=43, height=51, mask="auto", preserveAspectRatio=True)
        canvas.setFillColor(WHITE)
        canvas.setFont("Tdb-Bold", 9)
        canvas.drawString(MARGE + 55, h - 22, "RÉPUBLIQUE DE GUINÉE")
        canvas.setFont("Tdb", 8)
        canvas.drawString(MARGE + 55, h - 37, "Ministère de l'Économie, des Finances et du Budget")
        canvas.setFont("Times-Bold", 14)
        canvas.drawString(MARGE + 55, h - 57, "Tableau de bord des finances publiques")
        canvas.setFont("Tdb-Bold", 8)
        canvas.drawRightString(w - MARGE, h - 22, "FICHE DE SUIVI")
        canvas.setFont("Tdb", 7)
        canvas.drawRightString(w - MARGE, h - 37, "Document de travail")
        canvas.drawRightString(w - MARGE, h - 48, "diffusion restreinte")
        for i, couleur in enumerate(("#ce1126", "#fcd116", "#009460")):
            canvas.setFillColor(colors.HexColor(couleur))
            canvas.rect(i * w / 3, h - 74, w / 3, 3, fill=1, stroke=0)
        canvas.setStrokeColor(BORDER)
        canvas.line(MARGE, 43, w - MARGE, 43)
        canvas.setFont("Tdb", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGE, 31, "Document de travail - diffusion restreinte | " + _texte(self.titre_fiche))
        canvas.setFont("Tdb", 6)
        canvas.drawString(MARGE, 18, mention_droits())
        canvas.drawRightString(w - MARGE, 18, f"Généré le {self.genere_le} par {_texte(self.utilisateur)}")
        canvas.restoreState()


def _rubrique(numero: int, titre: str):
    """Intitulé de rubrique : numéro et titre sur un filet or, comme les en-têtes des tableaux PDF."""
    t = Table(
        [[_p(f"{numero}. {titre}", fontName="Tdb-Bold", fontSize=10.5, leading=13, textColor=NAVY, spaceAfter=0)]],
        colWidths=[LARGEUR],
    )
    t.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, -1), 1, GOLD),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return t


def _tableau_champs(lignes: list[tuple[str, object]], colonnes: int = 1):
    """Libellé / valeur, une ou deux paires par ligne ; « Non renseigné » plutôt qu'une case vide."""
    cellules = []
    for libelle, valeur in lignes:
        texte = _texte(valeur) if valeur not in (None, "") else "Non renseigné"
        cellules.append(
            (
                _p(libelle, fontSize=8, leading=10, textColor=MUTED, spaceAfter=0),
                _p(
                    texte,
                    fontName="Tdb" if valeur in (None, "") else "Tdb-Bold",
                    fontSize=9,
                    leading=12,
                    textColor=MUTED if valeur in (None, "") else INK,
                    spaceAfter=0,
                ),
            )
        )
    lignes_tableau = []
    for i in range(0, len(cellules), colonnes):
        ligne = []
        for libelle, valeur in cellules[i : i + colonnes]:
            ligne += [libelle, valeur]
        ligne += ["", ""] * (colonnes - len(cellules[i : i + colonnes]))
        lignes_tableau.append(ligne)
    part = LARGEUR / colonnes
    t = Table(lignes_tableau, colWidths=[part * 0.36, part * 0.64] * colonnes, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, BACKGROUND]),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, BORDER),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return t


def _encadre(texte: str, fond=TINT):
    t = Table([[_p(texte, fontSize=9.5, leading=13, spaceAfter=0)]], colWidths=[LARGEUR])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), fond),
                ("LINEBEFORE", (0, 0), (0, -1), 3, NAVY),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return t


def creer_fiche_dossier_pdf(alerte: Alerte, utilisateur: str) -> bytes:
    _polices()
    d = alerte.donnees or {}
    numero = str(d.get("numero") or "").strip()
    titre = f"Fiche de suivi - dossier n° {numero}"
    contexte = " · ".join(str(v) for v in (d.get("libelle_titre"), d.get("ministere")) if v)
    gravite = alerte.severite
    histoire = []

    # En-tête de la fiche : identité du dossier à gauche, gravité et statut à droite.
    pastille = Table(
        [
            [_p(GRAVITES.get(gravite, gravite), fontName="Tdb-Bold", fontSize=9, textColor=WHITE, spaceAfter=0)],
            [_p(STATUTS.get(alerte.statut, alerte.statut), fontSize=8, leading=10, textColor=INK, spaceAfter=0)],
        ],
        colWidths=[118],
    )
    pastille.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(COULEURS_GRAVITE.get(gravite, "#16314e"))),
                ("BOX", (0, 1), (-1, 1), 0.5, BORDER),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    identite = [
        _p("FICHE DE SUIVI D'UN DOSSIER", fontName="Tdb-Bold", fontSize=8, textColor=MUTED, spaceAfter=2),
        _p(f"Dossier n° {numero}", fontName="Tdb-Bold", fontSize=20, leading=24, textColor=NAVY, spaceAfter=3),
        _p(contexte or alerte.titre, fontSize=10, leading=13, textColor=INK, spaceAfter=0),
    ]
    entete = Table([[identite, pastille]], colWidths=[LARGEUR - 128, 128])
    entete.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ]
        )
    )
    histoire += [entete, Spacer(1, 12)]

    # Chiffres clés.
    def chiffre(libelle, valeur, detail=""):
        return [
            _p(libelle, fontSize=8, textColor=MUTED, spaceAfter=2),
            _p(valeur or "Non renseigné", fontName="Tdb-Bold", fontSize=15, leading=18, textColor=NAVY, spaceAfter=2),
            _p(detail, fontSize=7.5, leading=9.5, textColor=MUTED, spaceAfter=0),
        ]

    cles = Table(
        [
            [
                chiffre("Montant engagé", alerte.valeur),
                chiffre(
                    "En attente depuis",
                    _jours(d.get("jours")) or "Non renseignée",
                    f"depuis le {_date(d.get('depuis'))}" if d.get("depuis") else "",
                ),
                chiffre("Situation des données", _date(alerte.date_situation) or "—", "date de l'extraction source"),
            ]
        ],
        colWidths=[LARGEUR / 3] * 3,
    )
    cles.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("LINEAFTER", (0, 0), (1, 0), 0.5, BORDER),
                ("BACKGROUND", (0, 0), (-1, -1), BACKGROUND),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    histoire += [cles, Spacer(1, 14)]

    action = alerte.action_recommandee or (
        "Faire qualifier le motif de l'attente et confirmer la décision attendue auprès du service concerné."
    )
    sections = [
        ("Action proposée", [_encadre(action)]),
        (
            "Objet du dossier",
            [
                _encadre(d.get("objet") or "Objet non renseigné", fond=WHITE),
                Spacer(1, 6),
                _tableau_champs([("Bénéficiaire", d.get("beneficiaire"))]),
            ],
        ),
        (
            "Situation et traitement",
            [
                _tableau_champs(
                    [
                        ("Étape en attente", d.get("etape")),
                        ("Acteur concerné", d.get("acteur")),
                        ("État du dossier", d.get("etat")),
                        ("Procédure", d.get("procedure")),
                    ],
                    colonnes=2,
                )
            ],
        ),
        (
            "Rattachement administratif",
            [
                _tableau_champs(
                    [
                        ("Ministère / institution", d.get("ministere")),
                        ("Section budgétaire", d.get("section")),
                        ("Service", d.get("service")),
                        ("Sous-section", d.get("sous_section")),
                        ("Titre budgétaire", d.get("libelle_titre")),
                        ("Imputation budgétaire", d.get("imputation")),
                    ],
                    colonnes=2,
                )
            ],
        ),
        (
            "Dates et notifications",
            [
                _tableau_champs(
                    [
                        ("Création du dossier", _date(d.get("date_creation"))),
                        ("Dernier changement d'état", _date(d.get("date_etat"))),
                        ("Alerte levée le", _date(alerte.date)),
                        ("Situation des données", _date(alerte.date_situation)),
                        ("Notification par courriel", _date(alerte.notifiee_le) or "Non envoyée"),
                        ("Relance par courriel", _date(alerte.relancee_le) or "Non envoyée"),
                    ],
                    colonnes=2,
                )
            ],
        ),
        (
            "Origine de l'alerte",
            [
                _tableau_champs(
                    [
                        ("Constat", alerte.message),
                        ("Règle", alerte.regle.titre_modele.split(":")[0].strip() if alerte.regle else None),
                        ("Source des données", alerte.source.application if alerte.source else None),
                    ]
                )
            ],
        ),
    ]
    for i, (intitule, contenu) in enumerate(sections, start=1):
        histoire.append(KeepTogether([_rubrique(i, intitule), Spacer(1, 6), *contenu, Spacer(1, 12)]))

    # Cadre de décision, à compléter à la main après arbitrage.
    ligne_vide = _p(" ", fontSize=9, leading=16, spaceAfter=0)
    decision = Table(
        [
            [_p("Décision", fontName="Tdb-Bold", fontSize=8.5, textColor=MUTED, spaceAfter=0), ligne_vide],
            [_p("Observations", fontName="Tdb-Bold", fontSize=8.5, textColor=MUTED, spaceAfter=0), ligne_vide],
            [_p("", spaceAfter=0), ligne_vide],
            [
                _p("Date et visa", fontName="Tdb-Bold", fontSize=8.5, textColor=MUTED, spaceAfter=0),
                _p("Le ........ / ........ / ............", fontSize=9, textColor=MUTED, alignment=TA_RIGHT),
            ],
        ],
        colWidths=[LARGEUR * 0.22, LARGEUR * 0.78],
        rowHeights=[26, 26, 26, 40],
    )
    decision.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, NAVY),
                ("LINEBELOW", (1, 0), (1, 2), 0.3, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    n = len(sections) + 1
    histoire.append(KeepTogether([_rubrique(n, "Décision"), Spacer(1, 6), decision]))

    flux = BytesIO()
    _DocumentFiche(flux, titre, utilisateur).build(histoire, canvasmaker=_CanvasNumerote)
    return flux.getvalue()
