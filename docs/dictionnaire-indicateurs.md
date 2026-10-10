# Dictionnaire des indicateurs

Système intégré de pilotage des finances publiques (tableau de bord de la Ministre) — Ministère de l'Économie, des Finances et du Budget (République de Guinée).

Ce document définit chaque chiffre affiché : ce qu'il mesure, comment il est calculé, d'où il vient et quels
seuils déclenchent une alerte. Les seuils sont réglables sans intervention technique
(Administration › Paramètres et seuils) ; les valeurs indiquées ici sont les valeurs par défaut.

**Conventions**

- Montants stockés en GNF, affichés en milliards de GNF (« Mds »), avec une décimale.
- Pourcentages affichés sans décimale.
- Tous les taux de la Chaîne Dépense se calculent **sur les crédits actuels** (LFI + LFR + mouvements).
- Chaque chiffre porte une pastille de source : application, statut (réel, illustration, non raccordée) et
  date de situation.
- **Paiement ajusté** (affichage par défaut) : les engagements dont la procédure est payée hors de la chaîne
  sont exclus de l'ordonnancé et du payé. Ce sont la procédure Solde (salaires), les débits d'office (dette) et
  les régularisations PCT. Sans cet ajustement, ils feraient apparaître un faux reste à payer. Le mode « Bruts »
  les réintègre.

## 1. Dépenses (Chaîne Dépense)

| Indicateur | Définition et formule | Seuil / alerte |
|---|---|---|
| Crédits LFI | Σ `credit initial LFI` des lignes budgétaires. Valeur vide comptée 0 et signalée. | — |
| Crédits actuels | Σ `credit actuel`. | — |
| Variation LFI | (crédits actuels − crédits LFI) / crédits LFI. | — |
| Engagé | Σ `credits engages` (onglet Situation courante). | — |
| Taux d'engagement | Engagé / crédits actuels. | voir statut des ministères |
| Liquidé, ordonnancé, VBP, payé | Σ des colonnes correspondantes de Situation courante. | Note si liquidé > engagé |
| Taux d'ordonnancement | Ordonnancé / crédits actuels. | — |
| Taux de paiement | Payé / crédits actuels. | — |
| Ordonnancé ajusté | Ordonnancé − ordonnancé des engagements « hors chaîne ». | — |
| Payé ajusté | Payé − payé des engagements « hors chaîne ». | — |
| Payé / ordonnancé ajusté | Payé ajusté / ordonnancé ajusté. | < 35 % : paiements en retard (voir statut) |
| Reste à payer ajusté | Ordonnancé ajusté − payé ajusté. | — |
| Crédits non engagés | Crédits actuels − engagé. | — |
| Crédits disponibles | Σ `credits disponible`. | — |
| Ligne en dépassement | Ligne budgétaire dont les crédits disponibles sont < −1 GNF. | Alerte « lignes en dépassement » (sérieux) |
| Liquidé > engagé | Lignes dont le liquidé dépasse l'engagé. | Note sur la chaîne de la dépense |
| Rythme mensuel | Σ engagé par mois de **création** de l'engagement. Les mois postérieurs au 31 décembre relèvent de la période complémentaire. | Décembre et période complémentaire mis en évidence |
| Restes à payer par ancienneté | Σ (ordonnancé − payé) des engagements, par mois de création ; ancienneté = mois écoulés jusqu'à la date de situation. | > 12 mois : risque d'arriérés (alerte, sérieux) |
| Part d'un bénéficiaire | Engagé du bénéficiaire / engagé total. Les variantes d'écriture d'un même nom sont rapprochées. | — |

### Statut d'un ministère

Appliqué dans cet ordre, à partir des paiements **ajustés** :

1. **Sous-exécution** (critique) : crédits actuels ≥ 20 Mds et taux d'engagement < 50 % ;
2. sinon **Paiements en retard** (sérieux) : ordonnancé ajusté ≥ 20 Mds et payé / ordonnancé ajusté < 35 % ;
3. sinon **À suivre** (vigilance) : taux d'engagement < 75 % ;
4. sinon **Bon rythme**.

## 2. Investissements (Chaîne Dépense, titre 5 ; SIGPIP)

| Indicateur | Définition et formule | Seuil / alerte |
|---|---|---|
| Crédits, engagé, payé | Sommes des lignes du titre 5. | — |
| Projet | Une sous-section du titre 5. | — |
| Projet sans engagement | Crédits actuels > 1 Md et engagé nul. | Alerte « investissement faiblement engagé » (critique) si taux < 50 % ou projets sans engagement |
| Avancement physique | Taux d'avancement déclaré dans SIGPIP. | Affiché dès le raccordement de SIGPIP |

## 3. Recettes fiscales (SAFIG)

| Indicateur | Définition et formule | Seuil / alerte |
|---|---|---|
| Recouvré | Σ recouvré depuis le début de l'exercice. | — |
| Objectif de la période | Σ objectifs mensuels des mois écoulés (et non l'objectif annuel). | — |
| Taux de recouvrement | Recouvré / objectif de la période, global et par impôt. | < 80 % : « en retard » (alerte, sérieux) |
| Restes à recouvrer | Impositions émises non payées, par ancienneté. | — |
| Contentieux | Montants et dossiers en réclamation, recours ou au tribunal. | — |
| Contribuables actifs | Dernier mois disponible. | — |
| Taux de télédéclaration | Télédéclarants / contribuables actifs. | — |

## 4. Recettes douanières (SYDONIA)

| Indicateur | Définition et formule | Seuil / alerte |
|---|---|---|
| Recouvré, objectif, taux | Comme pour SAFIG, par nature de droit et par bureau. | < 80 % : en retard |
| Exonérations | Σ droits exonérés par régime. Part = exonérations / (recouvré + exonérations). | Part ≥ 10 % : alerte (vigilance) |
| Déclarations traitées | Nombre de déclarations enregistrées. | — |
| Délai moyen de dédouanement | Jours entre enregistrement et mainlevée, pondérés par le nombre de déclarations. | — |
| Circuits | Répartition vert (sans contrôle), jaune (documentaire), rouge (visite physique). | — |

## 5. Trésorerie (SCIE)

| Indicateur | Définition et formule | Seuil / alerte |
|---|---|---|
| Encaissements, décaissements | Σ depuis le début de l'exercice. | — |
| Solde de fin de période | Solde du dernier jour disponible. | — |
| Jours de décaissements | Solde / (décaissements de la période / jours calendaires de la période). | — |
| Seuil de trésorerie | Solde < 1 mois de décaissements moyens. | Alerte « trésorerie sous le seuil » (critique) |
| Délai moyen de paiement | Moyenne mensuelle des délais du mandat au paiement. | — |
| Tableau des opérations financières | Recettes par source (SAFIG, SYDONIA, SCIE), puis dépenses ordonnancées et payées (Chaîne Dépense). Source affichée ligne par ligne. | — |

## 6. Dette publique

| Indicateur | Définition et formule | Seuil / alerte |
|---|---|---|
| Encours total, extérieur, intérieur | Encours à la date de situation, par type de créancier. | — |
| Ratio dette / PIB | Encours total / PIB de l'exercice. | > 70 % (convergence CEDEAO) : alerte critique |
| Service de la dette engagé | Engagé du titre 1 dans la Chaîne Dépense (réel). | — |
| Échéancier | Principal et intérêts dus sur les cinq prochaines années. | — |

## 7. Masse salariale (Chaîne Dépense titre 2 ; FUGAS)

L'onglet a été remplacé par « Marchés publics » ; ces indicateurs restent utilisés par la synthèse et les alertes.

| Indicateur | Définition et formule | Seuil / alerte |
|---|---|---|
| Crédits de personnel | Crédits actuels du titre 2 ; part du budget = crédits titre 2 / crédits totaux. | — |
| Ordonnancé | Ordonnancé du titre 2 ; taux = ordonnancé / crédits du titre 2. | — |
| Masse mensuelle moyenne | Masse brute payée (FUGAS) / nombre de mois. | — |
| Agents payés, coût moyen | Effectif du dernier mois ; masse brute / effectif. | — |
| Contrôles de paie | Doublons, agents sans NIF, sans affectation, départs à la retraite. | Doublons > 0 : alerte (sérieux) |

## 8. Patrimoine (SICOM)

| Indicateur | Définition et formule | Seuil / alerte |
|---|---|---|
| Valeurs nette et brute | Σ par catégorie et par ministère. | — |
| Taux d'amortissement | (valeur brute − valeur nette) / valeur brute. | — |
| Biens immatriculés | Biens immatriculés / biens recensés. | — |
| Véhicules en service | Véhicules en service / parc total. | — |
| Institutions déployées | Institutions utilisant SICOM / institutions prévues. | — |
| Contrôles | Biens non inventoriés depuis plus de 2 ans, sans détenteur, véhicules à réformer, écart avec le SCIE. | Biens non inventoriés : alerte (vigilance) |

## 9. Portefeuille de l'État (SYSOP)

| Indicateur | Définition et formule | Seuil / alerte |
|---|---|---|
| Organismes suivis | Nombre d'EPA et de sociétés publiques. | — |
| Transferts de l'État | Ordonnancé du titre 4 (Chaîne Dépense, réel), face aux crédits du titre 4. | — |
| Subventions aux EPA | Payé face au prévu, par organisme. | — |
| Dividendes | Encaissé / voté. | Dividendes votés non encaissés : alerte (sérieux) |
| Transmission des états financiers | Organismes ayant transmis / organismes suivis. | Organismes déficitaires ou sans états : alerte (vigilance) |
| Mandats expirés | Nombre de mandats d'administrateurs échus. | — |

## 10. Marchés publics (Telemo)

Flux F3 (réservations de crédit), F4 (marchés immatriculés) et F5 (paiements) ; détail dans `flux-telemo.md`.

| Indicateur | Définition et formule | Seuil / alerte |
|---|---|---|
| Marchés immatriculés | Σ montant TTC (F4) ; nombre de marchés ; montant HT. | — |
| Part de l'entente directe | Montant TTC en entente directe / montant TTC total. | > 10 % (`entente_directe_part_max`, à confirmer) : alerte (sérieux) |
| Réservation → immatriculation | Moyenne (date d'immatriculation F4 − date de visa F3), en jours. | > 90 jours (`delai_passation_max_jours`) : vigilance |
| Immatriculation → premier paiement | Moyenne (premier paiement F5 − date d'immatriculation F4), en jours. | — |
| Exécution financière | Σ paiements F5 / Σ montant TTC F4. | — |
| Contrôles de cohérence | Marchés sans réservation ; au-delà du crédit réservé ; paiements au-delà du marché ; paiements sans marché ; réservations non utilisées depuis 90 jours. | Sans réservation, trop payé ou paiement orphelin : alerte (sérieux) |
| Titulaires | Montant TTC par NIF (dix premiers). | — |

## 11. Synthèse

| Indicateur | Source |
|---|---|
| Recettes fiscales et douanières | SAFIG + SYDONIA, chacun sur sa dernière situation ; taux face à l'objectif de la période. |
| Dépenses engagées | Chaîne Dépense (taux d'engagement). |
| Reste à payer ajusté | Chaîne Dépense. |
| Trésorerie fin de période | SCIE (jours de décaissements). |
| Encours de la dette | Application de la dette (ratio dette / PIB face au seuil CEDEAO). |
| Dépenses de personnel ordonnancées | Chaîne Dépense, titre 2. |

## 12. Contrôles de qualité des données (Chaîne Dépense)

| Contrôle | Niveau | Effet |
|---|---|---|
| Colonnes obligatoires présentes | Bloquant | Chargement refusé |
| Concordance du total engagé entre « Situation courante » et « Liste des engagements » (1 GNF par million) | Bloquant | Chargement refusé |
| Exercice et date de situation déterminés | Bloquant | Chargement refusé (à saisir à l'import) |
| Doublons sur la clé de ligne budgétaire | Avertissement | Lignes conservées et comptées |
| Valeurs absentes en LFI / LFR | Information | Comptées pour 0 |
| Lignes en dépassement, liquidé > engagé | Avertissement | Signalées |
| Numéros d'engagement non uniques | Information | Clé technique utilisée |
| Codes stockés comme nombres (zéros initiaux perdus) | Avertissement | Signalés |
