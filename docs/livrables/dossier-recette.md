# Dossier de recette

Système intégré de pilotage des finances publiques — Ministère de l'Économie, des Finances et du Budget.
Livrable n° 4 des termes de référence. Version 1.0, 10 octobre 2026.

## 1. Objet et organisation

Ce dossier liste les vérifications à dérouler pour prononcer la recette de la plateforme. Il est rempli en
séance par les représentants du SMSI et des directions métiers ; le prestataire assiste.

- **Colonne « Résultat »** : à remplir en séance par *Conforme*, *Non conforme* ou *Réserve*, avec une
  observation.
- **Colonne « Test automatique »** : quand elle est renseignée, le cas est aussi vérifié à chaque modification
  du code. Cela ne dispense pas de la vérification en séance.

### Prérequis de la séance

| Prérequis | État au 10 octobre 2026 |
|---|---|
| Plateforme installée sur le serveur de recette (les neuf services démarrés) | **À faire** : jamais démarrée hors du poste de développement |
| Certificat du ministère installé | À faire |
| Un compte par profil (cabinet, directeur, analyste, lecteur, administrateur) | À créer en recette |
| Une extraction réelle récente de la Chaîne Dépense | Disponible (16 août 2026) |
| Une extraction réelle d'au moins une autre source | **Aucune reçue** |
| Un téléphone avec une application d'authentification | À prévoir |

### État des tests automatiques

| Lot | Nombre | Résultat |
|---|---|---|
| Serveur (règles de gestion, connecteurs, API, droits, exports) | 235 | Tous réussis |
| Interface (pages, charte graphique) | 17 | Tous réussis |
| Navigation au clavier | 12 vérifications | Toutes réussies |
| Critères d'acceptation sur l'extraction réelle (6 tests) | 6 | **Non exécutés par défaut** : ils demandent le fichier réel, et le contrôle de concordance y échoue (voir R-03) |

Couverture de code : 99 % sur les règles de gestion, 93 % sur les connecteurs (seuil exigé : 80 %).

## 2. Cas de recette

### A. Accès et sécurité (TdR 4 : accès sécurisé ; 6.4.1)

| N° | Vérification | Résultat attendu | Test automatique | Résultat |
|---|---|---|---|---|
| A-01 | Ouvrir l'application en `http://` | Redirection vers `https://` | — | |
| A-02 | Contrôler le protocole négocié dans le navigateur | TLS 1.3 | — | |
| A-03 | Se connecter avec un mauvais mot de passe | Refus ; tentative inscrite au journal d'audit | `test_api` | |
| A-04 | Première connexion d'un compte cabinet | Enrôlement de la double authentification exigé | `test_api` | |
| A-05 | Compte cabinet, code à usage unique erroné | Refus | `test_api` | |
| A-06 | Compte directeur limité aux dépenses : ouvrir la page Dette par son adresse | Page absente, et l'API répond « refusé » | `test_api` | |
| A-07 | Compte lecteur : chercher le bouton d'export | Absent ; l'appel direct de l'export est refusé | `test_export` | |
| A-08 | Compte directeur : ouvrir `/administration` | Refusé | `test_admin` | |
| A-09 | Compte analyste limité aux marchés publics : explorer les engagements | Refusé | `test_exploration` | |
| A-10 | Réinitialiser la double authentification d'un compte | Nouvel enrôlement demandé à la connexion suivante | `test_admin` | |

### B. Collecte et chargement (TdR 3, 4 : ETL ; 6.2)

| N° | Vérification | Résultat attendu | Test automatique | Résultat |
|---|---|---|---|---|
| B-01 | Importer l'extraction de la Chaîne Dépense en **aperçu** | Contrôles affichés ; rien n'est chargé | `test_api` | |
| B-02 | Importer la même extraction pour de bon | Chargement « Succès » ; lignes lues, chargées, rejetées | `test_etl_chaine_depense` | |
| B-03 | Importer un fichier dont un onglet a perdu une colonne obligatoire | Chargement « Échec », message explicite, rien d'écrit | `test_etl_chaine_depense` | |
| B-04 | Importer une ligne portant un code de ministère inconnu | Ligne rejetée et comptée ; le code n'est pas créé | `test_connecteurs` | |
| B-05 | Réimporter exactement le même fichier | Mention « Contenu déjà chargé » ; pas de double compte dans les pages | `test_tracabilite` | |
| B-06 | Ouvrir le détail d'un chargement | Identifiant UUID, empreinte SHA-256, résultat de chaque contrôle | `test_tracabilite` | |
| B-07 | Télécharger le fichier reçu d'un chargement | Fichier identique à l'original ; téléchargement au journal d'audit | `test_tracabilite` | |
| B-08 | Déposer un fichier par SFTP dans `sources/<source>/` | Chargé à la relève suivante ; retiré du dépôt ; colonne « Par » : « Dépôt SFTP » | `test_echanges` (hors serveur SFTP) | |
| B-09 | Déposer par SFTP un fichier illisible | Chargement « Échec » visible ; fichier conservé en zone brute | `test_echanges` | |
| B-10 | Se connecter au SFTP avec un mot de passe | Refusé (clé uniquement) | — | |
| B-11 | Charger un classeur Telemo à trois onglets | Trois tables alimentées en **un** chargement | `test_telemo` | |
| B-12 | Charger un fichier JSON dont une ligne n'a pas un champ obligatoire | Ligne écartée et comptée dans le contrôle « schéma JSON » | `test_echanges` | |
| B-13 | Charger un fichier XML | Table alimentée | `test_echanges` | |
| B-14 | Tester la connexion d'une source PostgreSQL ou API depuis l'administration | Message de succès ou d'échec, sans afficher de secret | `test_admin`, `test_telemo` | |
| B-15 | Vérifier le chargement planifié d'une source lue automatiquement | Chargement présent à l'heure prévue, auteur « Automatique » | `test_connecteurs` (planification) | |
| B-16 | S'abonner à l'échange `tdb.evenements` de RabbitMQ, puis lancer un chargement | Message `chargement.<source>.succes` reçu | `test_echanges` (messagerie en mémoire) | |

### C. Modèle et qualité des données (TdR 6.3 ; 7.2 : référentiel unique)

| N° | Vérification | Résultat attendu | Test automatique | Résultat |
|---|---|---|---|---|
| C-01 | **Administration › Entrepôt** : lister les tables | Schémas `ref` (dimensions) et `dw` (faits) présents ; `dim_temps` alimentée | `test_tracabilite` | |
| C-02 | Changer la date de situation dans l'en-tête | Les pages affichent la situation choisie ; l'ancienne reste consultable | `test_api` | |
| C-03 | Rapprocher les totaux de la page Dépenses de ceux de la Chaîne Dépense à la même date | Égalité des crédits, engagements, ordonnancements et paiements | `test_acceptation` (non exécuté) | |
| C-04 | Contrôler le statut de trois ministères choisis par la DGB | Statut conforme à la règle du dictionnaire des indicateurs | `test_regles` | |
| C-05 | Modifier un seuil (par exemple le taux de sous-exécution) | Alertes et statuts recalculés ; modification au journal d'audit | `test_api`, `test_regles` | |

### D. Restitution (TdR 3, 4 : reporting ; 7.2)

| N° | Vérification | Résultat attendu | Test automatique | Résultat |
|---|---|---|---|---|
| D-01 | Parcourir les dix pages | Chaque chiffre porte sa source, son statut et sa date | `pages.test` | |
| D-02 | Repérer une page en données d'illustration | Bandeau et pastilles « illustration » | `test_demo` | |
| D-03 | Charger une extraction réelle d'une source en illustration | Les données fictives de cette source disparaissent | `test_demo` | |
| D-04 | Page Synthèse : marquer une alerte comme traitée | Elle quitte la liste des alertes ouvertes | `test_api` | |
| D-05 | Exporter une page en Excel | Classeur avec feuille « Lisez-moi » (source, statut, date, filtres) | `test_export` | |
| D-06 | Imprimer une page | A4 paysage, en-tête officiel, mention de diffusion restreinte | — | |
| D-07 | Mode présentation | Navigation masquée, contenu agrandi | — | |
| D-08 | Parcourir une page au clavier seul | Tous les éléments atteints, focus visible | `scripts/clavier.mjs` | |
| D-09 | Afficher l'application sur un téléphone | Aucun défilement horizontal de la page | `scripts/captures.mjs` | |
| D-10 | Analyste : regrouper les marchés par mode de passation, somme du montant TTC | Totaux égaux à ceux de la page Marchés publics | `test_exploration` | |
| D-11 | Analyste : exporter le résultat | Classeur en GNF non arrondis ; export au journal d'audit | `test_exploration` | |
| D-12 | Se connecter à la base avec le compte de BI | Lecture des vues agrégées possible ; écriture et tables d'administration refusées | `test_exploration` | |

### E. Interopérabilité (TdR 4 ; 6.4)

| N° | Vérification | Résultat attendu | Test automatique | Résultat |
|---|---|---|---|---|
| E-01 | Ouvrir `/api/docs/` | Documentation OpenAPI complète | `test_api` | |
| E-02 | Créer un jeton de partage limité à un domaine ; appeler l'API avec ce jeton | Lecture du domaine possible ; autres domaines et écriture refusés | `test_admin` | |
| E-03 | Désactiver le jeton, rappeler l'API | Refusé | `test_admin` | |
| E-04 | Télécharger les schémas JSON des flux d'une source | Un schéma par flux, champs obligatoires listés | `test_echanges` | |

### F. Exploitation (TdR 7.1 : guide d'exploitation)

| N° | Vérification | Résultat attendu | Test automatique | Résultat |
|---|---|---|---|---|
| F-01 | Arrêter puis redémarrer tous les services | Application disponible, données intactes | — | |
| F-02 | Sauvegarder la base et la zone brute, puis les restaurer sur un serveur vierge | Pages identiques à l'original ; fichiers des chargements téléchargeables | — | |
| F-03 | Redémarrer le service SFTP | L'empreinte du serveur ne change pas pour le partenaire | — | |
| F-04 | Appliquer une mise à jour | Migrations appliquées sans intervention ; configuration de l'administrateur conservée | — | |

## 3. Réserves connues avant la séance

| N° | Réserve | Conséquence | Levée |
|---|---|---|---|
| R-01 | Une seule source réelle (Chaîne Dépense) ; les huit autres pages sont en illustration | Le résultat attendu « entrepôt couvrant l'ensemble des applications critiques » n'est pas atteint | Raccordement source par source (chantier 4) |
| R-02 | La plateforme n'a jamais été démarrée avec Docker ; les services SFTP et RabbitMQ n'ont été vérifiés que par des tests automatiques sans serveur réel | Les cas A-01, A-02, B-08, B-10, B-16, F-01 à F-04 n'ont jamais été déroulés | Installation sur le serveur de recette |
| R-03 | L'extraction réelle de la Chaîne Dépense échoue au contrôle de concordance (écart de 0,8 Md entre deux onglets) ; elle a été chargée en relevant temporairement la tolérance | Les tests d'acceptation sur le fichier réel ne sont pas concluants | Arbitrage de la DGB sur la tolérance ou correction de l'extraction |
| R-04 | Lecture directe Oracle de la Chaîne Dépense jamais essayée sur la base réelle | Alimentation automatique non démontrée | Compte en lecture seule fourni par la DNSI |
| R-05 | Armoiries provisoires (version Wikimedia Commons) | Mention de crédit en pied de page | Fichier officiel du ministère |
| R-06 | Données ouvertes, second site, analyses prédictives non réalisés | Exigences des TdR 4 et 6.1 non couvertes | Chantiers 5, 6 et 7 |

## 4. Procès-verbal

| | Nom | Fonction | Date | Signature |
|---|---|---|---|---|
| Pour le SMSI | | | | |
| Pour la direction métier | | | | |
| Pour le prestataire | | | | |

Décision : ☐ Recette prononcée ☐ Recette prononcée avec réserves ☐ Recette ajournée
