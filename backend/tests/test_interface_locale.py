import json

import pytest
from django.http import Http404
from django.test import RequestFactory, override_settings

from apps.core.interface_locale import interface_locale, sante


def test_interface_locale_routes_et_fichiers(tmp_path):
    backend = tmp_path / "backend"
    dossier = tmp_path / "frontend" / "dist"
    (dossier / "assets").mkdir(parents=True)
    (dossier / "index.html").write_text("<html>Application locale</html>")
    (dossier / "assets" / "app.js").write_text("console.log('local');")
    request = RequestFactory().get("/depenses")
    with override_settings(BASE_DIR=backend, SERVIR_FRONTEND_LOCAL=True):
        r = interface_locale(request, "depenses")
        assert b"Application locale" in b"".join(r.streaming_content)
        assert r["Cache-Control"] == "no-store"
        r = interface_locale(request, "assets/app.js")
        assert b"console.log" in b"".join(r.streaming_content)
        for chemin in ("../../backend/.env", "assets/inconnu.js", "inconnu.svg"):
            with pytest.raises(Http404):
                interface_locale(request, chemin)
    with override_settings(SERVIR_FRONTEND_LOCAL=False), pytest.raises(Http404):
        interface_locale(request, "depenses")


def test_sante_identifie_le_serveur_local_sans_exposer_les_secrets():
    request = RequestFactory().get("/sante/")
    with override_settings(SERVIR_FRONTEND_LOCAL=True):
        corps = json.loads(sante(request).content)
        assert corps["application"] == "dashboard-mefb" and corps["mode"] == "local"
        assert isinstance(corps["pid"], int)
    with override_settings(SERVIR_FRONTEND_LOCAL=False):
        assert "pid" not in json.loads(sante(request).content)
