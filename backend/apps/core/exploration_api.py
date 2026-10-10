"""API de l'exploration libre des données (profil analyste)."""

from __future__ import annotations

from io import BytesIO

from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from . import exploration
from .audit import journaliser
from .export import ENTETE, MARINE
from .models import JournalAudit
from .permissions import DoubleAuthentification
from .reponses import jsonable, meta

PARAMETRE_Q = OpenApiParameter(
    "q",
    str,
    required=True,
    description='Requête JSON : {"jeu", "axes": [], "mesures": [{"champ", "agregat"}], "filtres": '
    '[{"champ", "operateur", "valeur"}], "exercice", "date_situation", "tri": {"champ", "sens"}, "limite"}',
)


class Explorer(BasePermission):
    message = "L'exploration des données est réservée aux analystes et aux administrateurs."

    def has_permission(self, request, view):
        return exploration.peut_explorer(request.user)


PERMISSIONS = [DoubleAuthentification, Explorer]


class CatalogueView(APIView):
    """Jeux de données accessibles, avec leurs axes, leurs mesures et les situations chargées."""

    permission_classes = PERMISSIONS

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        return Response(
            {
                "jeux": exploration.catalogue(request.user),
                "agregats": list(exploration.AGREGATS),
                "operateurs": list(exploration.OPERATEURS),
                "limites": {
                    "axes": exploration.MAX_AXES,
                    "mesures": exploration.MAX_MESURES,
                    "filtres": exploration.MAX_FILTRES,
                    "lignes": exploration.LIMITE_MAX,
                },
            }
        )


def _resultat(request, limite_max: int) -> dict:
    q = exploration.lire_requete(request.query_params.get("q", ""))
    if limite_max > exploration.LIMITE_MAX:
        q = {**q, "limite": limite_max}
    return exploration.executer(request.user, q, limite_max=limite_max) | {"requete": q}


class RequeteView(APIView):
    permission_classes = PERMISSIONS

    @extend_schema(parameters=[PARAMETRE_Q], responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        r = _resultat(request, exploration.LIMITE_MAX)
        f = r.pop("situation")
        r.pop("requete")
        return Response({"meta": meta(r["jeu"]["source"], f), "data": jsonable(r)})


class ExportView(APIView):
    """Résultat d'une requête d'exploration au format Excel ; l'export est inscrit au journal d'audit."""

    permission_classes = PERMISSIONS

    @extend_schema(parameters=[PARAMETRE_Q], responses={200: OpenApiTypes.BINARY})
    def get(self, request):
        r = _resultat(request, exploration.LIMITE_EXPORT)
        f, q, jeu = r["situation"], r["requete"], r["jeu"]
        m = meta(jeu["source"], f)
        statuts = {"reel": "réel", "demo": "illustration (chiffres fictifs)", "non_raccorde": "non raccordée"}
        wb = Workbook()
        ws = wb.active
        ws.title = "Lisez-moi"
        filtres = " ; ".join(f"{x['champ']} {x['operateur']} {x.get('valeur')}" for x in q.get("filtres") or [])
        for ligne in (
            ["République de Guinée · Ministère de l'Économie, des Finances et du Budget"],
            [f"Système intégré de pilotage des finances publiques — Exploration : {jeu['libelle']}"],
            ["Document de travail – diffusion restreinte"],
            [],
            ["Jeu de données", f"{jeu['libelle']} ({jeu['code']})"],
            ["Source", m["application"]],
            ["Statut de la source", statuts.get(m["statut_source"], m["statut_source"])],
            ["Exercice", m["exercice"]],
            ["Date de situation", m["date_situation"]],
            ["Filtres appliqués", filtres or "Aucun"],
            ["Exporté le", timezone.localtime().strftime("%d/%m/%Y %H:%M")],
            ["Exporté par", request.user.get_username()],
            ["Unités", "Montants en francs guinéens (GNF), non arrondis."],
            ["Lignes", f"{len(r['lignes'])} sur {r['nb_groupes']}" + (" (résultat tronqué)" if r["tronque"] else "")],
        ):
            ws.append(ligne)
        ws["A1"].font = Font(bold=True, color=MARINE)
        ws["A2"].font = Font(bold=True, size=14, color=MARINE)
        ws["A3"].font = Font(bold=True)
        ws.column_dimensions["A"].width = 24
        ws.column_dimensions["B"].width = 70

        ws = wb.create_sheet("Résultat")
        colonnes = r["colonnes"]
        ws.append([c["libelle"] for c in colonnes])
        for x in r["lignes"]:
            ws.append(
                [
                    jsonable(x.get(c["code"])) if c["type"] == "mesure" else x.get(f"{c['code']}__libelle")
                    for c in colonnes
                ]
            )
        if any(c["type"] != "mesure" for c in colonnes):
            ws.append(
                [
                    jsonable(r["totaux"].get(c["code"])) if c["type"] == "mesure" else ("Total" if i == 0 else None)
                    for i, c in enumerate(colonnes)
                ]
            )
            for cellule in ws[ws.max_row]:
                cellule.font = Font(bold=True)
        for cellule in ws[1]:
            cellule.font = Font(bold=True, color="FFFFFF")
            cellule.fill = ENTETE
            cellule.alignment = Alignment(wrap_text=True, vertical="center")
        ws.freeze_panes = "A2"
        for i, c in enumerate(colonnes, start=1):
            lettre = get_column_letter(i)
            ws.column_dimensions[lettre].width = 22 if c["type"] == "mesure" else 34
            if c["type"] == "mesure":
                for cellule in ws[lettre][1:]:
                    cellule.number_format = "#,##0" if c["agregat"] == "nombre" else "#,##0.00"

        journaliser(request, JournalAudit.Action.EXPORT, objet=f"exploration : {jeu['code']}", detail={"requete": q})
        tampon = BytesIO()
        wb.save(tampon)
        reponse = HttpResponse(
            tampon.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        date_nom = m.get("date_situation") or timezone.localdate().isoformat()
        reponse["Content-Disposition"] = f'attachment; filename="exploration-{jeu["code"]}-{date_nom}.xlsx"'
        return reponse
