"""Dette publique."""

from django.db import models

from apps.core.entrepot import FaitBase, dw_table, montant
from apps.referentiels.models import RefTypeCreancier


class FaitEncoursDette(FaitBase):
    type_creancier = models.ForeignKey(RefTypeCreancier, on_delete=models.PROTECT, related_name="+")
    exterieure = models.BooleanField()
    date = models.DateField()
    encours = montant()

    class Meta:
        db_table = dw_table("fait_encours_dette")


class FaitEcheancierDette(FaitBase):
    annee = models.PositiveSmallIntegerField()
    exterieure = models.BooleanField()
    principal = montant()
    interets = montant()

    class Meta:
        db_table = dw_table("fait_echeancier_dette")


class FaitIndicateurMacro(FaitBase):
    annee = models.PositiveSmallIntegerField()
    indicateur = models.CharField(max_length=32, help_text="pib, ratio_dette_pib…")
    valeur = models.DecimalField(max_digits=24, decimal_places=4)

    class Meta:
        db_table = dw_table("fait_indicateur_macro")
