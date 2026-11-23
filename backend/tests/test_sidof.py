"""SIDOF-ENTREPOT : lignes budgétaires (vm_lbudg) chargées comme situation de la Chaîne Dépense."""

import io
import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.core.filtres import resoudre_filtres
from apps.core.models import Chargement, FluxETL
from apps.depense import services
from apps.depense.models import FaitEngagement, FaitSituationLigne
from etl.connecteurs.sidof import SidofLignesBudgetairesConnector, est_copie_decalee

from .test_api import client_pour, utilisateur

pytestmark = pytest.mark.django_db
MD = 10**9


def _ligne(section, ss, titre, cred, eng, paye, *, source="2", groupe="0", bailleur="000", maj="2026-11-20T10:00:00Z"):
    return {
        "no_ex": "2026",
        "code_zone_geographique": "1",
        "cd_type_budget": "000",
        "cd_section": section,
        "libelle_court_section": f"MINISTERE {section}",
        "cd_ss_section": ss,
        "cd_titre": titre,
        "cd_chap": "1",
        "cd_art": "1",
        "cd_paragraphe": "10",
        "cd_ss_paragraphe": "00",
        "cd_bailleur": bailleur,
        "cd_source_fin": source,
        "cd_regul": "00",
        "cd_groupe_bail": groupe,
        "mt_cred": str(cred),
        "mt_cred_init": str(cred),
        "mt_eng": str(eng),
        "mt_eng_cf": str(eng),
        "mt_liq": str(eng),
        "mt_ord": str(eng),
        "mt_vbp": str(paye),
        "mt_paye": str(paye),
        "mt_bloque": "0.00",
        "mt_resrv": "0.00",
        "mt_prj_transf": None,
        "mt_delegation": "0.00",
        "mt_regie": "0.00",
        "mt_apad": "0.00",
        "simplemtbloque": "0.00",
        "mt_dispo": str(cred - eng),
        "id_pillier_simandou": 2,
        "libelle_pillier_simandou": "Education et Culture",
        "code_region": "00",
        "libelle_region": "Ensemble Region",
        "code_prefecture": "00",
        "libelle_prefecture": "Ensemble",
        "code_sous_prefecture": "00",
        "code_service": "14010",
        "libelle_long_service": f"Service {ss}",
        "dt_maj": maj,
    }


def _copie_decalee(ligne):
    """Défaut de vm_lbudg : source, groupe et bailleur décalés (« 0 / 000 / 2 » au lieu de « 2 / 0 / 000 »)."""
    return {
        **ligne,
        "cd_source_fin": ligne["cd_groupe_bail"],
        "cd_groupe_bail": ligne["cd_bailleur"],
        "cd_bailleur": ligne["cd_source_fin"],
    }


def jeu():
    justes = [
        _ligne("14", "140100000000", "5", 30 * MD, 6 * MD, 1 * MD, maj="2026-11-22T21:30:00Z"),
        _ligne("09", "090100000000", "3", 10 * MD, 8 * MD, 5 * MD),
        # Même sous-section sous une autre section : la section fait partie de la clé de ligne.
        _ligne("13", "090100000000", "3", 4 * MD, 1 * MD, 0),
    ]
    return justes + [_copie_decalee(r) for r in justes]


def test_copie_decalee_reconnue():
    juste = _ligne("14", "140100000000", "5", 1, 0, 0)
    assert not est_copie_decalee(juste)
    assert est_copie_decalee(_copie_decalee(juste))


def test_chargement_ecarte_les_copies_et_alimente_la_situation():
    ch = SidofLignesBudgetairesConnector(lignes=jeu(), exercice=2026).executer()
    assert ch.statut == "succes", ch.message_erreur
    assert ch.source.code == "chaine_depense" and ch.fichier == "sidof://lignes_budgetaires"
    # Date de situation : dernière mise à jour SIDOF (21 h 30 UTC = 21 h 30 à Conakry), pas la date d'appel.
    assert ch.date_situation == date(2026, 11, 22)
    assert ch.detail["sidof"] == {
        "lignes_recues": 6,
        "copies_decalees_ecartees": 3,
        "lignes_retenues": 3,
        "derniere_mise_a_jour": "2026-11-22T21:30:00Z",
    }
    lignes = FaitSituationLigne.objects.filter(chargement=ch)
    assert lignes.count() == 3
    assert {(r.source_financement, r.groupe_bailleur, r.bailleur) for r in lignes} == {("2", "0", "000")}
    assert not FaitEngagement.objects.filter(chargement=ch).exists()
    ligne = lignes.get(section_id="14")
    assert ligne.attributs["pillier simandou"] == "Education et Culture"
    assert ligne.attributs["libelle_region"] == "Ensemble Region"
    controles = {c["code"]: c for c in ch.detail["controles"]}
    assert controles["liste_engagements"]["niveau"] == "info"
    assert controles["sidof_copies_decalees"]["reussi"] is True
    assert "concordance_engage" not in controles

    # Les indicateurs de la page Dépenses lisent ce chargement comme une situation de la Chaîne Dépense.
    i = services.indicateurs(resoudre_filtres({"exercice": "2026"}, "chaine_depense"))
    assert i["credit_actuel"] == 44 * MD and i["credit_engage"] == 15 * MD and i["montant_paye"] == 6 * MD


def test_proportion_inhabituelle_de_copies_signalee():
    justes = jeu()[:3]
    ch = SidofLignesBudgetairesConnector(lignes=justes + [_copie_decalee(justes[0])], exercice=2026).executer()
    assert ch.statut == "succes"
    controle = next(c for c in ch.detail["controles"] if c["code"] == "sidof_copies_decalees")
    assert controle["reussi"] is False and controle["niveau"] == "avertissement"


def test_exercice_vide_refuse():
    ch = SidofLignesBudgetairesConnector(lignes=[], exercice=2026).executer()
    assert ch.statut == "echec" and "Aucune ligne budgétaire SIDOF" in ch.message_erreur


class _Reponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def test_lecture_paginee_avec_la_cle_et_sans_fuite_vers_un_autre_hote(settings):
    settings.SOURCES_EXTERNES = {
        **settings.SOURCES_EXTERNES,
        "sidof": {"url": "https://sidof.exemple", "cle": "cle-de-test", "timeout": 5},
    }
    pages = [
        {"results": jeu()[:2], "next": "https://sidof.exemple/api/v1/lignes-budgetaires/?curseur=x"},
        {"results": jeu()[2:], "next": None},
    ]
    appels = []

    def ouvrir(requete, timeout):
        appels.append((requete.full_url, requete.get_header("X-api-key")))
        return _Reponse(json.dumps(pages[len(appels) - 1]).encode())

    with patch("urllib.request.urlopen", side_effect=ouvrir):
        lignes = SidofLignesBudgetairesConnector(exercice=2026)._lire_pages()
    assert len(lignes) == 6
    assert appels[0] == ("https://sidof.exemple/api/v1/lignes-budgetaires/?no_ex=2026&taille=1000", "cle-de-test")
    assert all(cle == "cle-de-test" for _, cle in appels)

    pages[0]["next"] = "https://autre-hote.exemple/api/v1/lignes-budgetaires/?curseur=x"
    appels.clear()
    from etl.connecteurs.base import ErreurChargement

    with patch("urllib.request.urlopen", side_effect=ouvrir), pytest.raises(ErreurChargement):
        SidofLignesBudgetairesConnector(exercice=2026)._lire_pages()
    assert len(appels) == 1  # la clé n'est jamais envoyée à l'autre hôte


@pytest.fixture
def admin_sidof(settings):
    settings.SOURCES_EXTERNES = {
        **settings.SOURCES_EXTERNES,
        "sidof": {"url": "https://sidof.exemple", "cle": "cle-de-test", "timeout": 5},
    }
    return client_pour(utilisateur("etl-sidof", "dnsi_admin"))


def test_flux_sidof_cree_et_lance_depuis_ladministration(admin_sidof, settings):
    flux = FluxETL.objects.get(code="sidof-lignes-budgetaires")
    assert flux.profil == "sidof_lignes_budgetaires" and flux.source.code == "chaine_depense" and not flux.actif
    flux.exercice, flux.actif = 2026, True
    flux.save()
    url = f"/api/v1/admin/flux-etl/{flux.pk}/lancer/"
    with patch.object(SidofLignesBudgetairesConnector, "_lire_pages", return_value=jeu()):
        r = admin_sidof.post(url, {"apercu": False}, format="json")
    assert r.status_code == 200 and r.data["statut"] == "succes", r.data
    ch = Chargement.objects.get(pk=r.data["id"])
    assert ch.detail["flux_etl"] == "sidof-lignes-budgetaires" and ch.detail["origine"] == "sidof"
    assert sum(FaitSituationLigne.objects.filter(chargement=ch).values_list("credit_actuel", flat=True)) == Decimal(
        44 * MD
    )

    settings.SOURCES_EXTERNES = {**settings.SOURCES_EXTERNES, "sidof": {"url": "https://sidof.exemple", "cle": ""}}
    r = admin_sidof.post(url, {"apercu": True}, format="json")
    assert r.status_code == 400 and "SIDOF_API_KEY" in str(r.data)
