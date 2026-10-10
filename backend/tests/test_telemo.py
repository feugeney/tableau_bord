"""Flux Chaîne de dépenses ↔ Telemo : F3 (réservations), F4 (marchés immatriculés), F5 (paiements)."""

import io
import json
from datetime import date, datetime
from decimal import Decimal

import pytest
from openpyxl import Workbook

from apps.core.models import Chargement, MappingColonnes, Source
from apps.marches_publics.models import FaitMarche, FaitPaiementMarche, FaitReservationCredit
from apps.marches_publics.services import controles, page
from etl.connecteurs.generique import ApiConnector, ExcelGenericConnector

pytestmark = pytest.mark.django_db
MD = 10**9

F3 = [
    "Numéro de la réservation de crédit",
    "Exercice budgétaire",
    "Date création de la réservation",
    "Date validation de la réservation",
    "Identifiant de la ligne budgétaire (clé d'imputation complète)",
    "Objet de la réservation",
    "Autorité contractante",
    "Montant réservé",
    "Devise",
    "Date du visa",
]
F4 = [
    "Numéro d'immatriculation du marché",
    "Date d'immatriculation",
    "Numéro de la réservation de crédit associée",
    "Objet du marché",
    "Type de marché",
    "Mode de passation",
    "Autorité contractante",
    "Exercice budgétaire de rattachement",
    "Titulaire : NIF",
    "Titulaire : raison sociale",
    "Titulaire : RCCM / numéro d'immatriculation",
    "Titulaire : adresse et coordonnées",
    "Titulaire : coordonnées bancaires (banque, RIB / IBAN)",
    "Montant du marché HT",
    "Montant du marché TTC",
    "Montant de la TVA et autres taxes",
    "Devise",
    "Date de signature du marché",
    "Date d'approbation",
    "Délai / durée d'exécution",
    "Modalités de paiement",
]
F5 = ["Numéro d'immatriculation du marché", "Date paiement", "Référence paiement", "Montant paiement"]


def classeur(tmp_path, nom="Telemo en date du 30-06-2026.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.title = "F3 Réservations"
    ws.append(F3)
    ws.append(
        [
            "RES-1",
            "2026",
            datetime(2026, 1, 10),
            datetime(2026, 1, 12),
            "000.14.5.1.1.10.01",
            "Route A",
            "Autorité A",
            12 * MD,
            "GNF",
            datetime(2026, 1, 15),
        ]
    )
    ws.append(
        [
            "RES-2",
            "2026",
            datetime(2026, 2, 1),
            datetime(2026, 2, 2),
            "000.09.3.1.1.10.01",
            "Ordinateurs",
            "Autorité B",
            1 * MD,
            "GNF",
            datetime(2026, 2, 3),
        ]
    )
    ws.append(
        [
            "RES-3",
            "2026",
            datetime(2026, 1, 1),
            datetime(2026, 1, 2),
            "000.09.3.1.1.10.01",
            "Non utilisée",
            "Autorité B",
            5 * MD,
            "GNF",
            datetime(2026, 1, 3),
        ]
    )
    ws = wb.create_sheet("F4 Marchés")
    ws.append(F4)
    ws.append(
        [
            "MP-1",
            datetime(2026, 3, 1),
            "RES-1",
            "Route A",
            "Travaux",
            "Appel d'offres ouvert",
            "Autorité A",
            "2026",
            "NIF-1",
            "Entreprise A",
            "RCCM-1",
            "1 rue X",
            "BANQUE FR76…",
            9 * MD,
            10 * MD,
            1 * MD,
            "GNF",
            datetime(2026, 2, 25),
            datetime(2026, 2, 28),
            180,
            "Avance 15 %",
        ]
    )
    ws.append(
        [
            "MP-2",
            datetime(2026, 3, 10),
            "RES-2",
            "Ordinateurs",
            "Fourniture",
            "Gré à gré",
            "Autorité B",
            "2026",
            "NIF-2",
            "Entreprise B",
            "",
            "",
            "",
            1.1 * MD,
            1.2 * MD,
            0.1 * MD,
            "GNF",
            datetime(2026, 3, 5),
            datetime(2026, 3, 8),
            60,
            "",
        ]
    )
    ws.append(
        [
            "MP-3",
            datetime(2026, 4, 1),
            "",
            "Études",
            "Prestations intellectuelles",
            "Demande de cotation",
            "Autorité A",
            "2026",
            "NIF-1",
            "Entreprise A",
            "",
            "",
            "",
            0.5 * MD,
            0.6 * MD,
            0.1 * MD,
            "GNF",
            None,
            None,
            30,
            "",
        ]
    )
    ws = wb.create_sheet("F5 Paiements")
    ws.append(F5)
    ws.append(["MP-1", datetime(2026, 4, 1), "BCRG-1", 4 * MD])
    ws.append(["MP-2", datetime(2026, 4, 10), "BCRG-2", 1.5 * MD])  # au-delà du montant TTC (1,2 Md)
    ws.append(["MP-9", datetime(2026, 5, 1), "BCRG-3", 0.3 * MD])  # marché inconnu
    chemin = tmp_path / nom
    wb.save(chemin)
    return chemin


@pytest.fixture
def charge_telemo(db, tmp_path):
    ch = ExcelGenericConnector("telemo", None, classeur(tmp_path)).executer()
    assert ch.statut == "succes", ch.message_erreur
    return ch


def test_mappings_preremplis_depuis_la_description_des_flux(db):
    tables = set(MappingColonnes.objects.filter(source__code="telemo").values_list("table_cible", flat=True))
    assert tables == {"fait_reservation_credit", "fait_marche", "fait_paiement_marche"}
    colonnes = set(MappingColonnes.objects.filter(source__code="telemo").values_list("colonne_source", flat=True))
    assert not any("bancaire" in c or "adresse" in c or "RCCM" in c for c in colonnes)  # minimisation


def test_import_des_trois_flux_en_un_chargement(charge_telemo):
    assert charge_telemo.date_situation == date(2026, 6, 30) and charge_telemo.exercice == 2026
    assert charge_telemo.detail["comptes"]["fait_reservation_credit"]["chargees"] == 3
    assert charge_telemo.detail["comptes"]["fait_marche"]["chargees"] == 3
    assert charge_telemo.detail["comptes"]["fait_paiement_marche"]["chargees"] == 3
    assert Chargement.objects.filter(source__code="telemo").count() == 1  # un seul chargement, trois tables
    assert Source.objects.get(code="telemo").statut == "reel"


def test_libelles_metier_et_minimisation(charge_telemo):
    mp2 = FaitMarche.objects.get(numero_immatriculation="MP-2")
    assert mp2.mode_passation == "entente_directe" and mp2.type_marche == "fournitures"
    mp3 = FaitMarche.objects.get(numero_immatriculation="MP-3")
    assert mp3.mode_passation == "cotation" and mp3.type_marche == "prestations_intellectuelles"
    champs = {f.name for f in FaitMarche._meta.get_fields()}
    assert not {"rib", "iban", "adresse", "titulaire_rccm"} & champs
    assert FaitMarche.objects.get(numero_immatriculation="MP-1").montant_ttc == Decimal(10 * MD)


def test_controles_de_coherence(charge_telemo):
    from apps.core.domaines import filtres_source

    c = controles(filtres_source("telemo"))
    assert c["marches_sans_reservation"]["nombre"] == 1  # MP-3
    assert c["paiements_superieurs"]["nombre"] == 1  # MP-2 : 1,5 Md payé pour 1,2 Md
    assert c["paiements_superieurs"]["montant"] == Decimal("0.3") * MD
    assert c["paiements_sans_marche"]["nombre"] == 1  # MP-9
    assert c["reservations_inutilisees"]["nombre"] == 1  # RES-3, visée il y a plus de 90 jours
    assert c["delai_reservation_immatriculation"] == pytest.approx((45 + 35) / 2)
    d = page(filtres_source("telemo"))
    assert float(d["indicateurs"]["part_entente_directe"]) == pytest.approx(1.2 / 11.8)
    assert d["titulaires"][0]["titulaire_nif"] == "NIF-1" and d["titulaires"][0]["nombre"] == 2  # regroupés par NIF


def test_valeur_inconnue_rejetee(db, tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "F4 Marchés"
    ws.append(F4[:7] + ["Montant du marché TTC"])
    ws.append(["MP-1", datetime(2026, 3, 1), "", "X", "Travaux", "Procédure inventée", "Autorité A", 1 * MD])
    chemin = tmp_path / "Telemo en date du 30-06-2026.xlsx"
    wb.save(chemin)
    ch = ExcelGenericConnector("telemo", None, chemin).executer()
    assert ch.statut == "succes" and ch.lignes_rejetees == 1


class _Reponse(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_connecteur_api(db, monkeypatch, settings):
    """Pagination (« next »), jeton transmis, un flux par table, un seul chargement."""
    settings.SOURCES_EXTERNES = {
        **settings.SOURCES_EXTERNES,
        "telemo": {"url": "https://telemo.test/api", "jeton": "secret"},
    }
    appels = []
    pages = {
        "/reservations-credit": [
            {
                "results": [{"Numéro de la réservation de crédit": "R1", "Montant réservé": 5 * MD}],
                "next": "https://telemo.test/api/reservations-credit?page=2",
            },
            {"results": [{"Numéro de la réservation de crédit": "R2", "Montant réservé": MD}], "next": None},
        ],
        "/marches-immatricules": [
            [
                {
                    "Numéro d'immatriculation du marché": "M1",
                    "Type de marché": "travaux",
                    "Mode de passation": "aoo",
                    "Autorité contractante": "A",
                    "Montant du marché TTC": 4 * MD,
                    "Numéro de la réservation de crédit associée": "R1",
                }
            ]
        ],
        "/paiements": [
            {
                "data": [
                    {"Numéro d'immatriculation du marché": "M1", "Date paiement": "2026-05-02", "Montant paiement": MD}
                ]
            }
        ],
    }
    compteurs = {k: 0 for k in pages}

    def urlopen(requete, timeout=0):
        appels.append(requete)
        chemin = next(k for k in pages if k in requete.full_url)
        corps = pages[chemin][compteurs[chemin]]
        compteurs[chemin] += 1
        return _Reponse(json.dumps(corps).encode())

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    conf = Source.objects.get(code="telemo").configuration
    ch = ApiConnector("telemo", conf, date_situation=date(2026, 6, 30)).executer()
    assert ch.statut == "succes", ch.message_erreur
    assert FaitReservationCredit.objects.count() == 2 and FaitMarche.objects.count() == 1
    assert FaitPaiementMarche.objects.count() == 1
    assert all(r.get_header("Authorization") == "Bearer secret" for r in appels)
    assert "exercice=2026" in appels[0].full_url


def test_api_non_configuree(db):
    ch = ApiConnector("telemo", {"flux": []}, date_situation=date(2026, 6, 30)).executer()
    assert ch.statut == "echec" and "URL" in ch.message_erreur


def test_test_de_connexion_api(db, monkeypatch, settings):
    from apps.core.admin_api import tester_connexion
    from apps.core.models import TypeConnecteur

    s = Source.objects.get(code="telemo")
    s.connecteur = TypeConnecteur.API
    assert tester_connexion(s) == (False, "URL de l'API absente (configuration « url » ou variable d'environnement).")
    settings.SOURCES_EXTERNES = {
        **settings.SOURCES_EXTERNES,
        "telemo": {"url": "https://telemo.test/api", "jeton": "secret"},
    }
    monkeypatch.setattr("urllib.request.urlopen", lambda r, timeout=0: _Reponse(b"[]"))
    ok, message = tester_connexion(s)
    assert ok and "jeton transmis" in message and "secret" not in message
