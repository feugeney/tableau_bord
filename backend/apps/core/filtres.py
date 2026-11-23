"""Paramètres communs des requêtes : exercice, date_situation, nature, section, paiement."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from django.conf import settings
from django.db import connection
from rest_framework.exceptions import ValidationError

from apps.referentiels.models import NATURE_VERS_TITRE

from .models import Source, StatutChargement

# Critères multiples de la page Dépenses (paramètres d'URL, valeurs séparées par des virgules).
CRITERES = (
    "ministeres",
    "programmes",
    "titres",
    "fonctions",
    "piliers",
    "types_budget",
    "zones",
    "sources",
    "bailleurs",
)


@dataclass
class Filtres:
    exercice: Optional[int]
    date_situation: Optional[date]
    nature: Optional[str] = None
    section: Optional[str] = None
    # Payé enregistré dans la Chaîne Dépense (« brut ») par défaut, décision du 21/11/2026 ; « ajuste » sur demande.
    paiement: str = "brut"
    criteres: dict = field(default_factory=dict)

    @property
    def titre(self) -> Optional[str]:
        return NATURE_VERS_TITRE.get(self.nature) if self.nature else None

    def cle_cache(self) -> str:
        criteres = ";".join(f"{k}={','.join(v)}" for k, v in sorted(self.criteres.items()) if v)
        return f"{self.exercice}:{self.date_situation}:{self.nature}:{self.section}:{self.paiement}:{criteres}"

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
        # Critères multiples présents dans toutes les tables (ministère, titre) ; les autres : apps.depense.criteres.
        for cle, colonne, actif in (("ministeres", "section_code", avec_section), ("titres", "titre", avec_titre)):
            valeurs = self.criteres.get(cle) if actif else None
            if valeurs:
                clauses.append(f"{p}{colonne} IN ({', '.join(['%s'] * len(valeurs))})")
                params.extend(valeurs)
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
        situations = c.fetchall()
        if settings.TDB_EXERCICE_TEST:
            situations = [(e, d) for e, d in situations if e == settings.TDB_EXERCICE_TEST]
        return situations


def resoudre_filtres(params, source_code: str) -> Filtres:
    nature = params.get("nature") or None
    if nature and nature not in NATURE_VERS_TITRE:
        raise ValidationError({"nature": f"Valeurs admises : {', '.join(NATURE_VERS_TITRE)}"})
    paiement = params.get("paiement") or "brut"
    if paiement not in ("ajuste", "brut"):
        raise ValidationError({"paiement": "Valeurs admises : ajuste, brut"})
    try:
        exercice = int(params["exercice"]) if params.get("exercice") else None
        date_situation = date.fromisoformat(params["date_situation"]) if params.get("date_situation") else None
    except ValueError as exc:
        raise ValidationError({"detail": f"Paramètre invalide : {exc}"}) from exc

    situations = dernieres_situations(source_code)
    if settings.TDB_EXERCICE_TEST:
        if exercice is not None and exercice != settings.TDB_EXERCICE_TEST:
            raise ValidationError({"exercice": f"Test limité à l'exercice {settings.TDB_EXERCICE_TEST}."})
        exercice = settings.TDB_EXERCICE_TEST
    if exercice is None and situations:
        exercice = situations[0][0]
    if date_situation is None:
        date_situation = next((d for e, d in situations if e == exercice), None)
    elif (exercice, date_situation) not in situations:
        date_situation = None
    criteres = {}
    for cle in CRITERES:
        valeurs = tuple(sorted({v.strip() for v in (params.get(cle) or "").split(",") if v.strip()}))
        if len(valeurs) > 200 or any(len(v) > 80 for v in valeurs):
            raise ValidationError({cle: "Trop de valeurs ou valeur trop longue."})
        if valeurs:
            criteres[cle] = valeurs
    return Filtres(exercice, date_situation, nature, params.get("section") or None, paiement, criteres)


def statut_source(source_code: str) -> str:
    s = Source.objects.filter(code=source_code).values_list("statut", flat=True).first()
    return s or "non_raccorde"


def a_des_donnees(source_code: str) -> bool:
    return Source.objects.filter(code=source_code, chargements__statut=StatutChargement.SUCCES).exists()
