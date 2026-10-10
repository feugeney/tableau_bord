"""API de la page Dépenses (Chaîne Dépense) — préfixe /api/v1/depense/."""

from rest_framework.exceptions import NotFound, ValidationError

from apps.core.models import Domaine
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


class RestesAPayer(VueDepense):
    def calculer(self, request, f):
        return services.restes_a_payer_anciennete(f)


class Procedures(VueDepense):
    def calculer(self, request, f):
        return services.procedures(f)


class Beneficiaires(VueDepense):
    def calculer(self, request, f):
        try:
            top = min(max(int(request.query_params.get("top", 10)), 1), 100)
        except ValueError as exc:
            raise ValidationError({"top": "Entier attendu."}) from exc
        return services.beneficiaires(f, top)


class Investissement(VueDomaine):
    domaine = Domaine.INVESTISSEMENT
    source_code = "chaine_depense"
    page = "investissements"

    def calculer(self, request, f):
        return services.synthese_investissement(f)
