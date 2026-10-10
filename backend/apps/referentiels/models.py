"""Référentiels communs (schéma PostgreSQL « ref »).

Ils sont partagés par toutes les sources et permettent de croiser les données :
identifiant unique de l'État, nomenclature budgétaire, compte comptable, exercice.
"""

from django.db import models


def ref_table(nom: str) -> str:
    # Astuce Django pour cibler un schéma PostgreSQL : 'schema"."table'.
    return f'ref"."{nom}'


class CodeLibelle(models.Model):
    code = models.CharField(max_length=32, unique=True)
    libelle = models.CharField(max_length=255, blank=True)

    class Meta:
        abstract = True
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.libelle}" if self.libelle else self.code


class RefExercice(models.Model):
    annee = models.PositiveSmallIntegerField(primary_key=True)
    libelle = models.CharField(max_length=32, blank=True)
    date_debut = models.DateField(null=True, blank=True)
    date_fin = models.DateField(null=True, blank=True)
    fin_periode_complementaire = models.DateField(null=True, blank=True)

    class Meta:
        db_table = ref_table("ref_exercice")
        ordering = ["-annee"]

    def __str__(self):
        return str(self.annee)


class DimTemps(models.Model):
    """Dimension temps : une ligne par jour (table « ref.dim_temps »)."""

    date = models.DateField(primary_key=True)
    annee = models.PositiveSmallIntegerField(db_index=True)
    semestre = models.PositiveSmallIntegerField()
    trimestre = models.PositiveSmallIntegerField()
    mois = models.PositiveSmallIntegerField()
    jour = models.PositiveSmallIntegerField()
    semaine_iso = models.PositiveSmallIntegerField()
    jour_semaine = models.PositiveSmallIntegerField(help_text="1 = lundi … 7 = dimanche (ISO 8601)")
    libelle_mois = models.CharField(max_length=24, help_text="ex. « août 2026 »")
    libelle_trimestre = models.CharField(max_length=12, help_text="ex. « T3 2026 »")
    fin_de_mois = models.BooleanField(default=False)

    class Meta:
        db_table = ref_table("dim_temps")
        ordering = ["date"]

    def __str__(self):
        return self.date.isoformat()


class TypeZone(models.TextChoices):
    PAYS = "pays", "Pays"
    REGION = "region", "Région administrative"
    PREFECTURE = "prefecture", "Préfecture"
    COMMUNE = "commune", "Commune"


class RefZoneGeographique(CodeLibelle):
    """Dimension géographique. Codes ISO 3166-2 pour le pays et les régions (ex. « GN-K » : Kankan)."""

    type = models.CharField(max_length=12, choices=TypeZone.choices)
    parent = models.ForeignKey(
        "self", to_field="code", db_column="parent_code", null=True, blank=True, on_delete=models.PROTECT
    )

    class Meta(CodeLibelle.Meta):
        db_table = ref_table("ref_zone_geographique")


def zone():
    """Rattachement géographique facultatif d'un référentiel."""
    return models.ForeignKey(
        RefZoneGeographique,
        to_field="code",
        db_column="zone_code",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )


class TypeSection(models.TextChoices):
    MINISTERE = "ministere", "Ministère"
    INSTITUTION = "institution", "Institution"
    DEPENSES_COMMUNES = "depenses_communes", "Dépenses communes"


class RefSection(CodeLibelle):
    libelle_source = models.CharField(max_length=255, blank=True, help_text="Libellé brut de l'extraction")
    libelle_court = models.CharField(max_length=80, blank=True)
    type = models.CharField(max_length=24, choices=TypeSection.choices, default=TypeSection.MINISTERE)
    identifiant_etat = models.CharField(max_length=32, blank=True, help_text="Identifiant unique de l'État")
    fictif = models.BooleanField(default=False, help_text="Section fictive (données de démonstration)")

    class Meta(CodeLibelle.Meta):
        db_table = ref_table("ref_section")

    @property
    def libelle_affiche(self):
        return self.libelle_court or self.libelle


class RefSousSection(CodeLibelle):
    section = models.ForeignKey(RefSection, to_field="code", db_column="section_code", on_delete=models.PROTECT)

    class Meta(CodeLibelle.Meta):
        db_table = ref_table("ref_sous_section")


class RefNatureEconomique(CodeLibelle):
    """Hiérarchie titre › chapitre › article › paragraphe › sous-paragraphe.

    Le code est la concaténation pointée : « 5 », « 5.1 », « 5.1.1 », « 5.1.1.10 », « 5.1.1.10.01 ».
    """

    NIVEAUX = ["titre", "chapitre", "article", "paragraphe", "sous_paragraphe"]
    niveau = models.PositiveSmallIntegerField()  # 1 = titre … 5 = sous-paragraphe
    titre = models.CharField(max_length=4)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="enfants")

    class Meta(CodeLibelle.Meta):
        db_table = ref_table("ref_nature_economique")
        indexes = [models.Index(fields=["niveau", "titre"])]


# Codes titre et filtre « nature » de l'API.
TITRES = {"1": "Dette", "2": "Personnel", "3": "Biens et services", "4": "Transferts", "5": "Investissement"}
NATURE_VERS_TITRE = {"dette": "1", "personnel": "2", "biens_services": "3", "transferts": "4", "investissement": "5"}


class RefSourceFinancement(CodeLibelle):
    class Meta(CodeLibelle.Meta):
        db_table = ref_table("ref_source_financement")


class RefGroupeBailleur(CodeLibelle):
    class Meta(CodeLibelle.Meta):
        db_table = ref_table("ref_groupe_bailleur")


class RefBailleur(CodeLibelle):
    class Meta(CodeLibelle.Meta):
        db_table = ref_table("ref_bailleur")


class RefRegulation(CodeLibelle):
    """Libellés à renseigner par la DGB (codes 00, 01…, xx)."""

    class Meta(CodeLibelle.Meta):
        db_table = ref_table("ref_regulation")


class RefTypeBudget(CodeLibelle):
    class Meta(CodeLibelle.Meta):
        db_table = ref_table("ref_type_budget")


class RefTypeProcedure(models.Model):
    """Procédure d'exécution (colonne « Type engagement » de la Chaîne Dépense)."""

    libelle = models.CharField(max_length=120, unique=True)
    paiement_hors_chaine = models.BooleanField(default=False)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = ref_table("ref_type_procedure")
        ordering = ["libelle"]

    def __str__(self):
        return self.libelle


class RefEtatDossier(models.Model):
    libelle = models.CharField(max_length=120, unique=True)
    engagement_valide = models.BooleanField(default=False)

    class Meta:
        db_table = ref_table("ref_etat_dossier")
        ordering = ["libelle"]

    def __str__(self):
        return self.libelle


class RefBeneficiaire(models.Model):
    nom_normalise = models.CharField(max_length=255, unique=True)
    nom_affiche = models.CharField(max_length=255)
    identifiant_etat = models.CharField(max_length=32, blank=True, help_text="NIF ou identifiant unique")

    class Meta:
        db_table = ref_table("ref_beneficiaire")
        ordering = ["nom_affiche"]

    def __str__(self):
        return self.nom_affiche


class RefBeneficiaireAlias(models.Model):
    """Variante rapprochée d'un bénéficiaire (ex. « TRAOREGassimou » → « TRAORE Gassimou »)."""

    alias = models.CharField(max_length=255, unique=True, help_text="Clé normalisée de la variante")
    beneficiaire = models.ForeignKey(RefBeneficiaire, on_delete=models.CASCADE, related_name="alias")
    origine = models.CharField(max_length=16, default="auto", choices=[("auto", "auto"), ("manuel", "manuel")])

    class Meta:
        db_table = ref_table("ref_beneficiaire_alias")


class TypeOrganisme(models.TextChoices):
    EPA = "epa", "Établissement public administratif"
    SOCIETE = "societe", "Société publique"


class RefOrganisme(models.Model):
    """Organismes du portefeuille de l'État (SYSOP : 152 EPA et 80 sociétés publiques)."""

    identifiant_etat = models.CharField(max_length=32, unique=True)
    nom = models.CharField(max_length=255)
    sigle = models.CharField(max_length=40, blank=True)
    type = models.CharField(max_length=16, choices=TypeOrganisme.choices)
    tutelle = models.ForeignKey(
        RefSection, to_field="code", db_column="tutelle_code", null=True, blank=True, on_delete=models.SET_NULL
    )
    fictif = models.BooleanField(default=False, help_text="Organisme fictif (données de démonstration)")

    class Meta:
        db_table = ref_table("ref_organisme")
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class RefCompteComptable(CodeLibelle):
    classe = models.CharField(max_length=2, blank=True)

    class Meta(CodeLibelle.Meta):
        db_table = ref_table("ref_compte_comptable")


# ---- Référentiels propres aux autres domaines --------------------------------


class RefImpot(CodeLibelle):
    class Meta(CodeLibelle.Meta):
        db_table = ref_table("ref_impot")


class RefCentreImpots(CodeLibelle):
    zone = zone()

    class Meta(CodeLibelle.Meta):
        db_table = ref_table("ref_centre_impots")


class RefSecteurActivite(CodeLibelle):
    class Meta(CodeLibelle.Meta):
        db_table = ref_table("ref_secteur_activite")


class RefBureauDouane(CodeLibelle):
    zone = zone()

    class Meta(CodeLibelle.Meta):
        db_table = ref_table("ref_bureau_douane")


class RefNatureDroitDouane(CodeLibelle):
    class Meta(CodeLibelle.Meta):
        db_table = ref_table("ref_nature_droit_douane")


class RefTypeCreancier(CodeLibelle):
    exterieur = models.BooleanField(default=True)

    class Meta(CodeLibelle.Meta):
        db_table = ref_table("ref_type_creancier")


class RefCategorieBien(CodeLibelle):
    class Meta(CodeLibelle.Meta):
        db_table = ref_table("ref_categorie_bien")


class RefProjet(CodeLibelle):
    """Projet d'investissement (SIGPIP), rapproché de la sous-section de la Chaîne Dépense."""

    sous_section = models.ForeignKey(
        RefSousSection, to_field="code", db_column="sous_section_code", null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta(CodeLibelle.Meta):
        db_table = ref_table("ref_projet")
