"""Marchés publics (Telemo), d'après les flux d'échange Chaîne de dépenses ↔ Telemo.

- F3 : réservations de crédit visées par le contrôleur financier (Chaîne de dépenses → Telemo) ;
- F4 : marchés immatriculés (Telemo → Chaîne de dépenses) ;
- F5 : paiements effectifs BCRG des marchés (Chaîne de dépenses → Telemo).
F1 (LFI/LFR) et F2 (mouvements de crédits) sont déjà couverts par l'extraction de la Chaîne Dépense.

Minimisation : les coordonnées bancaires (RIB/IBAN), l'adresse et le RCCM du titulaire, transmis dans F4,
ne sont pas repris dans l'entrepôt ; le NIF et la raison sociale suffisent au pilotage.
"""

from django.db import models

from apps.core.entrepot import FaitBase, dw_table, montant
from apps.referentiels.models import RefSection

MODES = [
    ("aoo", "Appel d'offres ouvert"),
    ("aor", "Appel d'offres restreint"),
    ("cotation", "Demande de cotation"),
    ("drp", "Demande de renseignements et de prix"),
    ("entente_directe", "Entente directe (gré à gré)"),
]
TYPES = [
    ("travaux", "Travaux"),
    ("fournitures", "Fournitures"),
    ("services", "Services"),
    ("prestations_intellectuelles", "Prestations intellectuelles"),
]


class FaitReservationCredit(FaitBase):
    """F3 — réservation de crédit sur une ligne budgétaire, après visa du contrôleur financier."""

    numero_reservation = models.CharField(max_length=64, db_index=True)
    date_creation = models.DateField(null=True, blank=True)
    date_validation = models.DateField(null=True, blank=True)
    date_visa = models.DateField(null=True, blank=True)
    ligne_budgetaire = models.CharField(max_length=120, blank=True, help_text="Clé d'imputation complète")
    section = models.ForeignKey(
        RefSection,
        to_field="code",
        db_column="section_code",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    objet = models.TextField(blank=True)
    autorite_contractante = models.CharField(max_length=200, blank=True)
    montant_reserve = montant()
    devise = models.CharField(max_length=8, default="GNF")

    class Meta:
        db_table = dw_table("fait_reservation_credit")


class FaitMarche(FaitBase):
    """F4 — marché immatriculé dans Telemo (une ligne par marché et par date de situation)."""

    MODES = MODES
    TYPES = TYPES
    # Libellés rencontrés dans les extractions (comparés sans accents ni majuscules).
    SYNONYMES = {
        "mode_passation": {
            "gre a gre": "entente_directe",
            "entente directe": "entente_directe",
            "ed": "entente_directe",
            "aoo": "aoo",
            "ao ouvert": "aoo",
            "aor": "aor",
            "ao restreint": "aor",
            "demande de cotation": "cotation",
            "drp": "drp",
        },
        "type_marche": {
            "prestation intellectuelle": "prestations_intellectuelles",
            "pi": "prestations_intellectuelles",
            "service": "services",
            "fourniture": "fournitures",
        },
    }
    STATUTS = [
        ("immatricule", "Immatriculé"),
        ("en_execution", "En exécution"),
        ("receptionne", "Réceptionné"),
        ("resilie", "Résilié"),
    ]

    numero_immatriculation = models.CharField(max_length=64, db_index=True)
    date_immatriculation = models.DateField(null=True, blank=True)
    numero_reservation = models.CharField(max_length=64, blank=True, db_index=True, help_text="Lien avec F3")
    objet = models.TextField(blank=True)
    type_marche = models.CharField(max_length=32, choices=TYPES)
    mode_passation = models.CharField(max_length=32, choices=MODES)
    autorite_contractante = models.CharField(max_length=200)
    section = models.ForeignKey(
        RefSection,
        to_field="code",
        db_column="section_code",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Ministère de rattachement (via la ligne budgétaire de la réservation)",
    )
    titulaire_nif = models.CharField(max_length=32, blank=True, db_index=True)
    titulaire = models.CharField(max_length=200, blank=True, help_text="Raison sociale")
    montant_ht = montant()
    montant_taxes = montant(help_text="TVA et autres taxes")
    montant_ttc = montant()
    devise = models.CharField(max_length=8, default="GNF")
    date_lancement = models.DateField(null=True, blank=True, help_text="Lancement de la procédure (si fourni)")
    date_signature = models.DateField(null=True, blank=True)
    date_approbation = models.DateField(null=True, blank=True)
    delai_execution_jours = models.PositiveIntegerField(null=True, blank=True)
    # Modalités de paiement : avance de démarrage, acomptes, retenue de garantie, pénalités.
    avance_demarrage_taux = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    retenue_garantie_taux = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    modalites_paiement = models.TextField(blank=True)
    statut = models.CharField(max_length=16, choices=STATUTS, default="immatricule")
    montant_avenants = montant()
    avancement_physique = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    recours = models.BooleanField(default=False)

    class Meta:
        db_table = dw_table("fait_marche")
        indexes = [models.Index(fields=["exercice", "date_situation", "mode_passation"])]


class FaitPaiementMarche(FaitBase):
    """F5 — paiement effectif (BCRG) d'un marché."""

    numero_immatriculation = models.CharField(max_length=64, db_index=True)
    date_paiement = models.DateField()
    reference_paiement = models.CharField(max_length=64, blank=True)
    montant_paiement = montant()

    class Meta:
        db_table = dw_table("fait_paiement_marche")
