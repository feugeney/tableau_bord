# Plan de mise en conformité avec les termes de référence

Référence : « Termes de Référence pour la mise en œuvre d'un Entrepôt de données au MEFB (V1.0) », Service de
Modernisation des Systèmes d'Information (SMSI).

Ce document suit, exigence par exigence, l'écart entre les termes de référence (TdR) et la plateforme, et
l'ordre des chantiers qui le comblent. Il est mis à jour à la fin de chaque chantier.

États : **fait**, **partiel**, **à faire**, **décision** (attend un arbitrage du ministère).

## 1. Chantiers

| N° | Chantier | TdR | État |
|---|---|---|---|
| 1 | Modèle de données et traçabilité : dimension temps, zones géographiques, identifiant UUID des flux, zone brute des fichiers reçus | 6.1, 6.2, 6.3, 6.4.2 | **fait** |
| 2 | Échanges et collecte automatisée : dépôt de fichiers par SFTP, messagerie AMQP (RabbitMQ), schémas JSON des flux, XML, TLS 1.3 | 4, 6.2, 6.4.1, 6.4.2 | **fait** (services SFTP et RabbitMQ à démarrer sur le serveur de recette) |
| 3 | Profils et outils d'analyse : profil analyste, exploration libre des données, accès pour un outil de BI | 3, 4 | **fait** |
| 4 | Raccordement des sources réelles, une direction à la fois (dépend des accès fournis) | 3, 5, 7.2 | à faire |
| 5 | Analyses prédictives : projections de fin d'exercice | 4, 6.1 | à faire |
| 6 | Données ouvertes : diffusion au public et aux partenaires | 4 | décision |
| 7 | Deux sites (local et cloud), sauvegarde et reprise | 6.1 | décision |
| 8 | Livrables : calendrier, rapport d'analyse et de conception, rapport d'étape, dossier de recette, guide d'exploitation, manuel utilisateur | 7.1 | **fait** (première version, `livrables/`) |

## 2. Matrice de conformité

### Objectifs et fonctionnalités (TdR 3 et 4)

| Exigence | État | Où |
|---|---|---|
| Intégrer des sources multiples, internes et externes | partiel | Connecteurs fichier, Oracle, PostgreSQL et API en place ; une seule source réelle (Chaîne Dépense). Chantier 4. |
| Nettoyer et transformer, cohérence et qualité | fait | `etl/nettoyage.py`, contrôles à chaque chargement, lignes rejetées comptées. |
| Modèles multidimensionnels (faits et dimensions) | fait | Schémas `dw` (faits) et `ref` (dimensions), vues `mart`. |
| Outils de consultation, d'analyse, de reporting, de visualisation | fait | Tableau de bord, alertes, export Excel, impression, exploration libre, compte de BI en lecture seule. |
| ETL | fait | `etl/connecteurs/`. |
| Mise à jour périodique selon la criticité | fait | Planification par source (Administration › Sources et connecteurs). |
| Accès sécurisé par profil (administrateurs, analystes, décideurs) | fait | Profils cabinet, directeur, analyste, administrateur, lecteur ; double authentification pour le cabinet, les administrateurs et les analystes. |
| Interopérabilité par standards ouverts | fait | API REST documentée, partage par jeton, dépôt SFTP, événements AMQP. Voir `echanges-partenaires.md`. |
| Reporting, BI ou IA (analyses prédictives) | partiel | Tableaux de bord faits ; prédictif : chantier 5. |
| Diffusion automatique, données ouvertes | décision | Chantier 6. |

### Architecture et flux (TdR 6.1 et 6.2)

| Exigence | État | Où |
|---|---|---|
| Trois couches : sources, ETL, entrepôt central | fait | |
| Orientation « data lakehouse » | partiel | Zone brute : chaque fichier ou réponse d'API reçu est conservé tel quel, adressé par son empreinte (`etl/zone_brute.py`). Pas de moteur lakehouse dédié : volume actuel traité par PostgreSQL. |
| Déploiement sur deux sites (local et cloud) | décision | Chantier 7. |
| Extraction par API sécurisées, fichiers plats, connecteurs directs | fait | |
| Normalisation, suppression des doublons, enrichissement | fait | Un fichier déjà chargé est signalé (même empreinte). |
| Chargement périodique | fait | |
| Contrôle qualité et traçabilité des flux | fait | Historique des chargements, identifiant UUID, empreinte SHA-256, fichier d'origine téléchargeable, journal d'audit. |

### Modèles de données (TdR 6.3)

| Exigence | État | Où |
|---|---|---|
| Faits : budgets exécutés, recettes fiscales, opérations douanières, paiements de dette, mouvements de trésorerie | fait | Tables `dw.fait_*`. |
| Dimension temps (jour, mois, trimestre, année) | fait | `ref.dim_temps`, une ligne par jour. |
| Dimension entités (directions, institutions) | fait | `ref.ref_section`, `ref.ref_sous_section`, `ref.ref_organisme`. |
| Dimension nature des opérations, catégories économiques | fait | `ref.ref_nature_economique`, `ref.ref_type_procedure`. |
| Dimension zones géographiques | partiel | `ref.ref_zone_geographique` (pays et régions, codes ISO 3166-2). Rattachement des bureaux de douane et des centres d'impôts : avec les données réelles (chantier 4). |

### Protocoles et standards (TdR 6.4)

| Exigence | État | Où |
|---|---|---|
| HTTPS, TLS 1.3 | fait | TLS 1.3 seul (`nginx/nginx.conf`). |
| API REST, OpenAPI 3.0 | fait | Schéma : `/api/schema/` ; documentation interactive : `/api/docs/`. |
| Messages AMQP 0.9.1 (RabbitMQ) | fait | Tâches planifiées et événements `chargement.<source>.<statut>` (`etl/evenements.py`). |
| Fichiers par SFTP | fait | Un dossier par source, relevé toutes les 5 minutes (`etl/depots.py`). |
| JSON (principal), CSV et XML (compatibilité) | fait | JSON, CSV, XML et Excel. |
| Validation par schéma JSON | fait | Schéma par flux, téléchargeable ; lignes non conformes écartées et comptées (`etl/schemas.py`). |
| Dates ISO 8601, encodage UTF-8 | fait | |
| Montants en francs guinéens, séparateur de milliers espace | fait | |
| Identifiants UUID v4 pour les transactions | fait | Chaque chargement porte un UUID v4. |

### Livrables (TdR 7.1)

| Livrable | État | Où |
|---|---|---|
| Calendrier prévisionnel | fait | `livrables/calendrier-previsionnel.md` (en mois ; date de lancement à arrêter avec le SMSI). |
| Rapport d'analyse et de conception | fait | `livrables/rapport-analyse-conception.md`. |
| Rapports d'étape | fait | `livrables/rapport-etape-1.md` ; un rapport par étape. |
| Dossier de recette | fait | `livrables/dossier-recette.md` ; à dérouler sur le serveur de recette. |
| Guide d'exploitation technique | fait | `livrables/guide-exploitation.md` ; procédures à valider sur le serveur de recette. |
| Manuel utilisateur | fait | `livrables/manuel-utilisateur.md`. |

## 3. Points des TdR à faire préciser par le SMSI

- **Périmètre** (TdR 5) : la liste nominative des applications, leur direction propriétaire et le mode d'accès.
- **Sources citées et absentes de la plateforme** : SAP, Banque Centrale, FMI.
- **« Temps réel »** (TdR 7.2) face à l'alimentation quotidienne, hebdomadaire ou mensuelle (TdR 4).
- **Calendrier** : l'entrepôt (mois 7-8) est placé après les flux ETL (mois 4-6).
- **Références à d'autres projets** : « implémentation du PE dans SIGFiP », « transactions PIAFIP ».
- **Critères de recette**, volumes, disponibilité attendue, sauvegarde, cadre de protection des données.
