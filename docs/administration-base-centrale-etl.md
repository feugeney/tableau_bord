# Administration de la base centrale et des flux ETL

Le tableau de bord lit une base centrale PostgreSQL. Les informations des applications métiers y sont enregistrées après extraction, transformation et contrôles. Une consultation du tableau de bord ne déclenche pas de requête vers SYSOP.

## Parcours d'administration

1. **Vue d'ensemble** : cartographie des besoins par onglet, systèmes d'origine et destinations. Les situations et statuts affichés proviennent des chargements enregistrés.
2. **Connexions aux sources** : type de connexion, configuration technique et test d'accès. Les secrets restent dans les variables d'environnement.
3. **Flux ETL** : traitements SYSOP et Chaîne Dépense Oracle, exercice, activation, aperçu, alimentation et programmation.
4. **Exécutions et qualité** : historique, volumes, anomalies et résultats des contrôles.
5. **Base centrale** : tables, vues de restitution, fichiers reçus et rafraîchissement.
6. **Données de test** : génération et retrait des illustrations, séparés des opérations courantes.
7. Les mappings, règles d'alerte, utilisateurs, partages et journaux restent disponibles.

Les anciens noms physiques `ref`, `dw` et `mart` sont conservés pour éviter une migration des données et des requêtes sans bénéfice fonctionnel. Ils désignent respectivement les référentiels, les données importées et les vues utilisées pour calculer les indicateurs.

## Premier profil : SYSOP → portefeuille de l'État

Le pilote `sysop-portefeuille` utilise la connexion SYSOP existante et le connecteur PostgreSQL en lecture seule. Il récupère les organismes, subventions, dividendes, validations et résultats financiers. La cartographie présente les autres onglets ; elle ne signifie pas que leurs systèmes sont déjà raccordés.

Procédure :

1. Tester SYSOP dans **Connexions aux sources**.
2. Choisir l'exercice dans **Flux ETL** et enregistrer.
3. Lancer **Vérifier un aperçu**. Consulter le volume lu et les contrôles ; aucun fait métier n'est enregistré.
4. Autoriser l'alimentation réelle et enregistrer.
5. Cliquer sur **Actualiser les données** ; vérifier la réussite et les volumes dans l'historique.
6. Utiliser **Voir le portefeuille** pour consulter l'exercice importé. Le sélecteur de période du portefeuille utilise les situations SYSOP.

L'import est transactionnel. Les tentatives restent historisées ; les indicateurs utilisent le dernier chargement réussi de chaque exercice et date de situation. Une répétition ne cumule donc pas les montants. Un échec conserve la précédente situation valide. Un verrou PostgreSQL refuse deux exécutions simultanées de ce flux pour la même source et le même exercice.

La création des profils ne les active pas et ne crée aucune collecte automatique. L'exercice initial vient de la dernière importation réussie non fictive (SYSOP), du dernier chargement Oracle (Chaîne Dépense), ou de l'année courante en l'absence d'importation correspondante. Les anciennes programmations de ces deux sources sans exercice sont retirées.

## Chaîne Dépense Oracle : connexion et mapping existants

Le profil `oracle-chaine-depense` utilise la configuration de la source `chaine_depense`, les identifiants Oracle déjà présents dans l'environnement et les requêtes SQL existantes de `backend/etl/sql/chaine_depense`. Les requêtes configurées sont conservées ; aucune nouvelle correspondance métier n'est inventée. Les alias SQL constituent le mapping spécialisé Oracle, distinct des mappings de colonnes des connecteurs génériques.

La fiche du flux présente les requêtes et leurs champs de destination. `GDEP.LBUDG` alimente la situation budgétaire ; `GDEP.ENGAGEMENT` alimente le détail des engagements, enrichi avec les référentiels existants. Les deux requêtes filtrent explicitement l'exercice. L'import impose les clés complètes et un rapprochement bloquant par clé ; les dossiers écartés du rapprochement restent conservés dans les données importées.

Le test de connexion de l'interface et l'extraction utilisent le même client Oracle Thick configuré et une transaction source en lecture seule. En production, le blocage des heures ouvrées reste actif. Une case séparée permet une exception manuelle ponctuelle, enregistrée dans l'historique et le journal d'audit. Elle se décoche après chaque tentative, n'est pas enregistrée dans la configuration et n'est jamais transmise par les tâches planifiées.

Vérification locale du 13 novembre 2026 : la connexion fonctionnait mais la source active était encore configurée en import Excel, sans requêtes Oracle enregistrées. Le branchement a été rétabli en reprenant les requêtes préparées. Après aperçu, le chargement n° 23 a importé pour 2025 **13 395 lignes budgétaires et 24 958 engagements**, sans rejet et avec zéro clé en écart pour le rapprochement des engagements. L'avertissement `liquide_sup_engage` concerne six lignes ; les montants source sont conservés. Les crédits disponibles restent signalés indisponibles si la requête ne les fournit pas.

Les données 2026 déjà présentes proviennent de l'import Excel antérieur. Ce chargement Oracle 2025 ne les transforme pas en données Oracle 2026. Le lien **Voir les dépenses · 2025** ouvre explicitement l'exercice vérifié.

### Libellés des ministères et services

La liste « Ministères et institutions » affiche les noms complets issus de `GDEP.TC_SECTION` pour l'exercice importé. Les services du panneau de détail utilisent `GDEP.TC_SERVICE`, relié via `GDEP.TC_SOUS_SECTION` sur sa clé complète `(NO_EX, CODE_SECTION, CODE_SOUS_SECTION)`. À défaut de nom de service, le libellé de la sous-section est repris.

Les libellés sont conservés dans `core_chargement.detail.referentiels_libelles`, avec chaque extraction Oracle, et lus depuis son chargement actif. Cette conservation évite de remplacer les noms d'une autre période dans le référentiel commun. Les noms complets sont repris par le tableau, la recherche, le détail et l'export CSV ; les exports Excel et PDF utilisent les mêmes services de données.

Vérification du chargement n° 25 : **44 noms de ministères et institutions** comparés directement à Oracle, **3 514 libellés de services/sous-sections**, et montants par section identiques au chargement précédent.

## Programmation

Le champ cron appartient au flux. Vide, il implique un lancement manuel. Une expression telle que `0 2 * * *` programme le traitement à 2 h, fuseau `Africa/Conakry`. Les services Celery worker et beat doivent fonctionner pour que cette programmation s'exécute. Les paramètres sont relus lors de chaque exécution ; désactiver le flux retire sa tâche planifiée et bloque le chargement réel.

Les autres connecteurs conservent leur fonctionnement existant pendant la transition. Leur déplacement vers des flux dédiés doit accompagner la validation de leurs contrats métier, sans inventer de correspondances de colonnes.

## Suite du raccordement

Pour chaque système, renseigner et faire valider : responsable, accès en lecture, tables ou API, exercice, date de situation, unités, identifiants stables, mappings et règles métier. Implémenter ensuite le profil, tester un échantillon et rapprocher les totaux avant d'activer l'alimentation.

Le TOFE reste un scénario d'illustration autonome. Sa consolidation réelle exige des règles validées de périmètre, de classement, de période et de rapprochement des recettes, dépenses et financements. Il ne doit pas être présenté comme un TOFE officiel sur la seule base des sources disponibles.

## Installation et vérification

Depuis le dossier `backend`, appliquer `python manage.py migrate` puis `python manage.py initialiser`. L'ajout du pilote est idempotent et conserve ses réglages lors des initialisations suivantes.

Les tests `tests/test_etl_admin.py` couvrent les permissions et la double authentification, la validation des paramètres, la programmation, l'aperçu sans écriture, la répétition sans cumul, le maintien des données après échec, le refus d'une exécution concurrente et l'invalidation des caches après un import depuis un autre processus.
