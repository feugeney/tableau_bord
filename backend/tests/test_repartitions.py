"""Page Dépenses › Répartition de l'exécution : titre, fonction, zone d'exécution et type de budget."""

from decimal import Decimal

from apps.core.filtres import resoudre_filtres
from apps.depense.models import FaitSituationLigne
from apps.depense.services import repartitions


def _axe(d, nom):
    return next(a for a in d["axes"] if a["axe"] == nom)


def test_cinq_axes_et_zone_lue_dans_le_code_de_sous_section(charge):
    d = repartitions(resoudre_filtres({}, "chaine_depense"))
    titre = _axe(d, "titre")
    total = sum(p["engage"] for p in titre["parts"])
    assert total == sum(l.credit_engage for l in FaitSituationLigne.objects.filter(chargement=charge))
    for axe in ("fonction", "type_budget"):
        assert sum(p["engage"] for p in _axe(d, axe)["parts"]) == total
    # Sans CODE_ZONE_GEOGRAPHIQUE (Excel), la zone est le 6e chiffre du code de sous-section.
    lignes = FaitSituationLigne.objects.filter(chargement=charge)
    zones = {l.sous_section_id[5] for l in lignes if l.sous_section_id and l.sous_section_id[5] in "0123456"}
    zone = _axe(d, "zone")
    assert zone["disponible"] == bool(zones)
    assert {p["code"] for p in zone["parts"]} - {"?"} == zones
    assert _axe(d, "type_budget")["parts"][0]["libelle"] in ("Budget général", "BAS FCE")


def test_zone_et_fonction_issues_d_oracle(charge):
    FaitSituationLigne.objects.filter(chargement=charge).update(
        attributs={"code_zone_geographique": "3", "code_fonction": "709", "fonctionnelle": "Enseignement"}
    )
    d = repartitions(resoudre_filtres({}, "chaine_depense"))
    zone = _axe(d, "zone")
    assert zone["disponible"] and [p["libelle"] for p in zone["parts"]] == ["Services déconcentrés · intérieur"]
    assert [p["libelle"] for p in _axe(d, "fonction")["parts"]] == ["709 · Enseignement"]


def test_le_filtre_de_nature_garde_tous_les_titres(charge):
    tous = repartitions(resoudre_filtres({}, "chaine_depense"))
    filtre = repartitions(resoudre_filtres({"nature": "investissement"}, "chaine_depense"))
    assert _axe(filtre, "titre")["parts"] == _axe(tous, "titre")["parts"]
    assert filtre["titre_filtre"] == "5"
    engage_5 = next(p["engage"] for p in _axe(tous, "titre")["parts"] if p["code"] == "5")
    assert sum((p["engage"] for p in _axe(filtre, "type_budget")["parts"]), Decimal(0)) == engage_5


def test_six_etapes_de_la_chaine_reparties(charge):
    """Engagé, liquidé, ordonnancé, VBP et payé : chaque mesure retrouve le total de la situation."""
    d = repartitions(resoudre_filtres({}, "chaine_depense"))
    lignes = FaitSituationLigne.objects.filter(chargement=charge)
    for mesure, champ in (
        ("credit", "credit_actuel"),
        ("engage", "credit_engage"),
        ("liquide", "montant_liquide"),
        ("ordonnance", "montant_ordonnance"),
        ("vbp", "montant_vbp"),
        ("paye", "montant_paye"),
    ):
        attendu = sum((getattr(l, champ) or Decimal(0) for l in lignes), Decimal(0))
        assert sum((p[mesure] for p in _axe(d, "titre")["parts"]), Decimal(0)) == attendu, mesure


def test_pilier_avant_titre_et_totaux_des_six_mesures(charge):
    lignes = FaitSituationLigne.objects.filter(chargement=charge)
    lignes.update(attributs={"pilier_simandou": "1"})
    lignes.filter(pk=lignes.first().pk).update(attributs={})
    d = repartitions(resoudre_filtres({}, "chaine_depense"))
    assert [a["axe"] for a in d["axes"]][:2] == ["pilier", "titre"]
    pilier = _axe(d, "pilier")
    assert pilier["disponible"]
    assert any(p["libelle"] == "Pilier non renseigné" for p in pilier["parts"])
    assert any(p["code"] != "?" for p in pilier["parts"])
    for mesure in ("credit", "engage", "liquide", "ordonnance", "vbp", "paye"):
        assert sum(p[mesure] for p in pilier["parts"]) == sum(p[mesure] for p in _axe(d, "titre")["parts"])
    filtre = repartitions(resoudre_filtres({"nature": "investissement"}, "chaine_depense"))
    titre5 = next(p for p in _axe(d, "titre")["parts"] if p["code"] == "5")
    for mesure in ("credit", "engage", "liquide", "ordonnance", "vbp", "paye"):
        assert sum(p[mesure] for p in _axe(filtre, "pilier")["parts"]) == titre5[mesure]


def test_pilier_absent_signale_indisponible(charge):
    FaitSituationLigne.objects.filter(chargement=charge).update(attributs={})
    assert not _axe(repartitions(resoudre_filtres({}, "chaine_depense")), "pilier")["disponible"]
