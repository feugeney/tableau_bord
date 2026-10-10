"""Trésorerie et comptabilité (SCIE)."""

from django.db import models

from apps.core.entrepot import FaitBase, dw_table, montant


class FaitFluxTresorerie(FaitBase):
    jour = models.DateField(db_index=True)
    encaissements = montant()
    decaissements = montant()
    solde = montant()

    class Meta:
        db_table = dw_table("fait_flux_tresorerie")


class FaitDepotsCorrespondants(FaitBase):
    categorie = models.CharField(max_length=120)
    montant = montant()

    class Meta:
        db_table = dw_table("fait_depots_correspondants")


class FaitDelaiPaiement(FaitBase):
    mois = models.PositiveSmallIntegerField()
    delai_moyen_jours = models.DecimalField(max_digits=8, decimal_places=2)
    nombre_mandats = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = dw_table("fait_delai_paiement")


class FaitTofe(FaitBase):
    """Poste du tableau des opérations financières de l'État."""

    poste_code = models.CharField(max_length=32)
    poste_libelle = models.CharField(max_length=255)
    ordre = models.PositiveSmallIntegerField(default=0)
    montant = montant()

    class Meta:
        db_table = dw_table("fait_tofe")
