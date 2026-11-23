"""Page Dépenses : comparaison avec l'exercice précédent à la même date et courbe d'exécution cumulée."""

from datetime import date
from decimal import Decimal

from apps.core.filtres import resoudre_filtres
from apps.depense.comparaisons import comparaison_n1, courbe
from apps.depense.models import FaitEngagement, FaitSituationLigne
from etl.connecteurs.chaine_depense import ExcelChaineDepenseConnector

from .classeur import ecrire_classeur


def test_sans_exercice_precedent(charge):
    f = resoudre_filtres({}, "chaine_depense")
    assert comparaison_n1(f) == {"disponible": False, "motif": f"Exercice {f.exercice - 1} non chargé."}
    c = courbe(f)
    assert all(p["n1"] is None for p in c["points"])
    assert c["points"][-1]["prorata"] == 1
    # Le cumul de fin de série = engagé daté de l'exercice rapporté aux crédits.
    credits = sum(l.credit_actuel for l in FaitSituationLigne.objects.filter(chargement=charge))
    engage = sum(
        e.montant_engage for e in FaitEngagement.objects.filter(chargement=charge, date_creation__year=f.exercice)
    )
    derniere = [p for p in c["points"] if p["n"] is not None][-1]
    assert derniere["n"] == engage / credits


def test_exercice_precedent_a_la_meme_date(charge, tmp_path):
    n1 = charge  # exercice 2025, situation du 15/09/2026
    ch = ExcelChaineDepenseConnector(ecrire_classeur(tmp_path, "SC de 2026-2026 en date du 15-09-2026.xlsx")).executer()
    assert ch.statut == "succes", ch.message_erreur
    f = resoudre_filtres({"exercice": "2026"}, "chaine_depense")
    c = comparaison_n1(f)
    assert c["disponible"] and c["exercice"] == 2025 and c["date"] == date(2025, 9, 15)
    credits = sum(l.credit_actuel for l in FaitSituationLigne.objects.filter(chargement=n1))
    engage = sum(
        (
            e.montant_engage
            for e in FaitEngagement.objects.filter(
                chargement=n1, date_creation__year=2025, date_creation__lte=date(2025, 9, 15)
            )
        ),
        Decimal(0),
    )
    assert c["taux_engagement"] == engage / credits
    assert set(c["cloture"]) == {
        "taux_engagement",
        "taux_liquidation",
        "taux_ordonnancement",
        "taux_vbp",
        "taux_paiement",
    }
    assert any(p["n1"] is not None for p in courbe(f)["points"])


def test_courbe_bornee_a_la_date_et_ecart_visible(charge):
    from etl.mart import rafraichir_vues

    charge.date_situation = date(2025, 9, 15)
    charge.save(update_fields=["date_situation"])
    FaitSituationLigne.objects.filter(chargement=charge).update(date_situation=charge.date_situation)
    FaitEngagement.objects.filter(chargement=charge).update(date_situation=charge.date_situation)
    rafraichir_vues()
    f = resoudre_filtres({}, "chaine_depense")
    # Le même mois contient des créations avant et après la situation.
    dossiers = FaitEngagement.objects.filter(chargement=charge)
    dossiers.update(date_creation=date(2025, 9, 20))
    premier = dossiers.first()
    dossiers.filter(pk=premier.pk).update(date_creation=date(2025, 9, 10))
    c = courbe(f)
    credits = sum(l.credit_actuel for l in FaitSituationLigne.objects.filter(chargement=charge))
    assert c["engage_serie"] == premier.montant_engage
    assert c["points"][8]["n"] == premier.montant_engage / credits
    assert all(p["n"] is None for p in c["points"][9:])
    assert c["concordant"] == (c["engage_serie"] == c["engage_situation"])


def test_courbe_sans_dates_ne_fabrique_pas_un_taux_nul(charge):
    FaitEngagement.objects.filter(chargement=charge).update(date_creation=None)
    c = courbe(resoudre_filtres({}, "chaine_depense"))
    assert all(p["n"] is None for p in c["points"])
    assert c["concordant"] is False
