"""Permissions appliquées dans l'API (pas seulement dans l'interface)."""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Role


def otp_verifie(request) -> bool:
    auth = getattr(request, "auth", None)
    if auth is not None and hasattr(auth, "get"):
        return bool(auth.get("otp", False))
    # Session Django (admin) : django-otp positionne is_verified().
    verifie = getattr(request.user, "is_verified", None)
    return bool(verifie and verifie())


class DoubleAuthentification(BasePermission):
    """Profils cabinet et administrateur : jeton émis après vérification TOTP."""

    message = {"code": "2fa_requis", "detail": "Double authentification requise pour ce profil."}

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        return not u.exige_2fa or otp_verifie(request)


class AccesDomaine(BasePermission):
    """La vue déclare `domaine` ; un directeur ou un lecteur ne voit que ses domaines."""

    message = "Ce domaine ne fait pas partie de votre périmètre."

    def has_permission(self, request, view):
        domaine = getattr(view, "domaine", None)
        return domaine is None or request.user.peut_voir(domaine)


class Exporter(BasePermission):
    message = "Votre profil ne permet pas l'export."

    def has_permission(self, request, view):
        return request.user.peut_exporter(getattr(view, "domaine", "synthese"))


class AdminDNSI(BasePermission):
    message = "Réservé aux administrateurs DNSI."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_superuser or u.role == Role.DNSI_ADMIN))


class LectureOuAdminDNSI(AdminDNSI):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return super().has_permission(request, view)


PERMISSIONS_DONNEES = [DoubleAuthentification, AccesDomaine]
