"""Zone brute de l'entrepôt : ce qui est reçu d'une source est conservé tel quel.

Chaque fichier (ou réponse d'API) est rangé sous `MEDIA_ROOT/brut/<source>/<empreinte SHA-256><extension>`.
L'adressage par l'empreinte donne deux propriétés : un même contenu n'est stocké qu'une fois, et le contenu
d'un fichier archivé ne peut pas changer sans que son nom cesse de correspondre.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Union

from django.conf import settings

DOSSIER = "brut"
TAILLE_BLOC = 1024 * 1024


def racine() -> Path:
    return Path(settings.MEDIA_ROOT) / DOSSIER


def dossier_source(source_code: str) -> Path:
    d = racine() / source_code
    d.mkdir(parents=True, exist_ok=True)
    return d


def empreinte(chemin: Path) -> str:
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(TAILLE_BLOC), b""):
            h.update(bloc)
    return h.hexdigest()


def _relatif(chemin: Path) -> str:
    return chemin.relative_to(Path(settings.MEDIA_ROOT)).as_posix()


def archiver(source_code: str, origine: Union[Path, str, bytes], extension: str = "") -> tuple[str, str]:
    """Range `origine` (chemin ou contenu) dans la zone brute.

    Renvoie (chemin relatif à MEDIA_ROOT, empreinte SHA-256). Le fichier d'origine n'est pas modifié.
    """
    if isinstance(origine, bytes):
        sha = hashlib.sha256(origine).hexdigest()
        cible = dossier_source(source_code) / f"{sha}{extension.lower()}"
        if not cible.exists():
            cible.write_bytes(origine)
        return _relatif(cible), sha
    origine = Path(origine)
    sha = empreinte(origine)
    cible = dossier_source(source_code) / f"{sha}{(extension or origine.suffix).lower()}"
    if not cible.exists():
        shutil.copyfile(origine, cible)
    return _relatif(cible), sha


def chemin_absolu(relatif: str) -> Path:
    """Chemin d'un fichier archivé ; refuse tout chemin sortant de la zone brute."""
    base = racine().resolve()
    chemin = (Path(settings.MEDIA_ROOT) / relatif).resolve()
    if base not in chemin.parents:
        raise ValueError("Chemin hors de la zone brute.")
    return chemin
