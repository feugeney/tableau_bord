"""API de la page Dépenses (Chaîne Dépense) — préfixe /api/v1/depense/."""

from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.views import APIView

from apps.core.models import Domaine
from apps.core.permissions import DoubleAuthentification
from apps.core.reponses import VueDomaine
from apps.referentiels.models import RefSection

from . import services


class VueDepense(VueDomaine):
    domaine = Domaine.DEPENSE
    source_code = "chaine_depense"


class Indicateurs(VueDepense):
    page = "depenses"

    def calculer(self, request, f):
        return services.indicateurs(f)


class Pilotage(VueDepense):
    def calculer(self, request, f):
        from .pilotage import page

        return page(f)


class Chaine(VueDepense):
    def calculer(self, request, f):
        return services.chaine(f)


class Natures(VueDepense):
    def calculer(self, request, f):
        return services.natures(f)


class Sections(VueDepense):
    def calculer(self, request, f):
        return services.sections(f)


class SectionDetail(VueDepense):
    def calculer(self, request, f, code):
        if not RefSection.objects.filter(code=code).exists():
            raise NotFound("Section inconnue.")
        return services.section_detail(f, code)


class Mensuel(VueDepense):
    def calculer(self, request, f):
        return services.mensuel(f)


class Projection(VueDepense):
    def calculer(self, request, f):
        return services.projection(f)


class RestesAPayer(VueDepense):
    def calculer(self, request, f):
        return services.restes_a_payer_anciennete(f)


class Procedures(VueDepense):
    def calculer(self, request, f):
        return services.procedures(f)


class Criteres(VueDepense):
    """Valeurs proposées pour les filtres à critères multiples de la page Dépenses."""

    def calculer(self, request, f):
        from .criteres import options

        return options(f)


class ComparaisonN1(VueDepense):
    def calculer(self, request, f):
        from .comparaisons import comparaison_n1

        return comparaison_n1(f)


class Courbe(VueDepense):
    def calculer(self, request, f):
        from .comparaisons import courbe

        return courbe(f)


class Repartitions(VueDepense):
    def calculer(self, request, f):
        return services.repartitions(f)


class Simandou(VueDepense):
    def calculer(self, request, f):
        return services.simandou(f)


class Beneficiaires(VueDepense):
    def calculer(self, request, f):
        try:
            top = min(max(int(request.query_params.get("top", 10)), 1), 100)
        except ValueError as exc:
            raise ValidationError({"top": "Entier attendu."}) from exc
        return services.beneficiaires(f, top)


class PlanEngagement(VueDomaine):
    """Pilotage › Plan d'engagement (GDEP.TD_PLAN_ENG*) ; paramètre propre : periode (T1…T4)."""

    domaine = Domaine.TOFE
    source_code = "plan_engagement"
    page = "plan-engagement"

    def calculer(self, request, f):
        from .plan_engagement import page

        periode = request.query_params.get("periode") or None
        if periode and periode not in ("T1", "T2", "T3", "T4"):
            raise ValidationError({"periode": "Valeurs admises : T1, T2, T3, T4"})
        return page(f, periode)


class Investissement(VueDomaine):
    domaine = Domaine.INVESTISSEMENT
    source_code = "chaine_depense"
    page = "investissements"

    def calculer(self, request, f):
        return services.synthese_investissement(f)


class ExportMinisteres(APIView):
    """Export décideurs du tableau « Ministères et institutions » : GET /depense/ministeres.<xlsx|pdf>."""

    permission_classes = [DoubleAuthentification]

    def get(self, request, format_fichier: str):
        from django.http import HttpResponse
        from django.utils import timezone

        from apps.core.audit import journaliser
        from apps.core.filtres import resoudre_filtres
        from apps.core.models import JournalAudit

        from .export_ministeres import classeur, colonnes_choisies, pdf, preparer

        if format_fichier not in ("xlsx", "pdf"):
            raise NotFound("Format inconnu.")
        u = request.user
        if not (u.voit_tout() or (u.role != "lecteur" and u.peut_exporter(Domaine.DEPENSE))):
            raise PermissionDenied("Votre profil ne permet pas l'export de cette page.")
        f = resoudre_filtres(request.query_params, "chaine_depense")
        if f.date_situation is None:
            raise NotFound("Aucune situation de la Chaîne Dépense pour ces filtres.")
        d = preparer(f, colonnes_choisies(request.query_params.get("colonnes")))
        contenu = classeur(d, u.get_username()) if format_fichier == "xlsx" else pdf(d, u.get_username())
        journaliser(
            request,
            JournalAudit.Action.EXPORT,
            objet=f"ministeres.{format_fichier}",
            detail={"filtres": dict(request.query_params)},
        )
        type_mime = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if format_fichier == "xlsx"
            else "application/pdf"
        )
        reponse = HttpResponse(contenu, content_type=type_mime)
        jour = f.date_situation.isoformat() if f.date_situation else timezone.localdate().isoformat()
        reponse["Content-Disposition"] = f'attachment; filename="tdb-ministeres-{jour}.{format_fichier}"'
        reponse["Cache-Control"] = "private, no-store"
        return reponse
