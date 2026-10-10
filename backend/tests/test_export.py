from datetime import date
from io import BytesIO

import pytest
from openpyxl import load_workbook

from apps.core import demo
from apps.core.export import PAGES
from apps.core.models import JournalAudit

from .test_api import client_pour, utilisateur

pytestmark = pytest.mark.django_db


@pytest.fixture
def donnees(charge):
    demo.generer(exercice=2025, date_situation=date(2026, 9, 15))
    return charge


@pytest.mark.parametrize("page", list(PAGES))
def test_export_de_chaque_page(donnees, page):
    c = client_pour(utilisateur("cab", "ministre_cabinet"))
    r = c.get(f"/api/v1/export/{page}.xlsx")
    assert r.status_code == 200, page
    assert r["Content-Type"].startswith("application/vnd.openxmlformats")
    assert "attachment" in r["Content-Disposition"]
    wb = load_workbook(BytesIO(r.content))
    assert wb.sheetnames[0] == "Lisez-moi"
    lisez_moi = " ".join(str(c.value) for ligne in wb["Lisez-moi"].iter_rows() for c in ligne if c.value)
    assert "diffusion restreinte" in lisez_moi
    assert len(wb.sheetnames) > 1, f"{page} : aucune feuille de données"
    assert JournalAudit.objects.filter(action="export", objet=f"{page}.xlsx").exists()


def test_montants_en_milliards_et_sources(donnees):
    c = client_pour(utilisateur("cab", "ministre_cabinet"))
    wb = load_workbook(BytesIO(c.get("/api/v1/export/depenses.xlsx").content))
    ind = {ligne[0].value: ligne[1].value for ligne in wb["Indicateurs"].iter_rows(min_row=2)}
    assert ind["Crédits actuels (Mds GNF)"] == 105.0
    assert wb["Ministères"]["A1"].value
    wb = load_workbook(BytesIO(c.get("/api/v1/export/masse-salariale.xlsx").content))
    statuts = [ligne[2].value for ligne in wb["Lisez-moi"].iter_rows(min_row=13) if ligne[0].value]
    assert "réel" in statuts and "illustration (chiffres fictifs)" in statuts


def test_filtres_appliques(donnees):
    c = client_pour(utilisateur("cab", "ministre_cabinet"))
    wb = load_workbook(BytesIO(c.get("/api/v1/export/depenses.xlsx?nature=investissement").content))
    ind = {ligne[0].value: ligne[1].value for ligne in wb["Indicateurs"].iter_rows(min_row=2)}
    assert ind["Crédits actuels (Mds GNF)"] == 30.0
    lisez_moi = {ligne[0].value: ligne[1].value for ligne in wb["Lisez-moi"].iter_rows() if ligne[0].value}
    assert lisez_moi["Filtres appliqués"] == "Nature : Investissement"


def test_droits_export(donnees):
    assert (
        client_pour(utilisateur("lec", "lecteur", ["depense"])).get("/api/v1/export/depenses.xlsx").status_code == 403
    )
    dgi = client_pour(utilisateur("dgi", "directeur", ["recettes_fiscales"]))
    assert dgi.get("/api/v1/export/depenses.xlsx").status_code == 403
    assert dgi.get("/api/v1/export/recettes-fiscales.xlsx").status_code == 200
    assert client_pour(utilisateur("cab", "ministre_cabinet")).get("/api/v1/export/inconnue.xlsx").status_code == 404


def test_export_sans_donnees(db):
    r = client_pour(utilisateur("cab", "ministre_cabinet")).get("/api/v1/export/tresorerie.xlsx")
    assert r.status_code == 200
    assert load_workbook(BytesIO(r.content)).sheetnames == ["Lisez-moi"]
