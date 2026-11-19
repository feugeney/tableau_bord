from copy import deepcopy

import pandas as pd
import pytest

from apps.core.filtres import Filtres
from apps.core.models import Chargement
from apps.depense import services
from apps.depense.models import FaitSituationLigne
from apps.referentiels.models import RefSection
from etl.connecteurs.chaine_depense import libelles_oracle


def test_libelles_source_conserves_et_services_rattaches_a_la_bonne_section():
    df = pd.DataFrame(
        [
            {
                "section": "09",
                "libelle_section": "MINISTÈRE SOURCE EXACT",
                "libelle_court_section": "NOM COURT SOURCE",
                "sous_section": "001",
                "libelle_sous_section": "Direction TC_SERVICE A",
            },
            {
                "section": "14",
                "libelle_section": "INSTITUTION SOURCE",
                "sous_section": "001",
                "libelle_sous_section": "Direction TC_SERVICE B",
            },
        ],
        dtype=object,
    )
    refs = libelles_oracle({"situation": df})
    assert refs["sections"]["09"]["libelle"] == "MINISTÈRE SOURCE EXACT"
    assert refs["sections"]["09"]["libelle_court"] == "NOM COURT SOURCE"
    assert refs["sous_sections"]["09"]["001"] == "Direction TC_SERVICE A"
    assert refs["sous_sections"]["14"]["001"] == "Direction TC_SERVICE B"


@pytest.mark.django_db
def test_affichage_source_par_situation_sans_modifier_les_montants(charge, filtres):
    avant = services.sections(filtres)
    reference = RefSection.objects.get(code="09")
    libelle_local = reference.libelle
    code_service = FaitSituationLigne.objects.filter(chargement=charge, section_id="09").first().sous_section_id
    charge.detail["referentiels_libelles"] = {
        "sections": {
            "09": {"libelle": "MINISTÈRE SOURCE EXACT", "libelle_court": "SOURCE EXACTE", "type": "institution"}
        },
        "sous_sections": {"09": {code_service: "Direction TC_SERVICE"}},
    }
    charge.save(update_fields=["detail"])
    apres = services.sections(filtres)
    for a, b in zip(avant, apres):
        assert {k: v for k, v in a.items() if k not in ("libelle", "libelle_court")} == {
            k: v for k, v in b.items() if k not in ("libelle", "libelle_court")
        }
    assert next(s for s in apres if s["code"] == "09")["libelle"] == "MINISTÈRE SOURCE EXACT"
    detail = services.section_detail(filtres, "09")
    assert detail["libelle"] == "MINISTÈRE SOURCE EXACT"
    assert (
        next(s for s in detail["top_sous_sections"] if s["code"] == code_service)["libelle"] == "Direction TC_SERVICE"
    )
    reference.refresh_from_db()
    assert reference.libelle == libelle_local
    assert services._libelles_sections(Filtres(2026, filtres.date_situation))["09"]["libelle"] == libelle_local


@pytest.mark.django_db
def test_une_tentative_rejetee_ne_remplace_pas_les_noms_valides(charge, filtres):
    charge.detail["referentiels_libelles"] = {
        "sections": {"09": {"libelle": "Nom validé", "libelle_court": "Nom validé", "type": "ministere"}}
    }
    charge.save(update_fields=["detail"])
    detail = deepcopy(charge.detail)
    detail["referentiels_libelles"]["sections"]["09"]["libelle"] = "Nom rejeté"
    Chargement.objects.create(
        source=charge.source,
        exercice=charge.exercice,
        date_situation=charge.date_situation,
        statut="echec",
        detail=detail,
    )
    assert services.section_detail(filtres, "09")["libelle"] == "Nom validé"
