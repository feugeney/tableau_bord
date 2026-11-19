"""L'application de la dette est confirmée : SIGAD (libellé provisoire remplacé)."""

from django.db import migrations

ANCIEN = "Application de la dette (nom à confirmer)"


def renommer(apps, schema_editor):
    Source = apps.get_model("core", "Source")
    # Un libellé déjà modifié dans l'administration est conservé.
    Source.objects.filter(code="dette", application=ANCIEN).update(application="SIGAD")


def restaurer(apps, schema_editor):
    Source = apps.get_model("core", "Source")
    Source.objects.filter(code="dette", application="SIGAD").update(application=ANCIEN)


class Migration(migrations.Migration):
    dependencies = [("core", "0008_flux_oracle")]

    operations = [migrations.RunPython(renommer, restaurer)]
