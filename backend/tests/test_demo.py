from datetime import date
from decimal import Decimal

import pytest

from apps.core import demo
from apps.core.models import Alerte, Chargement, Source
from apps.referentiels.models import RefOrganisme, RefSection

from .test_api import client_pour, utilisateur

pytestmark = pytest.mark.django_db

SITUATION = dict(exercice=2025, date_situation=date(2025, 9, 15))


@pytest.fixture
def illustre(db):
    return demo.generer(**SITUATION)


def test_generation_toutes_sources(illustre):
    assert set(illustre) == set(demo.SOURCES_DEMO)
    assert all(v == "chargée" for v in illustre.values())
    assert set(Source.objects.filter(statut="demo").values_list("code", flat=True)) == set(demo.SOURCES_DEMO)
    assert Chargement.objects.filter(detail__demo=True).count() == len(demo.SOURCES_DEMO)


def test_anonymisation(illustre):
    # 232 organismes fictifs (152 EPA, 80 sociétés) ; sections fictives seulement pour les ministères de démo.
    assert RefOrganisme.objects.filter(fictif=True, type="epa").count() == 152
    assert RefOrganisme.objects.filter(fictif=True, type="societe").count() == 80
    assert not RefOrganisme.objects.filter(fictif=False).exists()
    from apps.paie.models import FaitPaie
    from apps.patrimoine.models import FaitPatrimoine

    assert not FaitPaie.objects.exclude(section__fictif=True).exists()
    assert not FaitPatrimoine.objects.exclude(section__fictif=True).exists()
    assert RefSection.objects.filter(fictif=True).count() == 8


def test_regeneration_idempotente(illustre):
    demo.generer(**SITUATION)
    assert Chargement.objects.filter(detail__demo=True).count() == len(demo.SOURCES_DEMO)


def test_source_reelle_jamais_ecrasee(db):
    Source.objects.filter(code="safig").update(statut="reel")
    r = demo.generer(**SITUATION, sources=["safig"])
    assert r["safig"].startswith("ignorée")
    assert not Chargement.objects.filter(source__code="safig").exists()


def test_suppression(illustre):
    demo.supprimer()
    assert not Source.objects.filter(statut="demo").exists()
    assert not Chargement.objects.filter(detail__demo=True).exists()


def test_alertes_des_domaines_illustres(illustre):
    domaines = set(Alerte.objects.values_list("domaine", flat=True))
    assert {"paie", "patrimoine", "portefeuille", "douanes"} <= domaines


@pytest.mark.parametrize(
    "prefixe, cle",
    [
        ("recettes-fiscales", "par_impot"),
        ("douanes", "circuits"),
        ("tresor", "tofe"),
        ("dette", "echeancier"),
        ("patrimoine", "parc"),
        ("portefeuille", "sante"),
        ("paie", "fugas"),
        ("marches-publics", "par_mode"),
    ],
)
def test_pages_de_domaine(illustre, prefixe, cle):
    c = client_pour(utilisateur("cab", "ministre_cabinet"))
    r = c.get(f"/api/v1/{prefixe}/")
    assert r.status_code == 200
    assert r.data["meta"]["statut_source"] == "demo"
    assert r.data["meta"]["date_situation"] == "2025-09-15"
    assert r.data["data"][cle]


def test_page_recettes_fiscales_coherente(illustre):
    c = client_pour(utilisateur("cab", "ministre_cabinet"))
    d = c.get("/api/v1/recettes-fiscales/").data["data"]
    i = d["indicateurs"]
    assert i["recouvre"] == pytest.approx(sum(x["recouvre"] for x in d["par_impot"]))
    assert 0 < i["taux"] < 1.1
    assert len(d["mensuel"]) == 9  # janvier à septembre


def test_synthese_avec_illustration(illustre):
    c = client_pour(utilisateur("cab", "ministre_cabinet"))
    kpis = {
        k["code"]: k for k in c.get("/api/v1/synthese/", {"mode_synthese": "demonstration"}).data["data"]["indicateurs"]
    }
    assert kpis["recettes"]["meta"]["statut_source"] == "demo" and kpis["recettes"]["valeur"] > 0
    assert kpis["dette"]["reference"] == 0.7
    assert kpis["tresorerie"]["valeur"] > 0


def test_masse_salariale_sans_fugas(db, charge):
    """Le volet réel (Chaîne Dépense, titre 2) s'affiche même si FUGAS n'est pas raccordé."""
    c = client_pour(utilisateur("cab", "ministre_cabinet"))
    d = c.get("/api/v1/paie/").data
    assert d["meta"]["statut_source"] == "non_raccorde"
    assert d["data"]["credits"]["meta"]["statut_source"] == "reel"
    assert d["data"]["fugas"]["donnees"] is None


def test_commande(db):
    from django.core.management import call_command

    call_command("seed_demo", "--exercice", "2025", "--date-situation", "2025-06-30", "--sources", "dette")
    assert Source.objects.get(code="dette").statut == "demo"
    call_command("seed_demo", "--supprimer")
    assert Source.objects.get(code="dette").statut == "non_raccorde"


def test_chargement_reel_retire_l_illustration(illustre, tmp_path):
    """Au premier chargement réel d'une source, ses données d'illustration disparaissent."""
    from apps.core.models import MappingColonnes
    from apps.paie.models import FaitPaie
    from apps.referentiels.models import RefSection
    from etl.connecteurs.generique import ExcelGenericConnector

    src = Source.objects.get(code="fugas")
    for col, champ, typ in (
        ("Mois", "mois", "entier"),
        ("Code", "section", "code"),
        ("Effectif", "effectif", "entier"),
    ):
        MappingColonnes.objects.create(
            source=src,
            table_cible="fait_paie",
            colonne_source=col,
            champ_cible=champ,
            type_donnee=typ,
            obligatoire=True,
        )
    RefSection.objects.get_or_create(code="09")
    fichier = tmp_path / "paie en date du 31-03-2025.csv"
    fichier.write_text("Mois;Code;Effectif\n3;09;100\n", encoding="utf-8")
    ch = ExcelGenericConnector("fugas", "fait_paie", fichier).executer()
    assert ch.statut == "succes", ch.message_erreur
    assert Source.objects.get(code="fugas").statut == "reel"
    assert not Chargement.objects.filter(source__code="fugas", detail__demo=True).exists()
    assert list(FaitPaie.objects.values_list("section_id", flat=True)) == ["09"]  # plus de ministères fictifs
    assert Chargement.objects.filter(source__code="safig", detail__demo=True).exists()  # autres sources intactes


def test_marches_publics_entente_directe(illustre):
    """Page, alerte et rapprochement : part de l'entente directe en montant, anonymisation des acteurs."""
    from apps.marches_publics.models import FaitMarche

    assert FaitMarche.objects.exists()
    assert not FaitMarche.objects.exclude(autorite_contractante__startswith="Autorité contractante").exists()
    assert not FaitMarche.objects.exclude(section=None).exists()  # aucun rattachement à un ministère réel
    c = client_pour(utilisateur("cab", "ministre_cabinet"))
    d = c.get("/api/v1/marches-publics/").data["data"]
    i = d["indicateurs"]
    ed = next(m for m in d["par_mode"] if m["code"] == "entente_directe")
    assert i["part_entente_directe"] == pytest.approx(ed["part"])
    assert sum(m["montant"] for m in d["par_mode"]) == pytest.approx(i["montant_ttc"])
    assert not FaitMarche.objects.exclude(titulaire_nif__startswith="DEMO-").exists()  # NIF fictifs
    assert d["controles"]["marches_sans_reservation"]["nombre"] > 0  # anomalies de démonstration
    assert d["engagements_chaine_depense"]["meta"]["source"] == "chaine_depense"
    assert Alerte.objects.filter(regle__code="marches_coherence").exists()
    if i["entente_directe_excessive"]:
        assert Alerte.objects.filter(regle__code="marches_entente_directe").exists()


def test_chaine_depense_sur_demande(db):
    """Jamais chargée par défaut ; sur demande, lignes et engagements fictifs cohérents entre eux."""
    from django.db.models import Sum

    from apps.depense.models import FaitEngagement, FaitSituationLigne

    assert "chaine_depense" not in demo.generer(**SITUATION, sources=["dette"])
    assert demo.generer(**SITUATION, sources=["chaine_depense"]) == {"chaine_depense": "chargée"}
    assert not FaitSituationLigne.objects.exclude(section__fictif=True).exists()
    engage = FaitEngagement.objects.aggregate(s=Sum("montant_engage"))["s"]
    assert FaitSituationLigne.objects.aggregate(s=Sum("credit_engage"))["s"] == pytest.approx(
        engage, rel=Decimal("0.000001")
    )
    c = client_pour(utilisateur("cab", "ministre_cabinet"))
    r = c.get("/api/v1/depense/indicateurs/", {"exercice": 2025, "date_situation": "2025-09-15"})
    assert r.status_code == 200
    assert r.data["meta"]["statut_source"] == "demo"
    assert 0 < r.data["data"]["taux_engagement"] < 1
    s = c.get("/api/v1/depense/simandou/", {"exercice": 2025, "date_situation": "2025-09-15"}).data["data"]
    assert len(s["piliers"]) == 5
    assert s["hors_pilier"] is not None  # dette et lignes sans pilier
    assert s["green"]["nb_lignes"] > 0
