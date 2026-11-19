from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import load_workbook

from apps.core import demo
from apps.core.filtres import resoudre_filtres
from apps.core.models import Chargement, Source
from apps.core.tofe import MD, page

from .test_api import client_pour, utilisateur


@pytest.fixture
def scenario(db):
    demo.generer(exercice=2026, date_situation=date(2026, 11, 13), sources=["tofe"])
    return resoudre_filtres({}, "tofe")


def test_equilibre_annuel_et_sens_du_financement(scenario):
    d = page(scenario)
    lignes = {r["code"]: r for r in d["lignes"]}
    assert lignes["recettes_dons"]["lfr"] == 46400 * MD
    assert lignes["depenses"]["lfr"] == 53000 * MD
    assert lignes["solde_global"]["lfr"] == -6600 * MD
    assert lignes["solde_caisse"]["lfr"] == -7100 * MD
    assert lignes["financement"]["lfr"] == 7100 * MD
    assert lignes["amortissement"]["lfr"] == 1800 * MD
    assert lignes["financement_exterieur"]["lfr"] == 7600 * MD
    for colonne in ("lfi", "lfr", "realise", "objectif_cumule", "realise_n1"):
        assert abs(lignes["ecart_financement"][colonne]) < Decimal("0.01")
    assert all(c["reussi"] for c in d["verifications"])
    assert lignes["solde_global"]["taux"] is None
    assert lignes["financement"]["taux"] is None
    assert (
        lignes["recettes_dons"]["taux"]
        == lignes["recettes_dons"]["realise"] / lignes["recettes_dons"]["objectif_cumule"]
    )


@pytest.mark.parametrize("jour", [date(2026, 1, 1), date(2026, 2, 15), date(2026, 12, 31), date(2027, 1, 15)])
def test_cumuls_mensuels_et_periode_complementaire(db, jour):
    demo.generer(exercice=2026, date_situation=jour, sources=["tofe"])
    d = page(resoudre_filtres({}, "tofe"))
    for champ in ("recettes_dons", "depenses", "solde_global"):
        assert abs(sum(m[champ] for m in d["mensuel"]) - d["indicateurs"][champ]) < Decimal("0.01")
    assert len(d["mensuel"]) == (12 if jour.year > 2026 else jour.month)
    assert all(c["reussi"] for c in d["verifications"])


def test_scenario_trace_sans_cumul_ni_ecriture_sources_reelles(scenario):
    ch = Chargement.objects.get(source__code="tofe")
    assert ch.detail["demo"] is True
    assert ch.detail["profil"] == "tofe_illustration_v1"
    assert Source.objects.get(code="tofe").statut == "demo"
    avant = page(scenario)["indicateurs"]
    demo.generer(exercice=2026, date_situation=scenario.date_situation, sources=["tofe"])
    assert Chargement.objects.filter(source__code="tofe").count() == 1
    assert page(scenario)["indicateurs"] == avant
    assert not Chargement.objects.exclude(source__code="tofe").exists()


def test_date_avant_exercice_refusee_sans_effacer_le_scenario(scenario):
    ch = Chargement.objects.get(source__code="tofe")
    with pytest.raises(ValueError, match="ne peut pas précéder"):
        demo.generer(exercice=2027, date_situation=date(2026, 11, 13), sources=["tofe"])
    assert Chargement.objects.filter(pk=ch.pk).exists()


def test_api_droits_periode_absente_et_export_identifie(scenario):
    u = utilisateur("direction-tofe", "directeur", ["tofe"])
    client = client_pour(u)
    r = client.get("/api/v1/tofe/")
    assert r.status_code == 200
    assert r.data["meta"]["statut_source"] == "demo"
    assert r.data["meta"]["exercice"] == 2026
    assert r.data["data"]["references"]
    assert client.get("/api/v1/tofe/", {"exercice": 2024}).data["data"] is None
    assert client_pour(utilisateur("autre", "directeur", ["depense"])).get("/api/v1/tofe/").status_code == 403
    export = client.get("/api/v1/export/tofe.xlsx")
    assert export.status_code == 200
    wb = load_workbook(BytesIO(export.content))
    textes = " ".join(str(c.value) for row in wb["Lisez-moi"] for c in row)
    assert "illustration" in textes and "Mds" in textes
    ws = wb["Tableau TOFE"]
    entetes = [c.value for c in ws[1]]
    assert "LFR simulée (Mds GNF)" in entetes
    index_lfr = entetes.index("LFR simulée (Mds GNF)")
    assert ws.cell(2, index_lfr + 1).value == 46400
