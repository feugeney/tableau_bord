"""Collecte automatisée par dépôt de fichiers (SFTP).

Chaque source a son dossier `DEPOT_ROOT/<code>/`. Les partenaires y déposent leurs extractions par SFTP ;
la relève périodique charge chaque fichier avec le connecteur de la source, puis le retire du dépôt : la
copie conservée est celle de la zone brute, rattachée au chargement.
"""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

from django.conf import settings

from apps.core.models import Chargement, Source, StatutChargement

logger = logging.getLogger(__name__)

EXTENSIONS = (".xlsx", ".csv", ".xml", ".json")
DOSSIER_EN_COURS = ".encours"


def racine() -> Path:
    return Path(settings.DEPOT_ROOT)


def preparer_dossiers() -> None:
    for code in Source.objects.values_list("code", flat=True):
        (racine() / code).mkdir(parents=True, exist_ok=True)


def _candidats(dossier: Path, maintenant: float) -> list[Path]:
    """Fichiers complets : extension admise, ni lien ni fichier caché, inchangés depuis le délai de stabilité."""
    fichiers = []
    for f in sorted(dossier.iterdir()):
        if f.is_symlink() or not f.is_file() or f.name.startswith(".") or f.suffix.lower() not in EXTENSIONS:
            continue
        if maintenant - f.stat().st_mtime < settings.DEPOT_STABILITE_SECONDES:
            continue  # transfert peut-être en cours
        fichiers.append(f)
    return fichiers


def _refuser(source: Source, nom: str, motif: str) -> Chargement:
    return Chargement.objects.create(
        source=source,
        fichier=nom,
        statut=StatutChargement.ECHEC,
        message_erreur=motif,
        detail={"origine": "depot"},
    )


def relever(maintenant: float | None = None) -> list[dict]:
    """Charge les fichiers déposés ; renvoie un compte rendu par fichier."""
    from etl.connecteurs import fabrique

    maintenant = time.time() if maintenant is None else maintenant
    preparer_dossiers()
    resultats = []
    for source in Source.objects.all():
        dossier = racine() / source.code
        for f in _candidats(dossier, maintenant):
            # Prise en charge exclusive : deux relèves simultanées ne traitent pas le même fichier.
            en_cours = dossier / DOSSIER_EN_COURS / f"{uuid.uuid4().hex[:8]}-{f.name}"
            en_cours.parent.mkdir(exist_ok=True)
            try:
                f.rename(en_cours)
            except OSError:
                continue
            try:
                if en_cours.stat().st_size > settings.IMPORT_TAILLE_MAX:
                    ch = _refuser(source, f.name, "Fichier trop volumineux.")
                else:
                    connecteur = fabrique.connecteur_pour(source, fichier=en_cours, nom_fichier=f.name)
                    connecteur.origine = "depot"
                    ch = connecteur.executer()
            except Exception as exc:  # le fichier suivant doit être traité quoi qu'il arrive
                logger.exception("Relève du dépôt %s : %s", source.code, f.name)
                ch = _refuser(source, f.name, f"{type(exc).__name__} : {exc}")
            finally:
                try:
                    en_cours.unlink(missing_ok=True)
                except OSError:
                    logger.warning("Fichier de dépôt non supprimé : %s", en_cours)
            resultats.append({"source": source.code, "fichier": f.name, "chargement": ch.pk, "statut": ch.statut})
    return resultats
