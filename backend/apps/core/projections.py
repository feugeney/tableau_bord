"""Projections de fin d'exercice.

À partir d'une série mensuelle et de la date de situation, on prolonge le réalisé jusqu'au 31 décembre par
des méthodes simples et vérifiables, et on présente une fourchette plutôt qu'un chiffre unique :

- **rythme moyen** : le rythme quotidien observé depuis le début de l'exécution se poursuit ;
- **rythme récent** : le rythme des trois derniers mois complets se poursuit ;
- **profil de l'exercice précédent** : même accélération de fin d'année que l'an passé (si l'historique existe).

Ces méthodes ne connaissent ni la saisonnalité (sauf la troisième) ni les décisions à venir. La vérification
rétrospective mesure ce qu'elles auraient donné si on les avait appliquées plus tôt dans l'exercice.
"""

from __future__ import annotations

import calendar
from collections.abc import Mapping
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

D0 = Decimal(0)
JOURS_MINIMUM = 60  # en deçà de deux mois d'exécution, pas de projection
MOIS_RECENTS = 3


def _fin_mois(d: date) -> date:
    return d.replace(day=calendar.monthrange(d.year, d.month)[1])


def _debut_mois(d: date) -> date:
    return d.replace(day=1)


def _mois_suivant(d: date) -> date:
    return (_debut_mois(d) + timedelta(days=32)).replace(day=1)


def _serie_exercice(serie: Mapping[date, Decimal], jour: date, exercice: int) -> dict[date, Decimal]:
    """Mois de l'exercice jusqu'au mois de la situation (clés ramenées au premier du mois)."""
    resultat: dict[date, Decimal] = {}
    for mois, montant in serie.items():
        m = _debut_mois(mois)
        if m.year == exercice and m <= jour:
            resultat[m] = resultat.get(m, D0) + Decimal(montant or 0)
    return resultat


def _cumul_au(serie: Mapping[date, Decimal], jour: date) -> Decimal:
    """Cumul au jour donné ; le mois en cours est compté au prorata des jours écoulés."""
    total = D0
    for mois, montant in serie.items():
        if _fin_mois(mois) <= jour:
            total += montant
        elif mois <= jour:
            total += montant * jour.day / calendar.monthrange(jour.year, jour.month)[1]
    return total


def _methodes(serie: dict[date, Decimal], jour: date, base: Decimal, horizon: date) -> dict[str, Decimal]:
    """Valeur projetée à `horizon` par méthode, à partir du cumul `base` constaté au `jour`."""
    actifs = [m for m, v in serie.items() if v > 0]
    if not actifs or base <= 0:
        return {}
    debut = min(actifs)
    ecoules = (jour - debut).days + 1
    restants = (horizon - jour).days
    if ecoules < JOURS_MINIMUM or restants < 0:
        return {}
    cumul_serie = sum(serie.values(), D0)
    resultat = {"rythme_moyen": base + cumul_serie / ecoules * restants}
    # Mois entièrement écoulés à la date du constat (un mois sans mouvement compte pour zéro).
    complets, m = [], debut
    while _fin_mois(m) <= jour:
        complets.append(m)
        m = _mois_suivant(m)
    recents = complets[-MOIS_RECENTS:]
    if len(recents) >= 2:
        jours = sum(calendar.monthrange(x.year, x.month)[1] for x in recents)
        resultat["rythme_recent"] = base + sum((serie.get(x, D0) for x in recents), D0) / jours * restants
    return resultat


def _profil_precedent(precedent: Mapping[date, Decimal], jour: date, base: Decimal) -> Optional[Decimal]:
    """Applique au réalisé le rapport « fin d'année / même date » de l'exercice précédent."""
    if not precedent:
        return None
    annee = min(m.year for m in precedent)
    serie = {_debut_mois(m): Decimal(v or 0) for m, v in precedent.items() if m.year == annee}
    try:
        meme_jour = jour.replace(year=annee)
    except ValueError:  # 29 février
        meme_jour = jour.replace(year=annee, day=28)
    a_date = _cumul_au(serie, meme_jour)
    total = sum(serie.values(), D0)
    if a_date <= 0 or total <= 0:
        return None
    return base * total / a_date


def _retrospective(serie: dict[date, Decimal], jour: date) -> list[dict]:
    """Ce que les méthodes auraient prévu pour aujourd'hui, appliquées à la fin de chaque mois passé."""
    realise = sum(serie.values(), D0)
    resultat = []
    for mois in sorted(serie):
        coupe = _fin_mois(mois)
        if coupe >= jour or _debut_mois(mois) == _debut_mois(jour):
            continue
        passe = {m: v for m, v in serie.items() if m <= mois}
        methodes = _methodes(passe, coupe, sum(passe.values(), D0), jour)
        if not methodes or realise <= 0:
            continue
        prevu = sum(methodes.values(), D0) / len(methodes)
        resultat.append({"arrete_au": coupe, "prevu": prevu, "realise": realise, "ecart": (prevu - realise) / realise})
    return resultat


def projeter(
    serie: Mapping[date, Decimal],
    date_situation: date,
    cible: Optional[Decimal] = None,
    realise: Optional[Decimal] = None,
    precedent: Optional[Mapping[date, Decimal]] = None,
    plafonner: bool = False,
    exercice: Optional[int] = None,
) -> dict:
    """Projection au 31 décembre de l'exercice (par défaut, l'année de `date_situation`).

    Une situation datée après le 31 décembre de l'exercice (période complémentaire, exercice passé) ne donne
    lieu à aucune projection : le réalisé est celui de l'exercice.

    `serie` : montant par mois (non cumulé). `realise` : cumul officiel à la date de situation, s'il diffère
    de la somme de la série (celle-ci ne sert alors qu'au rythme). `cible` : crédits ou objectif annuel.
    `plafonner` : la projection ne dépasse pas la cible (on n'engage pas au-delà des crédits ouverts).
    """
    exercice = exercice or date_situation.year
    fin = date(exercice, 12, 31)
    termine = date_situation > fin
    mois = _serie_exercice(serie, min(date_situation, fin), exercice)
    base = Decimal(realise) if realise is not None else sum(mois.values(), D0)
    methodes = {} if termine else _methodes(mois, date_situation, base, fin)
    profil = _profil_precedent(precedent or {}, date_situation, base) if methodes else None
    if profil is not None:
        methodes["profil_precedent"] = profil
    plafonne = False
    if plafonner and cible is not None:
        plafond = max(Decimal(cible), base)
        plafonne = any(v > plafond for v in methodes.values())
        methodes = {k: min(v, plafond) for k, v in methodes.items()}

    sortie = {
        "date_situation": date_situation,
        "horizon": fin,
        "realise": base,
        "cible": cible,
        "taux_realise": base / cible if cible else None,
        "fiable": bool(methodes),
        "plafonne": plafonne,
        "methodes": methodes,
        "bas": None,
        "haut": None,
        "central": None,
        "taux_bas": None,
        "taux_haut": None,
        "trajectoire": [],
        "retrospective": [],
        "erreur_moyenne": None,
    }
    # Trajectoire constatée : zéro au début du premier mois, cumul à chaque fin de mois, puis date de situation.
    cumul, points = D0, []
    if mois:
        points.append({"date": min(mois), "realise": D0, "bas": None, "haut": None})
    for m in sorted(mois):
        cumul += mois[m]
        fin_m = _fin_mois(m)
        if fin_m < min(date_situation, fin):
            points.append({"date": fin_m, "realise": cumul, "bas": None, "haut": None})
    if not methodes:
        if mois:
            points.append({"date": min(date_situation, fin), "realise": base, "bas": None, "haut": None})
        sortie["trajectoire"] = points
        if termine:
            sortie["motif"] = "Exercice terminé : le montant constaté est celui de l'exercice, sans projection."
        elif base <= 0:
            sortie["motif"] = "Aucune exécution constatée."
        else:
            sortie["motif"] = "Moins de deux mois d'exécution : projection non établie."
        return sortie

    bas, haut = min(methodes.values()), max(methodes.values())
    central = sum(methodes.values(), D0) / len(methodes)
    points.append({"date": date_situation, "realise": base, "bas": base, "haut": base})
    restants = (fin - date_situation).days
    m = _debut_mois(date_situation)
    while restants > 0 and m.year == date_situation.year:
        fin_m = _fin_mois(m)
        if fin_m > date_situation:
            part = Decimal((fin_m - date_situation).days) / restants
            points.append(
                {"date": fin_m, "realise": None, "bas": base + (bas - base) * part, "haut": base + (haut - base) * part}
            )
        m = _mois_suivant(m)
    retro = _retrospective(mois, date_situation)
    sortie.update(
        bas=bas,
        haut=haut,
        central=central,
        taux_bas=bas / cible if cible else None,
        taux_haut=haut / cible if cible else None,
        trajectoire=points,
        retrospective=retro,
        erreur_moyenne=(sum((abs(x["ecart"]) for x in retro), D0) / len(retro)) if retro else None,
    )
    return sortie
