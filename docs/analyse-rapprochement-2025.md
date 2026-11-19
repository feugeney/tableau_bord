# Analyse LBUDG / ENGAGEMENT — exercice 2025

Analyse du chargement Oracle local n° 2, situation extraite le 12 novembre 2026. Aucun chiffre ni règle applicative n'a été modifié pendant ce diagnostic.

## Méthode et intégrité

Comparaison des montants exacts en GNF, sans arrondi, par clé budgétaire complète de 14 colonnes. Chaque engagement est rattaché à sa ligne LBUDG avant agrégation. Les chiffres de la synthèse restent issus de LBUDG.

- 13 395 lignes LBUDG et 24 958 lignes ENGAGEMENT.
- Aucun doublon de clé source dans les deux ensembles.
- Aucun engagement sans ligne budgétaire correspondante.
- Aucune ligne rejetée lors de l'import.

## Cause du principal écart

La somme de tous les états et procédures d'ENGAGEMENT n'est pas le périmètre comparable à LBUDG.MT_ENG pour ces données 2025 :

| Élément | Montant exact GNF |
|---|---:|
| Somme brute ENGAGEMENT.MT_ENG | 33 375 739 016 309 |
| Dossiers abandonnés E9N à écarter du rapprochement | 3 572 137 682 767 |
| Procédure 52 (Dégagement), hors E9N, à écarter | 98 253 866 772 |
| Résultat comparable | 29 705 347 466 770 |
| LBUDG.MT_ENG | 29 705 347 466 770 |

L'égalité est vérifiée pour chaque clé budgétaire : aucune compensation entre lignes n'est nécessaire. Ce constat valide le rapprochement sur cet extrait, et ne constitue pas à lui seul une règle universelle pour tous les exercices. Les dégagements doivent rester traçables dans le détail ; les supprimer physiquement ou inverser arbitrairement leurs montants serait incorrect.

Le filtre limité aux seuls états E3N/F3N est insuffisant : il retire aussi des montants que LBUDG conserve. Il ne doit donc pas devenir un filtre général de la chaîne.

## Résultat par étape, après exclusion E9N et procédure 52

Écart = somme ENGAGEMENT moins somme LBUDG.

| Étape | Écart exact GNF | Lignes budgétaires présentant un écart |
|---|---:|---:|
| Engagé | 0 | 0 |
| Visé CF | 451 606 472 | 5 |
| Liquidé | 4 088 985 828 | 10 |
| Ordonnancé | 0 | 0 |
| Vu bon pour paiement | 0 | 0 |
| En cours de paiement | 0 | 0 |
| Payé | 0 | 0 |

Le reliquat CF est numériquement égal au montant CF des dossiers F1N. L'exclusion supplémentaire de F1N pour cette mesure donne également zéro écart sur chaque clé budgétaire, ce qui a été vérifié localement. La règle métier reste à confirmer spécifiquement pour cette mesure ; retirer les mêmes dossiers des ordonnancements casserait leur concordance déjà obtenue.

Pour la liquidation, les 10 lignes sont localisées. Par exemple, section 10, sous-section 100111000000, nature 3/5/2/10/00 : LBUDG indique 0 GNF liquidé et ENGAGEMENT totalise 1 338 965 328 GNF hors E9N. Le statut courant de l'engagement ne suffit pas à établir le traitement des opérations de liquidation, rejets ou annulations. Il faut examiner ces opérations avant de décider quel montant corriger.

## Conséquences pour l'implémentation

1. Remplacer la comparaison brute des engagements par un rapprochement explicite selon état et procédure, avec conservation des montants et codes source.
2. Vérifier la règle CF concernant F1N indépendamment des autres étapes.
3. Investiguer les opérations de liquidation des 10 lignes résiduelles.
4. Garder les données source intactes et produire des contrôles distincts par étape, plutôt qu'un avertissement général qui laisse croire que tous les montants sont incohérents.

Les résultats détaillés et les clés des cas sont conservés localement dans `captures/local-runtime/oracle/rapprochement_2025.json` et `cas_a_reconcilier_2025.json`, ignorés par Git. Le second fichier détaille les cas du scénario sans E9N avant exclusion des dégagements ; le rapport de rapprochement fournit les 10 clés résiduelles de liquidation du scénario complet.
