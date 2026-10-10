"""Patrimoine de l'État (SICOM)."""

from django.db import models

from apps.core.entrepot import FaitBase, dw_table, montant
from apps.referentiels.models import RefCategorieBien, RefSection


class FaitPatrimoine(FaitBase):
    categorie = models.ForeignKey(RefCategorieBien, on_delete=models.PROTECT, related_name="+")
    section = models.ForeignKey(
        RefSection, to_field="code", db_column="section_code", null=True, on_delete=models.PROTECT, related_name="+"
    )
    valeur_brute = montant()
    valeur_nette = montant()
    nombre_biens = models.PositiveIntegerField(default=0)
    biens_immatricules = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = dw_table("fait_patrimoine")


class FaitParcVehicules(FaitBase):
    ETATS = [("en_service", "En service"), ("en_panne", "En panne"), ("hors_usage", "Hors d'usage")]
    etat = models.CharField(max_length=16, choices=ETATS)
    type_vehicule = models.CharField(max_length=64, blank=True)
    nombre = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = dw_table("fait_parc_vehicules")


class FaitControlePatrimoine(FaitBase):
    CONTROLES = [
        ("non_inventories_2ans", "Biens non inventoriés depuis plus de 2 ans"),
        ("sans_detenteur", "Biens sans détenteur"),
        ("vehicules_a_reformer", "Véhicules hors d'usage à réformer"),
        ("ecart_scie", "Écart avec le SCIE"),
    ]
    controle = models.CharField(max_length=32, choices=CONTROLES)
    nombre = models.PositiveIntegerField(default=0)
    montant = montant()

    class Meta:
        db_table = dw_table("fait_controle_patrimoine")


class FaitDeploiementSicom(FaitBase):
    institutions_actives = models.PositiveIntegerField(default=0)
    institutions_prevues = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = dw_table("fait_deploiement_sicom")
