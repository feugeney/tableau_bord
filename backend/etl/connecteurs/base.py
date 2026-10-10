"""Interface commune des connecteurs : extract() → validate() → load()."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Optional

import pandas as pd
from django.db import transaction
from django.utils import timezone

from apps.core.models import Chargement, Source, StatutChargement

logger = logging.getLogger(__name__)


class ErreurChargement(Exception):
    """Échec bloquant : le chargement est rejeté et rien n'est écrit dans l'entrepôt."""


@dataclass
class Controle:
    code: str
    libelle: str
    niveau: str  # bloquant | avertissement | info
    reussi: bool
    valeur: Optional[Decimal] = None
    nombre: Optional[int] = None
    detail: dict = field(default_factory=dict)


@dataclass
class RapportValidation:
    controles: list[Controle] = field(default_factory=list)

    def ajouter(self, *args, **kwargs) -> Controle:
        c = Controle(*args, **kwargs)
        self.controles.append(c)
        return c

    @property
    def bloquants_en_echec(self) -> list[Controle]:
        return [c for c in self.controles if c.niveau == "bloquant" and not c.reussi]

    @property
    def valide(self) -> bool:
        return not self.bloquants_en_echec


class BaseConnector(ABC):
    """Un connecteur par source. Les sous-classes implémentent extract, validate et load.

    `extract()` renvoie un DataFrame par table logique (dict nom → DataFrame) : une
    extraction Chaîne Dépense contient plusieurs onglets ; un connecteur mono-table
    renvoie un dict à une seule entrée.
    """

    source_code: str = ""

    def __init__(self, exercice: Optional[int] = None, date_situation: Optional[date] = None, utilisateur=None):
        self.exercice = exercice
        self.date_situation = date_situation
        self.utilisateur = utilisateur
        self.donnees: dict[str, pd.DataFrame] = {}
        self.rapport = RapportValidation()
        self.comptes: dict[str, dict[str, int]] = {}

    @property
    def nom_fichier(self) -> str:
        return ""

    @abstractmethod
    def extract(self) -> dict[str, pd.DataFrame]: ...

    @abstractmethod
    def validate(self) -> RapportValidation: ...

    @abstractmethod
    def load(self, chargement: Chargement) -> int:
        """Écrit les données dans l'entrepôt ; renvoie le nombre de lignes chargées."""

    def source_brute(self):
        """Ce qui a été reçu, à conserver tel quel : (chemin ou contenu, extension).

        None pour une lecture directe en base (Oracle, PostgreSQL) : il n'y a pas de fichier à archiver.
        """
        fichier = getattr(self, "fichier", None)
        if fichier is None:
            return None
        extension = Path(self.nom_fichier).suffix
        if hasattr(fichier, "read"):
            contenu = fichier.read()
            fichier.seek(0)
            return contenu, extension
        return Path(fichier), extension

    def _archiver(self, chargement: Chargement) -> None:
        """Zone brute : copie du reçu, empreinte, et signalement d'un contenu déjà chargé."""
        from etl import zone_brute

        try:
            brut = self.source_brute()
            if brut is None or (isinstance(brut[0], Path) and not brut[0].is_file()):
                return
            chargement.fichier_archive, chargement.empreinte_sha256 = zone_brute.archiver(self.source_code, *brut)
        except OSError:
            logger.exception("Archivage en zone brute impossible (%s)", self.source_code)
            return
        deja = (
            Chargement.objects.filter(
                source=chargement.source,
                empreinte_sha256=chargement.empreinte_sha256,
                statut=StatutChargement.SUCCES,
            )
            .exclude(pk=chargement.pk)
            .order_by("-debut")
            .values_list("id", flat=True)
            .first()
        )
        if deja:
            chargement.detail["deja_charge"] = deja

    def apres_chargement(self, chargement: Chargement) -> None:
        """Rafraîchissement des vues, invalidation du cache et alertes."""
        from etl.mart import apres_chargement

        apres_chargement(chargement)

    # ------------------------------------------------------------ orchestration

    def executer(self, apercu: bool = False) -> Chargement:
        """Extraction, validation puis (sauf aperçu) chargement transactionnel."""
        source = Source.objects.get(code=self.source_code)
        chargement = Chargement.objects.create(
            source=source,
            fichier=self.nom_fichier,
            utilisateur=self.utilisateur if getattr(self.utilisateur, "pk", None) else None,
        )
        debut = time.monotonic()
        try:
            self.donnees = self.extract()
            chargement.exercice = self.exercice
            chargement.date_situation = self.date_situation
            chargement.lignes_lues = sum(len(df) for df in self.donnees.values())
            self.rapport = self.validate()
            if not self.rapport.valide:
                raise ErreurChargement(
                    " ; ".join(f"{c.libelle} ({c.detail.get('message', '')})" for c in self.rapport.bloquants_en_echec)
                )
            if apercu:
                chargement.statut = StatutChargement.APERCU
            else:
                with transaction.atomic():
                    chargement.lignes_chargees = self.load(chargement)
                    chargement.statut = StatutChargement.SUCCES
                    chargement.save()
                    self._enregistrer_controles(chargement)
        except ErreurChargement as exc:
            chargement.statut = StatutChargement.ECHEC
            chargement.message_erreur = str(exc)
        except Exception as exc:  # erreur technique : tracée, jamais silencieuse
            logger.exception("Chargement %s en échec", self.source_code)
            chargement.statut = StatutChargement.ECHEC
            chargement.message_erreur = f"{type(exc).__name__} : {exc}"
        chargement.lignes_rejetees = sum(c.get("rejetees", 0) for c in self.comptes.values())
        chargement.detail = {
            "comptes": self.comptes,
            "controles": [
                {
                    "code": c.code,
                    "libelle": c.libelle,
                    "niveau": c.niveau,
                    "reussi": c.reussi,
                    "valeur": str(c.valeur) if c.valeur is not None else None,
                    "nombre": c.nombre,
                    "detail": c.detail,
                }
                for c in self.rapport.controles
            ],
        }
        if getattr(self, "origine", None):
            chargement.detail["origine"] = self.origine  # « depot » : fichier relevé dans le dépôt SFTP
        self._archiver(chargement)
        chargement.fin = timezone.now()
        chargement.duree_secondes = round(time.monotonic() - debut, 2)
        chargement.save()
        if not apercu:
            from etl.evenements import chargement_termine

            chargement_termine(chargement)
        if chargement.statut == StatutChargement.SUCCES:
            if chargement.exercice:
                from apps.referentiels.temps import assurer_calendrier

                assurer_calendrier(chargement.exercice, chargement.exercice)
            if source.statut != "reel":
                source.statut = "reel"
                source.save(update_fields=["statut"])
            # Données réelles : les données d'illustration de cette source sont retirées.
            Chargement.objects.filter(source=source, detail__demo=True).delete()
            self.apres_chargement(chargement)
        return chargement

    def _enregistrer_controles(self, chargement: Chargement) -> None:
        from apps.qualite.models import ResultatControle

        ResultatControle.objects.bulk_create(
            ResultatControle(
                chargement=chargement,
                code=c.code,
                libelle=c.libelle,
                niveau=c.niveau,
                reussi=c.reussi,
                valeur=c.valeur,
                nombre=c.nombre,
                detail=c.detail,
            )
            for c in self.rapport.controles
        )
