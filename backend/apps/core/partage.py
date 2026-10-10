"""Partage de données : jetons d'accès en lecture seule pour les systèmes tiers.

En-tête attendu : « Authorization: Jeton tdb_… ». La clé n'est affichée qu'une fois, à la création.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import date

from django.db import transaction
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import SAFE_METHODS

from .models import JetonPartage, Role, Utilisateur

MOT_CLE = b"jeton"


def empreinte(cle: str) -> str:
    return hashlib.sha256(cle.encode()).hexdigest()


@transaction.atomic
def creer_jeton(
    nom: str, destinataire: str, domaines: list[str], expire_le: date | None, cree_par
) -> tuple[JetonPartage, str]:
    cle = "tdb_" + secrets.token_urlsafe(32)
    compte = Utilisateur.objects.create(
        username=f"partage-{secrets.token_hex(4)}",
        role=Role.LECTEUR,
        domaines=domaines,
        structure=destinataire[:120],
        first_name="Partage",
        last_name=nom[:150],
    )
    compte.set_unusable_password()  # aucun accès interactif
    compte.save()
    jeton = JetonPartage.objects.create(
        nom=nom,
        destinataire=destinataire,
        domaines=domaines,
        prefixe=cle[:12],
        empreinte=empreinte(cle),
        compte=compte,
        expire_le=expire_le,
        cree_par=cree_par if getattr(cree_par, "pk", None) else None,
    )
    return jeton, cle


class JetonPartageAuthentication(BaseAuthentication):
    """Authentifie un système tiers ; lecture seule, domaines limités à ceux du jeton."""

    def authenticate(self, request):
        entete = get_authorization_header(request).split()
        if not entete or entete[0].lower() != MOT_CLE:
            return None
        if len(entete) != 2:
            raise AuthenticationFailed("En-tête « Jeton » invalide.")
        jeton = (
            JetonPartage.objects.select_related("compte")
            .filter(empreinte=empreinte(entete[1].decode()), actif=True)
            .first()
        )
        if jeton is None or not jeton.compte.is_active:
            raise AuthenticationFailed("Jeton de partage inconnu ou révoqué.")
        if jeton.expire_le and jeton.expire_le < date.today():
            raise AuthenticationFailed("Jeton de partage expiré.")
        if request.method not in SAFE_METHODS:
            raise AuthenticationFailed("Un jeton de partage ne donne accès qu'en lecture.")
        JetonPartage.objects.filter(pk=jeton.pk).update(derniere_utilisation=timezone.now())
        return jeton.compte, jeton

    def authenticate_header(self, request):
        return "Jeton"
