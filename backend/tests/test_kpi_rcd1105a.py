"""Taux de la page Dépenses : chaque étape de la chaîne rapportée à la précédente.

Décision du 18/11/2026 (remplace les dénominateurs « engagé » du rapport RCD1105A) :
liquidé / engagé, ordonnancé / liquidé, VBP / ordonnancé, payé / ordonnancé.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.core.filtres import Filtres
from apps.depense import services


def _indicateurs(total, **filtres):
    with (
        patch.object(services, "_totaux", return_value=[total]),
        patch.object(services, "lignes_en_depassement", return_value=0),
        patch.object(services, "compter_lignes", return_value=0),
    ):
        return services.indicateurs(Filtres(2026, date(2026, 11, 12), **filtres))


@pytest.mark.parametrize("mode", ["brut", "ajuste"])
def test_taux_rapportes_a_l_etape_precedente(mode):
    total = {m: Decimal(0) for m in services.MESURES}
    total.update(
        credit_actuel=Decimal(1000),
        credit_engage=Decimal(500),
        montant_liquide=Decimal(450),
        montant_ordonnance=Decimal(400),
        montant_vbp=Decimal(300),
        montant_paye=Decimal(200),
        ordonnance_hors_chaine=Decimal(100),
        paye_hors_chaine=Decimal(10),
    )
    i = _indicateurs(total, paiement=mode)
    assert i["taux_engagement"] == Decimal("0.5")
    assert i["taux_liquidation"] == Decimal("0.9")
    assert i["taux_ordonnancement"] == Decimal(400) / Decimal(450)
    assert i["taux_vbp"] == Decimal("0.75")
    assert i["taux_paiement"] == Decimal("0.5")
    # Rapports aux crédits, conservés sous un nom distinct.
    assert i["taux_liquidation_sur_credits"] == Decimal("0.45")
    assert i["taux_ordonnancement_sur_credits"] == Decimal("0.4")
    assert i["taux_paiement_sur_credits"] == Decimal("0.2")
    # Les taux sont bruts : seul le reste à payer dépend du mode ajusté.
    assert i["paiement"]["reste_a_payer"] == (Decimal(200) if mode == "brut" else Decimal(110))


def test_sans_liquidation_le_taux_d_ordonnancement_est_indisponible():
    total = {m: Decimal(0) for m in services.MESURES}
    total.update(credit_actuel=Decimal(100), credit_engage=Decimal(50), montant_ordonnance=Decimal(40))
    i = _indicateurs(total)
    assert i["taux_ordonnancement"] is None
    assert i["taux_liquidation"] == 0
