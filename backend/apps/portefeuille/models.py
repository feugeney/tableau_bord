"""Portefeuille de l'État (SYSOP)."""

from django.db import models

from apps.core.entrepot import FaitBase, dw_table, montant
from apps.referentiels.models import RefOrganisme


class FaitSubventionEpa(FaitBase):
    organisme = models.ForeignKey(RefOrganisme, on_delete=models.PROTECT, related_name="+")
    prevu = montant()
    paye = montant()
    transfert_chaine_depense = montant(help_text="Rapprochement avec les transferts (titre 4)")

    class Meta:
        db_table = dw_table("fait_subvention_epa")


class FaitDividende(FaitBase):
    organisme = models.ForeignKey(RefOrganisme, on_delete=models.PROTECT, related_name="+")
    vote = montant()
    encaisse = montant()

    class Meta:
        db_table = dw_table("fait_dividende")


class FaitSanteFinanciere(FaitBase):
    STATUTS = [
        ("excedentaire", "Excédentaire"),
        ("equilibre", "À l'équilibre"),
        ("deficitaire", "Déficitaire"),
        ("non_transmis", "États non transmis"),
    ]
    organisme = models.ForeignKey(RefOrganisme, on_delete=models.PROTECT, related_name="+")
    resultat = montant(null=True)
    statut = models.CharField(max_length=16, choices=STATUTS)

    class Meta:
        db_table = dw_table("fait_sante_financiere")


class FaitGouvernance(FaitBase):
    organisme = models.ForeignKey(RefOrganisme, on_delete=models.PROTECT, related_name="+")
    etats_financiers_transmis = models.BooleanField(default=False)
    mandats_expires = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = dw_table("fait_gouvernance")


class FaitBudgetEpa(FaitBase):
    organisme = models.ForeignKey(RefOrganisme, on_delete=models.PROTECT, related_name="+")
    budget_primitif = montant()
    saisi = models.BooleanField(default=False)

    class Meta:
        db_table = dw_table("fait_budget_epa")
