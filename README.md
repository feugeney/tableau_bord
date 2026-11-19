# Tableau de bord des finances publiques — MEFB (République de Guinée)

Tableau de bord de la Ministre de l'Économie, des Finances et du Budget : dépenses, trésorerie, recettes,
dette, investissements, patrimoine, portefeuille de l'État et marchés publics, alimentés depuis une base centrale.

Base centrale de données financières de l'État alimentée par ETL et tableau de bord décisionnel : exécution budgétaire,
recettes, trésorerie, dette, investissements, patrimoine, portefeuille et paie. Chaque chiffre affiché
indique sa source et sa date de situation.

| Couche | Technologies |
|---|---|
| Backend | Python 3.12, Django 5, DRF, python-oracledb, pandas/openpyxl |
| Base centrale | PostgreSQL natif, schémas `staging`, `ref`, `dw`, `mart` |
| Frontend | React 18, TypeScript, Vite, Tailwind (composants façon shadcn/ui), TanStack Query et Table, Recharts |
| Poste local | PostgreSQL et Django ; interface compilée servie sur le même port |

## Démarrage local sous Windows

Le projet fonctionne sans Docker, Redis, RabbitMQ ni Nginx. PostgreSQL conserve la base centrale ;
Django sert l'API et l'interface compilée sur **http://127.0.0.1:8000**.

Prérequis pour une nouvelle installation : Python 3.12 ou plus récent, PostgreSQL natif et Node.js avec npm.
Node sert à compiler l'interface ; aucun serveur Node n'est nécessaire pendant l'utilisation.

1. Double-cliquer sur **Installer.cmd** une première fois : dépendances, compilation, base et migrations.
2. Double-cliquer sur **Lancer.cmd** : PostgreSQL et l'application démarrent ; le navigateur s'ouvre.
3. **Sauvegarder.cmd** produit une archive PostgreSQL vérifiée dans `sauvegardes/`.
4. **Arreter.cmd** arrête l'application et son instance PostgreSQL sans effacer les données.

Le fichier de configuration utilisé est **backend/.env**. Les secrets et connexions Oracle/SYSOP
existants sont conservés. Les initialisations suivantes préservent les comptes et les données.
Une première installation sans aucun compte crée `admin-local` et enregistre ses identifiants dans
`backend/.local/identifiants-initiaux.txt`, ignoré par Git ; la double authentification s'enrôle à la connexion.

La base est stockée dans `%LOCALAPPDATA%\tdb-ministre\pgdata`, hors du dossier synchronisé OneDrive.
Une base déjà présente est réutilisée. Les imports ETL se lancent manuellement depuis l'administration.
La programmation Celery reste une fonctionnalité séparée ; aucun worker ou broker n'est requis pour consulter
les pages, importer manuellement ou exporter les rapports. Le dépôt de fichiers local reste disponible.

L'application écoute uniquement sur le poste local. API : `/api/v1/` ; documentation : `/api/docs/` ;
administration Django : `/admin/`. Journaux : `backend/.local/logs/`.

Diagnostic : `powershell -ExecutionPolicy Bypass -File scripts/local.ps1 -Action diagnostic`.

## Développement local

```bash
# Backend (PostgreSQL local, Redis facultatif : REDIS_URL vide = cache mémoire)
cd backend
python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt   # Windows ; bin/ sous Linux
# Conserver backend/.env cree par Installer.cmd.
python manage.py migrate && python manage.py initialiser
python manage.py runserver

# Frontend (proxy /api → localhost:8000)
cd frontend && npm install && npm run dev
```

Qualité : `ruff check . && black --check . && pytest` (backend) ; `npm run lint && npm run typecheck && npm test` (frontend).
La CI GitHub Actions (`.github/workflows/ci.yml`) exécute l'ensemble et exige 80 % de couverture.

## Exports PDF

Chaque rubrique métier propose **Exporter (PDF)** à côté d'Excel. Les documents reprennent
la charte institutionnelle (armoiries, bleu marine, filet tricolore, indicateurs et tableaux),
les filtres, les dates et les sources de chaque bloc. Les tableaux sont paginés avec en-têtes
répétés ; les données d'illustration sont signalées et les données absentes restent indisponibles.

Depuis **Synthèse**, **Rapport complet (PDF)** regroupe uniquement les rubriques que l'utilisateur
peut exporter. Sans période imposée, chaque source conserve sa dernière situation propre ; une
période explicitement sélectionnée n'est pas remplacée par une autre période disponible.
L'Exploration propose également un PDF, en GNF, avec un maximum de 2 000 lignes annoncé dans
le document ; Excel reste disponible pour les volumes supérieurs.

API : `/api/v1/export/<page>.pdf`, `/api/v1/export/rapport.pdf`, `/api/v1/exploration/export.pdf`.
Les mêmes permissions et exigences de double authentification s'appliquent ; les exports sont
journalisés. Le rendu est produit localement par ReportLab, sans service tiers.

## Guide d'import — Chaîne Dépense (lot 1)

```bash
python manage.py import_chaine_depense "SC de 2025-2025 en date du 15-09-2026.xlsx" --date-situation 2026-09-15
python manage.py import_chaine_depense fichier.xlsx --apercu     # valide sans charger
```

Ou depuis l'API (rôle `dnsi_admin`) : `POST /api/v1/sources/chaine_depense/import/` (multipart :
`fichier`, `date_situation`, `exercice`, `apercu`).

- L'exercice et la date de situation sont lus dans le nom du fichier (« SC de AAAA-AAAA en date du JJ-MM-AAAA »),
  puis dans la colonne `Exercice`. Tous deux restent modifiables à l'import.
- Onglets lus : Situation courante, Liste des engagements, Détails des opérations, Régie et APAD. Les autres onglets
  (Délégations de crédits…) sont ignorés. Les colonnes supplémentaires de « Situation courante »
  (pilier Simandou, projet green, fonctionnelle…) sont conservées dans `attributs`.
- **Contrôle bloquant** : le total engagé de « Situation courante » doit égaler celui de « Liste des engagements »
  à 1 GNF près par million (paramètre `concordance_tolerance_par_million`). Sinon rien n'est chargé.
- Les situations s'empilent par date. Recharger une même date garde l'historique, mais seul le dernier chargement
  réussi est pris en compte (`mart.v_chargements_actifs`).
- Les autres sources passent par `ExcelGenericConnector`, avec un mapping configuré dans l'admin
  (Sources › Mapping des colonnes), ou par `PostgresConnector` (SICOM, SYSOP).

Critères d'acceptation (section 12) sur le fichier réel, non versionné :

```bash
TDB_FICHIER_ACCEPTATION="/chemin/SC de 2025-2025 en date du 15-09-2026.xlsx" pytest tests/test_acceptation.py
```

## Règles de gestion

Elles sont regroupées dans `backend/apps/core/regles.py` (100 % de couverture). Les seuils sont
paramétrables dans `core_parametre` (admin ou `PATCH /api/v1/parametres/<code>/`). Les taux se calculent
sur les crédits actuels. Le paiement est « ajusté » par défaut : les procédures dont
`paiement_hors_chaine = true` (Procedure Solde, débits d'office, régularisations PCT) sont exclues.

## Données d'illustration (sources non raccordées)

L'onglet **TOFE** présente un scénario entièrement fictif du cadre guinéen : recettes et dons,
charges, actifs non financiers, soldes et financement. Les hypothèses, conventions de signe et
références officielles sont détaillées dans [l'étude TOFE](docs/etude-tofe-guinee.md).
Il est indépendant des sources réelles et accessible aux comptes autorisés sur le domaine `tofe`.
Pour ne générer que cette illustration :

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py seed_demo --sources tofe --exercice 2026 --date-situation 2026-11-13
```

```bash
python manage.py seed_demo                      # SAFIG, SYDONIA, SCIE, dette, FUGAS, SICOM, SYSOP
python manage.py seed_demo --sources dette fugas --exercice 2026 --date-situation 2026-08-31
python manage.py seed_demo --supprimer          # retour à « Source non raccordée »
```

Même action depuis l'interface : **Administration › Données de test**.

- Statut `demo` : bandeau « Données d'illustration » sur la page, pastille « · illustration » sur chaque chiffre.
- Anonymisation : organismes, bureaux, centres et ministères fictifs (« Hôpital national A », « Bureau portuaire B »,
  « Ministère fictif C »). Aucun chiffre fictif n'est attribué à une structure réelle.
- Une source déjà raccordée (statut `reel`) n'est jamais écrasée. Les pages mixtes (Masse salariale, Trésorerie,
  Dette, Portefeuille) gardent les chiffres réels de la Chaîne Dépense, avec leur propre pastille de source.

## Module d'administration (rôle `dnsi_admin`, double authentification)

Interface : onglet **Administration** (icône roue dentée). API : `/api/v1/admin/…`. Toutes les actions sont journalisées.

| Rubrique | Contenu |
|---|---|
| Vue d'ensemble | Cartographie des onglets, des sources et des destinations dans la base centrale |
| État des sources | Statuts, dernières situations et tentatives d'alimentation |
| Connexions aux sources | Type de connexion, configuration sans secret, test d'accès et import de fichier |
| Flux ETL | SYSOP et Chaîne Dépense Oracle : exercice explicite, aperçu avec contrôles, activation, alimentation et programmation |
| Exécutions et qualité | Historique, volumes et contrôles de chaque chargement |
| Mappings de colonnes | Correspondances colonne source → champ de la base centrale (connecteurs génériques) |
| Base centrale | Volumes des tables `ref`/`dw` et des vues `mart`, fichiers reçus et rafraîchissement |
| Données de test | Génération et retrait des illustrations pour les sources non raccordées |
| Utilisateurs et accès | Comptes, rôles, domaines visibles, réinitialisation de la double authentification |
| Partage de données (API) | Jetons d'accès en lecture seule pour des systèmes tiers |
| Règles d'alerte | Activation, sévérité, seuils, messages ; réévaluation |
| Paramètres et seuils | Seuils des règles de gestion (`core_parametre`) |
| Journal d'audit | Connexions, consultations, imports, exports, administration |

Sécurité : aucun secret dans l'API ni en base. Les identifiants des connexions Oracle et PostgreSQL restent dans les
variables d'environnement (`CHAINE_DEPENSE_ORACLE_*`, `SICOM_DATABASE_URL`, `SYSOP_DATABASE_URL`, `TELEMO_API_*`) ; l'interface
indique seulement si elles sont renseignées. Les requêtes configurées sont limitées à la lecture (`SELECT`).

Parcours et transition : [Administration de la base centrale et des flux ETL](docs/administration-base-centrale-etl.md).

### Partage de données par jeton

```bash
curl -H "Authorization: Jeton tdb_…" https://<serveur>/api/v1/depense/indicateurs/
```

La clé n'est affichée qu'une fois, à la création ; seule son empreinte SHA-256 est conservée. Chaque jeton est limité
aux domaines choisis, en lecture seule, avec une date d'expiration facultative. Il peut être suspendu ou révoqué.

## Traçabilité des flux et dimensions communes

Mise en conformité avec les termes de référence de l'entrepôt : suivi dans `docs/plan-conformite.md`.

- **Zone brute** : tout fichier importé, et toute réponse d'API, est conservé tel que reçu sous
  `media/brut/<source>/<empreinte SHA-256>.<extension>`. Un même contenu n'est stocké qu'une fois ; un fichier
  déjà chargé est signalé. Le volume `media` est donc **à sauvegarder** avec la base.
- **Identifiant de flux** : chaque chargement porte un UUID v4, repris dans le journal d'audit.
- **Fichier d'origine** : téléchargeable par l'administrateur depuis **Imports et chargements**
  (`GET /api/v1/admin/chargements/<id>/fichier/`, téléchargement journalisé).
- **Échanges avec les partenaires** (`docs/echanges-partenaires.md`) : dépôt de fichiers par SFTP (un dossier
  par source, relève toutes les 5 minutes, `python manage.py relever_depots`), schémas JSON des flux,
  fichiers XML et JSON, événements AMQP `chargement.<source>.<statut>` sur RabbitMQ, TLS 1.3 seul.
- **Exploration et BI** : page « Exploration des données » pour les analystes et les administrateurs (jeu de
  données, axes, mesures, filtres ; aucune requête SQL libre ; export Excel journalisé). Compte PostgreSQL en
  lecture seule pour un outil de BI : `python manage.py creer_acces_bi`.
- **Projections de fin d'exercice** (`apps/core/projections.py`) : fourchette au 31 décembre pour les dépenses
  et les recettes, alerte si l'engagement projeté reste sous `projection_engagement_min`.
- **Livrables des termes de référence** : `docs/livrables/` (calendrier, rapport d'analyse et de conception,
  rapport d'étape, dossier de recette, guide d'exploitation, manuel utilisateur).
- **Dimension temps** : `ref.dim_temps`, une ligne par jour (année, semestre, trimestre, mois, semaine ISO),
  de 2015 à l'année courante + 5 ; étendue automatiquement à l'exercice d'un chargement.
- **Zones géographiques** : `ref.ref_zone_geographique` (pays et huit régions, codes ISO 3166-2). Référentiel
  fermé : un code inconnu rejette la ligne.

## Identité visuelle

Jetons dans `frontend/src/theme/tokens.css` (clair et sombre). Les couleurs du drapeau (`--gn-*`) ne servent qu'à la
signature : filet tricolore sous l'en-tête, pied de page, écran de connexion, impression. Un test
(`src/test/charte.test.ts`) le vérifie, ainsi que l'absence de couleur écrite en dur dans les composants.
Armoiries : `frontend/src/assets/armoiries.svg` est une version **provisoire** issue de Wikimedia Commons
(CC BY-SA 3.0, mention en pied de page). La remplacer par le fichier officiel du ministère, puis vider
`CREDIT_ARMOIRIES` dans `frontend/src/components/cadre/Signature.tsx` (voir `frontend/src/assets/LISEZMOI.md`).
Le nom de la plateforme se change en un seul endroit : `frontend/src/lib/identite.ts`.

## Rôles

| Rôle | Accès |
|---|---|
| `ministre_cabinet` | tout voir, exporter — double authentification obligatoire |
| `directeur` | ses domaines (champ `domaines` de l'utilisateur) |
| `analyste` | ses domaines, plus l'exploration libre (`/exploration`) — double authentification obligatoire |
| `dnsi_admin` | imports, sources, paramètres, règles d'alerte, journal — double authentification obligatoire |
| `lecteur` | lecture de ses domaines, sans export |

Les permissions sont appliquées dans l'API. Le journal d'audit (`core_journal_audit`) trace les connexions,
les consultations de page, les imports, les exports, les changements de paramètres et de statut d'alerte.

## État d'avancement

| Lot | Contenu | État |
|---|---|---|
| 1 | Socle Docker/Django/React, authentification + 2FA, rôles, cadre visuel, 10 onglets | fait |
| 2 | Référentiels communs, modèle de l'entrepôt (`ref`, `dw`, `mart`) | fait |
| 3 | ETL Chaîne Dépense, règles de gestion, tests d'acceptation (à lancer sur le fichier 2025) | fait |
| 4 | API et pages Dépenses, Synthèse, Investissements | fait (export `.xlsx` au lot 8) |
| 5 | Moteur d'alertes et panneau qualité | fait (toutes les règles de la section 6) |
| 6 | Connecteurs PostgreSQL SICOM et SYSOP, puis leurs pages | connecteur et pages faits (illustration en attendant le raccordement) |
| 7 | Démonstration SAFIG, SYDONIA, SCIE, dette, FUGAS (`seed_demo`) et pages | fait |
| — | Module d'administration de l'entrepôt, partage de données par jeton | fait |
| — | Refonte institutionnelle du frontend (charte, impression, présentation) | fait |
| 8 | Exports Excel, documentation (dictionnaire des indicateurs) | fait |
| — | Mise en conformité avec les termes de référence de l'entrepôt (`docs/plan-conformite.md`) | chantiers 1, 2, 3, 5 et 8 faits |
