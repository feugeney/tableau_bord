from datetime import date
from decimal import Decimal

import pytest

from apps.core import regles

MD = 10**9


def test_taux_denominateur_nul():
    assert regles.taux(5, 0) is None
    assert regles.taux(5, None) is None
    assert regles.taux(1, 4) == Decimal("0.25")


def test_taux_de_la_chaine_rapportes_a_l_etape_precedente():
    # Décision du 18/11/2026 : crédits → engagé → liquidé → ordonnancé → VBP / payé.
    assert regles.taux_engagement(71, 100) == Decimal("0.71")
    assert regles.taux_liquidation(90, 100) == Decimal("0.9")
    assert regles.taux_ordonnancement(50, 100) == Decimal("0.5")
    assert regles.taux_vbp(75, 100) == Decimal("0.75")
    assert regles.taux_paiement(25, 100) == Decimal("0.25")


def test_exemple_section_31_sur_l_ordonnance():
    ordonnance = Decimal("178162952352")
    vbp = Decimal("97406108382")
    paye = Decimal("65312383218")
    assert [round(r * 100) for r in (regles.taux_vbp(vbp, ordonnance), regles.taux_paiement(paye, ordonnance))] == [
        55,
        37,
    ]


@pytest.mark.parametrize(
    "fonction", [regles.taux_liquidation, regles.taux_ordonnancement, regles.taux_paiement, regles.taux_vbp]
)
def test_taux_execution_sans_denominateur(fonction):
    assert fonction(10, 0) is None
    assert fonction(10, None) is None
    assert fonction(0, 100) == 0
    assert fonction(150, 100) == Decimal("1.5")


def test_paiement_ajuste_exclut_hors_chaine():
    p = regles.paiement(76 * MD, 14 * MD, 60 * MD, 0)
    assert p.ordonnance == 16 * MD
    assert p.paye == 14 * MD
    assert p.reste_a_payer == 2 * MD
    assert p.paye_sur_ordonnance == Decimal("0.875")
    assert p.mode == "ajuste"


def test_paiement_brut():
    p = regles.paiement(76 * MD, 14 * MD, 60 * MD, 0, mode="brut")
    assert p.reste_a_payer == 62 * MD


def test_paiement_mode_invalide():
    with pytest.raises(ValueError):
        regles.paiement(1, 1, mode="autre")


def test_valeurs_acceptation_paiement_ajuste():
    # Section 12 : 27 286,96 ordonnancé / 19 786,09 payé hors procédures hors chaîne.
    p = regles.paiement(Decimal("27286.96"), Decimal("19786.09"))
    assert p.reste_a_payer == Decimal("7500.87")
    assert round(p.paye_sur_ordonnance * 100, 1) == Decimal("72.5")


@pytest.mark.parametrize(
    "credits, engage, ordo, paye, attendu",
    [
        (5774.2 * MD, 0.13 * 5774.2 * MD, 0, 0, "sous_execution"),  # Infrastructures
        (19 * MD, 1 * MD, 0, 0, "a_suivre"),  # < 20 Mds : pas de sous-exécution
        (100 * MD, 80 * MD, 50 * MD, 10 * MD, "paiements_retard"),
        (100 * MD, 60 * MD, 50 * MD, 40 * MD, "a_suivre"),
        (100 * MD, 80 * MD, 19 * MD, 0, "bon_rythme"),  # ordonnancé < 20 Mds
        (100 * MD, 80 * MD, 50 * MD, 20 * MD, "bon_rythme"),
        (0, 0, 0, 0, "bon_rythme"),
    ],
)
def test_statut_ministere(credits, engage, ordo, paye, attendu):
    assert regles.statut_ministere(credits, engage, ordo, paye).code == attendu


def test_statut_ordre_sous_execution_prioritaire():
    s = regles.statut_ministere(100 * MD, 10 * MD, 50 * MD, 0)
    assert s == regles.STATUT_SOUS_EXECUTION
    assert s.severite == "critique"


def test_statut_seuils_parametrables():
    s = regles.statut_ministere(100 * MD, 60 * MD, 0, 0, {"sous_execution_taux_engagement_max": 0.7})
    assert s.code == "sous_execution"


def test_projet_sans_engagement():
    assert regles.est_projet_sans_engagement("5", 2 * MD, 0)
    assert not regles.est_projet_sans_engagement("5", 1 * MD, 0)  # doit dépasser 1 Md
    assert not regles.est_projet_sans_engagement("5", 2 * MD, 1)
    assert not regles.est_projet_sans_engagement("3", 2 * MD, 0)


def test_ligne_en_depassement():
    assert regles.est_ligne_en_depassement(-2)
    assert not regles.est_ligne_en_depassement(-1)
    assert not regles.est_ligne_en_depassement(0)


def test_liquide_depasse_engage():
    assert regles.liquide_depasse_engage(10, 9)
    assert not regles.liquide_depasse_engage(9, 9)


def test_anciennete_et_risque_arriere():
    sit = date(2026, 9, 15)
    assert regles.anciennete_mois(date(2025, 9, 1), sit) == 12
    assert regles.anciennete_mois(date(2025, 3, 10), sit) == 18
    assert regles.anciennete_mois(None, sit) is None
    assert regles.anciennete_mois(date(2026, 10, 1), sit) == 0
    assert not regles.est_risque_arriere(12)
    assert regles.est_risque_arriere(13)
    assert not regles.est_risque_arriere(None)


def test_tresorerie():
    assert regles.tresorerie_sous_seuil(90, 100)
    assert not regles.tresorerie_sous_seuil(100, 100)
    assert regles.jours_de_decaissements(300, 900, 30) == Decimal(10)
    assert regles.jours_de_decaissements(300, 900, 0) is None


def test_recouvrement_en_retard():
    assert regles.recouvrement_en_retard(79, 100)
    assert not regles.recouvrement_en_retard(80, 100)
    assert not regles.recouvrement_en_retard(10, 0)


def test_ratio_dette_pib():
    r = regles.ratio_dette_pib(45, 100)
    assert r.ratio == Decimal("0.45") and not r.depasse and r.seuil == Decimal("0.7")
    assert regles.ratio_dette_pib(75, 100).depasse
    assert regles.ratio_dette_pib(75, 0).ratio is None


def test_concordance():
    assert regles.concordance_ok(1_000_000_000, 1_000_000_999)  # 999 GNF < 1 000 tolérés
    assert not regles.concordance_ok(1_000_000_000, 1_000_001_001)
    assert regles.concordance_ok(0, 0)
    assert regles.concordance_ok(0, 1)
    assert not regles.concordance_ok(3_226_607_108_344, 3_225_807_108_344)  # extraction du 16/08/2026


def test_en_milliards():
    assert regles.en_milliards(36_444_680_000_000) == Decimal("36444.68")
    assert regles.en_milliards(None) is None


def test_parametre_inconnu():
    with pytest.raises(KeyError):
        regles.parametre("inexistant")


@pytest.mark.django_db
def test_parametre_lu_en_base():
    from apps.core.models import Parametre

    Parametre.objects.filter(code="recouvrement_taux_min").update(valeur=0.9)
    regles.invalider_cache_parametres()
    assert regles.recouvrement_en_retard(85, 100)
    Parametre.objects.filter(code="recouvrement_taux_min").update(valeur=0.8)
    regles.invalider_cache_parametres()
