"""Paramètres communs des requêtes : exercice, date_situation, nature, section, paiement."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from django.db import connection
from rest_framework.exceptions import ValidationError

from apps.referentiels.models import NATURE_VERS_TITRE

from .models import Source, StatutChargement


@dataclass
class Filtres:
    exercice: Optional[int]
    date_situation: Optional[date]
    nature: Optional[str] = None
    section: Optional[str] = None
    paiement: str = "ajuste"

    @property
    def titre(self) -> Optional[str]:
        return NATURE_VERS_TITRE.get(self.nature) if self.nature else None

    def cle_cache(self) -> str:
        return f"{self.exercice}:{self.date_situation}:{self.nature}:{self.section}:{self.paiement}"

    def where(self, alias: str = "", avec_section: bool = True, avec_titre: bool = True) -> tuple[str, list]:
        """Clause WHERE paramétrée pour les vues mart (colonnes exercice, date_situation, section_code, titre)."""
        p = f"{alias}." if alias else ""
        clauses = [f"{p}exercice = %s", f"{p}date_situation = %s"]
        params: list = [self.exercice, self.date_situation]
        if avec_section and self.section:
            clauses.append(f"{p}section_code = %s")
            params.append(self.section)
        if avec_titre and self.titre:
            clauses.append(f"{p}titre = %s")
            params.append(self.titre)
        return " AND ".join(clauses), params


def dernieres_situations(source_code: str) -> list[tuple[int, date]]:
    """(exercice, date_situation) des chargements actifs d'une source, du plus récent au plus ancien."""
    with connection.cursor() as c:
        c.execute(
            """SELECT DISTINCT a.exercice, a.date_situation
               FROM mart.v_chargements_actifs a JOIN public.core_source s ON s.id = a.source_id
               WHERE s.code = %s AND a.date_situation IS NOT NULL
               ORDER BY a.exercice DESC, a.date_situation DESC""",
            [source_code],
        )
        return c.fetchall()


def resoudre_filtres(params, source_code: str) -> Filtres:
    nature = params.get("nature") or None
    if nature and nature not in NATURE_VERS_TITRE:
        raise ValidationError({"nature": f"Valeurs admises : {', '.join(NATURE_VERS_TITRE)}"})
    paiement = params.get("paiement") or "ajuste"
    if paiement not in ("ajuste", "brut"):
        raise ValidationError({"paiement": "Valeurs admises : ajuste, brut"})
    try:
        exercice = int(params["exercice"]) if params.get("exercice") else None
        date_situation = date.fromisoformat(params["date_situation"]) if params.get("date_situation") else None
    except ValueError as exc:
        raise ValidationError({"detail": f"Paramètre invalide : {exc}"}) from exc

    situations = dernieres_situations(source_code)
    if exercice is None and situations:
        exercice = situations[0][0]
    if date_situation is None:
        date_situation = next((d for e, d in situations if e == exercice), None)
    return Filtres(exercice, date_situation, nature, params.get("section") or None, paiement)


def statut_source(source_code: str) -> str:
    s = Source.objects.filter(code=source_code).values_list("statut", flat=True).first()
    return s or "non_raccorde"


def a_des_donnees(source_code: str) -> bool:
    return Source.objects.filter(code=source_code, chargements__statut=StatutChargement.SUCCES).exists()
