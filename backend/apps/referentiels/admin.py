from django.contrib import admin

from . import models as m


@admin.register(m.RefSection)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("code", "libelle_court", "libelle", "type", "identifiant_etat")
    list_editable = ("libelle_court", "type")
    search_fields = ("code", "libelle")


@admin.register(m.RefTypeProcedure)
class TypeProcedureAdmin(admin.ModelAdmin):
    list_display = ("libelle", "paiement_hors_chaine", "description")
    list_editable = ("paiement_hors_chaine",)


@admin.register(m.RefEtatDossier)
class EtatDossierAdmin(admin.ModelAdmin):
    list_display = ("libelle", "engagement_valide")
    list_editable = ("engagement_valide",)


class AliasInline(admin.TabularInline):
    model = m.RefBeneficiaireAlias
    extra = 0


@admin.register(m.RefBeneficiaire)
class BeneficiaireAdmin(admin.ModelAdmin):
    list_display = ("nom_affiche", "nom_normalise", "identifiant_etat")
    search_fields = ("nom_affiche", "nom_normalise")
    inlines = [AliasInline]


@admin.register(m.RefOrganisme)
class OrganismeAdmin(admin.ModelAdmin):
    list_display = ("nom", "type", "tutelle", "identifiant_etat", "fictif")
    list_filter = ("type", "fictif")


for modele in (
    m.RefRegulation,
    m.RefTypeBudget,
    m.RefSourceFinancement,
    m.RefGroupeBailleur,
    m.RefBailleur,
    m.RefImpot,
    m.RefCentreImpots,
    m.RefSecteurActivite,
    m.RefBureauDouane,
    m.RefNatureDroitDouane,
    m.RefTypeCreancier,
    m.RefCategorieBien,
    m.RefProjet,
    m.RefCompteComptable,
):
    admin.site.register(modele, list_display=("code", "libelle"), list_editable=("libelle",), search_fields=("code",))

admin.site.register(m.RefExercice)
admin.site.register(m.RefSousSection, list_display=("code", "libelle", "section"), search_fields=("code", "libelle"))
