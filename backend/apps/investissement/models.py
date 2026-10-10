"""Investissements publics."""

from django.db import models

from apps.core.entrepot import FaitBase, dw_table
from apps.referentiels.models import RefProjet


class FaitAvancementProjet(FaitBase):
    """Volet physique (SIGPIP). Le volet financier vient de la Chaîne Dépense (titre 5)."""

    projet = models.ForeignKey(RefProjet, on_delete=models.PROTECT, related_name="+")
    date = models.DateField()
    taux_physique = models.DecimalField(max_digits=5, decimal_places=4)
    statut = models.CharField(max_length=64, blank=True)

    class Meta:
        db_table = dw_table("fait_avancement_projet")
