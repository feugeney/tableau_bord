from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO, StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from openpyxl import load_workbook

from apps.core.filtres import Filtres
from apps.depense.models import FaitAPAD, FaitEngagement, FaitSituationLigne
from apps.depense.pilotage import page
from etl.connecteurs.chaine_depense import ExcelChaineDepenseConnector

from .test_api import client_pour, utilisateur

pytestmark = pytest.mark.django_db


@pytest.fixture
def client_cabinet():
    return client_pour(utilisateur("pilotage-cabinet", "ministre_cabinet"))


def test_disponibilite_et_montant_absent_ne_deviendra_pas_zero(charge, filtres):
    FaitSituationLigne.objects.filter(chargement=charge).update(
        credit_actuel=100, credit_engage=30, credit_reserve=10, montant_bloque=5, credit_disponible=55
    )
    b = page(filtres)["disponibilite"]
    assert b["disponible_reconstitue"] == b["credit_disponible"] == 385
    assert b["credits_non_engages"] == 490
    assert b["part_immobilisee"] == Decimal("0.15")
    fait = FaitSituationLigne.objects.filter(chargement=charge).first()
    fait.attributs["_mesures_absentes"] = ["credit_reserve"]
    fait.save(update_fields=["attributs"])
    b = page(filtres)["disponibilite"]
    assert b["credit_reserve"] is None and b["disponible_reconstitue"] is None
    assert b["part_immobilisee"] is None


def test_source_incomplete_et_filtres_isolent_les_perimetres(charge, filtres):
    charge.detail["colonnes_extraites"]["situation"].remove("montant_bloque")
    charge.detail["indicateurs_indisponibles"] = ["credit_disponible"]
    charge.save(update_fields=["detail"])
    f = Filtres(filtres.exercice, filtres.date_situation, "investissement", "14")
    d = page(f)
    assert d["disponibilite"]["montant_bloque"] is None
    assert d["disponibilite"]["credit_disponible"] is None
    assert d["disponibilite"]["credit_actuel"] == 30 * 10**9
    assert d["apad"]["avance_demarrage"] is None


def test_delais_excluent_dates_negatives_futures_et_manquantes(charge, filtres):
    qs = FaitEngagement.objects.filter(chargement=charge).order_by("pk")
    qs.update(date_creation=None, date_visa_cf=None, date_visa_ministre=None)
    lignes = list(qs[:4])
    for ligne, delai in zip(lignes, [2, 8, -1, 30]):
        ligne.date_creation = filtres.date_situation - timedelta(days=10)
        ligne.date_visa_cf = ligne.date_creation + timedelta(days=delai)
        ligne.save(update_fields=["date_creation", "date_visa_cf"])
    d = page(filtres)["delais"][0]
    assert d["paires_valides"] == 2
    assert d["mediane_jours"] == 5 and d["p90_jours"] == 8
    assert d["delais_negatifs"] == d["dates_futures"] == 1
    assert d["couverture"] == Decimal(2) / qs.count()


def test_rapprochement_detecte_ecarts_qui_se_compensent(charge, filtres):
    lignes = list(FaitSituationLigne.objects.filter(chargement=charge).order_by("pk")[:2])
    lignes[0].montant_paye += 123
    lignes[1].montant_paye -= 123
    for ligne in lignes:
        ligne.save(update_fields=["montant_paye"])
    r = next(r for r in page(filtres)["rapprochements"] if r["libelle"] == "Payé enregistré")
    assert r["ecart"] == 0
    assert r["cles_en_ecart"] == 2 and r["ecart_absolu"] == 246


def test_pilier_vide_reste_inconnu(charge, filtres):
    from apps.depense.services import simandou

    FaitSituationLigne.objects.filter(chargement=charge).update(attributs={"catégorie projet": "PS2040"})
    assert simandou(filtres)["hors_pilier"]["libelle"] == "Pilier non renseigné"


def test_apad_complement_par_empreinte_idempotent_et_sans_double_compte(classeur, tmp_path):
    wb = load_workbook(classeur)
    wb.remove(wb["APAD"])
    # La fixture générale inclut volontairement une ligne budgétaire dupliquée.
    wb["Situation courante"].delete_rows(wb["Situation courante"].max_row)
    ws = wb.create_sheet("APAD")
    ws.append(
        [
            "Exercice",
            "type budget",
            "gradm",
            "numero APAD",
            "numéro Marché",
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
            "Avance de demarrage",
            "Date Création",
        ]
    )
    ws.append(
        [
            2025,
            "000",
            "1401",
            1,
            "001",
            "14",
            "140100000000",
            "Service",
            "2",
            "5",
            "1",
            "1",
            "10",
            "01",
            "2",
            "0",
            "000",
            42,
            date(2025, 5, 1),
        ]
    )
    wb.save(classeur)
    ch = ExcelChaineDepenseConnector(classeur).executer()
    assert ch.statut == "succes", ch.message_erreur
    assert FaitAPAD.objects.filter(chargement=ch).count() == 1
    # Simule un import historique qui n'exploitait pas encore la feuille APAD.
    FaitAPAD.objects.filter(chargement=ch).delete()
    avant = list(
        FaitSituationLigne.objects.filter(chargement=ch).order_by("pk").values_list("credit_engage", "montant_paye")
    )
    sortie = StringIO()
    args = {"chargement": ch.pk, "fichier": str(classeur), "stdout": sortie}
    call_command("completer_details_depense", apercu=True, **args)
    assert not FaitAPAD.objects.filter(chargement=ch).exists()
    call_command("completer_details_depense", **args)
    call_command("completer_details_depense", **args)
    assert FaitAPAD.objects.filter(chargement=ch).count() == 1
    assert (
        list(
            FaitSituationLigne.objects.filter(chargement=ch).order_by("pk").values_list("credit_engage", "montant_paye")
        )
        == avant
    )
    d = page(Filtres(ch.exercice, ch.date_situation))
    assert d["apad"]["avance_demarrage"] == 42
    assert d["apad"]["nb_marches"] == 1
    autre = tmp_path / "different.xlsx"
    autre.write_bytes(b"autre contenu")
    with pytest.raises(CommandError, match="Empreinte différente"):
        call_command("completer_details_depense", chargement=ch.pk, fichier=str(autre))


def test_export_et_api_pilotage(charge, client_cabinet):
    r = client_cabinet.get("/api/v1/depense/pilotage/")
    assert r.status_code == 200 and r.data["data"]["apad"]["avance_demarrage"] is None
    r = client_cabinet.get("/api/v1/depense/pilotage/?exercice=2040")
    assert r.data["data"] is None
    r = client_cabinet.get("/api/v1/export/depenses.xlsx")
    assert r.status_code == 200
    wb = load_workbook(BytesIO(r.content))
    assert {
        "Délais de visa",
        "Rapprochement des phases",
        "APAD enregistrées",
    } <= set(wb.sheetnames)
    # Retirées de la page à la demande de l'utilisateur (19/11/2026) : absentes de l'export aussi.
    for retiree in (
        "Disponibilité des crédits",
        "Dossiers APAD",
        "Chaîne de la dépense",
        "Procédures",
        "Bénéficiaires (top 50)",
    ):
        assert retiree not in wb.sheetnames
    assert "Exécution par fonction" not in wb.sheetnames
    assert "Catégories de projet" not in wb.sheetnames
    r = client_cabinet.get("/api/v1/export/depenses.pdf")
    assert r.status_code == 200 and r.content.startswith(b"%PDF-")
