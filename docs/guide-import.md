# Guide d'import et de raccordement des sources

À l'usage des administrateurs de la DNSI (rôle « Administrateur DNSI », double authentification).
Toutes les opérations se font dans **Administration** (roue dentée à droite des onglets, ou menu du profil) et
sont inscrites au journal d'audit.

## 1. Charger une extraction de la Chaîne Dépense

1. **Administration › Sources et connecteurs**, choisir « Chaîne Dépense ».
2. Dans « Importer un fichier », sélectionner l'extraction `.xlsx`. Le nom attendu est
   « SC de AAAA-AAAA en date du JJ-MM-AAAA.xlsx » : l'exercice et la date de situation en sont tirés.
   Sinon, les saisir dans les champs prévus.
3. Laisser **« Aperçu seulement »** coché et cliquer sur **Valider le fichier** : rien n'est écrit, les
   contrôles de qualité s'affichent.
4. Si aucun contrôle n'est « Bloquant », décocher l'aperçu et cliquer sur **Charger le fichier**.

Ce qu'il faut savoir :

- Onglets lus : Situation courante, Liste des engagements, Détails des opérations, Régie. Les autres onglets
  (APAD, Délégations de crédits…) sont ignorés ; les colonnes supplémentaires de Situation courante sont conservées.
- **Contrôle bloquant de concordance** : le total engagé de « Situation courante » doit égaler celui de
  « Liste des engagements » à 1 GNF près par million. En cas d'écart, demander une nouvelle extraction à l'équipe
  de la Chaîne Dépense ; ne pas relever la tolérance en production.
- Recharger une même date de situation remplace la précédente dans l'affichage (l'historique est conservé).
  Une nouvelle date s'ajoute : les situations s'empilent.
- Après chaque chargement, les vues sont rafraîchies, le cache est vidé et les alertes sont réévaluées.

Équivalent en ligne de commande (serveur) :

```bash
python manage.py import_chaine_depense "SC de 2025-2025 en date du 15-09-2026.xlsx" --apercu
python manage.py import_chaine_depense "SC de 2025-2025 en date du 15-09-2026.xlsx"
```

## 2. Brancher une extraction Excel ou CSV d'une autre application

Exemple : effectifs et masse salariale mensuels de FUGAS.

1. **Administration › Mappings de colonnes**, source « FUGAS ».
2. Choisir la **table cible** (ex. `fait_paie`). Pour chaque champ, indiquer le nom de la colonne dans
   l'extraction (la casse et les accents sont ignorés), le type de donnée et si la colonne est obligatoire.
   Un champ « référence » (ministère, impôt, bureau…) attend un **code**.
3. **Sources et connecteurs › FUGAS** : connecteur « Excel / CSV générique », configuration
   `{"table_cible": "fait_paie"}`, puis importer le fichier avec aperçu, et enfin charger.

Au premier chargement réussi, le statut de la source passe à « réel » et les données d'illustration de cette
source cessent d'être affichées.

Règle : un code de ministère, de sous-section ou d'organisme inconnu **rejette la ligne**, il n'en crée pas.
Les référentiels propres au domaine (impôts, bureaux, catégories de biens…) sont complétés automatiquement.

## 3. Raccorder Telemo (marchés publics)

Flux F3 (réservations), F4 (marchés immatriculés) et F5 (paiements), chargés **ensemble** ; F1 et F2 sont
déjà couverts par la Chaîne Dépense. Détail et points à confirmer : `flux-telemo.md`.

- **Classeur** : trois onglets « F3 Réservations », « F4 Marchés », « F5 Paiements », intitulés de la
  description des flux en première ligne, fichier `Telemo en date du JJ-MM-AAAA.xlsx`. Importer depuis
  **Sources et connecteurs › Telemo** sans préciser de table cible. Les mappings sont préremplis.
- **API** : variables `TELEMO_API_URL` et `TELEMO_API_TOKEN`, connecteur « API », « Tester la
  connexion », puis charger. Points d'accès : `/reservations-credit`, `/marches-immatricules`, `/paiements`.

Les coordonnées bancaires, l'adresse et le RCCM des titulaires ne sont pas repris dans l'entrepôt.

## 4. Raccorder SICOM ou SYSOP (PostgreSQL)

1. Sur le serveur, renseigner la variable d'environnement avec un **compte en lecture seule** :
   `SICOM_DATABASE_URL=postgresql://lecteur:***@hote:5432/sicom` (idem `SYSOP_DATABASE_URL`), puis redémarrer
   les services `backend`, `worker` et `beat`.
2. **Sources et connecteurs › SICOM** : connecteur « PostgreSQL », configuration :

   ```json
   { "table_cible": "fait_patrimoine", "requete": "SELECT categorie, ministere AS section, valeur_brute, valeur_nette FROM v_tdb_patrimoine" }
   ```

   Seules les requêtes de lecture (`SELECT`) sont acceptées. Mieux vaut interroger une **vue dédiée** créée
   par l'équipe de l'application.
3. Déclarer les correspondances de colonnes (section 2) pour la table cible.
4. **Tester la connexion**, puis indiquer la planification, par exemple `0 2 * * *` (chaque nuit à 2 h).

## 5. Raccorder la Chaîne Dépense en direct (Oracle)

- Variables : `CHAINE_DEPENSE_ORACLE_DSN`, `CHAINE_DEPENSE_ORACLE_USER`, `CHAINE_DEPENSE_ORACLE_PASSWORD`
  (compte en lecture seule, sur une **réplique** ou des vues dédiées).
- Connecteur « Oracle — Chaîne Dépense ». La configuration donne une requête par onglet, avec les mêmes colonnes
  que l'extraction Excel :

  ```json
  { "replique": true, "requetes": { "situation": "SELECT … FROM v_situation_courante", "engagements": "SELECT … FROM v_engagements" } }
  ```

- Sans `"replique": true`, tout chargement est **refusé aux heures ouvrées** (7 h 30 – 18 h 30, du lundi au
  vendredi) pour protéger la base de production.

## 6. Données d'illustration

**Administration › Entrepôt et illustration › Générer les données d'illustration** remplit les onglets des sources
non raccordées avec des chiffres fictifs et des organismes fictifs, signalés « illustration » partout. Une source
déjà raccordée n'est jamais modifiée. « Retirer les données d'illustration » revient à « Source non raccordée ».

## 7. Partager des données avec un autre système

**Administration › Partage de données (API) › Nouveau jeton** : nom, destinataire, domaines partagés, date
d'expiration. La clé s'affiche **une seule fois** : la transmettre par un canal sûr. Le système tiers appelle
l'API en lecture seule :

```bash
curl -H "Authorization: Jeton tdb_…" https://<serveur>/api/v1/depense/indicateurs/
```

Un jeton peut être suspendu (coupure temporaire) ou révoqué (définitif).

## 8. Recevoir les fichiers par dépôt SFTP

Au lieu d'un import manuel, un partenaire peut déposer ses fichiers par SFTP dans le dossier de sa source
(`sources/<code>/`). Ils sont chargés automatiquement toutes les 5 minutes, avec le connecteur et le mapping
de la source, puis retirés du dépôt. Formats : Excel, CSV, XML, JSON. Mise en place, schémas JSON à remettre
au partenaire et événements de fin de chargement : `echanges-partenaires.md`.

## 9. Retrouver le fichier d'un chargement

Chaque fichier importé est conservé tel que reçu. Dans **Administration › Imports et chargements**, ouvrir un
chargement : on y lit l'identifiant du flux (UUID), l'empreinte SHA-256 du fichier, et le bouton « Télécharger
le fichier reçu ». Si le même fichier a déjà été chargé, la mention « Contenu déjà chargé » indique le numéro
du chargement précédent.

## 10. En cas de problème

| Symptôme | Cause probable | Action |
|---|---|---|
| « Concordance du total engagé » bloquant | Extraction incomplète ou prise à deux instants différents | Nouvelle extraction complète |
| « Colonnes obligatoires » bloquant | En-têtes renommés dans l'extraction | Vérifier les en-têtes, ou le mapping (sources génériques) |
| « Date de situation introuvable » | Nom de fichier non standard | Saisir la date à l'import |
| Lignes rejetées | Code de ministère ou d'organisme inconnu | Compléter le référentiel (admin Django) puis recharger |
| Test de connexion en échec | Variable d'environnement absente, réseau, droits | Vérifier la variable, l'accès réseau au serveur source et le compte en lecture seule |
| Chiffres inchangés après un import | Import en mode aperçu | Décocher « Aperçu seulement » et recharger |
