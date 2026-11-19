# Étude de l’extraction pour enrichir les dépenses et l’exécution budgétaire

Date de l’étude : 13 novembre 2026.

Le classeur fourni permet d’enrichir le suivi des dépenses. Une partie est déjà exploitée dans le tableau de bord. Les priorités sont le rapprochement des différentes vues, le suivi des disponibilités, les délais de traitement et le détail des avances APAD.

## Source et méthode

Source étudiée : `SC des pp_du_dimanche 16 août 2026 22_10_49.xlsx`, dans le dossier Téléchargements. Lecture de l’ensemble des six feuilles, des en-têtes, des cellules renseignées et des formules. Aucun changement du classeur ni nouvel import en base n’a été effectué. Aucune formule Excel n’est présente : les montants sont des valeurs exportées par le système producteur.

L’empreinte SHA-256 du fichier est `5eb8a77aa1840f442a2e0ff9dfbb5a305bbc9a13d672a3292d736fc5ed3d64aa`. Elle correspond exactement au chargement **1**, déjà réussi dans la base locale : exercice **2026**, date de situation enregistrée **16 août 2026**, **2 470 faits** chargés. Il faut compléter cet usage, sans réimporter en doublon.

La date du 16 août provient du nom de l’export et de ses métadonnées d’import. La feuille « Situation courante » ne comporte pas sa propre colonne exercice/date de situation. Les feuilles de détail renseignées portent l’exercice 2026. Le périmètre exact du rapport et l’heure d’arrêté doivent être confirmés auprès du producteur. Les montants ci-dessous suivent la convention GNF de l’application. Le classeur ne fournit pas un libellé d’unité globale permettant de la confirmer indépendamment. Les montants en devises sont traités séparément.

## Ce que contient réellement le fichier

Les effectifs excluent la ligne d’en-tête et les lignes vides.

| Feuille et plage inspectée | Données | Situation dans l’application |
|---|---|---|
| Situation courante, A1:AO1809 | 1 808 lignes budgétaires, 41 colonnes, 38 sections, 671 sous-sections | Déjà chargée dans `FaitSituationLigne` |
| Liste des engagements, A1:AH662 | 661 lignes de détail, 34 colonnes, 34 sections, 234 libellés de bénéficiaires distincts | Déjà chargée dans `FaitEngagement` |
| Détails des opérations, A1:Y1 | En-têtes uniquement | Structure reconnue, aucune opération disponible |
| Délégations de credits, A1:T1 | En-têtes uniquement | Feuille ignorée par le connecteur actuel |
| Régie, A1:S2 | Une ligne, montant de 30 000 000 000 | Déjà chargée dans `FaitRegie` |
| APAD, A1:S85 | 84 lignes, 70 numéros de marché distincts, 20 sections, 44 sous-sections | Feuille ignorée par le connecteur actuel |

Le type de budget est `000` dans les lignes renseignées. Les titres présents sont 2, 3, 4 et 5. Ce fichier seul ne prouve donc pas la couverture de l’ensemble du budget national. Les créations d’engagement commencent le **27 avril 2026** et finissent le **13 août 2026** : l’absence d’enregistrements de janvier à mars ne doit pas devenir une dépense nulle certifiée.

Les colonnes supplémentaires de la situation sont déjà conservées dans `attributs`. Les piliers Simandou et le marquage « green » disposent déjà d’un traitement et d’un affichage. La fonction et la catégorie de projet sont conservées, mais ne disposent pas de la même restitution dédiée dans Dépenses.

## Chiffres de référence et contrôles

Totaux calculés depuis les 1 808 lignes de « Situation courante », sans ajouter les autres feuilles.

| Mesure | Montant selon la convention GNF |
|---|---:|
| Crédits actuels, W2:W1809 | 25 141 131 129 628 |
| Crédits engagés, Z2:Z1809 | 3 226 607 108 344 |
| Liquidé, AC2:AC1809 | 2 394 496 878 496 |
| Ordonnancé, AD2:AD1809 | 1 567 493 279 338 |
| Payé enregistré, AG2:AG1809 | 228 911 083 856 |
| Disponible source, X2:X1809 | 19 870 347 346 187 |
| Réservé, Y2:Y1809 | 934 130 613 565 |
| Bloqué, AH2:AH1809 | 1 110 046 061 532 |

Les taux calculés sur ce périmètre sont : engagé/crédits **12,83 %**, payé enregistré/crédits **0,91 %**, ordonnancé/engagé **48,58 %**, payé enregistré/ordonnancé **14,60 %**. Ce sont des ratios de l’extraction, pas une mesure certifiée de l’exécution nationale ou des décaissements du Trésor.

### La disponibilité peut être expliquée précisément

L’égalité suivante est vérifiée sur **les 1 808 lignes**, sans exception :

`Disponible source = crédits actuels − engagé − réservé − bloqué`

Ainsi, « crédits non engagés » et « disponible source » représentent deux montants différents. Les crédits non engagés s’élèvent à **21 914 524 021 284**. La différence de **2 044 176 675 097** correspond exactement au réservé et au bloqué dans cet export. Une restitution de cette décomposition aiderait directement les utilisateurs.

L’égalité `engagé = engagé en projet + engagé CF` est aussi vérifiée sur chaque ligne. Le projet d’engagement n’est donc pas un montant supplémentaire à ajouter au total engagé. Il ne faut pas non plus ajouter les autres phases de la chaîne entre elles.

### Les deux vues de la dépense ne concordent pas entièrement

Comparaison par section, sous-section, titre, chapitre, article, paragraphe, sous-paragraphe, source de financement, groupe bailleur et bailleur. L’exercice et le type de budget sont constants dans ce fichier. Aucune collision de clé n’est observée dans la situation avec cette combinaison. La régulation reste une dimension à conserver dans le modèle, même si le détail des engagements ne la fournit pas.

| Mesure | Situation courante | Liste des engagements | Écart situation moins détail | Clés en écart |
|---|---:|---:|---:|---:|
| Engagé | 3 226 607 108 344 | 3 225 807 108 344 | +800 000 000 | 2 |
| Engagé CF | 1 749 613 772 242 | 1 751 936 860 472 | −2 323 088 230 | 2 |
| Liquidé | 2 394 496 878 496 | 2 370 166 938 496 | +24 329 940 000 | 4 |
| Ordonnancé | 1 567 493 279 338 | 1 567 493 279 338 | 0 | 0 |
| VBP | 845 408 644 388 | 845 907 144 388 | −498 500 000 | 2 |
| Payé | 228 911 083 856 | 228 911 083 856 | 0 | 0 |

L’écart engagé de 800 millions est localisé sur la section `79`, sous-section `261003000000` : 600 millions pour le titre 2, nature `1/1/14/03`, et 200 millions pour le titre 3, nature `1/2/10/00`. Le financement est `2/0/001` pour les deux. Les engagements correspondants ne sont pas présents avec ces montants sur ces imputations dans la liste. Le motif ne peut pas être déduit de l’export seul.

Le chargement historique a accepté cet écart avec une tolérance enregistrée de **300 GNF par million**. Une réussite technique d’import ne signifie donc pas une égalité comptable. Le tableau de rapprochement doit présenter les différences exactes et leur résolution, même si la tolérance est respectée. Les projections et courbes issues des engagements doivent continuer à afficher leur écart à la situation de référence.

Autres constats : **39 lignes** ont un liquidé supérieur à l’engagé, **4 lignes** ont un disponible négatif, **11 lignes** n’ont pas de LFI renseignée et **toutes les LFR sont vides**. Les quatre disponibles négatifs sont aux lignes Excel 1719, 1769, 1772 et 1775. Aucun engagé n’est supérieur aux crédits actuels dans ce fichier : un disponible négatif ne permet pas, à lui seul, de conclure à ce type de dépassement.

## Enrichissements recommandés

| Priorité | Restitution proposée | Calcul ou source | Condition d’usage |
|---|---|---|---|
| 1 | Crédits non engagés, réservés, bloqués et disponible source | W, X, Y, Z et AH de la situation | Afficher séparément les notions et conserver la valeur source négative |
| 1 | Tableau de rapprochement situation/détail | Agrégation au même périmètre, pour chaque mesure du tableau précédent | Montrer les clés en écart et distinguer import réussi et données rapprochées |
| 2 | Délai de visa CF et dossiers sans visa renseigné | Dates de création et de visa CF, AD et AE des engagements | Calculer sur les paires datées, publier l’effectif couvert, ne pas assimiler toute date manquante à un blocage |
| 2 | Avances APAD par ministère, projet et marché | APAD A:S, montant R et date S | Charger dans une table distincte et rapprocher avant consolidation |
| 2 | Régies enregistrées | Feuille Régie, montant Q, date R, état S | Une demande validée DAF ne prouve pas un paiement ni une justification comptable |
| 3 | Exécution par fonction et catégorie de projet | Situation AN:AO, croisement avec W, Z, AD et AG | Conserver « non codifié » et « non renseigné » comme catégories explicites |
| 3 | Qualité du rattachement aux piliers Simandou | Situation AL, restitution existante à compléter | Une cellule vide ne prouve pas que le projet est hors du programme |

### Délais de traitement

Les **661** engagements ont une date de création. **333** ont une date de visa CF et **332** une date de visa ministre. Sur les 333 paires création/visa CF, la médiane est **5 jours calendaires**, le maximum **94 jours** et aucun délai n’est négatif. Ce constat porte uniquement sur les lignes avec les deux dates.

Les 332 visas ministre datés portent le même jour que le visa CF. Avant d’en faire un indicateur de performance, vérifier si ces dates représentent deux validations indépendantes ou une alimentation commune par le système. Les colonnes `Date état` et `Date Maj` ne constituent pas un journal complet des changements d’état. Elles ne suffisent pas à reconstruire la durée de chaque phase.

### APAD : le principal détail supplémentaire

La somme de `APAD!R2:R85` vaut **1 046 304 263 824**, contre **935 019 102 451** dans `Situation courante!AJ2:AJ1809`. L’écart APAD moins situation est de **111 285 161 373**, réparti sur **15 clés d’imputation**. Toutes les clés APAD existent dans la situation. L’APAD comporte 45 clés d’imputation à montant non nul, contre 43 lignes avec avance non nulle dans la situation.

Il faut conserver ces deux vues et expliquer leur différence. Ne pas ajouter le total APAD à la dépense payée, à l’engagé ou aux avances déjà présentes dans la situation. Le détail ne fournit pas d’état APAD, de date de paiement, de montant remboursé/récupéré ni de lien explicite vers un numéro d’engagement. Il permet de suivre les avances enregistrées par marché et projet, mais pas de calculer un encours d’avances non apurées fiable.

Les 84 lignes ont des numéros APAD qui se répètent : seulement 18 numéros distincts. Le couple `gradm + numéro APAD` est unique sur cet export. Cette observation doit être confirmée comme clé métier par le producteur, en ajoutant au minimum l’exercice et le type de budget. Le numéro de marché sert au rapprochement avec les marchés, avec son propre périmètre d’unicité à confirmer.

### Dimensions déjà présentes, à mieux exploiter

Le fichier contient cinq piliers Simandou renseignés sur 1 679 lignes, et **129 lignes sans pilier renseigné**. Ces dernières représentent **1 483 198 910 593** de crédits. Le libellé actuel « Hors pilier Simandou » mérite d’être remplacé par « Pilier non renseigné » tant que l’absence de rattachement n’est pas confirmée.

Le marquage green est renseigné sur toutes les lignes : **60 OUI**, pour **2 245 492 124 608** de crédits. C’est un marquage du producteur, pas une certification d’impact environnemental.

La fonction est « Non codifié » sur **678 lignes**, représentant **10 856 973 475 558** de crédits. La catégorie projet contient `PS2040` sur **486 lignes** et est vide sur 1 322 lignes. Le rattachement à un pilier et la catégorie `PS2040` ne doivent pas être assimilés automatiquement.

## Données manquantes à demander au système producteur

Pour un suivi complet, demander en priorité :

1. Les critères de sélection du rapport, l’exercice et la date d’arrêté explicites, l’unité des montants, le dictionnaire des états et la signification des montants par phase.
2. L’identifiant stable de la ligne budgétaire et de l’engagement, ainsi que les règles pour APAD, régies et marchés. Sur les engagements, 20 groupes numéro/section concernent 41 lignes. Ces lignes ne sont pas des doublons exacts et leurs imputations diffèrent : ne pas les supprimer sur ce seul couple.
3. Les références et dates réelles de liquidation, ordonnancement, prise en charge, paiement, annulation et régularisation. L’onglet opérations de ce fichier est vide.
4. Pour les APAD et régies : état, bénéficiaire, engagement lié, paiements, pièces justificatives, récupération et apurement.
5. Le détail des délégations : la situation indique **9 865 232 891**, alors que la feuille des délégations est vide. Une feuille vide n’établit pas l’absence de délégations.
6. La LFR si elle existe, et le journal des modifications budgétaires. Une colonne LFR vide doit rester « non renseignée » dans les comparaisons.

Les dix lignes d’engagement en devises portent EUR ou USD. Les montants en devises doivent être agrégés par monnaie et rapprochés avec les montants budgétaires selon une règle de conversion documentée. Ne pas additionner EUR, USD et GNF.

Les paiements mensuels réels et les arriérés certifiés ne sont pas calculables avec ce seul export : absence de date de paiement par opération et d’échéance exigible. Les montants regroupés par mois de création restent des cohortes d’engagements, même lorsqu’ils portent une colonne « payé ».

## Mise en œuvre ETL proposée

1. Conserver le classeur brut et son empreinte. Enregistrer système producteur, exercice, arrêté, filtres du rapport et unité. Détecter le doublon avant chargement.
2. Déclarer les six feuilles attendues avec un statut distinct : présente renseignée, présente vide ou absente. Ne pas transformer une feuille absente ou vide en preuve d’un total financier nul.
3. Ajouter des faits APAD et délégations distincts, liés au chargement et à l’imputation. Conserver les identifiants source, la ligne Excel et les colonnes non mappées. Le connecteur actuel ne reconnaît que situation, engagements, opérations et régies.
4. Préserver les codes en texte, y compris leurs zéros initiaux, les dates, les valeurs brutes et les indicateurs de montant absent. Garder le grain propre à chaque feuille. Agréger les détails avant toute jointure aux lignes budgétaires pour éviter de multiplier les crédits.
5. Exécuter les contrôles de structure, de clés et de dates, puis les rapprochements par imputation et par mesure. Archiver les écarts sans réécrire les montants source. Distinguer validation technique, rapprochement et validation métier.
6. Alimenter les indicateurs depuis un seul instantané actif par périmètre. Ne pas ajouter les instantanés successifs, ni fusionner automatiquement un fichier 2026 avec une connexion Oracle 2025. Pour un même périmètre couvert par deux canaux, fixer une priorité de source et les utiliser en contrôle croisé.
7. Ajouter les restitutions dans l’ordre : disponibilités et rapprochements, délais couverts, APAD/régies, fonctions et catégories. Les états de sources et les détails techniques restent dans Administration.

Le même contrat de données peut ensuite être alimenté par un export de fichier régulier ou par des vues en lecture seule du système producteur. La base locale de l’application reste la base centrale alimentée par l’ETL. L’étude ne suppose pas que ce système soit SYSOP : son identité et son lien avec la Chaîne Dépense raccordée doivent être confirmés avant de choisir le connecteur.

## Portée de cette livraison

Cette étude prépare les prochains lots. Elle n’ajoute aucun montant au tableau de bord et ne modifie pas les règles métier. Les rapprochements signalent des différences observées ; leur origine doit être confirmée avec le producteur avant toute correction de données ou exclusion de périmètre.
