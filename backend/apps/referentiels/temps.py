"""Alimentation de la dimension temps (ref.dim_temps)."""

from __future__ import annotations

import calendar
from datetime import date, timedelta

from .models import DimTemps

MOIS = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]
PREMIERE_ANNEE = 2015
ANNEES_A_VENIR = 5


def ligne(d: date) -> DimTemps:
    trimestre = (d.month - 1) // 3 + 1
    return DimTemps(
        date=d,
        annee=d.year,
        semestre=1 if d.month <= 6 else 2,
        trimestre=trimestre,
        mois=d.month,
        jour=d.day,
        semaine_iso=d.isocalendar()[1],
        jour_semaine=d.isoweekday(),
        libelle_mois=f"{MOIS[d.month - 1]} {d.year}",
        libelle_trimestre=f"T{trimestre} {d.year}",
        fin_de_mois=d.day == calendar.monthrange(d.year, d.month)[1],
    )


def assurer_calendrier(debut: int, fin: int) -> int:
    """Crée les jours manquants des années `debut` à `fin` incluses ; renvoie le nombre de jours ajoutés."""
    presentes = set(
        DimTemps.objects.filter(annee__gte=debut, annee__lte=fin).values_list("annee", flat=True).distinct()
    )
    jours = []
    for annee in range(debut, fin + 1):
        if annee in presentes:
            continue
        d = date(annee, 1, 1)
        while d.year == annee:
            jours.append(ligne(d))
            d += timedelta(days=1)
    DimTemps.objects.bulk_create(jours, batch_size=2000, ignore_conflicts=True)
    return len(jours)


def initialiser_calendrier() -> int:
    return assurer_calendrier(PREMIERE_ANNEE, date.today().year + ANNEES_A_VENIR)
