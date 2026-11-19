# Revue du projet — 13 novembre 2026

Périmètre : code backend/frontend, paramètres locaux non secrets, ETL, permissions, planification, CI, documentation d'exploitation et tests. Revue locale ; aucun nouvel appel aux bases métier Oracle/SYSOP, aucun déploiement ni modification des règles métier. Les tests utilisent une base de test distincte. Cette revue ne constitue pas une recette métier exhaustive ou un test d'intrusion.

## Priorités avant une utilisation décisionnelle

### 1. Aligner la période affichée avec la source de chaque page

Constat confirmé : `frontend/src/hooks/useSituation.ts:14` appelle `/situations/` sans source ; `backend/apps/core/api.py:441` utilise alors `chaine_depense`. Le portefeuille peut donc afficher les données SYSOP d'une période différente de celle proposée par le sélecteur général. Localement : dépenses 2026 au 16/08/2026, SYSOP 2025 extrait le 13/11/2026.

Action : choisir la source selon la page, inclure cette source dans la clé de cache frontend, vérifier la validité des filtres lors des changements d'onglet. Pour les pages mixtes, conserver une période explicite par bloc et signaler les différences. Ne pas substituer silencieusement une autre période lorsque l'utilisateur en impose une.

Validation attendue : le sélecteur et la réponse API désignent la même situation ; une période absente affiche une absence de données explicite.

### 2. Rendre les actualisations SYSOP exécutables et observables

Constat confirmé : `backend/etl/planification.py:29` programme uniquement le code source, tandis que `backend/etl/connecteurs/sysop.py:44` exige un exercice. La tâche locale `chargement-sysop` est activée avec `args=["sysop"]` et `kwargs={}`. Son invocation ne peut pas réussir sans exercice.

Action : définir les exercices à actualiser dans la configuration de la source et les transmettre aux tâches. Ajouter un état visible de la dernière tentative, du dernier succès et de la prochaine exécution ; protéger contre les imports concurrents d'une même source/situation. Ne pas déduire automatiquement que l'exercice courant est disponible chez le partenaire.

Validation attendue : tester le véritable chemin planificateur → tâche → fabrique → connecteur, avec une source simulée ; tester aussi les échecs et une seconde invocation simultanée.

### 3. Imposer la double authentification aux accès privilégiés

Constat confirmé : `Utilisateur.exige_2fa` dépend du rôle, tandis que `AdminDNSI` autorise aussi les superutilisateurs. Le compte local `essai-admin`, superutilisateur de rôle directeur, a `exige_2fa=False`.

Action : appliquer l'exigence aux superutilisateurs et aux accès privilégiés ; examiner également l'accès `/admin/`, actuellement déclaré avec le site Django standard. Prévoir l'enrôlement et une procédure de récupération avant activation ; les comptes de test ne doivent pas servir en production.

Validation attendue : aucun compte privilégié ne lit ni ne modifie l'administration sans une session satisfaisant la politique 2FA, quel que soit son rôle déclaré.

### 4. Distinguer données réelles, qualité et fraîcheur

Constat confirmé dans la base actuellement utilisée : les dépenses reposent sur un import Excel du 16/08/2026, avec un écart engagé de 800 000 000 GNF entre onglets, 39 lignes liquidé > engagé, quatre lignes en dépassement et onze valeurs LFI absentes. Le contrôle d'écart avait été accepté avec une tolérance de 300 GNF par million. L'égalité des totaux avec l'entrepôt ne résout pas ces anomalies source.

Action : afficher séparément origine réelle/illustration, date métier, extraction, rapprochement et avertissements. Rechercher le chargement Oracle documenté avant de considérer les dépenses comme actualisées ; définir et faire valider les tolérances métier. Ajouter l'accès au détail expliquant chaque anomalie.

Validation attendue : les écarts sont visibles sur les pages et dans les exports ; aucune mention « réel » ne signifie implicitement « rapproché » ou « à jour ».

### 5. Partager l'invalidation du cache entre processus

Constat : avec `REDIS_URL` vide, le cache et la version des données sont locaux à chaque processus (`backend/config/settings/base.py:174`, `backend/etl/mart.py`). Un import lancé en ligne de commande ne vide pas le cache du serveur déjà démarré. Ce comportement a nécessité des redémarrages pendant cette session. Docker configure Redis, ce problème concerne donc notamment le mode local sans Redis.

Action : utiliser un cache partagé ou une version des données stockée en base ; rendre le rafraîchissement fiable après un import manuel comme après une tâche. Actualiser aussi les requêtes frontend après un import depuis l'interface.

Validation attendue : importer depuis un processus distinct, puis constater les nouvelles valeurs immédiatement dans une API déjà utilisée, sans redémarrage.

## Sécurité et exploitation à renforcer

### 6. Empêcher la suppression du journal d'audit

Constat confirmé : `JournalAuditAdmin` interdit ajout et modification mais ne surcharge pas `has_delete_permission` (`backend/apps/core/admin.py:51`). Le contrôle local renvoie `True` pour un superutilisateur.

Action : désactiver suppression individuelle et suppression en lot, limiter les droits SQL et définir une rétention avec archivage. Si une conservation opposable est requise, prévoir une copie indépendante des administrateurs applicatifs.

### 7. Révoquer les sessions côté serveur

Constat : le frontend efface les jetons lors de la déconnexion ; aucune route de révocation ni liste de révocation des jetons de rafraîchissement n'a été trouvée. La rotation est activée, sans configuration de révocation des anciens refresh tokens dans `SIMPLE_JWT`.

Action : prévoir une révocation à la déconnexion et à la réinitialisation des accès, avec une politique explicite pour les sessions déjà ouvertes. Tester la réutilisation d'un ancien jeton après rotation et après déconnexion.

### 8. Vérifier l'état des dépendances et la restauration

Constat : `/sante/` retourne toujours `ok` sans vérifier la base. La configuration Nginx ne route explicitement que `/api/` et `/admin/` vers Django ; `/sante/` tombe dans le routage frontend. Des procédures de sauvegarde/restauration existent, mais la documentation indique qu'elles restent à exécuter en recette.

Action : séparer présence du processus et disponibilité métier, contrôler la base et le dernier succès ETL, rendre ces contrôles accessibles au superviseur ; sauvegarder base et zone brute ensemble et réaliser un exercice de restauration. Définir les objectifs de perte de données et de délai de reprise.

## Évolutions produit utiles

- Une fiche source réunissant connectivité, exercice disponible, dernière extraction, qualité et historique.
- Depuis chaque indicateur, un détail expliquant le montant, son périmètre, la formule et les exclusions.
- Des comparaisons N/N-1 limitées aux périodes et périmètres comparables ; absence explicite lorsque l'historique manque.
- Un circuit de traitement des anomalies : responsable, justification, décision, date et trace des corrections.
- Un démarrage local documenté et reproductible, qui vérifie l'identité de la base utilisée. Le conflit de port avec un autre projet montre l'utilité de cette vérification.

## Vérifications

- Backend : **282 réussis, 1 échec, 6 ignorés** (suite complète, 275,59 s). Échec : `tests/test_demo.py::test_chaine_depense_sur_demande`, comparaison `pytest.approx(engage, rel=1e-6)` mélangeant un montant `Decimal` et une tolérance `float`. Ce résultat ne démontre pas un défaut des indicateurs de production ; corriger le contrôle avec une tolérance cohérente en Decimal puis vérifier l'écart réel de la génération d'illustration.
- Frontend : **17 tests réussis**, contrôle TypeScript réussi, compilation de production réussie ; ESLint : zéro erreur et huit avertissements liés au rechargement de composants en développement.
- Ruff : **deux erreurs E501**, dans `backend/apps/core/demo.py`, lignes 564 et 567.
- Black : **deux fichiers à reformater** : `backend/apps/core/demo.py` et `backend/tests/test_sysop_connexion.py` ; 133 fichiers conformes.
- Migrations : contrôle `makemigrations --check --dry-run` réussi ; aucune migration manquante détectée.
- Les six tests d'acceptation nécessitant un fichier réel ont été ignorés, faute de `TDB_FICHIER_ACCEPTATION`. Ils ne constituent donc pas une validation métier réussie.

La CI actuelle échouerait sur Ruff, Black et le test backend ci-dessus. Corriger ces points avant une livraison, puis relancer les contrôles requis, dont la couverture minimale de 80 % (non mesurée lors de cette revue).

Ordre proposé : périodes et identité de la base → 2FA et audit → actualisations/cache → rapprochement métier → surveillance/restauration → évolutions de présentation.
