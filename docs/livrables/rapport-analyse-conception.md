# Rapport d'analyse et de conception

Entrepôt de données du Ministère de l'Économie, des Finances et du Budget (MEFB) — livrable n° 2 des termes de
référence (TdR 7.1). Version 1.0, 10 octobre 2026.

## 1. Objet

Ce rapport décrit l'existant analysé, l'architecture retenue, le modèle de données, les flux d'alimentation,
la sécurité et les choix de conception de la plateforme « Système intégré de pilotage des finances
publiques ». Il renvoie, pour le détail, aux documents suivants :

- `../plan-conformite.md` : suivi, exigence par exigence, de la conformité aux TdR ;
- `../dictionnaire-indicateurs.md` : définition et formule de chaque indicateur ;
- `../echanges-partenaires.md` : contrat d'échange avec les applications sources et les partenaires ;
- `../flux-telemo.md` : flux entre la Chaîne de dépenses et Telemo.

## 2. Analyse de l'existant

### 2.1 Applications sources recensées

| Application | Structure | Domaine | Mode d'accès prévu | État |
|---|---|---|---|---|
| Chaîne Dépense (Oracle) | DNSI / DGB | Dépenses budgétaires | Extraction Excel aujourd'hui ; lecture directe Oracle prévue | **Données réelles** |
| SAFIG | Direction générale des impôts | Recettes fiscales | Fichier (Excel, CSV, XML, JSON) ou dépôt SFTP | Illustration |
| SYDONIA | Direction générale des douanes | Recettes douanières | Fichier ou dépôt SFTP | Illustration |
| SCIE (Système comptable intégré de l'État) | Trésor public | Trésorerie et comptabilité | Fichier ou dépôt SFTP | Illustration |
| Application de la dette (nom à confirmer) | Direction de la dette | Dette publique | Fichier ou dépôt SFTP | Illustration |
| SIGPIP | Investissements publics | Investissements publics | Fichier ou dépôt SFTP | Non raccordée |
| FUGAS | Gestion de la paie | Masse salariale | Fichier ou dépôt SFTP | Illustration |
| SICOM (comptabilité matière) | DNSI / DNCM | Patrimoine de l'État | Lecture directe PostgreSQL | Illustration |
| SYSOP (EPA et sociétés publiques) | DGPEIP | Portefeuille de l'État | Lecture directe PostgreSQL | Illustration |
| Telemo (marchés publics) | À confirmer | Marchés publics | API REST ou fichier | Illustration |
| PLEB | À confirmer | Préparation budgétaire | À définir | Non raccordée |

« Illustration » : la page correspondante est alimentée par des données fictives, signalées comme telles à
l'écran, en attendant le raccordement. Aucun chiffre fictif n'est attribué à un organisme réel.

### 2.2 Constats

- **Données cloisonnées** : chaque application a sa nomenclature. Le croisement repose sur des référentiels
  communs (ministères et institutions, nature économique, organismes).
- **Qualité variable des extractions** : libellés avec espaces parasites, codes stockés comme nombres (zéros
  initiaux perdus), valeurs absentes. Chaque chargement applique un nettoyage et des contrôles, bloquants ou
  non.
- **Écart de concordance sur l'extraction réelle** : sur l'extraction de la Chaîne Dépense du 16 août 2026, le
  total engagé diffère de 0,8 milliard de GNF entre deux onglets. Le contrôle correspondant est bloquant ; la
  tolérance à retenir est à arrêter avec la DGB (voir section 9).
- **Paiements hors chaîne** : certaines procédures (dette, salaires) sont payées hors de la chaîne de la
  dépense. Les indicateurs de paiement existent en version « ajustée » (ces procédures exclues) et « brute ».

### 2.3 Sources citées par les TdR et non recensées

SAP, la Banque Centrale et le FMI sont cités par les TdR mais ne figurent pas dans la liste des applications
communiquée. Leur périmètre est à préciser (voir section 9).

## 3. Architecture

### 3.1 Vue d'ensemble

```
Sources                  Collecte                    Entrepôt (PostgreSQL)              Restitution
─────────                ────────                    ─────────────────────              ───────────
Fichiers ───┐            Connecteurs :               Zone brute (fichiers reçus)        Tableau de bord (10 pages)
Dépôt SFTP ─┤            extraction ─ validation ─   ref   : dimensions                 Alertes
API REST ───┼──────────▶ chargement                  dw    : tables de faits            Exploration (analystes)
Oracle ─────┤            + contrôles de qualité      mart  : vues agrégées              Export Excel, impression
PostgreSQL ─┘            + journal des chargements                                      API REST, jetons de partage
                                                                                        Événements AMQP
                                                                                        Outil de BI (compte en lecture)
```

### 3.2 Composants

| Composant | Technologie | Rôle |
|---|---|---|
| Entrepôt | PostgreSQL 16 | Schémas `ref`, `dw`, `mart` ; tables d'administration dans `public` |
| Application serveur | Python, Django 5, Django REST Framework | API, règles de gestion, connecteurs, alertes |
| Tâches planifiées | Celery, Celery beat | Chargements automatiques, relève du dépôt SFTP |
| Messagerie | RabbitMQ (AMQP 0.9.1) | File des tâches ; événements publiés aux partenaires |
| Cache | Redis | Réponses de l'API (15 minutes, invalidées à chaque chargement) |
| Interface | React 18, TypeScript | Tableau de bord, exploration, administration |
| Frontal | nginx | Terminaison HTTPS (TLS 1.3), fichiers statiques |
| Dépôt de fichiers | Serveur SFTP | Réception des extractions des partenaires |

L'ensemble est décrit dans `docker-compose.yml` (neuf services).

### 3.3 Orientation « lakehouse »

Les TdR demandent une orientation « data lakehouse ». Le choix retenu est proportionné aux volumes actuels
(quelques milliers de lignes par chargement) :

- une **zone brute** conserve chaque fichier et chaque réponse d'API tels que reçus, adressés par leur
  empreinte SHA-256 ; tout chargement peut être rejoué à partir du reçu ;
- les données structurées sont dans PostgreSQL, sans moteur lakehouse dédié.

Si les volumes l'exigent (opérations douanières ou fiscales détaillées, plusieurs millions de lignes par
mois), la zone brute pourra être déplacée vers un stockage objet et les tables de faits les plus volumineuses
partitionnées par exercice, sans changer les connecteurs.

### 3.4 Déploiement

Un site est décrit aujourd'hui (conteneurs Docker). Les TdR demandent deux sites, local et cloud : le choix
de l'hébergeur et du mode de réplication relève d'un arbitrage du ministère (chantier 7 du plan de
conformité).

## 4. Modèle de données

### 4.1 Principes

- **Les situations datées s'empilent** : chaque table de faits porte l'exercice, la date de situation, la
  source et le chargement. Un nouveau chargement n'écrase jamais le précédent.
- **Le dernier chargement réussi fait foi** : pour une source, un exercice et une date de situation, seules
  les lignes du dernier chargement réussi sont lues (vue `mart.v_chargements_actifs`).
- **Référentiels communs fermés** : un code de ministère, de sous-section, d'organisme ou de zone inconnu
  rejette la ligne ; il n'est jamais créé à la volée.
- **Minimisation** : les données sans utilité pour le pilotage ne sont pas reprises (coordonnées bancaires,
  adresse et RCCM des titulaires de marchés).

### 4.2 Dimensions (schéma `ref`)

| Dimension | Table | Contenu |
|---|---|---|
| Temps | `dim_temps` | Une ligne par jour : année, semestre, trimestre, mois, semaine ISO, fin de mois |
| Exercice | `ref_exercice` | Année, dates de début et de fin, période complémentaire |
| Entités | `ref_section`, `ref_sous_section`, `ref_organisme` | Ministères et institutions, services, EPA et sociétés publiques |
| Nature des opérations | `ref_nature_economique`, `ref_type_procedure`, `ref_etat_dossier` | Titres et natures, procédures, états des dossiers |
| Zones géographiques | `ref_zone_geographique` | Pays et régions (codes ISO 3166-2) |
| Financement | `ref_bailleur`, `ref_groupe_bailleur`, `ref_source_financement` | Bailleurs et sources de financement |
| Tiers | `ref_beneficiaire` | Bénéficiaires, avec leurs variantes d'écriture |
| Propres aux domaines | `ref_impot`, `ref_centre_impots`, `ref_bureau_douane`, `ref_type_creancier`, `ref_categorie_bien`, `ref_projet`… | Complétés automatiquement au chargement |

### 4.3 Tables de faits (schéma `dw`)

| Domaine | Tables |
|---|---|
| Dépenses | `fait_situation_ligne`, `fait_engagement`, `fait_operation`, `fait_regie` |
| Recettes fiscales | `fait_recouvrement_fiscal`, `fait_reste_a_recouvrer`, `fait_contentieux`, `fait_contribuables` |
| Recettes douanières | `fait_recette_douane`, `fait_declaration`, `fait_exoneration` |
| Trésorerie | `fait_flux_tresorerie`, `fait_depots_correspondants`, `fait_delai_paiement`, `fait_tofe` |
| Dette | `fait_encours_dette`, `fait_echeancier_dette`, `fait_indicateur_macro` |
| Investissements | `fait_avancement_projet` (le volet financier vient de la Chaîne Dépense) |
| Masse salariale | `fait_paie`, `fait_controle_paie` |
| Patrimoine | `fait_patrimoine`, `fait_parc_vehicules`, `fait_controle_patrimoine`, `fait_deploiement_sicom` |
| Portefeuille | `fait_subvention_epa`, `fait_dividende`, `fait_sante_financiere`, `fait_gouvernance`, `fait_budget_epa` |
| Marchés publics | `fait_reservation_credit`, `fait_marche`, `fait_paiement_marche` |

### 4.4 Vues agrégées (schéma `mart`)

Huit vues matérialisées, rafraîchies après chaque chargement : `mv_depense_par_section_titre`,
`mv_depense_synthese`, `mv_depense_mensuelle`, `mv_restes_a_payer_anciennete`, `mv_depense_procedures`,
`mv_depense_beneficiaires`, `mv_investissement_projets`, `mv_synthese_globale`.

## 5. Flux d'alimentation

### 5.1 Cycle d'un chargement

1. **Réception** : fichier importé, fichier relevé dans le dépôt SFTP, réponse d'API ou lecture directe.
2. **Extraction** : lecture, mise en correspondance des colonnes selon le mapping configuré.
3. **Validation** : contrôles bloquants (colonnes obligatoires, concordance) et avertissements.
4. **Chargement** : écriture en une transaction ; en cas d'échec, rien n'est écrit.
5. **Après chargement** : rafraîchissement des vues, évaluation des alertes, invalidation du cache,
   publication d'un événement AMQP.

Chaque chargement est tracé : identifiant UUID, fichier d'origine conservé et empreinte, lignes lues,
chargées et rejetées, résultat de chaque contrôle, durée, auteur.

### 5.2 Connecteurs

| Connecteur | Usage |
|---|---|
| Excel — Chaîne Dépense | Extraction multi-onglets de la Chaîne Dépense |
| Oracle — Chaîne Dépense | Lecture directe, refusée aux heures ouvrées pour ne pas charger la production |
| Générique (Excel, CSV, XML, JSON) | Toute extraction, par mapping de colonnes configurable sans code |
| PostgreSQL | SICOM et SYSOP, compte en lecture seule, requêtes `SELECT` uniquement |
| API REST | Telemo et autres ; pagination suivie, jeton hors base |

### 5.3 Périodicité

La planification se règle par source dans le module d'administration (expression cron). Les connecteurs
automatiques (Oracle, PostgreSQL, API) sont planifiés la nuit à 2 heures par défaut ; le dépôt SFTP est relevé
toutes les 5 minutes.

## 6. Règles de gestion, seuils et alertes

Les règles sont centralisées dans un seul module (`apps/core/regles.py`) et tous les seuils sont paramétrables
depuis l'administration, sans intervention sur le code. Seize paramètres et quinze règles d'alerte sont en
place ; leur liste et leurs formules figurent dans `../dictionnaire-indicateurs.md`.

Les alertes ont trois niveaux de gravité (critique, sérieux, vigilance), sont recalculées à chaque
chargement, et peuvent être marquées comme traitées.

## 7. Sécurité et gouvernance des données

| Sujet | Disposition |
|---|---|
| Chiffrement en transit | HTTPS, TLS 1.3 uniquement |
| Authentification | Identifiant et mot de passe ; jetons de courte durée (30 minutes, renouvelables 10 heures) ; limitation des tentatives de connexion |
| Double authentification | Obligatoire pour le cabinet, les administrateurs et les analystes (code à usage unique) |
| Profils | Ministre / Cabinet, Directeur, Analyste, Administrateur, Lecteur |
| Cloisonnement | Par domaine, appliqué dans l'API et pas seulement à l'écran |
| Comptes sur les sources | Lecture seule ; aucun secret stocké en base |
| Journal d'audit | Connexions, consultations, imports, exports, changements de paramètres et d'alertes |
| Partage avec un partenaire | Jeton en lecture seule, limité à des domaines, révocable ; seule son empreinte est stockée |
| Exposition | Réseau du ministère ou VPN ; pas d'exposition directe sur Internet |
| Données d'illustration | Organismes et personnes fictifs ; retirées dès le premier chargement réel de la source |

## 8. Restitution

- **Tableau de bord** : dix pages (synthèse, dépenses, trésorerie, recettes fiscales, recettes douanières,
  dette, investissements, patrimoine, portefeuille, marchés publics). Chaque chiffre affiche sa source, son
  statut (réel ou illustration) et sa date de situation.
- **Exploration** : requêtes libres par jeu de données, axes, mesures et filtres, pour les analystes.
- **Exports** : Excel pour chaque page et pour chaque résultat d'exploration ; impression A4 paysage.
- **Outil de BI** : compte PostgreSQL en lecture seule sur les vues agrégées et les dimensions.
- **API REST** documentée (OpenAPI 3.0).

## 9. Points ouverts à arbitrer

| N° | Point | Interlocuteur |
|---|---|---|
| 1 | Liste nominative des applications du périmètre, direction propriétaire et mode d'accès de chacune | SMSI |
| 2 | Périmètre de SAP, de la Banque Centrale et du FMI | SMSI |
| 3 | Tolérance du contrôle de concordance de la Chaîne Dépense (l'extraction réelle présente un écart de 0,8 Md) | DGB |
| 4 | Libellés officiels : codes de régulation, types de budget, libellés courts des ministères | DGB |
| 5 | Mode d'échange réel de l'API Telemo et structure propriétaire | À identifier |
| 6 | Seuil réglementaire de l'entente directe | Autorité des marchés publics |
| 7 | Nom de l'application de la dette ; périmètre de PLEB | Directions concernées |
| 8 | Données publiables en données ouvertes | Cabinet |
| 9 | Hébergeur et mode de réplication du second site | SMSI |
| 10 | « Temps réel » (TdR 7.2) : fréquence d'alimentation réellement attendue par source | SMSI |
