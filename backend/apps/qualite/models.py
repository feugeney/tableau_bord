"""Contrôles de qualité des données."""

from django.db import models


class ResultatControle(models.Model):
    """Résultat d'un contrôle de qualité pour un chargement donné."""

    NIVEAUX = [("bloquant", "Bloquant"), ("avertissement", "Avertissement"), ("info", "Information")]
    chargement = models.ForeignKey("core.Chargement", on_delete=models.CASCADE, related_name="controles")
    code = models.CharField(max_length=64)
    libelle = models.CharField(max_length=255)
    niveau = models.CharField(max_length=16, choices=NIVEAUX)
    reussi = models.BooleanField()
    valeur = models.DecimalField(max_digits=24, decimal_places=2, null=True)
    nombre = models.PositiveIntegerField(null=True)
    detail = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "qualite_resultat_controle"
        ordering = ["chargement", "code"]
