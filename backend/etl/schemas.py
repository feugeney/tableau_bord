"""Schémas JSON des flux, déduits du mapping de colonnes (core_mapping_colonnes).

Le schéma est le contrat d'échange remis au partenaire : clés attendues, types, champs obligatoires.
Il sert aussi à écarter les lignes non conformes d'un flux JSON avant leur chargement.
"""

from __future__ import annotations

from jsonschema import Draft202012Validator

from apps.core.models import MappingColonnes

from .connecteurs.generique import modele_fait

BROUILLON = "https://json-schema.org/draft/2020-12/schema"
# Les sources transmettent parfois un nombre sous forme de texte : les deux sont admis, la conversion tranche.
TYPES = {
    "texte": ["string", "number", "integer"],
    "code": ["string", "number", "integer"],
    "montant": ["number", "string"],
    "taux": ["number", "string"],
    "entier": ["integer", "number", "string"],
    "date": ["string"],
    "booleen": ["boolean", "string", "integer"],
}


def schema_flux(source_code: str, table: str) -> dict:
    mappings = list(MappingColonnes.objects.filter(source__code=source_code, table_cible=table).order_by("id"))
    champs = {f.name: f for f in modele_fait(table)._meta.get_fields() if getattr(f, "concrete", False)}
    proprietes, obligatoires = {}, []
    for m in mappings:
        p: dict = {"type": list(TYPES[m.type_donnee])}
        if m.type_donnee == "date":
            p["format"] = "date"
            p["description"] = "Date ISO 8601 (AAAA-MM-JJ)"
        elif m.type_donnee == "montant":
            p["description"] = "Montant en francs guinéens (GNF)"
        choix = getattr(champs.get(m.champ_cible), "choices", None)
        if choix:
            p["description"] = "Valeurs admises (code ou libellé) : " + " ; ".join(f"{c} ({l})" for c, l in choix)
        if m.obligatoire:
            obligatoires.append(m.colonne_source)
        else:
            p["type"].append("null")
        proprietes[m.colonne_source] = p
    return {
        "$schema": BROUILLON,
        "$id": f"urn:mefb:entrepot:flux:{source_code}:{table}",
        "title": f"{source_code} → {table}",
        "type": "object",
        "properties": proprietes,
        "required": obligatoires,
        # Les champs supplémentaires sont acceptés et ignorés (ils ne sont pas repris dans l'entrepôt).
        "additionalProperties": True,
    }


def schemas_source(source_code: str) -> dict[str, dict]:
    tables = (
        MappingColonnes.objects.filter(source__code=source_code)
        .order_by("table_cible")
        .values_list("table_cible", flat=True)
        .distinct()
    )
    return {t: schema_flux(source_code, t) for t in tables}


def filtrer(source_code: str, table: str, lignes: list) -> tuple[list[dict], int]:
    """Sépare les lignes conformes au schéma des autres ; renvoie (lignes conformes, nombre écarté)."""
    validateur = Draft202012Validator(schema_flux(source_code, table))
    conformes = [x for x in lignes if isinstance(x, dict) and validateur.is_valid(x)]
    return conformes, len(lignes) - len(conformes)
