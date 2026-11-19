"""Rapports PDF paginés, charte institutionnelle et mêmes données/droits que les exports Excel."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import reportlab
from django.http import HttpResponse
from django.utils import timezone
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    CondPageBreak,
    Frame,
    KeepTogether,
    LongTable,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.views import APIView

from .audit import journaliser
from .export import MONTANTS, PAGES, TAUX, _aplatir, _contenu, _lib, _valeur
from .filtres import resoudre_filtres
from .models import JournalAudit
from .permissions import DoubleAuthentification
from .reponses import masquer_disponible, meta

# Couleurs de frontend/src/theme/tokens.css ; aucune couleur d'état utilisée pour une donnée.
NAVY = colors.HexColor("#16314e")
GOLD = colors.HexColor("#b8860b")
INK = colors.HexColor("#0e1a28")
MUTED = colors.HexColor("#4a5668")
BORDER = colors.HexColor("#dce2ea")
BACKGROUND = colors.HexColor("#f3f5f8")
TINT = colors.HexColor("#fff9eb")
BLUE = colors.HexColor("#2a78d6")
WHITE = colors.white
PAGE = landscape(A4)
MARGIN = 34
WIDTH = PAGE[0] - 2 * MARGIN
STATUTS = {
    "reel": "Réel",
    "demo": "ILLUSTRATION - chiffres fictifs",
    "non_raccorde": "Non raccordée",
    "mixte": "Sources multiples",
}
MONTANTS_PDF = MONTANTS | {
    "credit_simandou",
    "credit_green",
    "engage_green",
    "cible",
    "central",
    "bas",
    "haut",
    "projete",
}


def _libelle(cle):
    libelles = {
        "recettes_dons": "Recettes et dons (Mds GNF)",
        "solde_global": "Solde global (Mds GNF)",
        "solde_primaire": "Solde primaire (Mds GNF)",
        "financement": "Financement net (Mds GNF)",
        "valeur_affichee": "Valeur",
    }
    return libelles.get(cle, _lib(cle) + (" (Mds GNF)" if cle.split(".")[-1] in MONTANTS_PDF - MONTANTS else ""))


def _texte(value):
    text = str(value if value is not None else "Non disponible")
    for original, replacement in {
        "\u202f": " ",
        "\xa0": " ",
        "−": "-",
        "–": "-",
        "—": "-",
        "‑": "-",
        "…": "...",
        "→": "vers",
    }.items():
        text = text.replace(original, replacement)
    return "".join(c for c in text if c in "\n\t" or ord(c) >= 32)


def _polices():
    if "Tdb" not in pdfmetrics.getRegisteredFontNames():
        fonts = Path(reportlab.__file__).parent / "fonts"
        pdfmetrics.registerFont(TTFont("Tdb", str(fonts / "Vera.ttf")))
        pdfmetrics.registerFont(TTFont("Tdb-Bold", str(fonts / "VeraBd.ttf")))
        pdfmetrics.registerFontFamily("Tdb", normal="Tdb", bold="Tdb-Bold", italic="Tdb", boldItalic="Tdb-Bold")


def _style(nom="normal", **kwargs):
    base = dict(fontName="Tdb", fontSize=9, leading=13, textColor=INK, spaceAfter=5)
    base.update(kwargs)
    return ParagraphStyle(nom, **base)


def _p(value, **kwargs):
    return Paragraph(escape(_texte(value)).replace("\n", "<br/>"), _style(**kwargs))


def _format(cle, valeur, brut=False):
    if valeur is None:
        return "Non disponible"
    if isinstance(valeur, bool):
        return "Oui" if valeur else "Non"
    if isinstance(valeur, (date, datetime)):
        return valeur.strftime("%d/%m/%Y")
    if isinstance(valeur, (int, float, Decimal)):
        base = cle.split(".")[-1]
        nombre = valeur if brut else float(valeur) / 10**9 if base in MONTANTS_PDF else _valeur(cle, valeur)
        if not brut and (base in TAUX or base.startswith(("taux_", "part_")) or base == "erreur_moyenne"):
            return f"{nombre * 100:,.1f} %".replace(",", " ").replace(".", ",")
        decimals = 2 if brut else 1 if base in MONTANTS_PDF else 2
        if isinstance(valeur, int) and (brut or base not in MONTANTS_PDF):
            decimals = 0
        return f"{nombre:,.{decimals}f}".replace(",", " ").replace(".", ",")
    if isinstance(valeur, (dict, list)):
        return (
            "; ".join(f"{k}: {_format(k, v, brut)}" for k, v in valeur.items())
            if isinstance(valeur, dict)
            else "; ".join(_texte(v) for v in valeur)
        )
    return STATUTS.get(valeur, valeur) if isinstance(valeur, str) else str(valeur)


def _source(m):
    jour = m.get("date_situation")
    if jour:
        jour = date.fromisoformat(str(jour)[:10]).strftime("%d/%m/%Y")
    application = m.get("application") or m.get("source")
    if m.get("source") == "chaine_depense":
        application = "Chaîne Dépense"
    origine = {"fichier": "Fichier importé", "oracle": "Oracle", "postgresql": "PostgreSQL"}.get(m.get("origine"))
    return " | ".join(
        str(x)
        for x in (
            application,
            origine,
            STATUTS.get(m.get("statut_source"), "Non disponible"),
            f"Exercice {m['exercice']}" if m.get("exercice") else None,
            f"Situation au {jour}" if jour else "Situation non disponible",
        )
        if x
    )


@dataclass
class BlocPdf:
    titre: str
    donnees: object
    meta: dict
    brut: bool = False
    libelles: dict = field(default_factory=dict)


class CollecteurPdf:
    def __init__(self, titre, informations, reel_seulement=False):
        self.titre = titre
        self.meta = informations
        if reel_seulement and informations.get("statut_source") != "reel":
            self.meta = {**informations, "statut_source": "non_raccorde"}
        self.blocs = []
        self.reel_seulement = reel_seulement

    def feuille(self, nom, donnees, meta_bloc=None):
        if donnees is None or donnees == [] or donnees == {}:
            return
        informations = dict(meta_bloc or self.meta)
        if self.reel_seulement and informations.get("statut_source") != "reel":
            donnees = {"disponibilite": "Données réelles non disponibles pour cette période."}
            informations["statut_source"] = "non_raccorde"
        if "credit_disponible" in informations.get("indicateurs_indisponibles", []):
            donnees = masquer_disponible(donnees)
        if isinstance(donnees, list):
            statuts = {
                x.get("statut")
                for x in donnees
                if isinstance(x, dict) and x.get("statut") in STATUTS and ("valeur" not in x or x["valeur"] is not None)
            }
            if len(statuts) > 1:
                informations = {"application": "Sources détaillées dans les lignes", "statut_source": "mixte"}
        self.blocs.append(BlocPdf(nom, donnees, informations))


class DocumentPdf(BaseDocTemplate):
    def __init__(self, flux, titre, utilisateur):
        self.titre_rapport = titre
        self.utilisateur = utilisateur
        self.genere_le = timezone.localtime().strftime("%d/%m/%Y à %H:%M")
        super().__init__(
            flux,
            pagesize=PAGE,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=96,
            bottomMargin=51,
            title=_texte(titre),
            author="MEFB - République de Guinée",
            allowSplitting=True,
        )
        cadre = Frame(MARGIN, 51, WIDTH, PAGE[1] - 147, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates(PageTemplate(id="institutionnel", frames=cadre, onPage=self._cadre))

    def _cadre(self, canvas, doc):
        w, h = PAGE
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, h - 71, w, 71, fill=1, stroke=0)
        image = Path(__file__).parent / "assets" / "armoiries.png"
        if image.is_file():
            canvas.drawImage(str(image), MARGIN, h - 61, width=43, height=51, mask="auto", preserveAspectRatio=True)
        canvas.setFillColor(WHITE)
        canvas.setFont("Tdb-Bold", 9)
        canvas.drawString(MARGIN + 55, h - 22, "RÉPUBLIQUE DE GUINÉE")
        canvas.setFont("Tdb", 8)
        canvas.drawString(MARGIN + 55, h - 37, "Ministère de l'Économie, des Finances et du Budget")
        canvas.setFont("Times-Bold", 14)
        canvas.drawString(MARGIN + 55, h - 57, "Tableau de bord des finances publiques")
        for i, couleur in enumerate(("#ce1126", "#fcd116", "#009460")):
            canvas.setFillColor(colors.HexColor(couleur))
            canvas.rect(i * w / 3, h - 74, w / 3, 3, fill=1, stroke=0)
        canvas.setStrokeColor(BORDER)
        canvas.line(MARGIN, 43, w - MARGIN, 43)
        canvas.setFont("Tdb", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN, 31, "Document de travail - diffusion restreinte | " + _texte(self.titre_rapport))
        canvas.drawRightString(w - MARGIN, 31, f"Page {doc.page}")
        canvas.setFont("Tdb", 6)
        canvas.drawString(
            MARGIN, 18, "Armoiries : Turn685 d'après Ttzavaras / Wikimedia Commons - CC BY-SA 3.0. Adaptation PNG."
        )
        canvas.drawRightString(w - MARGIN, 18, "Généré le " + self.genere_le)
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if getattr(flowable, "titre_rubrique", None):
            cle = f"rubrique-{self.page}-{len(self.canv._code)}"
            self.canv.bookmarkPage(cle)
            self.canv.addOutlineEntry(_texte(flowable.titre_rubrique), cle, 0, False)


def _table(bloc, donnees, colonnes, largeur=WIDTH):
    def lib(k):
        return bloc.libelles.get(k) or (_libelle(k) if not bloc.brut else k.replace("_", " ").capitalize())

    textes = [
        [_p(bloc.titre + " | " + _source(bloc.meta), fontSize=8, leading=11), *[""] * (len(colonnes) - 1)],
        [_p(lib(c), fontName="Tdb-Bold", fontSize=8, leading=10, textColor=WHITE) for c in colonnes],
    ]
    numeriques = {
        k
        for k in colonnes
        if any(isinstance(r.get(k), (int, float, Decimal)) and not isinstance(r.get(k), bool) for r in donnees)
    }
    if "valeur_affichee" in colonnes:
        numeriques.add("valeur_affichee")
    for ligne in donnees:
        textes.append(
            [
                _p(
                    _format(c, ligne.get(c), bloc.brut),
                    fontSize=8,
                    leading=10.5,
                    alignment=TA_RIGHT if c in numeriques else TA_LEFT,
                    fontName="Tdb-Bold" if ligne.get("agregat") else "Tdb",
                )
                for c in colonnes
            ]
        )
    textes_cols = [c for c in colonnes if c not in numeriques]
    poids_apad = {
        "ministere": 2.6,
        "libelle_projet": 3.4,
        "gestionnaire": 0.9,
        "numero_apad": 0.7,
        "numero_marche": 0.8,
        "date_creation": 1.1,
        "avance_demarrage": 1.25,
    }
    poids = [
        (
            poids_apad.get(c, 1)
            if bloc.titre == "Dossiers APAD"
            else 2.8
            if c == colonnes[0] and c not in numeriques
            else 2
            if c in textes_cols
            else 1.15
        )
        for c in colonnes
    ]
    largeurs = [largeur * p / sum(poids) for p in poids]
    tableau = LongTable(textes, colWidths=largeurs, repeatRows=2, splitByRow=1, splitInRow=1, hAlign="LEFT")
    tableau.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 0), (-1, 0)),
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    TINT if bloc.meta.get("statut_source") in ("demo", "mixte") else BACKGROUND,
                ),
                ("BACKGROUND", (0, 1), (-1, 1), NAVY),
                ("ROWBACKGROUNDS", (0, 2), (-1, -1), [WHITE, BACKGROUND]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 1), (-1, 1), 1, GOLD),
                ("LINEBELOW", (0, 2), (-1, -1), 0.3, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return tableau


def _graphe(bloc, lignes):
    """Aperçu vectoriel lisible ; les valeurs détaillées restent intégralement dans les tableaux."""
    if bloc.titre == "Tableau TOFE":
        return None  # Les agrégats et leurs enfants ne forment pas une série additive.
    libelle = next((c for c in ("libelle", "nom", "beneficiaire", "poste", "mois") if c in lignes[0]), None)
    mesure = next(
        (
            c
            for c in ("credit_actuel", "recettes_dons", "encours", "recouvre", "montant_engage", "prevu", "realise")
            if c in lignes[0] and all(isinstance(x.get(c), (int, float, Decimal)) for x in lignes)
        ),
        None,
    )
    if not libelle or not mesure or len(lignes) < 3 or len(lignes) > 60:
        return None
    selection = lignes[-6:] if libelle == "mois" else sorted(lignes, key=lambda x: float(x[mesure]), reverse=True)[:6]
    maximum = max(float(x[mesure]) for x in selection)
    if maximum <= 0 or any(float(x[mesure]) < 0 for x in selection):
        return None
    dessin = Drawing(WIDTH, 23 * len(selection) + 26)
    x0, zone = 235, WIDTH - 340
    for index, ligne in enumerate(selection):
        y = dessin.height - 23 * (index + 1)
        nom = _texte(ligne[libelle])
        if isinstance(ligne[libelle], (date, datetime)):
            nom = _format(libelle, ligne[libelle])
        while pdfmetrics.stringWidth(nom, "Tdb", 8) > 220:
            nom = nom[:-5] + "..."
        dessin.add(String(0, y + 3, nom, fontName="Tdb", fontSize=8, fillColor=INK))
        dessin.add(Rect(x0, y, zone, 11, fillColor=BACKGROUND, strokeColor=None))
        dessin.add(Rect(x0, y, zone * float(ligne[mesure]) / maximum, 11, fillColor=BLUE, strokeColor=None))
        dessin.add(
            String(
                WIDTH - 5,
                y + 2,
                _format(mesure, ligne[mesure], bloc.brut),
                textAnchor="end",
                fontName="Tdb-Bold",
                fontSize=8,
                fillColor=NAVY,
            )
        )
    dessin.add(
        String(
            x0,
            dessin.height - 4,
            _texte(bloc.libelles.get(mesure) or _libelle(mesure))
            + (" - aperçu de 6 lignes ; détail intégral ci-dessous" if len(lignes) > 6 else ""),
            fontName="Tdb",
            fontSize=7,
            fillColor=MUTED,
        )
    )
    return dessin


def _blocs(bloc):
    contenu = []
    titre = _p(bloc.titre, fontName="Tdb-Bold", fontSize=12, leading=17, spaceBefore=12)
    contenu.extend([CondPageBreak(90), titre])
    if isinstance(bloc.donnees, dict):
        lignes = []
        for cle, valeur in _aplatir(bloc.donnees).items():
            if isinstance(valeur, list):
                contenu.extend(
                    _blocs(BlocPdf(cle.replace("_", " ").capitalize(), valeur, bloc.meta, bloc.brut, bloc.libelles))
                )
            else:
                lignes.append(
                    {
                        "indicateur": _libelle(cle) if not bloc.brut else bloc.libelles.get(cle, cle),
                        "valeur_affichee": _format(cle, valeur, bloc.brut),
                    }
                )
        if lignes:
            contenu.append(_table(bloc, lignes, ["indicateur", "valeur_affichee"]))
    elif isinstance(bloc.donnees, list):
        lignes = [_aplatir(x) if isinstance(x, dict) else {"valeur": x} for x in bloc.donnees]
        if not lignes:
            contenu.append(_p("Aucune donnée disponible."))
            return contenu
        colonnes = [c for c in dict.fromkeys(k for r in lignes for k in r) if c not in ("niveau", "agregat")]
        if "libelle" in colonnes and "code" in colonnes:
            colonnes.remove("code")
        if len(colonnes) <= 8:
            graphe = _graphe(bloc, lignes)
            if graphe:
                contenu.extend([graphe, Spacer(1, 8)])
            contenu.append(_table(bloc, lignes, colonnes))
        else:
            identifiant = next(
                (k for k in ("libelle", "beneficiaire", "nom", "poste", "code", "mois") if k in colonnes), colonnes[0]
            )
            autres = [c for c in colonnes if c != identifiant]
            for debut in range(0, len(autres), 6):
                contenu.extend([_table(bloc, lignes, [identifiant, *autres[debut : debut + 6]]), Spacer(1, 10)])
    else:
        contenu.append(_p(bloc.donnees))
    contenu.append(Spacer(1, 9))
    return contenu


def creer_pdf(rapports, utilisateur, titre="Rapport financier", filtres="", note=""):
    _polices()
    flux = BytesIO()
    doc = DocumentPdf(flux, titre, utilisateur)
    contenu = []
    for index, rapport in enumerate(rapports):
        if index:
            contenu.append(PageBreak())
        heading = _p(rapport.titre, fontName="Tdb-Bold", fontSize=20, leading=25, textColor=NAVY, spaceAfter=10)
        heading.titre_rubrique = rapport.titre
        contenu.extend(
            [
                heading,
                _p(_source(rapport.meta), fontSize=8, textColor=MUTED),
                _p(
                    f"Exporté par : {utilisateur} | Filtres : "
                    f"{filtres or 'Dernière situation disponible de chaque source'}",
                    fontSize=8,
                    textColor=MUTED,
                ),
            ]
        )
        if note:
            contenu.append(_p(note, textColor=MUTED, fontSize=8))
        illustration = rapport.meta.get("statut_source") == "demo" or any(
            b.meta.get("statut_source") in ("demo", "mixte") for b in rapport.blocs
        )
        if illustration:
            bandeau = Table(
                [
                    [
                        _p(
                            "DONNÉES D'ILLUSTRATION : les rubriques signalées sont fictives. "
                            "Les blocs réels conservent leur propre source et leur propre date.",
                            fontSize=9,
                            leading=13,
                        )
                    ]
                ],
                colWidths=[WIDTH],
            )
            bandeau.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), TINT),
                        ("BOX", (0, 0), (-1, -1), 0.6, GOLD),
                        ("LEFTPADDING", (0, 0), (-1, -1), 9),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                        ("TOPPADDING", (0, 0), (-1, -1), 9),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                    ]
                )
            )
            contenu.extend([bandeau, Spacer(1, 9)])
        contenu.append(
            _p(
                "Montants en milliards de GNF (Mds), sauf indication contraire ; ratios en %. "
                "Les données absentes restent indisponibles.",
                fontSize=8,
                textColor=MUTED,
            )
        )
        premier = next((b for b in rapport.blocs if b.titre == "Indicateurs" and isinstance(b.donnees, dict)), None)
        if premier:
            cles = (
                ["recettes_dons", "depenses", "solde_global", "financement"]
                if "recettes_dons" in premier.donnees
                else list(premier.donnees)
            )
            valeurs = [
                (k, v)
                for k in cles
                for v in [premier.donnees[k]]
                if isinstance(v, (int, float, Decimal)) and not isinstance(v, bool)
            ][:4]
            if valeurs:
                cellules = [
                    [
                        _p(_libelle(k), fontSize=8, textColor=MUTED),
                        _p(_format(k, v), fontName="Tdb-Bold", fontSize=17, leading=22, textColor=NAVY),
                    ]
                    for k, v in valeurs
                ]
                kpis = Table([[cell for cell in cellules]], colWidths=[WIDTH / len(cellules)] * len(cellules))
                kpis.setStyle(
                    TableStyle(
                        [
                            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("TOPPADDING", (0, 0), (-1, -1), 11),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
                        ]
                    )
                )
                contenu.extend([KeepTogether([kpis]), Spacer(1, 10)])
        if not rapport.blocs:
            contenu.append(_p("Aucune donnée disponible pour cette rubrique avec la période et les filtres demandés."))
        for bloc in rapport.blocs:
            contenu.extend(_blocs(bloc))
    doc.build(contenu)
    return flux.getvalue()


def _autorise(user, page):
    return user.role != "lecteur" and user.peut_exporter(PAGES[page][0])


class ExportPdfView(APIView):
    permission_classes = [DoubleAuthentification]

    def get(self, request, page):
        if page != "rapport" and page not in PAGES:
            raise NotFound("Page inconnue.")
        pages = [p for p in PAGES if _autorise(request.user, p)] if page == "rapport" else [page]
        if not pages or any(not _autorise(request.user, p) for p in pages):
            raise PermissionDenied("Votre profil ne permet pas l'export de cette rubrique.")
        if "synthese" in pages:
            pages = ["synthese", *[p for p in pages if p != "synthese"]]
        filtres = " | ".join(f"{k.replace('_', ' ')} : {v}" for k, v in request.query_params.items())
        rapports = []
        for cle in pages:
            _, source, titre = PAGES[cle]
            f = resoudre_filtres(request.query_params, source)
            decision = page == "rapport" and request.query_params.get("mode_synthese", "decision") == "decision"
            rapport = CollecteurPdf(titre, meta(source, f), reel_seulement=decision and cle != "synthese")
            _contenu(cle, request, rapport)
            if cle == "depenses" and f.date_situation is not None:
                from apps.depense import services

                rapport.feuille("Simandou et projets green", services.simandou(f))
                rapport.feuille("Projections de fin d'exercice", services.projection(f))
            rapports.append(rapport)
        titre = "Rapport complet - rubriques autorisées" if page == "rapport" else PAGES[page][2]
        contenu = creer_pdf(rapports, request.user.get_username(), titre, filtres)
        journaliser(
            request,
            JournalAudit.Action.EXPORT,
            objet=f"{page}.pdf",
            detail={"filtres": dict(request.query_params), "rubriques": pages},
        )
        reponse = HttpResponse(contenu, content_type="application/pdf")
        jour = rapports[0].meta.get("date_situation") or timezone.localdate().isoformat()
        reponse["Content-Disposition"] = f'attachment; filename="tdb-{page}-{jour}.pdf"'
        reponse["Cache-Control"] = "private, no-store"
        return reponse
