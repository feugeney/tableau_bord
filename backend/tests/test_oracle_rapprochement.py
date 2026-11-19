from datetime import date
from unittest.mock import patch

import pandas as pd

from etl.connecteurs.chaine_depense import OracleChaineDepenseConnector


def connecteur_test(montants=(100, 200), exclusions=True):
    ch = OracleChaineDepenseConnector(exercice=2025, date_situation=date(2026, 11, 13))
    commun = {k: "1" for k in ch.cle_ligne}
    commun.update(exercice="2025", section="31", titre="3", sous_section="3101")
    situation = [
        dict(
            commun,
            article=str(i + 1),
            credit_engage=m,
            credit_actuel=1000,
            montant_liquide=0,
            montant_ordonnance=0,
            montant_paye=0,
        )
        for i, m in enumerate((100, 200))
    ]
    engagements = [
        dict(
            commun,
            article=str(i + 1),
            groupe_administratif="3101",
            numero=str(i + 1),
            montant_engage=m,
            montant_ordonnance=0,
            montant_paye=0,
            type_procedure="Procédure normale",
            etat_dossier="Dépense engagée",
            code_etat_dossier="E3N",
            code_type_procedure="01",
        )
        for i, m in enumerate(montants)
    ]
    if exclusions:
        engagements += [
            dict(engagements[0], numero="3", montant_engage=7, code_etat_dossier="E9N"),
            dict(engagements[1], numero="4", montant_engage=3, code_type_procedure="52"),
        ]
    ch.donnees = {
        "situation": pd.DataFrame(situation, dtype=object),
        "engagements": pd.DataFrame(engagements, dtype=object),
    }
    return ch


def valider(ch):
    with patch("apps.core.regles._parametres_base", return_value={}):
        return ch.validate()


def test_rapprochement_par_cle_sans_supprimer_les_sources():
    ch = connecteur_test()
    assert valider(ch).valide
    assert len(ch.donnees["engagements"]) == 4
    assert ch.donnees["engagements"]["montant_engage"].sum() == 310
    assert ch.informations_chargement["rapprochement_engage"]["cles_en_ecart"] == 0
    assert ch.informations_chargement["rapprochement_engage"]["lignes_ecartees_du_controle"] == 2


def test_egalite_globale_ne_masque_pas_les_ecarts_entre_lignes():
    ch = connecteur_test(montants=(99, 201), exclusions=False)
    rapport = valider(ch)
    assert not rapport.valide
    controle = next(c for c in rapport.controles if c.code == "concordance_engage_par_cle")
    assert controle.nombre == 2


def test_exercice_inconnu_ne_beneficie_pas_d_un_controle_plus_faible():
    ch = connecteur_test(montants=(99, 200))
    ch.exercice = 2026
    assert not valider(ch).valide


def test_validation_repetee_ne_reutilise_pas_un_perimetre_precedent():
    ch = connecteur_test()
    assert valider(ch).valide
    ch.donnees["engagements"].loc[0, "montant_engage"] = 1
    assert not valider(ch).valide
