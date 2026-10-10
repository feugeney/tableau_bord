from datetime import date
from decimal import Decimal

import pytest

from apps.core.models import Alerte, Chargement
from apps.depense import services
from apps.depense.models import FaitEngagement, FaitOperation, FaitRegie, FaitSituationLigne
from apps.qualite.models import ResultatControle
from apps.referentiels.models import (
    RefBeneficiaire,
    RefBeneficiaireAlias,
    RefNatureEconomique,
    RefRegulation,
    RefSection,
    RefTypeProcedure,
)
from etl.connecteurs.chaine_depense import ExcelChaineDepenseConnector

from .classeur import LIGNES_ENG, MD, _eng, ecrire_classeur

pytestmark = pytest.mark.django_db


def controle(ch, code):
    return next(c for c in ch.detail["controles"] if c["code"] == code)


def test_chargement_comptes_et_meta(charge):
    assert charge.exercice == 2025
    assert charge.date_situation == date(2026, 9, 15)
    assert charge.lignes_lues == 14
    assert charge.lignes_chargees == 14
    assert charge.lignes_rejetees == 0
    assert charge.detail["comptes"]["situation"]["chargees"] == 7
    assert FaitSituationLigne.objects.count() == 7
    assert FaitEngagement.objects.count() == 6
    assert FaitOperation.objects.count() == 1
    assert FaitRegie.objects.count() == 0  # onglet vide, structure présente
    assert charge.source.statut == "reel"
    assert ResultatControle.objects.filter(chargement=charge).exists()


def test_codes_et_libelles_nettoyes(charge):
    ligne = FaitSituationLigne.objects.filter(section_id="09").first()
    assert ligne.type_budget == "000"
    assert ligne.regulation == "00"  # espace final supprimé
    assert ligne.sous_paragraphe == "01"
    assert ligne.nature_id == f"{ligne.titre}.1.1.10.01"
    assert ligne.attributs == {"pillier simandou": "Infrastructures"}
    assert RefRegulation.objects.filter(code="00").exists()
    assert not RefRegulation.objects.filter(code="00 ").exists()
    # Libellé de la fixture conservé, libellé brut de l'extraction mémorisé.
    s = RefSection.objects.get(code="14")
    assert s.libelle_court == "Infrastructures"
    assert s.libelle_source == "MINISTERES DES INFRASTRUCTURES"
    assert RefNatureEconomique.objects.get(code="5").libelle == "Investissement"
    assert RefNatureEconomique.objects.get(code="5.1.1.10.01").parent.code == "5.1.1.10"


def test_lfi_absente_signalee(charge):
    ligne = FaitSituationLigne.objects.get(section_id="09", titre="3")
    assert ligne.lfi_absent and ligne.credit_initial_lfi == 0
    assert controle(charge, "absents_credit_initial_lfi")["nombre"] == 1


def test_controles_qualite(charge):
    assert controle(charge, "concordance_engage")["reussi"]
    assert controle(charge, "doublons_cle_ligne")["nombre"] == 2  # comptés, pas écrasés
    assert controle(charge, "lignes_depassement")["nombre"] == 1
    assert controle(charge, "liquide_sup_engage")["nombre"] == 1
    assert controle(charge, "numero_engagement_non_unique")["nombre"] == 0


def test_beneficiaires_rapproches(charge):
    assert RefBeneficiaire.objects.count() == 4
    traore = RefBeneficiaire.objects.get(nom_normalise="GALBGDTRAOREGASSIMOU")
    assert traore.nom_affiche == "GAL BGD TRAORE Gassimou"
    assert RefBeneficiaireAlias.objects.filter(beneficiaire=traore).count() == 2
    assert FaitEngagement.objects.filter(beneficiaire=traore).count() == 2


def test_procedures_hors_chaine(charge):
    assert RefTypeProcedure.objects.get(libelle="Procedure Solde").paiement_hors_chaine
    assert not RefTypeProcedure.objects.get(libelle="Procedure normale").paiement_hors_chaine


def test_concordance_bloquante(db, tmp_path):
    engs = LIGNES_ENG[:-1] + [
        _eng(
            "5",
            "99",
            "990200000000",
            "1",
            "BCRG",
            "Procedure normale",
            "Depense engagee",
            20 * MD + 100_000,
            0,
            0,
            None,
        )
    ]
    chemin = ecrire_classeur(tmp_path, engagements=engs)
    ch = ExcelChaineDepenseConnector(chemin).executer()
    assert ch.statut == "echec"
    assert "Concordance" in ch.message_erreur
    assert FaitSituationLigne.objects.count() == 0  # rien n'est écrit


def test_colonne_obligatoire_manquante(db, tmp_path):
    from openpyxl import load_workbook

    chemin = ecrire_classeur(tmp_path)
    wb = load_workbook(chemin)
    wb["Liste des engagements"].delete_cols(20)  # « Montant engagé »
    wb.save(chemin)
    ch = ExcelChaineDepenseConnector(chemin).executer()
    assert ch.statut == "echec"
    assert "engagements" in ch.message_erreur


def test_date_situation_introuvable(db, tmp_path):
    chemin = ecrire_classeur(tmp_path, nom="export.xlsx")
    ch = ExcelChaineDepenseConnector(chemin).executer()
    assert ch.statut == "echec" and "date de situation" in ch.message_erreur
    ch = ExcelChaineDepenseConnector(chemin, date_situation=date(2026, 9, 15)).executer()
    assert ch.statut == "succes" and ch.exercice == 2025  # exercice lu dans la colonne


def test_apercu_ne_charge_rien(db, classeur):
    ch = ExcelChaineDepenseConnector(classeur).executer(apercu=True)
    assert ch.statut == "apercu"
    assert ch.lignes_lues == 14
    assert FaitSituationLigne.objects.count() == 0


def test_recharger_meme_date_ne_double_pas(charge, classeur, filtres):
    ExcelChaineDepenseConnector(classeur).executer()
    assert FaitSituationLigne.objects.count() == 14  # historique conservé
    assert services.indicateurs(filtres)["credit_actuel"] == 105 * MD


def test_situations_empilees(charge, tmp_path):
    autre = ecrire_classeur(tmp_path, nom="SC de 2025-2025 en date du 30-09-2026.xlsx")
    ExcelChaineDepenseConnector(autre).executer()
    from apps.core.filtres import dernieres_situations, resoudre_filtres

    assert [d for _, d in dernieres_situations("chaine_depense")] == [date(2026, 9, 30), date(2026, 9, 15)]
    assert resoudre_filtres({}, "chaine_depense").date_situation == date(2026, 9, 30)
    f = resoudre_filtres({"date_situation": "2026-09-15"}, "chaine_depense")
    assert services.indicateurs(f)["credit_actuel"] == 105 * MD


def test_erreur_technique_tracee(db, tmp_path):
    fichier = tmp_path / "SC de 2025-2025 en date du 15-09-2026.xlsx"
    fichier.write_text("pas un classeur")
    ch = ExcelChaineDepenseConnector(fichier).executer()
    assert ch.statut == "echec" and ch.message_erreur
    assert Chargement.objects.get(pk=ch.pk).duree_secondes is not None


# ------------------------------------------------------------------ services


def test_indicateurs(filtres):
    i = services.indicateurs(filtres)
    assert i["credit_initial_lfi"] == 92 * MD
    assert i["credit_actuel"] == 105 * MD
    assert i["credit_engage"] == 77 * MD
    assert i["taux_engagement"] == Decimal(77) / Decimal(105)
    assert i["montant_ordonnance"] == 76 * MD
    assert i["montant_paye"] == 14 * MD
    assert i["credits_non_engages"] == 28 * MD
    assert i["hors_chaine"] == {"ordonnance": 60 * MD, "paye": 0}
    assert i["paiement"]["ordonnance"] == 16 * MD
    assert i["paiement"]["reste_a_payer"] == 2 * MD
    assert i["paiement"]["paye_sur_ordonnance"] == Decimal("0.875")
    assert i["nb_lignes"] == 7 and i["nb_engagements"] == 6


def test_indicateurs_bruts(filtres):
    filtres.paiement = "brut"
    assert services.indicateurs(filtres)["paiement"]["reste_a_payer"] == 62 * MD


def test_filtre_nature_et_section(filtres):
    filtres.nature = "investissement"
    assert services.indicateurs(filtres)["credit_actuel"] == 30 * MD
    filtres.nature, filtres.section = None, "09"
    assert services.indicateurs(filtres)["credit_actuel"] == 15 * MD


def test_chaine_depense(filtres):
    c = services.chaine(filtres)
    assert [p["code"] for p in c["phases"]] == ["credits", "engage", "liquide", "ordonnance", "vbp", "paye"]
    assert c["liquide_depasse_engage"] is True  # 77,5 > 77
    assert c["nb_lignes_liquide_sup_engage"] == 1


def test_sections_et_statuts(filtres):
    par_code = {s["code"]: s for s in services.sections(filtres)}
    assert par_code["14"]["statut"]["libelle"] == "Sous-exécution"
    assert par_code["09"]["statut"]["code"] == "bon_rythme"
    assert par_code["09"]["nb_lignes_depassement"] == 1
    # Dépenses communes : payé hors chaîne → pas de faux retard de paiement en mode ajusté.
    assert par_code["99"]["statut"]["code"] == "bon_rythme"
    assert par_code["99"]["reste_a_payer"] == 0


def test_section_detail(filtres):
    d = services.section_detail(filtres, "09")
    assert d["libelle_court"] == "Économie, Finances et Budget"
    assert len(d["top_sous_sections"]) == 1
    assert len(d["lignes_depassement"]) == 1
    assert {n["titre"] for n in d["natures"]} == {"2", "3"}


def test_natures(filtres):
    natures = {n["titre"]: n for n in services.natures(filtres)}
    assert natures["5"]["libelle"] == "Investissement"
    e = natures["5"]["empile"]
    assert e["paye"] + e["ordonnance_non_paye"] + e["engage_non_ordonnance"] + e["disponible"] == 30 * MD


def test_mensuel_periode_complementaire(filtres):
    m = services.mensuel(filtres)
    assert m["engage_periode_complementaire"] == 20 * MD
    assert any(r["decembre"] for r in m["mois"])


def test_restes_a_payer_anciennete(filtres):
    r = services.restes_a_payer_anciennete(filtres)
    assert r["reste_a_payer_risque_arriere"] == 2 * MD
    filtres.paiement = "brut"
    assert (
        services.restes_a_payer_anciennete(filtres)["reste_a_payer_risque_arriere"] == 42 * MD
    )  # dette de janv. 2026 : 8 mois


def test_procedures_et_beneficiaires(filtres):
    procs = {p["procedure"]: p for p in services.procedures(filtres)}
    assert procs["Procedure Solde"]["hors_chaine"]
    b = services.beneficiaires(filtres, top=2)
    assert b["total_engage"] == 77 * MD
    assert b["beneficiaires"][0]["beneficiaire"] == "SOLDE DES AGENTS"
    assert len(b["beneficiaires"]) == 2


def test_investissement(filtres):
    inv = services.synthese_investissement(filtres)
    assert inv["credit_actuel"] == 30 * MD and inv["credit_engage"] == 3 * MD
    assert inv["nb_projets"] == 2
    assert inv["nb_projets_sans_engagement"] == 1
    assert inv["credits_projets_sans_engagement"] == 2 * MD
    assert inv["top_ministeres"][0]["libelle_court"] == "Infrastructures"


def test_alertes_generees(charge):
    codes = set(Alerte.objects.values_list("regle__code", flat=True))
    assert {
        "depense_sous_execution",
        "investissement_faible",
        "depense_lignes_depassement",
        "depense_hors_chaine",
        "depense_restes_anciens",
    } <= codes
    a = Alerte.objects.get(regle__code="depense_sous_execution")
    assert a.severite == "critique" and "Infrastructures" in a.message
    assert a.date_situation == date(2026, 9, 15)
