"""Faits de la Chaîne Dépense (lot 1 : données réelles)."""

from django.db import models

from apps.core.entrepot import FaitBase, dw_table, montant
from apps.referentiels.models import (
    RefBeneficiaire,
    RefEtatDossier,
    RefNatureEconomique,
    RefSection,
    RefSousSection,
    RefTypeProcedure,
)


class ImputationMixin(models.Model):
    """Codes d'imputation budgétaire, conservés en texte (zéros initiaux)."""

    type_budget = models.CharField(max_length=8, blank=True)
    section = models.ForeignKey(
        RefSection, to_field="code", db_column="section_code", on_delete=models.PROTECT, related_name="+"
    )
    sous_section = models.ForeignKey(
        RefSousSection,
        to_field="code",
        db_column="sous_section_code",
        null=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    titre = models.CharField(max_length=4, db_index=True)
    chapitre = models.CharField(max_length=4, blank=True)
    article = models.CharField(max_length=4, blank=True)
    paragraphe = models.CharField(max_length=4, blank=True)
    sous_paragraphe = models.CharField(max_length=4, blank=True)
    nature = models.ForeignKey(
        RefNatureEconomique,
        to_field="code",
        db_column="nature_code",
        null=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    source_financement = models.CharField(max_length=8, blank=True)
    groupe_bailleur = models.CharField(max_length=8, blank=True)
    bailleur = models.CharField(max_length=8, blank=True)

    class Meta:
        abstract = True


class FaitSituationLigne(ImputationMixin, FaitBase):
    """Une ligne par ligne budgétaire et par date de situation (onglet « Situation courante »)."""

    regulation = models.CharField(max_length=4, blank=True)
    # Hash de la clé métier (type budget + sous-section + nature + source + bailleur + régulation).
    cle_ligne = models.CharField(max_length=40, db_index=True)

    credit_initial_lfi = montant()
    credit_lfr = montant()
    credit_douzieme_provisoire = montant()
    credit_actuel = montant()
    credit_disponible = montant()
    credit_reserve = montant()
    credit_engage = montant()
    credit_engage_projet = montant()
    credit_engage_cf = montant()
    montant_liquide = montant()
    montant_ordonnance = montant()
    montant_vbp = montant()
    montant_encours_paiement = montant()
    montant_paye = montant()
    montant_bloque = montant()
    montant_delegation = montant()
    avance_demarrage = montant()
    montant_regie = montant()

    # Valeur vide dans l'extraction : 0 dans les calculs, mais signalée.
    lfi_absent = models.BooleanField(default=False)
    lfr_absent = models.BooleanField(default=False)
    # Colonnes additionnelles de l'extraction (pilier Simandou, projet green, fonctionnelle…).
    attributs = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = dw_table("fait_situation_ligne")
        indexes = [
            models.Index(fields=["exercice", "date_situation", "section"]),
            models.Index(fields=["date_situation", "cle_ligne"]),
        ]


class FaitEngagement(ImputationMixin, FaitBase):
    """Une ligne par engagement.

    Le numéro d'engagement n'est pas unique, même combiné avec la section : la clé
    est technique (id) ; `cle_imputation` est un hash des colonnes d'imputation.
    La clé métier sera documentée une fois confirmée par l'équipe Chaîne Dépense.
    """

    numero = models.CharField(max_length=32, db_index=True)
    cle_imputation = models.CharField(max_length=40, db_index=True)
    type_procedure = models.ForeignKey(RefTypeProcedure, null=True, on_delete=models.PROTECT, related_name="+")
    etat_dossier = models.ForeignKey(RefEtatDossier, null=True, on_delete=models.PROTECT, related_name="+")
    beneficiaire = models.ForeignKey(RefBeneficiaire, null=True, on_delete=models.PROTECT, related_name="+")
    beneficiaire_brut = models.CharField(max_length=255, blank=True)
    objet = models.TextField(blank=True)
    devise = models.CharField(max_length=8, blank=True)

    date_creation = models.DateField(null=True, db_index=True)
    date_visa_cf = models.DateField(null=True)
    date_visa_ministre = models.DateField(null=True)
    date_etat = models.DateField(null=True)
    date_maj = models.DateField(null=True)

    montant_initial = montant()
    montant_engage = montant()
    montant_engage_cf = montant()
    montant_retenu = montant()
    montant_liquide = montant()
    montant_ordonnance = montant()
    montant_vbp = montant()
    montant_ecp = montant()
    montant_paye = montant()
    montant_devise = montant()

    class Meta:
        db_table = dw_table("fait_engagement")
        indexes = [models.Index(fields=["exercice", "date_situation", "section"])]


class FaitOperation(ImputationMixin, FaitBase):
    """Détail des opérations (onglet « Détails des opérations »)."""

    numero_engagement = models.CharField(max_length=32, blank=True, db_index=True)
    type_procedure = models.ForeignKey(RefTypeProcedure, null=True, on_delete=models.PROTECT, related_name="+")
    etat_dossier = models.ForeignKey(RefEtatDossier, null=True, on_delete=models.PROTECT, related_name="+")
    type_origine = models.CharField(max_length=120, blank=True)
    beneficiaire = models.ForeignKey(RefBeneficiaire, null=True, on_delete=models.PROTECT, related_name="+")
    beneficiaire_brut = models.CharField(max_length=255, blank=True)
    objet = models.TextField(blank=True)
    code_devise = models.CharField(max_length=8, blank=True)
    date_visa_vbp = models.DateField(null=True)

    montant_engage = montant()
    montant_engage_cf = montant()
    montant_liquide = montant()
    montant_devise = montant()
    montant_vbp = montant()
    montant_ordonnance = montant()
    montant_paye = montant()
    montant = montant()  # en dernier : ce nom masque ensuite la fabrique montant()

    class Meta:
        db_table = dw_table("fait_operation")


class FaitRegie(ImputationMixin, FaitBase):
    """Régies (onglet vide dans certaines extractions : la structure doit exister)."""

    gestionnaire = models.CharField(max_length=16, blank=True, help_text="gradm")
    numero_regie = models.CharField(max_length=32, blank=True)
    nature_flux = models.CharField(max_length=16, blank=True)
    montant_regie = montant()
    date_creation = models.DateField(null=True)
    etat_dossier_brut = models.CharField(max_length=120, blank=True)

    class Meta:
        db_table = dw_table("fait_regie")
