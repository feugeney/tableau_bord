"""Export décideurs du tableau « Ministères et institutions » (Excel et PDF)."""

from io import BytesIO

from openpyxl import load_workbook

from apps.core.models import JournalAudit
from apps.depense.models import FaitSituationLigne
from tests.test_api import client_pour, utilisateur


def test_excel_structure_et_total(charge):
    client = client_pour(utilisateur("cabinet", "ministre_cabinet"))
    r = client.get("/api/v1/depense/ministeres.xlsx")
    assert r.status_code == 200
    assert r["Content-Disposition"].startswith('attachment; filename="tdb-ministeres-')
    wb = load_workbook(BytesIO(r.content))
    assert wb.sheetnames == ["Ministères", "Méthode"]
    ws = wb["Ministères"]
    assert ws["A2"].value == "Exécution budgétaire par ministère et institution"
    entete = next(row for row in ws.iter_rows() if row[0].value == "N°")[0].row
    assert ws.freeze_panes == f"C{entete + 1}" and ws.auto_filter.ref.startswith(f"A{entete}")
    total = [c.value for c in ws[ws.max_row]]
    assert total[1].startswith("Total (")
    credits = sum(l.credit_actuel for l in FaitSituationLigne.objects.filter(chargement=charge))
    assert abs(total[2] - float(credits) / 1e9) < 1e-6
    lignes = list(ws.iter_rows(min_row=entete + 1, max_row=ws.max_row - 1, values_only=True))
    non_engage = [l[6] for l in lignes]
    assert non_engage == sorted(non_engage, reverse=True)  # trié sur les crédits non engagés
    assert JournalAudit.objects.filter(action="export", objet="ministeres.xlsx").exists()


def test_pdf_et_filtres(charge):
    client = client_pour(utilisateur("cabinet", "ministre_cabinet"))
    r = client.get("/api/v1/depense/ministeres.pdf", {"titres": "2"})
    assert r.status_code == 200 and r.content.startswith(b"%PDF-")


def test_export_refuse_au_lecteur(charge):
    client = client_pour(utilisateur("lecteur", "lecteur", ["depense"]))
    assert client.get("/api/v1/depense/ministeres.xlsx").status_code == 403
    assert client_pour(utilisateur("c2", "ministre_cabinet")).get("/api/v1/depense/ministeres.doc").status_code == 404


def test_colonnes_choisies_a_l_ecran(charge):
    """L'export suit les colonnes affichées : rang et libellé toujours, « Engagé » donne montant et taux."""
    client = client_pour(utilisateur("cabinet", "ministre_cabinet"))
    r = client.get("/api/v1/depense/ministeres.xlsx", {"colonnes": "taux_engagement,montant_vbp,inconnue"})
    assert r.status_code == 200
    ws = load_workbook(BytesIO(r.content))["Ministères"]
    entete = next(row for row in ws.iter_rows() if row[0].value == "N°")
    assert [c.value for c in entete] == [
        "N°",
        "Ministère / institution",
        "Engagé",
        "Taux d'engagement",
        "Vu bon à payer",
    ]
    vbp = sum(l.montant_vbp or 0 for l in FaitSituationLigne.objects.filter(chargement=charge))
    assert abs(ws.cell(ws.max_row, 5).value - float(vbp) / 1e9) < 1e-6
    methode = [row[0] for row in load_workbook(BytesIO(r.content))["Méthode"].iter_rows(min_row=2, values_only=True)]
    assert methode == ["Taux d'engagement", "Vu bon à payer", "Repère N−1"]
    pdf = client.get("/api/v1/depense/ministeres.pdf", {"colonnes": "credit_actuel"})
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-")
