"""Masse salariale (FUGAS)."""

from django.db import models

from apps.core.entrepot import FaitBase, dw_table, montant
from apps.referentiels.models import RefSection


class FaitPaie(FaitBase):
    mois = models.PositiveSmallIntegerField()
    section = models.ForeignKey(
        RefSection, to_field="code", db_column="section_code", on_delete=models.PROTECT, related_name="+"
    )
    effectif = models.PositiveIntegerField(default=0)
    masse_brute = montant()
    masse_nette = montant()

    class Meta:
        db_table = dw_table("fait_paie")


class FaitControlePaie(FaitBase):
    CONTROLES = [
        ("doublons", "Doublons"),
        ("sans_nif", "Agents sans NIF"),
        ("sans_affectation", "Agents sans affectation"),
        ("departs_retraite", "Départs à la retraite"),
    ]
    controle = models.CharField(max_length=32, choices=CONTROLES)
    nombre_agents = models.PositiveIntegerField(default=0)
    montant = montant()

    class Meta:
        db_table = dw_table("fait_controle_paie")
