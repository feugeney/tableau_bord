"""Filtres à critères multiples de la page Dépenses (ministère, programme, titre, fonction, pilier, BAS,
zone, source de financement, bailleur)."""

import pytest
from rest_framework.exceptions import ValidationError

from apps.core.filtres import resoudre_filtres
from apps.depense import services
from apps.depense.criteres import options
from apps.depense.models import FaitEngagement, FaitSituationLigne


def _f(**params):
    return resoudre_filtres(
        {k: ",".join(v) if isinstance(v, (list, tuple)) else v for k, v in params.items()}, "chaine_depense"
    )


def test_un_filtre_qui_retient_tout_retrouve_les_vues_mart(charge):
    """Recalcul depuis les tables de faits = vues mart, bloc par bloc."""
    sources = sorted(
        set(FaitSituationLigne.objects.filter(chargement=charge).values_list("source_financement", flat=True))
    )
    base, tout = _f(), _f(sources=sources)
    a, b = services.indicateurs(base), services.indicateurs(tout)
    for cle in (
        "credit_actuel",
        "credit_engage",
        "montant_liquide",
        "montant_ordonnance",
        "montant_paye",
        "nb_engagements",
    ):
        assert a[cle] == b[cle], cle
    assert a["paiement"] == b["paiement"]
    assert services.restes_a_payer_anciennete(base) == services.restes_a_payer_anciennete(tout)
    assert services.procedures(base) == services.procedures(tout)
    assert services.beneficiaires(base) == services.beneficiaires(tout)


def test_criteres_cumules_et_valeurs_multiples(charge):
    lignes = FaitSituationLigne.objects.filter(chargement=charge)
    sections = sorted(set(lignes.values_list("section_id", flat=True)))[:2]
    attendu = sum(l.credit_actuel for l in lignes if l.section_id in sections and l.titre == "2")
    i = services.indicateurs(_f(ministeres=sections, titres=["2"]))
    assert i["credit_actuel"] == attendu
    # Plusieurs valeurs d'un même critère : OU.
    tous_titres = services.indicateurs(_f(ministeres=sections))
    assert tous_titres["credit_actuel"] == sum(l.credit_actuel for l in lignes if l.section_id in sections)


def test_engagements_filtres_par_la_ligne_budgetaire(charge):
    """Le pilier n'existe que sur la ligne : l'engagement de même imputation est retenu."""
    lignes = FaitSituationLigne.objects.filter(chargement=charge)
    piliers = {l.attributs.get("pillier simandou") for l in lignes} - {None, ""}
    assert piliers, "le classeur d'essai porte un pilier Simandou"
    pilier = sorted(piliers)[0]
    avec = services.indicateurs(_f(piliers=[pilier]))
    attendu = sum(l.credit_actuel for l in lignes if l.attributs.get("pillier simandou") == pilier)
    assert avec["credit_actuel"] == attendu
    assert avec["nb_engagements"] <= FaitEngagement.objects.filter(chargement=charge).count()
    # Aucun engagement retenu pour un pilier inexistant.
    assert services.indicateurs(_f(piliers=["inexistant"]))["nb_engagements"] == 0


def test_options_des_criteres(charge):
    d = {c["cle"]: c for c in options(_f())["criteres"]}
    assert set(d) == {
        "ministeres",
        "programmes",
        "titres",
        "fonctions",
        "piliers",
        "types_budget",
        "zones",
        "sources",
        "bailleurs",
    }
    assert d["ministeres"]["disponible"] and d["ministeres"]["valeurs"]
    # Absent de l'extraction Excel : signalé, pas proposé vide.
    assert not d["programmes"]["disponible"] and "Oracle" in d["programmes"]["raison"]
    # La zone, elle, se lit dans le code de sous-section (6e chiffre).
    assert all(v["code"] in "0123456" for v in d["zones"]["valeurs"])


def test_valeurs_trop_nombreuses_refusees(db):
    with pytest.raises(ValidationError):
        resoudre_filtres({"bailleurs": ",".join(str(i) for i in range(300))}, "chaine_depense")


def test_api_depense_filtree(charge):
    from tests.test_api import client_pour, utilisateur

    client = client_pour(utilisateur("cabinet", "ministre_cabinet"))
    r = client.get("/api/v1/depense/indicateurs/", {"titres": "2"})
    assert r.status_code == 200
    complet = client.get("/api/v1/depense/indicateurs/").json()["data"]["credit_actuel"]
    assert r.json()["data"]["credit_actuel"] < complet
    assert client.get("/api/v1/depense/criteres/").status_code == 200


@pytest.mark.parametrize(
    "attributs",
    [
        {"pillier simandou": "Sante et Bien-etre"},  # extraction Excel
        {"pilier_simandou": "5"},  # ancienne extraction Oracle (identifiant)
        {"pillier simandou": "Santé et Bien-être"},  # extraction Oracle (libellé TC_PILLIER_SIMANDOU)
    ],
)
def test_pilier_ramene_a_sa_forme_de_reference(charge, attributs):
    FaitSituationLigne.objects.filter(chargement=charge).update(attributs=attributs)
    tous = services.indicateurs(_f())["credit_actuel"]
    assert services.indicateurs(_f(piliers=["Sante et Bien-etre"]))["credit_actuel"] == tous
    assert [p["libelle"] for p in services.simandou(_f())["piliers"]] == ["Santé et bien-être"]
