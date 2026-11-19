# Manuel utilisateur

Système intégré de pilotage des finances publiques — Ministère de l'Économie, des Finances et du Budget.
Livrable n° 6 des termes de référence. Version 1.0, 10 octobre 2026.

Ce manuel s'adresse aux personnes qui consultent le tableau de bord : cabinet, directeurs, analystes et
lecteurs. L'administration technique est décrite dans le guide d'exploitation.

## 1. Se connecter

1. Ouvrir l'adresse de l'application dans le navigateur, depuis le réseau du ministère ou par le VPN.
2. Saisir l'identifiant et le mot de passe remis par l'administrateur.
3. Selon le profil, un **code à six chiffres** est demandé (voir ci-dessous).

### Double authentification

Les profils Ministre / Cabinet, Administrateur et Analyste doivent confirmer leur connexion avec un code
généré par une application d'authentification sur leur téléphone (Google Authenticator, Microsoft
Authenticator ou équivalent).

- **Première connexion** : l'écran affiche une clé à enregistrer dans l'application du téléphone. Saisir
  ensuite le code affiché par le téléphone pour terminer.
- **Connexions suivantes** : saisir le code du moment.
- **Code refusé** : vérifier que l'heure du téléphone est exacte, attendre le code suivant et réessayer.
- **Téléphone perdu ou changé** : demander à l'administrateur de réinitialiser la double authentification.

La session se ferme d'elle-même après dix heures sans activité.

## 2. Comprendre l'écran

### L'en-tête

- **Exercice** et **Situation au** : ils s'appliquent à toutes les pages. La date de situation est la date à
  laquelle les données ont été arrêtées dans l'application source. Changer de date permet de revoir une
  situation passée.
- **Montants en Mds GNF** : sauf mention contraire, les montants sont en milliards de francs guinéens.
- **Lune ou soleil** : thème sombre ou clair.
- **Pastille à vos initiales** : votre profil, et le bouton de déconnexion.

### La barre d'onglets

Dix pages : Synthèse, Dépenses, Trésorerie, Recettes fiscales, Recettes douanières, Dette publique,
Investissements, Patrimoine de l'État, Portefeuille de l'État, Marchés publics. Vous ne voyez que les pages
de votre périmètre.

À droite de la barre :

| Bouton | Effet |
|---|---|
| Sommaire (à gauche) | Liste des sections de la page, pour y aller directement |
| Longue-vue | Exploration des données (analystes et administrateurs) |
| Roue dentée | Administration (administrateurs) |
| Flèches | Mode présentation : navigation masquée et contenu agrandi, pour la projection |
| Imprimante | Impression de la page au format A4 paysage |

### L'origine de chaque chiffre

Chaque indicateur et chaque graphique porte une pastille :

| Pastille | Signification |
|---|---|
| Nom de l'application · **réel** · date | Chiffres issus de l'application source, à la date indiquée |
| Nom de l'application · **illustration** (bordure en pointillés) | Chiffres **fictifs**, qui montrent la forme de l'information en attendant le raccordement de l'application. Ne pas les utiliser pour décider. |
| **non raccordée** | Aucune donnée pour cette application |

Une page alimentée par des données d'illustration affiche en plus un bandeau en haut de page.

### Les états

Les états sont toujours écrits, jamais donnés par la seule couleur :

| État | Sens |
|---|---|
| Critique | Situation qui appelle une décision immédiate |
| Sérieux | Situation à traiter |
| Vigilance | Point à surveiller |
| Bon / Conforme | Rien à signaler |

## 3. Les pages

Chaque page suit le même ordre : indicateurs clés, points d'attention, analyses, détail. Les définitions et
les formules de tous les indicateurs sont dans le dictionnaire des indicateurs.

| Page | Ce qu'on y lit |
|---|---|
| Synthèse | Les six indicateurs principaux, les alertes ouvertes, les recettes et les dépenses par mois, l'état des sources |
| Dépenses | Crédits, engagements, ordonnancements et paiements ; chaîne de la dépense ; ministères en sous-exécution ou en retard de paiement ; restes à payer ; bénéficiaires |
| Trésorerie | Solde de fin de période, jours de décaissements couverts, flux, délais de paiement |
| Recettes fiscales | Recouvrement face à l'objectif, par impôt et par centre ; restes à recouvrer ; contentieux |
| Recettes douanières | Recettes face à l'objectif, par bureau ; délais de dédouanement ; exonérations |
| Dette publique | Encours, ratio dette / PIB face au seuil de la CEDEAO, échéancier |
| Investissements | Engagement des crédits d'investissement, projets sans engagement |
| Patrimoine de l'État | Valeur des biens, parc de véhicules, contrôles de la comptabilité matière |
| Portefeuille de l'État | Subventions aux EPA, dividendes, santé financière des organismes |
| Marchés publics | Marchés immatriculés, part de l'entente directe, délais, contrôles de cohérence entre réservations, marchés et paiements |

### Gestes utiles

- **Icône « i »** à côté d'un indicateur : sa définition.
- **Voir le tableau** sous un graphique : les mêmes chiffres en tableau.
- **En-tête de colonne** d'un tableau : tri croissant ou décroissant.
- **Champ « Rechercher »** au-dessus d'un tableau : filtre sur le texte.
- **Clic sur une ligne** (par exemple un ministère dans la page Dépenses) : ouvre le détail dans un panneau
  latéral. La touche Échap le ferme.
- **Page Dépenses, « paiements ajustés / bruts »** : la vue ajustée exclut les procédures payées hors de la
  chaîne de la dépense (dette, salaires) ; c'est la vue par défaut.

Tout est utilisable au clavier : Tab pour avancer, Entrée pour ouvrir, Échap pour fermer.

### La projection de fin d'exercice

Les pages Dépenses, Recettes fiscales et Recettes douanières affichent une carte **Projection de fin
d'exercice**. Elle prolonge le montant constaté jusqu'au 31 décembre et donne une **fourchette**, pas un
chiffre unique.

- Le trait plein est le cumul constaté ; la bande en tirets est la fourchette projetée ; la ligne horizontale
  en tirets est la cible (crédits ou objectif annuel).
- **Méthode et fiabilité** détaille le calcul et indique de combien la méthode se serait trompée si on l'avait
  appliquée plus tôt dans l'année.
- Dans la page Dépenses, un tableau liste les ministères les plus éloignés de leurs crédits en fin d'exercice.

La projection est **indicative** : elle suppose que le rythme constaté se poursuit. Elle ne connaît ni les
décisions à venir ni l'accélération habituelle de fin d'année, et elle sous-estime en début d'exécution.

## 4. Les alertes

La page Synthèse liste les alertes ouvertes, de la plus grave à la moins grave. Chaque alerte indique ce
qui est constaté, la valeur mesurée, l'action recommandée et la source.

- Filtrer par gravité ou par domaine avec les boutons au-dessus de la liste.
- **Détail** : explication complète du constat.
- **Marquer comme traitée** : l'alerte quitte la liste des alertes ouvertes. Elle reviendra si la situation
  se reproduit lors d'un chargement suivant.

Les alertes sont recalculées à chaque nouveau chargement de données.

## 5. Exporter et imprimer

- **Exporter (Excel)**, en haut à droite de chaque page : un classeur avec une feuille par tableau, et une
  feuille « Lisez-moi » qui rappelle l'exercice, la date de situation, les filtres et, pour chaque feuille, la
  source et son statut (réel ou illustration). Le profil Lecteur ne peut pas exporter.
- **Imprimer** : la page est mise en forme pour le format A4 paysage, avec l'en-tête officiel et la mention
  « Document de travail – diffusion restreinte ».

Chaque export est inscrit au journal d'audit.

## 6. Explorer les données (analystes)

La page **Exploration des données** permet de construire ses propres tableaux, dans la limite de ses
domaines.

1. **Jeu de données** : choisir la table à interroger (par exemple « Engagements » ou « Marchés
   immatriculés »).
2. **Situation** : par défaut, la dernière chargée.
3. **Regrouper par** : cocher jusqu'à cinq axes (ministère, nature, mode de passation…). Une date peut être
   regroupée par mois, par trimestre ou par année.
4. **Mesures** : cocher les montants ou quantités à calculer, et choisir pour chacun somme, moyenne, minimum
   ou maximum. Le nombre de lignes est toujours compté.
5. **Filtres** : ajouter des conditions (égal à, différent de, contient, au moins, au plus, parmi).
6. **Lancer la requête**.

Le résultat s'affiche en tableau, avec les totaux et un graphique de la première mesure. Les montants y sont
en **francs guinéens, non arrondis**. Le bouton **Exporter (Excel)** produit le résultat complet (jusqu'à
50 000 lignes), accompagné d'une feuille « Lisez-moi ».

Sans aucun axe, la requête renvoie les totaux du jeu de données.

## 7. Les profils

| Profil | Voit | Peut exporter | Exploration | Double authentification |
|---|---|---|---|---|
| Ministre / Cabinet | Toutes les pages | Oui | Non | Oui |
| Directeur | Les pages de ses domaines | Oui | Non | Non |
| Analyste | Les pages de ses domaines | Oui | Oui, sur ses domaines | Oui |
| Lecteur | Les pages de ses domaines | Non | Non | Non |
| Administrateur | Toutes les pages et l'administration | Oui | Oui | Oui |

## 8. Questions fréquentes

**Les chiffres n'ont pas changé depuis hier.** Regarder la date de situation dans la pastille : elle indique
la date de la dernière extraction chargée, pas la date du jour.

**Une page affiche « illustration ».** L'application correspondante n'est pas encore raccordée ; les chiffres
sont fictifs.

**Une page manque dans la barre d'onglets.** Elle n'est pas dans votre périmètre. S'adresser à
l'administrateur.

**Un total ne correspond pas à celui d'une autre application.** Vérifier la date de situation, puis la vue
des paiements (ajustée ou brute). Si l'écart demeure, le signaler à l'administrateur avec la page, la date et
le chiffre attendu.
