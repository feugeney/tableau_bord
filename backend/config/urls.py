from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.core import admin_api, exploration_api
from apps.core import api as core_api
from apps.core.api_domaines import PAGES_DOMAINES, VueRecettesAdministratives, vue_page
from apps.core.etl_admin import CatalogueView, FluxViewSet
from apps.core.export import ExportView
from apps.core.export_pdf import ExportPdfView
from apps.core.interface_locale import interface_locale, sante
from apps.core.notifications_api import NotificationMailViewSet
from apps.core.synthese import SyntheseView
from apps.depense import api as dep

router = DefaultRouter(trailing_slash=True)
router.register("sources", core_api.SourceViewSet, basename="source")
router.register("alertes", core_api.AlerteViewSet, basename="alerte")
router.register("parametres", core_api.ParametreViewSet, basename="parametre")
router.register("journal", core_api.JournalViewSet, basename="journal")

routeur_admin = DefaultRouter(trailing_slash=True)
routeur_admin.register("notifications", NotificationMailViewSet, basename="admin-notification")
routeur_admin.register("flux-etl", FluxViewSet, basename="admin-flux-etl")
routeur_admin.register("sources", admin_api.SourceAdminViewSet, basename="admin-source")
routeur_admin.register("mappings", admin_api.MappingViewSet, basename="admin-mapping")
routeur_admin.register("chargements", admin_api.ChargementAdminViewSet, basename="admin-chargement")
routeur_admin.register("regles-alerte", admin_api.RegleAlerteViewSet, basename="admin-regle")
routeur_admin.register("utilisateurs", admin_api.UtilisateurViewSet, basename="admin-utilisateur")
routeur_admin.register("partages", admin_api.JetonViewSet, basename="admin-partage")

administration = [
    path("alimentation/", CatalogueView.as_view()),
    path("tables-cibles/", admin_api.TablesCiblesView.as_view()),
    path("entrepot/", admin_api.EntrepotView.as_view()),
    path("referentiels/", admin_api.ReferentielsAdminView.as_view()),
    path("", include(routeur_admin.urls)),
]

depense = [
    path("indicateurs/", dep.Indicateurs.as_view()),
    path("pilotage/", dep.Pilotage.as_view()),
    path("chaine/", dep.Chaine.as_view()),
    path("natures/", dep.Natures.as_view()),
    path("titres/", dep.Titres.as_view()),
    path("titres/<str:titre>/", dep.TitreDetail.as_view()),
    path("sections/", dep.Sections.as_view()),
    path("sections/<str:code>/", dep.SectionDetail.as_view()),
    path("mensuel/", dep.Mensuel.as_view()),
    path("projection/", dep.Projection.as_view()),
    path("restes-a-payer/anciennete/", dep.RestesAPayer.as_view()),
    path("procedures/", dep.Procedures.as_view()),
    path("beneficiaires/", dep.Beneficiaires.as_view()),
    path("simandou/", dep.Simandou.as_view()),
    path("repartitions/", dep.Repartitions.as_view()),
    path("criteres/", dep.Criteres.as_view()),
    path("comparaison-n1/", dep.ComparaisonN1.as_view()),
    path("courbe/", dep.Courbe.as_view()),
    path("ministeres.<str:format_fichier>", dep.ExportMinisteres.as_view()),
]

api_v1 = [
    path("auth/connexion/", core_api.ConnexionView.as_view()),
    path("auth/rafraichir/", TokenRefreshView.as_view()),
    path("auth/moi/", core_api.MoiView.as_view()),
    path("auth/2fa/activer/", core_api.Activer2FAView.as_view()),
    path("auth/2fa/confirmer/", core_api.Confirmer2FAView.as_view()),
    path("synthese/", SyntheseView.as_view()),
    path("depense/", include(depense)),
    path("investissement/", dep.Investissement.as_view()),
    path("pilotage/plan-engagement/", dep.PlanEngagement.as_view()),
    path("recettes-administratives/", VueRecettesAdministratives.as_view()),
    path("qualite/", core_api.QualiteView.as_view()),
    path("situations/", core_api.SituationsView.as_view()),
    path("admin/", include(administration)),
    path("export/<slug:page>.xlsx", ExportView.as_view()),
    path("export/<slug:page>.pdf", ExportPdfView.as_view()),
    path("exploration/jeux/", exploration_api.CatalogueView.as_view()),
    path("exploration/requete/", exploration_api.RequeteView.as_view()),
    path("exploration/export.xlsx", exploration_api.ExportView.as_view()),
    path("exploration/export.pdf", exploration_api.ExportPdfView.as_view()),
    # Pages de domaine ; « indicateurs/ » est conservé pour compatibilité.
    *[re_path(rf"^{p}/(?:indicateurs/)?$", vue_page(p)) for p in [*PAGES_DOMAINES, "paie"]],
    path("", include(router.urls)),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
    path("sante/", sante),
]

if getattr(settings, "SERVIR_FRONTEND_LOCAL", False):
    urlpatterns += [
        re_path(
            r"^(?!api(?:/|$)|admin(?:/|$)|sante(?:/|$))(?P<chemin>.*)$",
            interface_locale,
        )
    ]
