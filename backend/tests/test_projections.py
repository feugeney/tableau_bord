"""Chantier 5 de la mise en conformité : projections de fin d'exercice."""

from datetime import date
from decimal import Decimal

import pytest

from apps.core.projections import projeter

MD = Decimal(10**9)


def serie(annee, **mois):
    noms = ["jan", "fev", "mar", "avr", "mai", "jun", "jul", "aou", "sep", "oct", "nov", "dec"]
    return {date(annee, noms.index(k) + 1, 1): Decimal(str(v)) * MD for k, v in mois.items()}


# ------------------------------------------------------------------ méthodes


def test_rythme_constant_projete_le_total_annuel():
    """Dix par jour toute l'année : toutes les méthodes retrouvent 3 650 au 31 décembre."""
    s = {date(2026, m, 1): Decimal(10 * j) for m, j in zip(range(1, 8), (31, 28, 31, 30, 31, 30, 31))}
    p = projeter(s, date(2026, 7, 31), cible=Decimal(7300))
    assert p["fiable"] and p["realise"] == 2120
    assert p["methodes"]["rythme_moyen"] == pytest.approx(Decimal(3650))
    assert p["methodes"]["rythme_recent"] == pytest.approx(Decimal(3650))
    assert p["bas"] == pytest.approx(p["haut"]) and float(p["taux_haut"]) == pytest.approx(0.5)
    assert float(p["taux_realise"]) == pytest.approx(2120 / 7300)
    assert all(abs(x["ecart"]) < Decimal("1e-9") for x in p["retrospective"]) and p["erreur_moyenne"] < Decimal("1e-9")


def test_execution_commencee_en_cours_d_annee():
    """Le rythme se mesure depuis le premier mois d'exécution, pas depuis le 1er janvier."""
    s = serie(2026, avr=48.9, mai=377.5, jun=1518.6, jul=752.2, aou=528.6)
    p = projeter(s, date(2026, 8, 16), cible=25141 * MD)
    realise = Decimal("3225.8") * MD
    assert p["realise"] == realise
    # 138 jours du 1er avril au 16 août ; 137 jours restants.
    assert p["methodes"]["rythme_moyen"] == pytest.approx(realise + realise / 138 * 137)
    # Trois derniers mois complets : mai, juin, juillet (92 jours).
    recent = (Decimal("377.5") + Decimal("1518.6") + Decimal("752.2")) * MD / 92
    assert p["methodes"]["rythme_recent"] == pytest.approx(realise + recent * 137)
    assert p["bas"] == p["methodes"]["rythme_moyen"] and p["haut"] == p["methodes"]["rythme_recent"]
    assert 0.25 < p["taux_bas"] < p["taux_haut"] < 0.30  # loin des crédits


def test_cumul_officiel_distinct_de_la_serie():
    """La série ne donne que le rythme ; le point de départ est le cumul officiel de la situation."""
    s = serie(2026, jan=100, fev=100, mar=100, avr=100)
    p = projeter(s, date(2026, 4, 30), realise=Decimal(450) * MD)
    additionnel = Decimal(400) * MD / 120 * 245
    assert p["realise"] == 450 * MD and p["methodes"]["rythme_moyen"] == pytest.approx(450 * MD + additionnel)


def test_profil_de_l_exercice_precedent():
    """Avec l'historique, l'accélération de fin d'année de l'an passé est appliquée."""
    precedent = serie(
        2025, jan=10, fev=10, mar=10, avr=10, mai=10, jun=10, jul=10, aou=10, sep=10, oct=10, nov=40, dec=60
    )
    s = serie(2026, jan=12, fev=12, mar=12, avr=12, mai=12, jun=12)
    p = projeter(s, date(2026, 6, 30), precedent=precedent)
    # En 2025 : 60 au 30 juin, 200 en fin d'année → coefficient 200 / 60.
    assert p["methodes"]["profil_precedent"] == pytest.approx(Decimal(72) * MD * 200 / 60)
    assert p["haut"] == p["methodes"]["profil_precedent"] > p["methodes"]["rythme_moyen"]
    assert set(p["methodes"]) == {"rythme_moyen", "rythme_recent", "profil_precedent"}


def test_mois_sans_mouvement_compte_dans_le_rythme_recent():
    s = serie(2026, jan=90, fev=0, mar=0, avr=0, mai=10)
    p = projeter(s, date(2026, 5, 31))
    assert p["methodes"]["rythme_recent"] < p["methodes"]["rythme_moyen"]  # février à avril : rien


# ------------------------------------------------------------------ cas limites


@pytest.mark.parametrize(
    "s, jour, motif",
    [
        ({}, date(2026, 6, 30), "Aucune exécution"),
        (serie(2026, jun=0), date(2026, 6, 30), "Aucune exécution"),
        (serie(2026, jul=50), date(2026, 8, 16), "Moins de deux mois"),
    ],
)
def test_projection_non_etablie(s, jour, motif):
    p = projeter(s, jour, cible=Decimal(1000) * MD)
    assert not p["fiable"] and motif in p["motif"]
    assert p["bas"] is None and p["haut"] is None and p["taux_haut"] is None and p["retrospective"] == []


def test_mois_hors_exercice_ignores():
    """Période complémentaire et mois postérieurs à la situation : hors du calcul."""
    s = {**serie(2026, jan=10, fev=10, mar=10), date(2027, 1, 1): 999 * MD, date(2026, 9, 1): 999 * MD}
    assert projeter(s, date(2026, 3, 31))["realise"] == 30 * MD


def test_fin_d_exercice():
    """Au 31 décembre, la projection est le réalisé."""
    s = serie(
        2026, **{m: 10 for m in ["jan", "fev", "mar", "avr", "mai", "jun", "jul", "aou", "sep", "oct", "nov", "dec"]}
    )
    p = projeter(s, date(2026, 12, 31))
    assert p["bas"] == p["haut"] == p["realise"] == 120 * MD
    assert p["trajectoire"][-1] == {"date": date(2026, 12, 31), "realise": 120 * MD, "bas": 120 * MD, "haut": 120 * MD}


def test_exercice_passe_sans_projection():
    """Situation datée après le 31 décembre de l'exercice (période complémentaire) : pas de projection."""
    s = {**serie(2025, oct=10, nov=20, dec=30), date(2026, 1, 1): 5 * MD}
    p = projeter(s, date(2026, 9, 15), cible=100 * MD, exercice=2025)
    assert not p["fiable"] and "Exercice terminé" in p["motif"] and p["horizon"] == date(2025, 12, 31)
    assert p["realise"] == 60 * MD and float(p["taux_realise"]) == pytest.approx(0.6)  # janvier 2026 hors exercice
    assert p["trajectoire"][-1] == {"date": date(2025, 12, 31), "realise": 60 * MD, "bas": None, "haut": None}
    assert [x["date"] for x in p["trajectoire"]] == [
        date(2025, 10, 1),
        date(2025, 10, 31),
        date(2025, 11, 30),
        date(2025, 12, 31),
    ]


# ------------------------------------------------------------------ trajectoire et vérification


def test_trajectoire():
    s = serie(2026, avr=48.9, mai=377.5, jun=1518.6, jul=752.2, aou=528.6)
    p = projeter(s, date(2026, 8, 16))
    t = p["trajectoire"]
    assert [x["date"] for x in t] == [
        date(2026, 4, 1),
        date(2026, 4, 30),
        date(2026, 5, 31),
        date(2026, 6, 30),
        date(2026, 7, 31),
        date(2026, 8, 16),
        date(2026, 8, 31),
        date(2026, 9, 30),
        date(2026, 10, 31),
        date(2026, 11, 30),
        date(2026, 12, 31),
    ]
    constate = [x["realise"] for x in t[:6]]
    assert constate[0] == 0 and constate == sorted(constate) and constate[-1] == p["realise"]
    jonction = t[5]
    assert jonction["bas"] == jonction["haut"] == p["realise"]  # les deux tracés se rejoignent à la date de situation
    assert all(x["realise"] is None for x in t[6:])
    assert t[-1]["bas"] == pytest.approx(p["bas"]) and t[-1]["haut"] == pytest.approx(p["haut"])
    assert [x["bas"] for x in t[5:]] == sorted(x["bas"] for x in t[5:])


def test_verification_retrospective():
    """Appliquée à la fin de chaque mois passé, la méthode est comparée au réalisé du 16 août."""
    s = serie(2026, avr=48.9, mai=377.5, jun=1518.6, jul=752.2, aou=528.6)
    p = projeter(s, date(2026, 8, 16))
    r = {x["arrete_au"]: x for x in p["retrospective"]}
    # Fin avril : 30 jours d'exécution, pas de projection. Fin mai : 61 jours, la méthode s'applique.
    assert set(r) == {date(2026, 5, 31), date(2026, 6, 30), date(2026, 7, 31)}
    assert not projeter(s, date(2026, 4, 30))["fiable"]
    fin_juin = Decimal("1945.0") * MD
    moyen = fin_juin + fin_juin / 91 * 47
    # Fin juin, les trois mois complets (avril à juin) sont toute l'exécution : les deux méthodes coïncident.
    assert r[date(2026, 6, 30)]["prevu"] == pytest.approx(moyen)
    # Fin juillet, le rythme récent (mai à juillet) est plus soutenu que le rythme moyen.
    fin_juillet = Decimal("2697.2") * MD
    attendu = (fin_juillet / 122 + (Decimal("2648.3") * MD) / 92) / 2 * 16 + fin_juillet
    assert r[date(2026, 7, 31)]["prevu"] == pytest.approx(attendu)
    assert r[date(2026, 6, 30)]["realise"] == p["realise"]
    ecarts = [float(x["ecart"]) for x in p["retrospective"]]
    assert float(p["erreur_moyenne"]) == pytest.approx(sum(abs(e) for e in ecarts) / 3)
    assert all(e < 0 for e in ecarts)  # l'exécution a accéléré : la méthode sous-estimait


def test_plafonnement_aux_credits():
    """Un engagement projeté ne dépasse pas les crédits ouverts ; une recette peut dépasser son objectif."""
    s = serie(2026, jan=30, fev=30, mar=30, avr=30)
    libre = projeter(s, date(2026, 4, 30), cible=200 * MD)
    assert libre["haut"] > 200 * MD and not libre["plafonne"]
    borne = projeter(s, date(2026, 4, 30), cible=200 * MD, plafonner=True)
    assert borne["bas"] == borne["haut"] == 200 * MD and borne["plafonne"] and borne["taux_haut"] == 1
    assert borne["trajectoire"][-1]["haut"] == 200 * MD
    # Crédits déjà dépassés : la projection ne redescend pas sous le réalisé.
    depasse = projeter(s, date(2026, 4, 30), cible=100 * MD, plafonner=True)
    assert depasse["bas"] == depasse["haut"] == depasse["realise"] == 120 * MD


# ------------------------------------------------------------------ pages et alerte


@pytest.mark.django_db
def test_projection_des_depenses(charge):
    from apps.core.filtres import resoudre_filtres
    from apps.depense import services

    f = resoudre_filtres({}, "chaine_depense")
    p = services.projection(f)
    e = p["engagement"]
    i = services.indicateurs(f)
    assert e["realise"] == i["credit_engage"] and e["cible"] == i["credit_actuel"]
    assert e["horizon"] == date(f.exercice, 12, 31) and float(p["seuil"]) == 0.8
    if e["fiable"]:
        assert e["realise"] <= e["bas"] <= e["haut"] <= max(e["cible"], e["realise"])
        assert all(
            m["taux_projete"] is None or m["taux_projete"] <= 1 or m["credit_engage"] > m["credit_actuel"]
            for m in p["ministeres"]
        )
        taux = [m["taux_projete"] for m in p["ministeres"] if m["taux_projete"] is not None]
        assert taux == sorted(taux)  # les plus éloignés de leurs crédits d'abord
    else:
        assert e["motif"] and p["ministeres"] == [] and not p["sous_le_seuil"]


@pytest.mark.django_db
def test_point_d_acces_et_droits(charge):
    from .test_api import client_pour, utilisateur

    cabinet = client_pour(utilisateur("cab", "ministre_cabinet"))
    r = cabinet.get("/api/v1/depense/projection/")
    assert r.status_code == 200 and r.data["meta"]["source"] == "chaine_depense"
    assert set(r.data["data"]) >= {"engagement", "ministeres", "seuil", "sous_le_seuil"}
    assert isinstance(r.data["data"]["engagement"]["trajectoire"], list)
    autre = client_pour(utilisateur("dir", "directeur", ["dette"]))
    assert autre.get("/api/v1/depense/projection/").status_code == 403


@pytest.mark.django_db
def test_alerte_de_projection(charge, monkeypatch):
    from apps.core.alertes import evaluer_alertes
    from apps.core.models import Alerte
    from apps.depense import services

    def fausse(taux_bas, taux_haut, sous_le_seuil):
        cible = 1000 * MD
        return {
            "engagement": {
                "taux_bas": Decimal(str(taux_bas)),
                "taux_haut": Decimal(str(taux_haut)),
                "taux_realise": Decimal("0.13"),
                "cible": cible,
                "haut": cible * Decimal(str(taux_haut)),
            },
            "seuil": 0.8,
            "sous_le_seuil": sous_le_seuil,
            "nb_ministeres_sous_le_seuil": 7,
        }

    monkeypatch.setattr(services, "projection", lambda f: fausse(0.26, 0.29, True))
    evaluer_alertes(domaine="depense")
    a = Alerte.objects.get(regle__code="depense_projection_faible")
    assert a.severite == "vigilance" and a.titre == "Engagement projeté entre 26 % et 29 % des crédits au 31 décembre"
    assert "710,0 Mds" in a.message and "7 ministère(s)" in a.message and "13 %" in a.message
    monkeypatch.setattr(services, "projection", lambda f: fausse(0.85, 0.92, False))
    evaluer_alertes(domaine="depense")
    assert not Alerte.objects.filter(regle__code="depense_projection_faible", statut="ouverte").exists()


@pytest.mark.django_db
def test_projection_des_recettes_sans_objectif_annuel():
    """Recettes d'illustration : huit mois chargés, donc pas d'objectif annuel connu."""
    from apps.core import demo
    from apps.core.filtres import Filtres
    from apps.recettes_fiscales import services

    demo.generer(sources=["safig"])
    from apps.core.domaines import filtres_source

    f = filtres_source("safig")
    assert isinstance(f, Filtres)
    p = services.page(f)["projection"]
    assert p["fiable"] and p["cible"] is None and p["taux_haut"] is None
    assert p["realise"] < p["bas"] <= p["haut"] and p["horizon"].month == 12
