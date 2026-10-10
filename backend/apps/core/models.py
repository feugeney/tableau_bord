"""Socle : utilisateurs, rôles, sources, chargements, paramètres, alertes et audit."""

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class Domaine(models.TextChoices):
    SYNTHESE = "synthese", "Synthèse"
    DEPENSE = "depense", "Dépenses budgétaires"
    RECETTES_FISCALES = "recettes_fiscales", "Recettes fiscales"
    DOUANES = "douanes", "Recettes douanières"
    TRESOR = "tresor", "Trésorerie et comptabilité"
    DETTE = "dette", "Dette publique"
    INVESTISSEMENT = "investissement", "Investissements publics"
    PAIE = "paie", "Masse salariale"
    PATRIMOINE = "patrimoine", "Patrimoine de l'État"
    PORTEFEUILLE = "portefeuille", "Portefeuille de l'État"
    MARCHES_PUBLICS = "marches_publics", "Marchés publics"
    PREPARATION = "preparation", "Préparation budgétaire"


class Role(models.TextChoices):
    MINISTRE_CABINET = "ministre_cabinet", "Ministre / Cabinet"
    DIRECTEUR = "directeur", "Directeur (son domaine)"
    DNSI_ADMIN = "dnsi_admin", "Administrateur DNSI"
    ANALYSTE = "analyste", "Analyste (exploration de ses domaines)"
    LECTEUR = "lecteur", "Lecteur"


# L'analyste accède au détail des données (bénéficiaires, titulaires) : double authentification exigée.
ROLES_2FA = {Role.MINISTRE_CABINET, Role.DNSI_ADMIN, Role.ANALYSTE}


class Utilisateur(AbstractUser):
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.LECTEUR)
    # Domaines visibles pour les rôles "directeur", "analyste" et "lecteur" (liste de codes Domaine).
    domaines = models.JSONField(default=list, blank=True)
    structure = models.CharField(max_length=120, blank=True, help_text="DGI, DGD, Trésor, DGB, DGPEIP…")

    class Meta:
        db_table = "core_utilisateur"
        verbose_name = "utilisateur"

    @property
    def exige_2fa(self) -> bool:
        return self.role in ROLES_2FA

    def voit_tout(self) -> bool:
        return self.is_superuser or self.role in (Role.MINISTRE_CABINET, Role.DNSI_ADMIN)

    def peut_voir(self, domaine: str) -> bool:
        if self.voit_tout():
            return True
        if domaine == Domaine.SYNTHESE:
            # La synthèse ne montre que les blocs autorisés (filtrage dans l'API).
            return True
        return domaine in (self.domaines or [])

    def peut_exporter(self, domaine: str) -> bool:
        if self.role == Role.LECTEUR:
            return False
        return self.peut_voir(domaine)


class StatutSource(models.TextChoices):
    REEL = "reel", "Données réelles"
    DEMO = "demo", "Données de démonstration"
    NON_RACCORDE = "non_raccorde", "Source non raccordée"


class TypeConnecteur(models.TextChoices):
    EXCEL_CHAINE_DEPENSE = "excel_chaine_depense", "Excel — Chaîne Dépense"
    ORACLE_CHAINE_DEPENSE = "oracle_chaine_depense", "Oracle — Chaîne Dépense"
    EXCEL_GENERIQUE = "excel_generique", "Excel / CSV générique"
    POSTGRES = "postgres", "PostgreSQL"
    API = "api", "API"
    AUCUN = "aucun", "Aucun"


class Source(models.Model):
    code = models.SlugField(max_length=40, unique=True)
    domaine = models.CharField(max_length=32, choices=Domaine.choices)
    application = models.CharField(max_length=120)
    structure = models.CharField(max_length=160)
    statut = models.CharField(max_length=16, choices=StatutSource.choices, default=StatutSource.NON_RACCORDE)
    connecteur = models.CharField(max_length=32, choices=TypeConnecteur.choices, default=TypeConnecteur.AUCUN)
    configuration = models.JSONField(default=dict, blank=True, help_text="Paramètres du connecteur (sans secrets).")
    planification_cron = models.CharField(max_length=64, blank=True, help_text="ex. « 0 2 * * * » (nuit)")
    en_production_depuis = models.DateField(null=True, blank=True)
    remarque = models.CharField(max_length=255, blank=True)
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "core_source"
        ordering = ["ordre", "code"]

    def __str__(self):
        return f"{self.application} ({self.code})"


class StatutChargement(models.TextChoices):
    EN_COURS = "en_cours", "En cours"
    APERCU = "apercu", "Aperçu (non chargé)"
    SUCCES = "succes", "Succès"
    ECHEC = "echec", "Échec"


class Chargement(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, help_text="Identifiant du flux (UUID v4)")
    source = models.ForeignKey(Source, on_delete=models.PROTECT, related_name="chargements")
    fichier = models.CharField(max_length=255, blank=True)
    fichier_archive = models.CharField(
        max_length=255, blank=True, help_text="Copie conservée telle que reçue (zone brute), relative à MEDIA_ROOT"
    )
    empreinte_sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    exercice = models.PositiveSmallIntegerField(null=True, blank=True)
    date_situation = models.DateField(null=True, blank=True)
    lignes_lues = models.PositiveIntegerField(default=0)
    lignes_rejetees = models.PositiveIntegerField(default=0)
    lignes_chargees = models.PositiveIntegerField(default=0)
    detail = models.JSONField(default=dict, blank=True, help_text="Comptes par onglet, contrôles…")
    debut = models.DateTimeField(auto_now_add=True)
    fin = models.DateTimeField(null=True, blank=True)
    duree_secondes = models.FloatField(null=True, blank=True)
    statut = models.CharField(max_length=16, choices=StatutChargement.choices, default=StatutChargement.EN_COURS)
    message_erreur = models.TextField(blank=True)
    utilisateur = models.ForeignKey("core.Utilisateur", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = "core_chargement"
        ordering = ["-debut"]
        indexes = [models.Index(fields=["source", "statut", "-date_situation"])]


class Parametre(models.Model):
    """Seuils et règles paramétrables (valeurs par défaut dans apps.core.regles.PARAMETRES_DEFAUT)."""

    code = models.CharField(max_length=64, unique=True)
    valeur = models.JSONField()
    libelle = models.CharField(max_length=255)
    unite = models.CharField(max_length=32, blank=True)
    modifie_le = models.DateTimeField(auto_now=True)
    modifie_par = models.ForeignKey("core.Utilisateur", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = "core_parametre"
        ordering = ["code"]


class MappingColonnes(models.Model):
    """Mapping configurable colonne source → champ cible, pour les connecteurs génériques."""

    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="mappings")
    table_cible = models.CharField(max_length=64, help_text="ex. fait_recouvrement_fiscal")
    onglet = models.CharField(max_length=120, blank=True)
    colonne_source = models.CharField(max_length=160)
    champ_cible = models.CharField(max_length=64)
    type_donnee = models.CharField(
        max_length=16,
        choices=[
            ("texte", "texte"),
            ("code", "code"),
            ("montant", "montant"),
            ("entier", "entier"),
            ("date", "date"),
            ("taux", "taux"),
            ("booleen", "booléen"),
        ],
        default="texte",
    )
    obligatoire = models.BooleanField(default=False)

    class Meta:
        db_table = "core_mapping_colonnes"
        unique_together = [("source", "table_cible", "champ_cible")]


class Severite(models.TextChoices):
    CRITIQUE = "critique", "Critique"
    SERIEUX = "serieux", "Sérieux"
    VIGILANCE = "vigilance", "Vigilance"


SEVERITE_ORDRE = {Severite.CRITIQUE: 0, Severite.SERIEUX: 1, Severite.VIGILANCE: 2}


class RegleAlerte(models.Model):
    code = models.SlugField(max_length=64, unique=True)
    domaine = models.CharField(max_length=32, choices=Domaine.choices)
    severite = models.CharField(max_length=16, choices=Severite.choices)
    classe = models.CharField(max_length=160, help_text="Chemin Python de l'évaluateur (apps.core.alertes.…)")
    seuils = models.JSONField(default=dict, blank=True)
    titre_modele = models.CharField(max_length=255)
    message_modele = models.TextField(help_text="Variables entre accolades : {nombre}, {montant}…")
    action_recommandee = models.TextField(blank=True)
    lien = models.CharField(max_length=160, blank=True, help_text="Route du frontend, ex. /depenses")
    actif = models.BooleanField(default=True)

    class Meta:
        db_table = "core_regle_alerte"
        ordering = ["domaine", "code"]


class StatutAlerte(models.TextChoices):
    NOUVELLE = "nouvelle", "Nouvelle"
    VUE = "vue", "Vue"
    TRAITEE = "traitee", "Traitée"


class Alerte(models.Model):
    regle = models.ForeignKey(RegleAlerte, null=True, on_delete=models.SET_NULL, related_name="alertes")
    date = models.DateTimeField(auto_now_add=True)
    domaine = models.CharField(max_length=32, choices=Domaine.choices)
    source = models.ForeignKey(Source, null=True, on_delete=models.SET_NULL)
    chargement = models.ForeignKey(Chargement, null=True, blank=True, on_delete=models.SET_NULL)
    date_situation = models.DateField(null=True, blank=True)
    severite = models.CharField(max_length=16, choices=Severite.choices)
    titre = models.CharField(max_length=255)
    message = models.TextField()
    valeur = models.CharField(max_length=64, blank=True, help_text="Chiffre clé affiché")
    action_recommandee = models.TextField(blank=True)
    lien = models.CharField(max_length=160, blank=True)
    statut = models.CharField(max_length=16, choices=StatutAlerte.choices, default=StatutAlerte.NOUVELLE)
    statut_modifie_par = models.ForeignKey("core.Utilisateur", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = "core_alerte"
        ordering = ["-date"]
        indexes = [models.Index(fields=["domaine", "severite", "statut"])]


class JournalAudit(models.Model):
    class Action(models.TextChoices):
        CONNEXION = "connexion", "Connexion"
        ECHEC_CONNEXION = "echec_connexion", "Échec de connexion"
        CONSULTATION = "consultation", "Consultation"
        EXPORT = "export", "Export"
        IMPORT = "import", "Import"
        PARAMETRE = "parametre", "Modification de paramètre"
        ALERTE = "alerte", "Changement de statut d'alerte"

    date = models.DateTimeField(auto_now_add=True, db_index=True)
    utilisateur = models.ForeignKey("core.Utilisateur", null=True, on_delete=models.SET_NULL)
    identifiant = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=32, choices=Action.choices)
    objet = models.CharField(max_length=255, blank=True)
    detail = models.JSONField(default=dict, blank=True)
    adresse_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "core_journal_audit"
        ordering = ["-date"]


class JetonPartage(models.Model):
    """Jeton d'accès en lecture seule à l'API, pour partager des données avec un système tiers.

    La clé n'est jamais stockée en clair : seule son empreinte SHA-256 l'est. Chaque jeton est
    rattaché à un compte technique (rôle « lecteur ») limité aux domaines partagés.
    """

    nom = models.CharField(max_length=120)
    destinataire = models.CharField(max_length=160, help_text="Structure ou système destinataire")
    domaines = models.JSONField(default=list)
    prefixe = models.CharField(max_length=12, unique=True)
    empreinte = models.CharField(max_length=64, unique=True)
    compte = models.OneToOneField("core.Utilisateur", on_delete=models.CASCADE, related_name="jeton_partage")
    expire_le = models.DateField(null=True, blank=True)
    actif = models.BooleanField(default=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    cree_par = models.ForeignKey("core.Utilisateur", null=True, on_delete=models.SET_NULL, related_name="+")
    derniere_utilisation = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "core_jeton_partage"
        ordering = ["-cree_le"]
