"""Recettes fiscales (SAFIG)."""

from django.db import models

from apps.core.entrepot import FaitBase, dw_table, montant
from apps.referentiels.models import RefCentreImpots, RefImpot, RefSecteurActivite


class FaitRecouvrementFiscal(FaitBase):
    impot = models.ForeignKey(RefImpot, on_delete=models.PROTECT, related_name="+")
    centre = models.ForeignKey(RefCentreImpots, null=True, on_delete=models.PROTECT, related_name="+")
    secteur = models.ForeignKey(RefSecteurActivite, null=True, on_delete=models.PROTECT, related_name="+")
    mois = models.PositiveSmallIntegerField()
    objectif = montant()
    recouvre = montant()

    class Meta:
        db_table = dw_table("fait_recouvrement_fiscal")


class FaitResteARecouvrer(FaitBase):
    impot = models.ForeignKey(RefImpot, null=True, on_delete=models.PROTECT, related_name="+")
    centre = models.ForeignKey(RefCentreImpots, null=True, on_delete=models.PROTECT, related_name="+")
    anciennete = models.CharField(max_length=32, blank=True)
    montant = montant()

    class Meta:
        db_table = dw_table("fait_reste_a_recouvrer")


class FaitContentieux(FaitBase):
    impot = models.ForeignKey(RefImpot, null=True, on_delete=models.PROTECT, related_name="+")
    stade = models.CharField(max_length=64, blank=True)
    nombre_dossiers = models.PositiveIntegerField(default=0)
    montant = montant()

    class Meta:
        db_table = dw_table("fait_contentieux")


class FaitContribuables(FaitBase):
    centre = models.ForeignKey(RefCentreImpots, null=True, on_delete=models.PROTECT, related_name="+")
    mois = models.PositiveSmallIntegerField()
    actifs = models.PositiveIntegerField(default=0)
    teledeclarants = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = dw_table("fait_contribuables")
