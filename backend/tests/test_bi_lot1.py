from datetime import date
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

import pytest
from openpyxl import load_workbook

from apps.core import demo
from apps.core.domaines import depense, filtres_source
from apps.core.filtres import Filtres
from apps.depense import services
from etl.connecteurs.chaine_depense import OracleChaineDepenseConnector

from .test_api import client_pour, utilisateur
from .test_oracle_rapprochement import connecteur_test

pytestmark = pytest.mark.django_db


@pytest.fixture
def cabinet():
    return client_pour(utilisateur("cab-bi", "ministre_cabinet"))


def test_synthese_reelle_ne_transmet_ni_montants_ni_series_dillustration(charge, cabinet):
    demo.generer(exercice=charge.exercice, date_situation=charge.date_situation)
    reelle = cabinet.get("/api/v1/synthese/").data["data"]
    assert reelle["mode_synthese"] == "decision"
    for k in reelle["indicateurs"]:
        if k["meta"]["statut_source"] == "demo":
            assert k["valeur"] is None
            assert "taux" not in k and "reference" not in k
    assert {r["source"] for r in reelle["serie_mensuelle"]} <= {"chaine_depense"}
    demonstration = cabinet.get("/api/v1/synthese/", {"mode_synthese": "demonstration"}).data["data"]
    assert next(k for k in demonstration["indicateurs"] if k["code"] == "recettes")["valeur"] > 0
    assert cabinet.get("/api/v1/synthese/", {"mode_synthese": "inconnu"}).status_code == 400


def test_dates_inconnues_et_exercices_absents_ne_sont_pas_remplaces(charge, cabinet):
    params = {"exercice": charge.exercice, "date_situation": "2026-01-01"}
    assert cabinet.get("/api/v1/depense/indicateurs/", params).data["data"] is None
    assert all(k.get("valeur") is None for k in cabinet.get("/api/v1/synthese/", params).data["data"]["indicateurs"])
    assert filtres_source("chaine_depense", 2030) is None
    assert depense(2030, titre="4") == (None, None)
    assert cabinet.get("/api/v1/synthese/", {"exercice": "incorrect"}).status_code == 400


def test_serie_oracle_rapprochee_conserve_brut_et_mois_exclus():
    exemple = connecteur_test()
    exemple.donnees["engagements"]["date_creation"] = [date(2025, m, 1) for m in range(1, 5)]
    connecteur = OracleChaineDepenseConnector(exercice=2025, date_situation=date(2026, 11, 13))
    with patch.object(connecteur, "extract", return_value=exemple.donnees):
        ch = connecteur.executer()
    assert ch.statut == "succes", ch.message_erreur
    f = Filtres(2025, date(2026, 11, 13))
    m = services.mensuel(f)
    assert m["rapprochement"]["concordant"]
    assert m["rapprochement"]["comparable"] == m["rapprochement"]["reference"] == Decimal(300)
    assert m["rapprochement"]["brut"] == Decimal(310)
    assert m["rapprochement"]["ecart_perimetre"] == Decimal(10)
    assert len(m["mois"]) == 4
    assert sum(r["montant_engage"] for r in m["mois"]) == 300
    assert sum(r["montant_engage_brut"] for r in m["mois"]) == 310
    # La règle ne s'applique pas à une extraction qui n'a pas été rapprochée.
    ch.detail.pop("rapprochement_engage")
    ch.save(update_fields=["detail"])
    m = services.mensuel(f)
    assert m["rapprochement"]["comparable"] == 310
    assert not m["rapprochement"]["concordant"]


def test_export_synthese_reprend_le_mode_et_la_table_de_passage(charge, cabinet):
    demo.generer(exercice=charge.exercice, date_situation=charge.date_situation)
    r = cabinet.get("/api/v1/export/synthese.xlsx")
    assert r.status_code == 200
    assert charge.date_situation.isoformat() in r["Content-Disposition"]
    wb = load_workbook(BytesIO(r.content))
    assert "Mode de lecture" in wb.sheetnames and "Rapprochement mensuel" in wb.sheetnames
    lignes = list(wb["Indicateurs"].values)
    entetes = lignes[0]
    valeur = entetes.index("Valeur (Mds GNF)")
    code = entetes.index("Code")
    assert all(r[valeur] is None for r in lignes[1:] if r[code] in ("recettes", "dette", "tresorerie"))


def test_les_metadonnees_distinguent_situation_et_extraction(charge, cabinet):
    r = cabinet.get("/api/v1/depense/indicateurs/").data
    assert r["meta"]["origine"] == "fichier"
    assert r["meta"]["date_extraction"]
    assert r["meta"]["exercice"] == charge.exercice
    assert r["meta"]["date_situation"] == charge.date_situation.isoformat()


def test_le_rapport_decisionnel_ne_conserve_pas_de_chiffres_fictifs():
    from apps.core.export_pdf import CollecteurPdf

    c = CollecteurPdf("Essai", {"source": "safig", "statut_source": "demo"}, reel_seulement=True)
    c.feuille("Recettes", {"montant": 123456789})
    assert c.meta["statut_source"] != "demo"
    assert "montant" not in c.blocs[0].donnees
    c.feuille("Données réelles", {"montant": 12}, {"source": "chaine_depense", "statut_source": "reel"})
    assert c.blocs[1].donnees["montant"] == 12


def test_projection_suspendue_si_perimetre_mensuel_non_rapproche():
    exemple = connecteur_test()
    exemple.donnees["engagements"]["date_creation"] = [date(2025, m, 1) for m in range(1, 5)]
    connecteur = OracleChaineDepenseConnector(exercice=2025, date_situation=date(2025, 6, 30))
    with patch.object(connecteur, "extract", return_value=exemple.donnees):
        ch = connecteur.executer()
    assert ch.statut == "succes", ch.message_erreur
    ch.detail.pop("rapprochement_engage")
    ch.save(update_fields=["detail"])
    p = services.projection(Filtres(2025, date(2025, 6, 30)))
    assert not p["engagement"]["fiable"] and p["engagement"]["central"] is None
    assert "série mensuelle" in p["engagement"]["motif"]
