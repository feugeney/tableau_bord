"""Portefeuille de l'État (SYSOP) : EPA et sociétés publiques ; transferts réels de la Chaîne Dépense (titre 4)."""

from __future__ import annotations

from django.db.models import Count, Sum

from apps.core import regles
from apps.core.domaines import bloc, chargements_actifs, depense, somme
from apps.core.filtres import Filtres
from apps.referentiels.models import TypeOrganisme

from .models import FaitDividende, FaitGouvernance, FaitSanteFinanciere, FaitSubventionEpa

LIBELLES_SANTE = dict(FaitSanteFinanciere.STATUTS)


def page(f: Filtres) -> dict:
    ids = chargements_actifs("sysop", f)
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
        "sante": [{"statut": k, "libelle": v, "nombre": statuts.get(k, 0)} for k, v in FaitSanteFinanciere.STATUTS],
        "gouvernance": {
            "etats_non_transmis": gouv.filter(etats_financiers_transmis=False).count(),
            "mandats_expires": gouv.aggregate(n=Sum("mandats_expires"))["n"] or 0,
            "organismes_mandats_expires": [
                {"libelle": g.organisme.nom, "mandats_expires": g.mandats_expires}
                for g in gouv.filter(mandats_expires__gt=0).order_by("-mandats_expires", "organisme__nom")[:10]
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
