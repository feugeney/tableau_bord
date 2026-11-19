# Correction des KPI de dépenses — RCD1105A

> **Remplacé le 18/11/2026.** Sur décision de pilotage, chaque taux est désormais
> rapporté à l'étape précédente de la chaîne : liquidé / engagé, ordonnancé / liquidé,
> VBP / ordonnancé, payé / ordonnancé (l'engagement reste engagé / crédits). Les taux de la page
> Dépenses ne reproduisent donc plus les pourcentages du rapport RCD1105A ci-dessous, qui reste
> documenté pour mémoire. Formules en vigueur : `apps/core/regles.py` et `dictionnaire-indicateurs.md`.

## Référence et périmètre

Rapport fourni par l'utilisateur : « Taux d'exécution des crédits », RCD1105A,
exercice 2026, daté du 12 novembre 2026, groupe administratif 3101,
section 31 (ministère de l'Environnement). Les deux pages ont été inspectées.
La deuxième page poursuit la ligne des totaux ; elle n'est pas un second jeu de données à additionner.

## Formules du rapport

| Colonne | Montant | Formule du taux |
|---|---|---|
| 1 | Crédit | — |
| 2 | Engagé | 2 / 1 |
| 3 | Ordonnancé | 3 / 2 |
| 4 | Vu bon à payer | 4 / 2, intitulé « Arriérés % » dans le rapport |
| 5 | Payé | 5 / 2 |

Le dashboard utilisait ordonnancé/crédit et payé/crédit comme taux principaux.
Ils sont remplacés par ordonnancé/engagé et payé/engagé. Le ratio VBP/engagé est ajouté.
Les calculs emploient les sommes des montants exacts en GNF avant division,
et non une moyenne des pourcentages des lignes. Le dénominateur nul donne un taux indisponible.

La colonne « Arriérés % » désigne dans ce document VBP/engagé ; elle ne prouve
ni un montant d'impayés ni leur ancienneté. Les restes à payer conservent leur
calcul distinct ordonnancé − payé, avec le mode brut/ajusté existant.
Les taux RCD1105A sont bruts et ne changent pas lorsque ce mode est basculé.

## Exemple numérique vérifié

| Mesure de la ligne section 31 | GNF |
|---|---:|
| Crédit | 384 760 237 928 |
| Engagé | 185 491 586 590 |
| Ordonnancé | 178 162 952 352 |
| VBP | 97 406 108 382 |
| Payé | 65 312 383 218 |

Les taux arrondis à l'entier reproduisent **48 %, 96 %, 53 %, 35 %**
(engagement, ordonnancement, VBP, paiement). Cet exemple est couvert par des tests
des règles et du service API ; il ne constitue pas une nouvelle situation importée.

## Propagation

- Page Dépenses : taux et références explicites, ajout du VBP/engagé.
- Simandou : taux de paiement sur les engagés, référence indiquée à l'écran.
- Masse salariale et Synthèse : les comparaisons explicitement présentées face aux crédits
  restent sur les crédits, via le champ distinct `taux_ordonnancement_sur_credits`.
- Exports : intitulés des taux et formats de pourcentage mis à jour.
- La chaîne graphique conserve ses ratios complémentaires sur les crédits, indiqués dans son sous-titre.
- Les autres indicateurs alimentés par la Chaîne Dépense sont rafraîchis par les vues matérialisées et le cache API.

## Disponibilité des sources et contrôles de rechargement

L'utilisateur a autorisé une exception ponctuelle au créneau Oracle, en lecture seule.
L'aperçu 2026 est vide dans GDEP. L'inventaire des exercices accessibles confirme
que GDEP et GBPROG s'arrêtent à 2025 ; GB contient les anciens exercices jusqu'à 2017.
Le rapport 2026 ne doit donc pas être présenté comme rapproché des données Oracle 2025.
Il faudra identifier une source contenant 2026 pour en afficher les montants.

Pour 2025, l'écart global brut préexistant est dû au périmètre des dossiers abandonnés
E9N et des dégagements (procédure 52), déjà analysé dans `analyse-rapprochement-2025.md`.
Le contrôle Oracle vérifie désormais le candidat comparable sur chaque clé budgétaire
complète de 14 colonnes : le périmètre n'est accepté que si toutes les clés concordent.
Une compensation entre lignes ne suffit pas à valider le chargement.
Les dossiers exclus de ce contrôle restent intégralement conservés dans l'entrepôt ;
aucun filtre supplémentaire n'est appliqué aux montants LBUDG ou aux engagements chargés.
Le contrôle est bloquant, sans recours à l'option d'acceptation d'un écart de test.

Le rechargement réel a réussi le 13 novembre 2026 (chargement n° 8) :
13 395 lignes budgétaires et 24 958 engagements, soit 38 353 faits chargés,
sans rejet. Les vues de restitution, les alertes et le cache API ont été rafraîchis.
L'exercice 2026 n'a pas été importé ; l'aperçu vide reste tracé comme un échec.

Les écarts de liquidation et de visa CF documentés précédemment restent à analyser
séparément : la concordance des engagements n'atteste pas l'égalité de toutes les étapes.
