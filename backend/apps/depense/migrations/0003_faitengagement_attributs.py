from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("depense", "0002_vues_mart")]

    operations = [
        migrations.AddField(
            model_name="faitengagement",
            name="attributs",
            field=models.JSONField(default=dict, blank=True),
        ),
    ]
