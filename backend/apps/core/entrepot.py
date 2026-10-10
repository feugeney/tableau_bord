"""Briques communes aux tables de faits (schéma « dw »)."""

from django.db import models

Montant = models.DecimalField  # alias lisible


def dw_table(nom: str) -> str:
    return f'dw"."{nom}'


def montant(**kwargs):
    """NUMERIC(20,2) en GNF."""
    kwargs.setdefault("default", 0)
    return models.DecimalField(max_digits=20, decimal_places=2, **kwargs)


class FaitBase(models.Model):
    """Colonnes techniques : on empile les situations datées, on n'écrase jamais."""

    exercice = models.PositiveSmallIntegerField(db_index=True)
    date_situation = models.DateField(db_index=True)
    source = models.ForeignKey("core.Source", on_delete=models.PROTECT, related_name="+")
    chargement = models.ForeignKey("core.Chargement", on_delete=models.CASCADE, related_name="+")

    class Meta:
        abstract = True
