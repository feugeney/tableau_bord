"""Portefeuille de l'État (SYSOP) : EPA et sociétés publiques ; transferts réels de la Chaîne Dépense (titre 4)."""

from __future__ import annotations

from django.db.models import Count, Q, Sum

from apps.core import regles
from apps.core.domaines import bloc, chargements_actifs, depense, somme
from apps.core.filtres import Filtres
from apps.core.models import Chargement
from apps.referentiels.models import TypeOrganisme

from .models import FaitDividende, FaitGouvernance, FaitSanteFinanciere, FaitSubventionEpa

LIBELLES_SANTE = dict(FaitSanteFinanciere.STATUTS)


def page(f: Filtres) -> dict:
    ids = chargements_actifs("sysop", f)
    chargement = Chargement.objects.filter(pk__in=ids).order_by("-fin", "-id").first()
    reel_sysop = bool(chargement and chargement.detail.get("profil") == "sysop_portefeuille")
    sub = FaitSubventionEpa.objects.filter(chargement_id__in=ids).select_related("organisme")
    div = FaitDividende.objects.filter(chargement_id__in=ids).select_related("organisme")
    sante = FaitSanteFinanciere.objects.filter(chargement_id__in=ids)
    gouv = FaitGouvernance.objects.filter(chargement_id__in=ids).select_related("organisme")
    organismes = list(sante.values("organisme__type").annotate(n=Count("organisme_id", distinct=True)))
    nb = {o["organisme__type"]: o["n"] for o in organismes}
    tot_sub = somme(sub, "prevu", "paye")
    tot_div = somme(div, "vote", "encaisse")
    transmis = gouv.filter(etats_financiers_transmis=True).count()
    fc, transferts = depense(f.exercice, titre="4")
    statuts = {s["statut"]: s["n"] for s in sante.values("statut").annotate(n=Count("id"))}
    couverture = {
        "epa_avec_subvention": sub.values("organisme_id").distinct().count(),
        "societes_avec_dividende": div.values("organisme_id").distinct().count(),
        "resultats_exploitables": sante.filter(resultat__isnull=False).values("organisme_id").distinct().count(),
        "organismes_validation_etablie": transmis,
        "organismes_recenses": sum(nb.values()),
        "obligations_dividendes_connues": False,
    }
    return {
        "indicateurs": {
            "epa": nb.get(TypeOrganisme.EPA, 0),
            "societes": nb.get(TypeOrganisme.SOCIETE, 0),
            "subventions_prevues": tot_sub["prevu"],
            "subventions_payees": tot_sub["paye"],
            "dividendes_votes": tot_div["vote"],
            "dividendes_encaisses": tot_div["encaisse"],
            "taux_dividendes": regles.taux(tot_div["encaisse"], tot_div["vote"]),
            "taux_transmission": regles.taux(transmis, gouv.count()),
        },
        "couverture": couverture,
        "perimetre_transferts": (
            "Ensemble du titre 4 de la Chaîne Dépense ; périmètre plus large que le portefeuille. "
            "Ne pas additionner aux subventions SYSOP."
        ),
        "avertissement_periode": (
            "Le contexte budgétaire utilise une autre date de situation que SYSOP ; "
            "les dates sont indiquées sur chaque bloc."
            if fc and fc.date_situation != f.date_situation
            else None
        ),
        "transferts": bloc(
            "chaine_depense",
            fc,
            (
                None
                if not transferts
                else {
                    "credit_actuel": transferts["credit_actuel"],
                    "montant_ordonnance": transferts["montant_ordonnance"],
                    "montant_paye": transferts["montant_paye"],
                }
            ),
        ),
        "subventions": [
            {"libelle": s.organisme.nom, "prevu": s.prevu, "paye": s.paye} for s in sub.order_by("-prevu")[:10]
        ],
        "dividendes": [
            {"libelle": d.organisme.nom, "vote": d.vote, "encaisse": d.encaisse}
            for d in div.filter(vote__gt=0).order_by("-vote")[:10]
        ],
        "sante": [
            {
                "statut": k,
                "libelle": "Validation non établie" if reel_sysop and k == "non_transmis" else v,
                "nombre": statuts.get(k, 0),
            }
            for k, v in FaitSanteFinanciere.STATUTS
        ],
        "precision_sante": (
            "Couverture des résultats nets XI associés aux états validés. "
            "Un résultat absent ne permet pas de conclure sur la santé financière de l'organisme."
            if reel_sysop
            else None
        ),
        "precision_transmission": (
            "Niveaux 4 et 6 : validation Directeur technique ou Résultat disponible. "
            "Tous les types d'états présents pour un organisme doivent satisfaire cette règle. "
            "Ce taux ne mesure ni la réception de tous les documents attendus ni leur complétude."
            if reel_sysop
            else None
        ),
        "gouvernance": {
            "etats_non_transmis": gouv.filter(etats_financiers_transmis=False).count(),
            "mandats_expires": None if reel_sysop else (gouv.aggregate(n=Sum("mandats_expires"))["n"] or 0),
            "mandats_disponibles": not reel_sysop,
            "organismes_mandats_expires": [
                {"libelle": g.organisme.nom, "mandats_expires": g.mandats_expires}
                for g in (
                    gouv.filter(mandats_expires__gt=0).order_by("-mandats_expires", "organisme__nom")[:10]
                    if not reel_sysop
                    else []
                )
            ],
        },
    }


def dividendes_non_verses(f: Filtres) -> dict:
    div = FaitDividende.objects.filter(chargement_id__in=chargements_actifs("sysop", f), vote__gt=0)
    impayes = [d for d in div if d.encaisse < d.vote]
    return {"nombre": len(impayes), "montant": sum((d.vote - d.encaisse for d in impayes), start=0)}


def sante(f: Filtres) -> dict:
    s = FaitSanteFinanciere.objects.filter(chargement_id__in=chargements_actifs("sysop", f))
    return {
        "deficitaires": s.filter(statut="deficitaire").count(),
        "non_transmis": s.filter(statut="non_transmis").count(),
    }


def recettes_administratives(f: Filtres) -> dict:
    """Recettes › Recettes administratives : dividendes versés à l'État par les sociétés publiques (SYSOP).

    Voté = dividende attendu, arrêté par l'organe délibérant ; encaissé = montant versé au Trésor.
    Une société sans ligne de dividende n'est pas comptée comme débitrice : l'obligation n'est pas connue.
    """
    div = list(
        FaitDividende.objects.filter(chargement_id__in=chargements_actifs("sysop", f))
        .filter(Q(vote__gt=0) | Q(encaisse__gt=0))
        .select_related("organisme", "organisme__tutelle")
    )
    societes = []
    for d in div:
        reste = max(d.vote - d.encaisse, 0)
        statut = "verse" if d.vote and d.encaisse >= d.vote else ("partiel" if d.encaisse > 0 else "non_verse")
        if not d.vote:
            statut = "sans_vote"
        societes.append(
            {
                "libelle": d.organisme.nom,
                "sigle": d.organisme.sigle,
                "tutelle": d.organisme.tutelle.libelle_affiche if d.organisme.tutelle else "",
                "vote": d.vote,
                "encaisse": d.encaisse,
                "reste": reste,
                "taux": regles.taux(d.encaisse, d.vote),
                "statut": statut,
            }
        )
    societes.sort(key=lambda s: (-s["vote"], -s["encaisse"], s["libelle"]))
    vote = sum((s["vote"] for s in societes), 0)
    encaisse = sum((s["encaisse"] for s in societes), 0)
    return {
        "indicateurs": {
            "dividendes_votes": vote,
            "dividendes_encaisses": encaisse,
            "taux_recouvrement": regles.taux(encaisse, vote),
            "reste_a_encaisser": sum((s["reste"] for s in societes), 0),
            "nb_societes": len(societes),
            "nb_non_verses": sum(1 for s in societes if s["statut"] in ("non_verse", "partiel")),
        },
        "societes": societes,
        "perimetre": (
            "Dividendes des sociétés publiques du portefeuille de l'État (SYSOP). Les autres recettes non "
            "fiscales (droits et frais administratifs, redevances, amendes) ne sont pas encore raccordées."
        ),
    }
