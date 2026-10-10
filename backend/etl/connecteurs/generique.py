"""Connecteurs génériques (SAFIG, SYDONIA, SCIE, dette, SIGPIP, FUGAS, SICOM, SYSOP, Telemo).

Le mapping colonne source → champ cible est lu dans core_mapping_colonnes : brancher une nouvelle
extraction ne demande aucune modification de code.

Une source à plusieurs tables (ex. Telemo : réservations F3, marchés F4, paiements F5) se charge en
**un seul chargement** : classeur à un onglet par table (colonne « onglet » du mapping), ou plusieurs
points d'accès d'API. Des chargements séparés à la même date de situation se masqueraient les uns les autres.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

import pandas as pd
from django.apps import apps
from django.conf import settings
from django.db import models

from apps.core.models import MappingColonnes, Source
from apps.referentiels.models import CodeLibelle, RefOrganisme, RefSection, RefSousSection, RefZoneGeographique
from etl import nettoyage as n

from .base import BaseConnector, ErreurChargement, RapportValidation

TAILLE_LOT = 2000
CHAMPS_TECHNIQUES = {"id", "exercice", "date_situation", "source", "chargement"}
# Référentiels communs fermés : un code inconnu rejette la ligne au lieu de créer une entrée.
REFERENTIELS_FERMES = (RefSection, RefSousSection, RefOrganisme, RefZoneGeographique)


def modele_fait(table_cible: str) -> type[models.Model]:
    """Retrouve le modèle Django d'une table de faits à partir de son nom (« fait_paie »)."""
    for m in apps.get_models():
        if m._meta.db_table.split('"."')[-1] == table_cible:
            return m
    raise ErreurChargement(f"Table cible inconnue : {table_cible}")


def valeur_choix(f: models.Field, v, synonymes: dict[str, str]) -> str:
    """Valeur d'un champ à liste fermée : code, libellé ou synonyme métier (« Gré à gré » → entente_directe)."""
    brut = n.libelle(v)
    cle = n.cle_entete(brut)
    for code, libelle in f.choices:
        if cle in (n.cle_entete(code), n.cle_entete(libelle)):
            return code
    if cle in synonymes:
        return synonymes[cle]
    raise ValueError(f"Valeur inconnue pour {f.name} : {brut!r}")


class MappingMixin:
    """Validation et chargement pilotés par core_mapping_colonnes, pour une ou plusieurs tables."""

    def mappings(self, table: str) -> list[MappingColonnes]:
        return list(MappingColonnes.objects.filter(source__code=self.source_code, table_cible=table))

    def appliquer_mapping(self, df: pd.DataFrame, table: str) -> pd.DataFrame:
        maps = self.mappings(table)
        if not maps:
            raise ErreurChargement(
                f"Aucun mapping configuré pour {self.source_code} → {table} (core_mapping_colonnes)."
            )
        par_cle = {n.cle_entete(c): c for c in df.columns}
        colonnes = {}
        for m in maps:
            col = par_cle.get(n.cle_entete(m.colonne_source))
            if col is not None:
                colonnes[col] = m.champ_cible
        self._types = getattr(self, "_types", {})
        self._obligatoires = getattr(self, "_obligatoires", {})
        self._types[table] = {m.champ_cible: m.type_donnee for m in maps}
        self._obligatoires[table] = [m.champ_cible for m in maps if m.obligatoire]
        return df[list(colonnes)].rename(columns=colonnes)

    def validate(self) -> RapportValidation:
        rapport = RapportValidation()
        if not self.donnees:
            rapport.ajouter(
                "tables",
                "Au moins une table reconnue",
                "bloquant",
                False,
                detail={"message": "aucun onglet ni flux ne correspond au mapping"},
            )
        for table, df in self.donnees.items():
            manquants = [c for c in self._obligatoires.get(table, []) if c not in df.columns]
            rapport.ajouter(
                f"colonnes_obligatoires_{table}",
                f"Colonnes obligatoires de {table}",
                "bloquant",
                not manquants,
                detail={"message": ", ".join(manquants) or "ok"},
            )
        for table, nombre in getattr(self, "_hors_schema", {}).items():
            rapport.ajouter(
                f"schema_json_{table}",
                f"Lignes conformes au schéma JSON de {table}",
                "avertissement",
                nombre == 0,
                nombre=nombre,
                detail={"message": "lignes écartées : clé obligatoire absente ou type inattendu"},
            )
        for champ in ("exercice", "date_situation"):
            if getattr(self, champ) is None:
                rapport.ajouter(
                    champ, f"{champ} déterminé", "bloquant", False, detail={"message": "à saisir à l'import"}
                )
        return rapport

    def lignes_json(self, table: str, lignes: list) -> pd.DataFrame:
        """Lignes JSON d'une table : celles qui ne respectent pas le schéma du flux sont écartées et comptées."""
        from etl import schemas

        conformes, ecartees = schemas.filtrer(self.source_code, table, lignes)
        self._hors_schema = getattr(self, "_hors_schema", {})
        self._hors_schema[table] = ecartees
        if not conformes:  # flux sans ligne (ex. aucun paiement encore) : table vide, pas une erreur de structure
            return pd.DataFrame(columns=[m.colonne_source for m in self.mappings(table)], dtype=object)
        return pd.DataFrame(conformes, dtype=object)

    def _convertir(self, table: str, f: models.Field, v, synonymes: dict):
        if f.choices and not n.est_vide(v):
            return valeur_choix(f, v, synonymes.get(f.name, {}))
        t = self._types.get(table, {}).get(f.name, "texte")
        if t == "montant":
            return n.montant_ou_zero(v)
        if t == "entier":
            return None if n.est_vide(v) and f.null else (0 if n.est_vide(v) else int(float(v)))
        if t == "taux":
            return None if n.est_vide(v) else n.montant_ou_zero(v)
        if t == "date":
            return n.date_(v)
        if t == "booleen":
            return str(v).strip().lower() in {"1", "oui", "true", "vrai", "o", "x"}
        if t == "code":
            return n.code(v)
        return n.libelle(v)

    def load(self, chargement) -> int:
        return sum(self._charger_table(chargement, table, df) for table, df in self.donnees.items())

    def _charger_table(self, chargement, table: str, df: pd.DataFrame) -> int:
        modele = modele_fait(table)
        synonymes = getattr(modele, "SYNONYMES", {})
        refs: dict[str, dict[str, int]] = {}
        champs = {f.name: f for f in modele._meta.get_fields() if getattr(f, "concrete", False)}
        objets, rejetees = [], 0
        for r in df.to_dict("records"):
            valeurs = {}
            try:
                for champ, v in r.items():
                    f = champs.get(champ)
                    if f is None or champ in CHAMPS_TECHNIQUES:
                        continue
                    if isinstance(f, models.ForeignKey):
                        valeurs[f.attname] = self._resoudre_ref(f, n.code(v), refs)
                    else:
                        valeurs[champ] = self._convertir(table, f, v, synonymes)
            except ValueError:
                rejetees += 1
                continue
            objets.append(
                modele(
                    exercice=self.exercice,
                    date_situation=self.date_situation,
                    source_id=chargement.source_id,
                    chargement_id=chargement.id,
                    **valeurs,
                )
            )
        modele.objects.bulk_create(objets, batch_size=TAILLE_LOT)
        hors_schema = getattr(self, "_hors_schema", {}).get(table, 0)
        self.comptes[table] = {
            "lues": len(df) + hors_schema,
            "chargees": len(objets),
            "rejetees": rejetees + hors_schema,
        }
        return len(objets)

    @staticmethod
    def _resoudre_ref(f: models.ForeignKey, code: str, cache: dict) -> Optional[object]:
        """Code → clé du référentiel ; les référentiels propres au domaine sont complétés à la volée."""
        if not code:
            return None
        cible = f.related_model
        champ_cle = f.target_field.name
        memo = cache.setdefault(f.name, {})
        if code not in memo:
            if issubclass(cible, CodeLibelle) and not issubclass(cible, REFERENTIELS_FERMES):
                obj, _ = cible.objects.get_or_create(code=code)
            else:
                obj = cible.objects.filter(**{champ_cle: code}).first()
                if obj is None:
                    raise ValueError(f"{cible.__name__} inconnu : {code}")
            memo[code] = getattr(obj, champ_cle)
        return memo[code]

    def _dates_par_defaut(self, nom: str) -> None:
        exercice_nom, date_nom = n.infos_nom_fichier(nom)
        self.date_situation = self.date_situation or date_nom
        if self.exercice is None:
            self.exercice = exercice_nom or (self.date_situation.year if self.date_situation else None)


class ExcelGenericConnector(MappingMixin, BaseConnector):
    """Fichier Excel, CSV, XML ou JSON.

    - `table_cible` donné : une table (onglet `onglet`, sinon le premier) ;
    - `table_cible` absent : toutes les tables dont le mapping désigne un onglet présent dans le classeur.
    - XML : une table, un élément par ligne sous la racine, un sous-élément par colonne.
    - JSON : une liste d'objets (une table), ou un objet {clé: liste} à plusieurs tables, la clé étant le nom
      de la table, celui de l'onglet du mapping ou le chemin du flux d'API (réponses archivées rejouables).
    """

    def __init__(
        self,
        source_code: str,
        table_cible: Optional[str],
        fichier,
        onglet: Optional[str] = None,
        nom_fichier: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.source_code = source_code
        self.table_cible = table_cible
        self.fichier = fichier
        self.onglet = onglet
        self._nom = nom_fichier or Path(str(fichier)).name

    @property
    def nom_fichier(self) -> str:
        return self._nom

    def extract(self) -> dict[str, pd.DataFrame]:
        self._dates_par_defaut(self._nom)
        if self._nom.lower().endswith(".csv"):
            if not self.table_cible:
                raise ErreurChargement("Un fichier CSV ne contient qu'une table : préciser la table cible.")
            df = pd.read_csv(self.fichier, dtype=object, sep=None, engine="python", encoding="utf-8-sig")
            return {self.table_cible: self.appliquer_mapping(df.dropna(how="all"), self.table_cible)}
        if self._nom.lower().endswith(".xml"):
            if not self.table_cible:
                raise ErreurChargement("Un fichier XML ne contient qu'une table : préciser la table cible.")
            try:
                df = pd.read_xml(self.fichier, parser="etree", dtype=object)
            except Exception as exc:
                raise ErreurChargement(f"Fichier XML illisible : {exc}") from exc
            return {self.table_cible: self.appliquer_mapping(df.dropna(how="all"), self.table_cible)}
        if self._nom.lower().endswith(".json"):
            return self._extraire_json()
        if self.table_cible:
            df = pd.read_excel(self.fichier, sheet_name=self.onglet or 0, dtype=object, engine="openpyxl")
            return {self.table_cible: self.appliquer_mapping(df.dropna(how="all"), self.table_cible)}
        tables = (
            MappingColonnes.objects.filter(source__code=self.source_code)
            .exclude(onglet="")
            .values_list("table_cible", "onglet")
            .distinct()
        )
        donnees = {}
        with pd.ExcelFile(self.fichier, engine="openpyxl") as classeur:
            onglets = {n.cle_entete(o): o for o in classeur.sheet_names}
            for table, onglet in tables:
                feuille = onglets.get(n.cle_entete(onglet))
                if feuille and table not in donnees:
                    df = classeur.parse(feuille, dtype=object).dropna(how="all")
                    donnees[table] = self.appliquer_mapping(df, table)
        return donnees

    def _extraire_json(self) -> dict[str, pd.DataFrame]:
        try:
            if hasattr(self.fichier, "read"):
                contenu = json.load(self.fichier)
                self.fichier.seek(0)
            else:
                contenu = json.loads(Path(self.fichier).read_text(encoding="utf-8-sig"))
        except ValueError as exc:
            raise ErreurChargement(f"Fichier JSON illisible : {exc}") from exc
        if isinstance(contenu, list):
            if not self.table_cible:
                raise ErreurChargement("Une liste JSON ne contient qu'une table : préciser la table cible.")
            par_table = {self.table_cible: contenu}
        elif isinstance(contenu, dict):
            # Clés reconnues : table cible, onglet du mapping, chemin du flux d'API.
            source = Source.objects.get(code=self.source_code)
            alias = {n.cle_entete(f["chemin"]): f["table_cible"] for f in (source.configuration or {}).get("flux", [])}
            for table, onglet in MappingColonnes.objects.filter(source=source).values_list("table_cible", "onglet"):
                alias[n.cle_entete(table)] = table
                if onglet:
                    alias[n.cle_entete(onglet)] = table
            par_table = {
                alias[n.cle_entete(cle)]: lignes
                for cle, lignes in contenu.items()
                if isinstance(lignes, list) and n.cle_entete(cle) in alias
            }
        else:
            raise ErreurChargement("JSON inattendu : liste d'objets ou objet {table: liste} attendu.")
        return {t: self.appliquer_mapping(self.lignes_json(t, lignes), t) for t, lignes in par_table.items()}


class ApiConnector(MappingMixin, BaseConnector):
    """API REST JSON en lecture (ex. Telemo). Un « flux » = un point d'accès → une table cible.

    Configuration de la source : {"url": "https://…", "flux": [{"chemin": "/marches", "table_cible": "fait_marche"}]}.
    L'URL et le jeton peuvent venir des variables d'environnement (SOURCES_EXTERNES) ; le jeton n'est jamais
    stocké en base. Réponses acceptées : liste d'objets, ou objet {"results" | "data" | "items": […], "next": url}.
    """

    CLES_LISTE = ("results", "data", "items")
    PAGES_MAX = 500

    def __init__(self, source_code: str, configuration: dict, **kwargs):
        super().__init__(**kwargs)
        self.source_code = source_code
        self.configuration = configuration or {}
        externe = settings.SOURCES_EXTERNES.get(source_code, {})
        self.url = (self.configuration.get("url") or externe.get("url") or "").rstrip("/")
        self.jeton = externe.get("jeton") or os.environ.get(self.configuration.get("variable_jeton", ""), "")

    @property
    def nom_fichier(self) -> str:
        return f"api://{self.source_code}"

    def _lire(self, url: str) -> list[dict]:
        lignes, pages = [], 0
        while url and pages < self.PAGES_MAX:
            requete = urllib.request.Request(url, headers={"Accept": "application/json"})
            if self.jeton:
                requete.add_header("Authorization", f"Bearer {self.jeton}")
            with urllib.request.urlopen(requete, timeout=60) as r:  # noqa: S310 (URL configurée par la DNSI)
                corps = json.loads(r.read().decode("utf-8"))
            if isinstance(corps, list):
                lignes.extend(corps)
                break
            cle = next((k for k in self.CLES_LISTE if isinstance(corps.get(k), list)), None)
            if cle is None:
                raise ErreurChargement(f"Réponse d'API inattendue ({url}) : liste d'objets attendue.")
            lignes.extend(corps[cle])
            url, pages = corps.get("next"), pages + 1
        return lignes

    def extract(self) -> dict[str, pd.DataFrame]:
        if not self.url:
            raise ErreurChargement(f"URL de l'API {self.source_code} non configurée.")
        flux = self.configuration.get("flux") or []
        if not flux:
            raise ErreurChargement("Aucun flux configuré (clé « flux » de la configuration).")
        if self.date_situation is None:
            from datetime import date

            self.date_situation = date.today()
        self.exercice = self.exercice or self.date_situation.year
        donnees, recu = {}, {}
        for f in flux:
            params = {"exercice": self.exercice, **(f.get("parametres") or {})}
            url = f"{self.url}{f['chemin']}?{urllib.parse.urlencode(params)}"
            recu[f["chemin"]] = self._lire(url)
            df = self.lignes_json(f["table_cible"], recu[f["chemin"]])
            donnees[f["table_cible"]] = self.appliquer_mapping(df, f["table_cible"])
        self._recu = recu
        return donnees

    def source_brute(self):
        recu = getattr(self, "_recu", None)
        if recu is None:
            return None
        return json.dumps(recu, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8"), ".json"


class PostgresConnector(MappingMixin, BaseConnector):
    """SICOM et SYSOP (PostgreSQL, exploités par la DNSI) : compte en lecture seule."""

    def __init__(self, source_code: str, table_cible: str, requete: str, **kwargs):
        super().__init__(**kwargs)
        self.source_code = source_code
        self.table_cible = table_cible
        self.requete = requete

    @property
    def nom_fichier(self) -> str:
        return f"postgresql://{self.source_code}/{self.table_cible}"

    def extract(self) -> dict[str, pd.DataFrame]:
        import psycopg

        url = settings.SOURCES_EXTERNES.get(self.source_code, {}).get("url")
        if not url:
            raise ErreurChargement(f"Connexion PostgreSQL {self.source_code} non configurée.")
        with psycopg.connect(url, options="-c default_transaction_read_only=on") as cnx:
            with cnx.cursor() as cur:
                cur.execute(self.requete, {"exercice": self.exercice})
                cols = [d.name for d in cur.description]
                df = pd.DataFrame(cur.fetchall(), columns=cols, dtype=object)
        if self.exercice is None and self.date_situation:
            self.exercice = self.date_situation.year
        return {self.table_cible: self.appliquer_mapping(df, self.table_cible)}


def source_existe(code: str) -> bool:
    return Source.objects.filter(code=code).exists()
