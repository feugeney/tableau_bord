"""Interface compilée servie par Django sur le poste local."""

import os
from pathlib import Path

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.http import FileResponse, Http404, JsonResponse
from django.utils._os import safe_join
from django.views.static import serve


def sante(request):
    donnees = {"statut": "ok", "application": "dashboard-mefb"}
    if getattr(settings, "SERVIR_FRONTEND_LOCAL", False):
        donnees.update(mode="local", pid=os.getpid())
    return JsonResponse(donnees)


def interface_locale(request, chemin=""):
    if not getattr(settings, "SERVIR_FRONTEND_LOCAL", False):
        raise Http404
    dossier = Path(settings.BASE_DIR).parent / "frontend" / "dist"
    try:
        fichier = Path(safe_join(dossier, chemin))
    except SuspiciousFileOperation:
        raise Http404 from None
    if fichier.is_file():
        return serve(request, chemin, document_root=dossier)
    if chemin.startswith("assets/") or Path(chemin).suffix:
        raise Http404
    index = dossier / "index.html"
    if not index.is_file():
        return JsonResponse({"detail": "Interface non compilée. Lancez Installer.cmd."}, status=503)
    reponse = FileResponse(index.open("rb"), content_type="text/html; charset=utf-8")
    reponse["Cache-Control"] = "no-store"
    return reponse
