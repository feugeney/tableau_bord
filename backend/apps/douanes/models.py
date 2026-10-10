"""Recettes douanières (SYDONIA)."""

from django.db import models

from apps.core.entrepot import FaitBase, dw_table, montant
from apps.referentiels.models import RefBureauDouane, RefNatureDroitDouane


class FaitRecetteDouane(FaitBase):
    nature_droit = models.ForeignKey(RefNatureDroitDouane, on_delete=models.PROTECT, related_name="+")
    bureau = models.ForeignKey(RefBureauDouane, null=True, on_delete=models.PROTECT, related_name="+")
    mois = models.PositiveSmallIntegerField()
    objectif = montant()
    recouvre = montant()

    class Meta:
        db_table = dw_table("fait_recette_douane")


class FaitDeclaration(FaitBase):
    CIRCUITS = [("vert", "Vert"), ("jaune", "Jaune"), ("rouge", "Rouge")]
    bureau = models.ForeignKey(RefBureauDouane, null=True, on_delete=models.PROTECT, related_name="+")
    circuit = models.CharField(max_length=8, choices=CIRCUITS)
    date_enregistrement = models.DateField()
    date_mainlevee = models.DateField(null=True)
    nombre = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = dw_table("fait_declaration")


class FaitExoneration(FaitBase):
    regime = models.CharField(max_length=120)
    beneficiaire_type = models.CharField(max_length=120, blank=True)
    mois = models.PositiveSmallIntegerField()
    montant = montant()

    class Meta:
        db_table = dw_table("fait_exoneration")
