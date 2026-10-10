"""Marchés publics (Telemo) : indicateurs et contrôles de cohérence entre les flux F3, F4 et F5.

Le rapprochement se fait sur le numéro de réservation (F3 ↔ F4) et le numéro d'immatriculation (F4 ↔ F5).
Les engagements passés en procédure « marché public » viennent de la Chaîne Dépense (réel).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db import connection
from django.db.models import Count, F, Q, Sum

from apps.core import regles
from apps.core.domaines import bloc, chargements_actifs, filtres_source
from apps.core.filtres import Filtres

from .models import FaitMarche, FaitPaiementMarche, FaitReservationCredit

LIBELLES_MODES = dict(FaitMarche.MODES)
LIBELLES_TYPES = dict(FaitMarche.TYPES)
LIBELLES_STATUTS = dict(FaitMarche.STATUTS)
D0 = Decimal(0)
JOURS_RESERVATION_INUTILISEE = 90


def _jeu(f: Filtres):
    ids = chargements_actifs("telemo", f)
    return (
        FaitMarche.objects.filter(chargement_id__in=ids),
        FaitReservationCredit.objects.filter(chargement_id__in=ids),
        FaitPaiementMarche.objects.filter(chargement_id__in=ids),
    )


def _moyenne(valeurs: list[int]) -> float | None:
    return round(sum(valeurs) / len(valeurs), 1) if valeurs else None


def _repartition(qs, champ: str, libelles: dict, total: Decimal) -> list[dict]:
    lignes = qs.values(champ).annotate(nombre=Count("id"), montant=Sum("montant_ttc")).order_by("-montant")
    return [
        {
            "code": x[champ],
            "libelle": libelles.get(x[champ], x[champ]),
            "nombre": x["nombre"],
            "montant": x["montant"] or D0,
            "part": regles.taux(x["montant"] or D0, total),
        }
        for x in lignes
    ]


def controles(f: Filtres) -> dict:
    """Cohérence F3 (réservations) ↔ F4 (marchés) ↔ F5 (paiements)."""
    marches, reservations, paiements = _jeu(f)
    reserves = {r.numero_reservation: r for r in reservations}
    payes: dict[str, Decimal] = defaultdict(lambda: D0)
    premiers: dict[str, date] = {}
    for p in paiements.only("numero_immatriculation", "montant_paiement", "date_paiement"):
        payes[p.numero_immatriculation] += p.montant_paiement
        if p.numero_immatriculation not in premiers or p.date_paiement < premiers[p.numero_immatriculation]:
            premiers[p.numero_immatriculation] = p.date_paiement

    sans_reservation, depasse_reservation, sur_payes = [], [], []
    delais_reservation, delais_paiement = [], []
    immatricules = set()
    for m in marches:
        immatricules.add(m.numero_immatriculation)
        r = reserves.get(m.numero_reservation) if m.numero_reservation else None
        ligne = {
            "numero": m.numero_immatriculation,
            "autorite_contractante": m.autorite_contractante,
            "objet": m.objet,
            "montant_ttc": m.montant_ttc,
        }
        if r is None:
            sans_reservation.append(ligne)
        else:
            if m.montant_ttc > r.montant_reserve:
                depasse_reservation.append(
                    {**ligne, "montant_reserve": r.montant_reserve, "ecart": m.montant_ttc - r.montant_reserve}
                )
            if r.date_visa and m.date_immatriculation:
                delais_reservation.append((m.date_immatriculation - r.date_visa).days)
        paye = payes.get(m.numero_immatriculation, D0)
        if paye > m.montant_ttc + m.montant_avenants:
            sur_payes.append({**ligne, "montant_paye": paye, "ecart": paye - m.montant_ttc - m.montant_avenants})
        if m.numero_immatriculation in premiers and m.date_immatriculation:
            delais_paiement.append((premiers[m.numero_immatriculation] - m.date_immatriculation).days)

    utilisees = set(marches.exclude(numero_reservation="").values_list("numero_reservation", flat=True))
    limite = f.date_situation - timedelta(days=JOURS_RESERVATION_INUTILISEE)
    inutilisees = [r for n, r in reserves.items() if n not in utilisees and r.date_visa and r.date_visa <= limite]
    orphelins = [n for n in payes if n not in immatricules]
    return {
        "marches_sans_reservation": {
            "nombre": len(sans_reservation),
            "montant": sum((x["montant_ttc"] for x in sans_reservation), D0),
            "exemples": sans_reservation[:10],
        },
        "marches_depassant_reservation": {
            "nombre": len(depasse_reservation),
            "montant": sum((x["ecart"] for x in depasse_reservation), D0),
            "exemples": sorted(depasse_reservation, key=lambda x: -x["ecart"])[:10],
        },
        "paiements_superieurs": {
            "nombre": len(sur_payes),
            "montant": sum((x["ecart"] for x in sur_payes), D0),
            "exemples": sorted(sur_payes, key=lambda x: -x["ecart"])[:10],
        },
        "paiements_sans_marche": {"nombre": len(orphelins), "montant": sum((payes[n] for n in orphelins), D0)},
        "reservations_inutilisees": {
            "nombre": len(inutilisees),
            "montant": sum((r.montant_reserve for r in inutilisees), D0),
            "jours": JOURS_RESERVATION_INUTILISEE,
        },
        "delai_reservation_immatriculation": _moyenne(delais_reservation),
        "delai_immatriculation_paiement": _moyenne(delais_paiement),
        "montant_paye": sum(payes.values(), D0),
    }


def engagements_marches(exercice: int | None) -> dict:
    """Engagements passés en procédure « marché public » (Chaîne Dépense, réel)."""
    fc = filtres_source("chaine_depense", exercice)
    if fc is None:
        return bloc("chaine_depense", None, None)
    where, params = fc.where()
    with connection.cursor() as c:
        c.execute(
            f"""SELECT procedure, sum(nb_engagements), sum(montant_engage), sum(montant_ordonnance), sum(montant_paye)
                FROM mart.mv_depense_procedures WHERE {where} AND procedure ILIKE %s
                GROUP BY procedure ORDER BY 3 DESC""",
            params + ["% MP%"],
        )
        lignes = [
            {"libelle": p, "nb_engagements": int(n), "montant_engage": e, "montant_ordonnance": o, "montant_paye": py}
            for p, n, e, o, py in c.fetchall()
        ]
    total = {k: sum((x[k] for x in lignes), D0) for k in ("montant_engage", "montant_ordonnance", "montant_paye")}
    return bloc(
        "chaine_depense",
        fc,
        {"procedures": lignes, **total, "nb_engagements": sum(x["nb_engagements"] for x in lignes)},
    )


def page(f: Filtres) -> dict:
    marches, reservations, _ = _jeu(f)
    total = marches.aggregate(t=Sum("montant_ttc"))["t"] or D0
    ht = marches.aggregate(t=Sum("montant_ht"))["t"] or D0
    ed = marches.filter(mode_passation="entente_directe").aggregate(t=Sum("montant_ttc"))["t"] or D0
    part_ed = regles.taux(ed, total)
    avenants = marches.aggregate(t=Sum("montant_avenants"))["t"] or D0
    ctl = controles(f)
    seuil_delai = regles.parametre("delai_passation_max_jours")

    mensuel = (
        marches.exclude(date_immatriculation=None)
        .values(mois=F("date_immatriculation__month"))
        .annotate(nombre=Count("id"), montant=Sum("montant_ttc"))
        .order_by("mois")
    )
    par_autorite = list(
        marches.values(libelle=F("autorite_contractante"))
        .annotate(nombre=Count("id"), montant=Sum("montant_ttc"))
        .order_by("-montant")[:10]
    )
    # Titulaires regroupés par NIF (une même entreprise peut apparaître sous plusieurs raisons sociales).
    titulaires = list(
        marches.exclude(titulaire_nif="")
        .values("titulaire_nif")
        .annotate(nombre=Count("id"), montant=Sum("montant_ttc"))
        .order_by("-montant")[:10]
    )
    noms = dict(marches.exclude(titulaire_nif="").values_list("titulaire_nif", "titulaire"))
    for t in titulaires:
        t["libelle"] = noms.get(t["titulaire_nif"], t["titulaire_nif"])
        t["part"] = regles.taux(t["montant"], total)
    statuts = {
        s["statut"]: s for s in marches.values("statut").annotate(nombre=Count("id"), montant=Sum("montant_ttc"))
    }
    return {
        "indicateurs": {
            "nb_marches": marches.count(),
            "montant_ttc": total,
            "montant_ht": ht,
            "part_entente_directe": part_ed,
            "entente_directe_excessive": regles.entente_directe_excessive(part_ed),
            "seuil_entente_directe": regles.parametre("entente_directe_part_max"),
            "montant_reserve": reservations.aggregate(t=Sum("montant_reserve"))["t"] or D0,
            "nb_reservations": reservations.count(),
            "delai_reservation_immatriculation": ctl["delai_reservation_immatriculation"],
            "delai_immatriculation_paiement": ctl["delai_immatriculation_paiement"],
            "seuil_delai": seuil_delai,
            "montant_paye": ctl["montant_paye"],
            "taux_paiement": regles.taux(ctl["montant_paye"], total),
            "montant_avenants": avenants,
            "part_avenants": regles.taux(avenants, total),
            "nb_en_execution": marches.filter(statut="en_execution").count(),
            "nb_recours": marches.filter(recours=True).count(),
        },
        "controles": ctl,
        "par_mode": _repartition(marches, "mode_passation", LIBELLES_MODES, total),
        "par_type": _repartition(marches, "type_marche", LIBELLES_TYPES, total),
        "par_statut": [
            {
                "code": c,
                "libelle": lib,
                "nombre": statuts.get(c, {}).get("nombre", 0),
                "montant": statuts.get(c, {}).get("montant") or D0,
            }
            for c, lib in FaitMarche.STATUTS
        ],
        "mensuel": list(mensuel),
        "par_autorite": par_autorite,
        "titulaires": titulaires,
        "engagements_chaine_depense": engagements_marches(f.exercice),
    }


def entente_directe(f: Filtres) -> dict:
    marches, _, _ = _jeu(f)
    agg = marches.aggregate(
        total=Sum("montant_ttc"),
        ed=Sum("montant_ttc", filter=Q(mode_passation="entente_directe")),
        nb=Count("id", filter=Q(mode_passation="entente_directe")),
    )
    part = regles.taux(agg["ed"] or D0, agg["total"] or D0)
    return {
        "part": part,
        "montant": agg["ed"] or D0,
        "nombre": agg["nb"],
        "excessive": regles.entente_directe_excessive(part),
    }
