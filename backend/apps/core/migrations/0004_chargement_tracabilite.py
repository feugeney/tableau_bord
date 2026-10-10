import uuid

from django.db import migrations, models


def attribuer_uuid(apps, schema_editor):
    """Un UUID distinct par chargement existant (la valeur par défaut d'un AddField serait commune)."""
    Chargement = apps.get_model("core", "Chargement")
    for c in Chargement.objects.filter(uuid__isnull=True).only("id"):
        c.uuid = uuid.uuid4()
        c.save(update_fields=["uuid"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_alter_alerte_domaine_alter_reglealerte_domaine_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="chargement",
            name="empreinte_sha256",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="chargement",
            name="fichier_archive",
            field=models.CharField(
                blank=True,
                help_text="Copie conservée telle que reçue (zone brute), relative à MEDIA_ROOT",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="chargement",
            name="uuid",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(attribuer_uuid, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="chargement",
            name="uuid",
            field=models.UUIDField(
                default=uuid.uuid4, editable=False, help_text="Identifiant du flux (UUID v4)", unique=True
            ),
        ),
    ]
