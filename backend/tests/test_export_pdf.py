import json
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from pypdf import PdfReader
from rest_framework.test import APIClient

from apps.core import demo
from apps.core.export import PAGES
from apps.core.export_pdf import CollecteurPdf, _format, creer_pdf
from apps.core.models import JournalAudit

from .test_api import client_pour, utilisateur

pytestmark = pytest.mark.django_db


@pytest.fixture
def donnees(charge):
    demo.generer(exercice=2025, date_situation=date(2026, 9, 15))
    return charge


def texte(response):
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")
    lecteur = PdfReader(BytesIO(response.content))
    return lecteur, "\n".join(p.extract_text() for p in lecteur.pages)


@pytest.mark.parametrize("page", list(PAGES))
def test_pdf_de_chaque_rubrique(donnees, page):
    c = client_pour(utilisateur("cab", "ministre_cabinet"))
    r = c.get(f"/api/v1/export/{page}.pdf")
    lecteur, contenu = texte(r)
    assert "attachment" in r["Content-Disposition"]
    assert "no-store" in r["Cache-Control"]
    assert "diffusion restreinte" in contenu
    assert "RÉPUBLIQUE DE GUINÉE" in contenu
    assert len(lecteur.pages) >= 1
    for i, p in enumerate(lecteur.pages, 1):
        assert f"Page {i}" in p.extract_text()
        assert p.mediabox.width > p.mediabox.height
    assert JournalAudit.objects.filter(action="export", objet=f"{page}.pdf").exists()


def test_pdf_filtres_unites_sources_et_absences(donnees):
    c = client_pour(utilisateur("cab", "ministre_cabinet"))
    _, contenu = texte(c.get("/api/v1/export/depenses.pdf", {"nature": "investissement"}))
    assert "nature : investissement" in contenu
    assert "30,0" in contenu  # crédits d'investissement de la fixture, en milliards
    assert "Mds" in contenu and "Simandou" in contenu and "Projections" in contenu
    _, demo_pdf = texte(c.get("/api/v1/export/tofe.pdf"))
    assert "ILLUSTRATION" in demo_pdf and "chiffres fictifs" in demo_pdf
    _, vide = texte(c.get("/api/v1/export/tofe.pdf", {"exercice": 2020}))
    assert "Aucune donnée disponible" in vide


def test_rapport_complet_respecte_le_perimetre(donnees):
    directeur = client_pour(utilisateur("dir", "directeur", ["depense"]))
    _, contenu = texte(directeur.get("/api/v1/export/rapport.pdf"))
    trace = JournalAudit.objects.get(action="export", objet="rapport.pdf")
    assert set(trace.detail["rubriques"]) == {"synthese", "depenses"}
    assert "Dépenses" in contenu
    assert "TOFE - données d'illustration" not in contenu
    assert "\nSources\n" not in contenu


def test_pdf_droits_et_double_authentification(donnees):
    assert APIClient().get("/api/v1/export/depenses.pdf").status_code == 401
    lecteur = client_pour(utilisateur("lecteur", "lecteur", ["depense"]))
    assert lecteur.get("/api/v1/export/depenses.pdf").status_code == 403
    assert lecteur.get("/api/v1/export/rapport.pdf").status_code == 403
    dgi = client_pour(utilisateur("dgi", "directeur", ["recettes_fiscales"]))
    assert dgi.get("/api/v1/export/depenses.pdf").status_code == 403
    assert dgi.get("/api/v1/export/recettes-fiscales.pdf").status_code == 200
    cab = utilisateur("cab", "ministre_cabinet")
    assert client_pour(cab, otp=False).get("/api/v1/export/rapport.pdf").status_code == 403
    assert client_pour(cab).get("/api/v1/export/inconnue.pdf").status_code == 404


def test_pdf_grandes_tables_pagination_et_caracteres(db):
    informations = {"source": "essai", "statut_source": "demo", "date_situation": "2026-11-13", "exercice": 2026}
    rapport = CollecteurPdf("Essai paginé", informations)
    rapport.feuille(
        "Tableau long",
        [
            {"libelle": f"Ligne {i} <texte & caractères>", **{f"mesure_{n}": Decimal(i) for n in range(12)}}
            for i in range(80)
        ],
    )
    lecteur = PdfReader(BytesIO(creer_pdf([rapport], "essai")))
    assert len(lecteur.pages) > 4
    assert "Ligne 0" in lecteur.pages[0].extract_text()
    contenu = "\n".join(p.extract_text() for p in lecteur.pages)
    assert "Ligne 79 <texte & caractères>" in contenu
    assert "Mesure 11" in contenu
    assert "ILLUSTRATION" in contenu
    assert _format("montant_paye", Decimal("1234567890")) == "1,2"
    assert _format("taux_engagement", Decimal("0.125")) == "12,5 %"
    assert _format("montant_paye", None) == "Non disponible"


def test_pdf_indicateur_non_fourni_masque(db):
    rapport = CollecteurPdf("Oracle", {"indicateurs_indisponibles": ["credit_disponible"]})
    rapport.feuille("Indicateurs", {"credit_disponible": 0, "nb_lignes_depassement": 0})
    assert rapport.blocs[0].donnees["credit_disponible"] is None
    assert rapport.blocs[0].donnees["nb_lignes_depassement"] is None


def test_pdf_exploration_droits_et_donnees(charge):
    analyste = client_pour(utilisateur("analyste", "analyste", ["depense"]))
    q = {"jeu": "fait_situation_ligne", "axes": ["section"], "mesures": [{"champ": "credit_engage"}]}
    _, contenu = texte(analyste.get("/api/v1/exploration/export.pdf", {"q": json.dumps(q)}))
    assert "montants en GNF" in contenu and "Résultats" in contenu
    interdit = client_pour(utilisateur("autre", "analyste", ["dette"]))
    assert interdit.get("/api/v1/exploration/export.pdf", {"q": json.dumps(q)}).status_code == 403
