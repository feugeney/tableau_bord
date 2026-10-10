from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Alerte, Chargement, JournalAudit, MappingColonnes, Parametre, RegleAlerte, Source, Utilisateur


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Profil tableau de bord", {"fields": ("role", "domaines", "structure")}),)
    list_display = ("username", "get_full_name", "role", "structure", "is_active", "last_login")
    list_filter = ("role", "is_active")


class MappingInline(admin.TabularInline):
    model = MappingColonnes
    extra = 0


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("code", "application", "structure", "statut", "connecteur", "planification_cron")
    list_editable = ("statut",)
    inlines = [MappingInline]


@admin.register(Chargement)
class ChargementAdmin(admin.ModelAdmin):
    list_display = ("id", "source", "fichier", "date_situation", "statut", "lignes_chargees", "duree_secondes")
    list_filter = ("source", "statut")
    readonly_fields = [f.name for f in Chargement._meta.fields]


@admin.register(Parametre)
class ParametreAdmin(admin.ModelAdmin):
    list_display = ("code", "valeur", "unite", "libelle", "modifie_le")


@admin.register(RegleAlerte)
class RegleAlerteAdmin(admin.ModelAdmin):
    list_display = ("code", "domaine", "severite", "actif")
    list_editable = ("actif",)


@admin.register(Alerte)
class AlerteAdmin(admin.ModelAdmin):
    list_display = ("date", "domaine", "severite", "titre", "statut")
    list_filter = ("domaine", "severite", "statut")


@admin.register(JournalAudit)
class JournalAuditAdmin(admin.ModelAdmin):
    list_display = ("date", "identifiant", "action", "objet", "adresse_ip")
    list_filter = ("action",)
    readonly_fields = [f.name for f in JournalAudit._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
