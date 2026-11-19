# Raccordement SYSOP — Portefeuille de l'État

## État du raccordement

Connexion PostgreSQL vérifiée en lecture seule sur le serveur SYSOP (adresse et port dans `SYSOP_DATABASE_URL`).
Les identifiants restent dans `backend/.env` (`SYSOP_DATABASE_URL`).
Le premier import réel de l'exercice **2025** a été effectué le **13 novembre 2026**,
après validation de l'aperçu. La source est affichée comme réelle ; aucune nouvelle
planification automatique n'a été créée. Il s'agit de la situation de 2025 à la date
d'extraction, et non d'une reconstruction historique au 31 décembre 2025.

Le chargement contient 152 EPA et 80 sociétés publiques, 47 agrégats de subventions,
un agrégat de dividendes et un suivi de santé/validation pour chacun des 232 organismes
(512 faits au total). Les totaux importés ont été rapprochés du journal d'extraction :

| Montant 2025 | GNF |
|---|---:|
| Subventions prévues, base LFR | 567 518 791 559 |
| Subventions versées | 213 422 657 094 |
| Dividendes prévus | 5 000 000 000 |
| Dividendes réalisés | 5 000 000 000 |

Aucun état de 2025 aux niveaux `4` ou `6` ni résultat net `XI` n'a été trouvé lors
de l'extraction. Le dashboard indique donc 232 organismes sans états validés et ne
classe aucun de ces organismes comme étant à l'équilibre. Les mandats restent non raccordés.

Diagnostic depuis le dossier `backend` :

```powershell
.\.venv\Scripts\python.exe manage.py diagnostiquer_sysop
.\.venv\Scripts\python.exe manage.py charger_sysop --exercice 2025 --apercu
.\.venv\Scripts\python.exe manage.py charger_sysop --exercice 2025
```

## Mapping vérifié dans le schéma public

| Donnée | Table et colonne SYSOP | Cible / règle |
|---|---|---|
| Identifiant organisme | `organisme_publique.no_op` | `RefOrganisme.identifiant_etat` ; ne pas confondre avec la clé primaire Django |
| Nom | `organisme_publique.lib_long_op`, `lib_court_op` | `RefOrganisme.nom` ; priorité et traitement des noms absents à définir |
| Sigle | `organisme_publique.sigle_op` | `RefOrganisme.sigle` |
| Type | `organisme_publique.type_op_id` | `EPA` → `epa` ; `SP` → `societe` (confirmation utilisateur) |
| Tutelle | `organisme_publique.tutelle_technique_id` | Référentiel `tutelle_technique.cd_ministere` ; correspondance avec les sections du dashboard à vérifier |
| Subventions | `subvention_etat` | Organisme : `organisme_id` ; exercice : `exercice_id` ; montants : `mt_sub_lfi`, `mt_sub_lfr`, `mt_sub_verse` |
| Dividendes | `dividende_sp` | Organisme : `organisme_id` ; exercice : `exercice_id` ; montants : `mt_div_prevu`, `mt_div_realise` |
| Validation des états | `validation_etats` | Organisme : `organisme_id` ; exercice : `exercice` ; type : `type_etat` ; niveau : `validation_id` ; date : `dt_validation` |
| Résultat net | `ligne_cpte_resultat` | Rubrique `cadre_cpte_resultat_id = 'XI'` ; montant `mt_ligne_gnf` ; organisme `organisme_id` et exercice `exercice` |

La rubrique `XI` du référentiel `cadre_cpte` porte le libellé
« RESULTAT NET (XG+XH+RQ+RS) ». Les règles de sélection entre plusieurs lignes
(source d'information, devise, catégorie, version) restent à vérifier avant import.

## Règles métier confirmées

- Un état est considéré comme transmis lorsqu'il est validé par le Directeur technique.
- Les niveaux `4` (« Validé par Directeur Technique ») et `6` (« Résultat disponible »)
  satisfont cette règle. L'inclusion du niveau `6` a été explicitement confirmée par l'utilisateur.
- Les autres niveaux ne satisfont pas cette règle : `0` brouillon, `1` attente Chef Service,
  `2` attente Directeur Technique, `3` renvoi en correction.
- Le résultat net positif indique un organisme excédentaire ; négatif, déficitaire ; nul, à l'équilibre.
  Un montant absent reste indisponible et ne doit pas être transformé en zéro.
- Les transferts de l'État restent issus de la Chaîne Dépense, titre 4 (confirmation utilisateur).
- Pour les subventions, le montant prévu est initialement la LFI (`mt_sub_lfi`), puis la LFR
  (`mt_sub_lfr`) après révision (confirmation utilisateur). Les deux montants ne s'additionnent pas.
  Une LFR à zéro donne un prévu de zéro (confirmation utilisateur) : ne jamais revenir
  à la LFI au motif que la LFR vaut zéro. Le signal d'application de la LFR reste
  à identifier pour distinguer une situation initiale d'une situation révisée.

### Profil des subventions vérifié en lecture seule

`mt_sub_lfi` et `mt_sub_lfr` sont obligatoires (`NOT NULL`). Aucun statut ni date
d'application de la LFR n'apparaît dans la structure de `subvention_etat`.
Le profil agrégé observé contient 42 lignes pour 2024 (35 LFR positives, 7 à zéro)
et 47 lignes pour 2025 (40 LFR positives, 7 à zéro). Aucun cas observé ne combine
une LFI positive et une LFR à zéro ; aucune LFR négative n'a été relevée.
La règle métier confirmée par l'utilisateur conserve une LFR à zéro comme un prévu à zéro.

## Traitement de l'import initial et limites

- Le connecteur dédié `SysopPortefeuilleConnector` charge toutes les tables de faits
  en une transaction locale et lit SYSOP dans une transaction en lecture seule
  avec isolation répétable. Il est sélectionné par le profil `sysop_portefeuille`.
- Les organismes sont résolus par `identifiant_etat`, sans utiliser les identifiants
  source comme clés primaires Django. Les tutelles ne sont pas encore rapprochées.
- Pour 2025, les subventions sont affichées sur la base LFR, y compris les zéros.
- Les montants `mt_sub_verse` et `mt_div_realise` alimentent respectivement payé
  et encaissé ; `mt_div_prevu` alimente voté. Ces correspondances restent à affiner
  si les définitions SYSOP distinguent prévision, vote et encaissement effectif.
- L'import retient une version par organisme/type d'état, ordonnée par date de
  validation puis identifiant. Tous les types présents doivent être aux niveaux
  `4` ou `6` et sans date de rejet pour compter l'organisme comme validé. Le jeu
  complet de documents requis et la gestion des versions restent à formaliser.
- Plusieurs lignes XI pour le même organisme bloquent l'import : aucune somme
  arbitraire de résultats de sources ou catégories différentes n'est effectuée.
- Le comptage porte sur le référentiel actuel des organismes, sans reconstruction
  de leur périmètre historique ni de leurs dates d'activité en 2025.

## Points restant à compléter

1. Définir les prochains exercices à charger et la fréquence d'actualisation.
2. Identifier les valeurs de `type_etat` et définir les documents exigés par organisme :
   un bilan validé seul ne permet pas de supposer que tous les états financiers sont transmis.
3. Définir le traitement des versions, corrections et rejets pour retenir l'état courant,
   sans compter plusieurs fois un organisme ou réutiliser une validation devenue caduque.
4. Identifier le signal d'application de la LFR (statut, date ou valeur absente),
   et confirmer si `mt_sub_verse` représente le payé attendu par le dashboard.
5. Confirmer que les dividendes prévus/réalisés correspondent bien aux votés/encaissés,
   ainsi que l'unité monétaire et le grain des lignes des deux tables de montants.
6. Rapprocher les tutelles SYSOP avec les sections du dashboard.
7. Compléter le traitement des états requis, des versions et des rejets avant extension des résultats financiers.
8. Identifier la source des mandats d'administrateurs et du budget primitif des EPA.

Les contrôles de l'import sont conservés dans le journal des chargements ; un échec
de validation ne remplace pas une situation précédemment chargée avec succès.
