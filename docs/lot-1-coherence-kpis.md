# Lot 1 — Cohérence des KPI

Corrections de lecture et de périmètre des pages Synthèse, Dépenses et Portefeuille. Les montants importés dans la base centrale sont conservés.

## Synthèse

- Mode « Données réelles » par défaut : les valeurs, taux et références d'illustration ne sont pas transmis. Le mode « Démonstration » est explicite et conservé dans les exports.
- Une date ou un exercice absent ne déclenche plus de substitution silencieuse. Les blocs restent sans données pour la période demandée.
- Le total recettes fiscales/douanières requiert les deux sources autorisées, le même exercice et la même date ; les permissions couvrent les deux domaines.
- Les cohortes d'engagements et les encaissements sont présentés dans des graphiques séparés, sans calcul implicite d'un solde budgétaire.
- Les alertes de synthèse sont limitées à l'exercice demandé et, en mode décisionnel, aux sources réelles.

## Dépenses

- Les ratios portent leur dénominateur : ordonnancé/engagé et payé enregistré/engagé. Le RCD1105A conserve ses formules.
- « Crédits non engagés » remplace « Disponible » lorsque le calcul est crédits actuels moins engagé.
- Les soldes ajustés sont explicitement à rapprocher avec le Trésor ; l'ancienneté depuis la création de l'engagement ne certifie ni l'exigibilité ni un stock d'arriérés.
- Les LFI absentes, engagements supérieurs aux crédits, liquidations supérieures aux engagements et soldes ajustés négatifs sont signalés sans correction automatique des sources.
- La série mensuelle reprend le périmètre comparable Oracle uniquement si le chargement contient le rapprochement exact par clé issu de la validation. Aucun filtre général n'est appliqué aux autres extractions. Les données brutes restent disponibles et l'écart de périmètre est exposé.
- Les projections sont suspendues lorsque la série mensuelle n'est pas rapprochée avec la situation budgétaire.

Résultat sur les données Oracle 2025 déjà chargées : brut **33 375,7 Mds GNF**, comparable et KPI **29 705,3 Mds GNF**, écart de périmètre **3 670,4 Mds GNF**, écart résiduel nul. Pour l'ancien Excel 2026, l'écart résiduel de 0,8 Md GNF reste signalé ; les montants ne sont pas forcés à concordance.

## Portefeuille

- Les subventions versées aux EPA renseignés remplacent le titre 4 global dans les cartes principales.
- Le titre 4 est conservé dans un contexte budgétaire séparé, explicitement plus large que le portefeuille et non additionnable aux montants SYSOP.
- Le taux de dividendes précise qu'il porte sur les montants attendus renseignés et donne le nombre de sociétés concernées. Aucune obligation de versement ni échéance n'est inventée.
- La validation des états SYSOP est distinguée de la réception et de la complétude des documents. L'absence de résultat exploitable ne donne pas lieu à un diagnostic financier ni à un affichage rassurant de zéros « déficitaires ».
- Les barres de subventions et dividendes ne qualifient plus de retard en l'absence d'échéances.

Couverture de l'import SYSOP 2025 : **47 EPA** avec ligne de subvention sur 152 recensés ; **une société** avec dividende renseigné ; aucun résultat exploitable selon le raccordement actuel. Le référentiel comporte 232 organismes, ce qui ne représente pas 232 dossiers financiers complets.

## Périodes et exports

Les pastilles distinguent exercice, situation et origine (Oracle ou fichier importé), avec la date d'extraction dans le détail de source. Une période indisponible est affichée explicitement dans le sélecteur. Pendant un changement de filtres, les valeurs de l'ancienne période ne restent pas présentées sous le nouvel en-tête.

Excel et PDF reprennent les nouveaux intitulés, le mode de la Synthèse et les éléments de rapprochement. Le rapport complet décisionnel remplace les blocs d'illustration par une disponibilité explicite ; les exports individuels de démonstration restent accessibles.

## Vérification

Tests backend de périodes, permissions, absence de montants fictifs, cohérence mensuelle, absence de filtre non validé, exports et projection suspendue. Tests frontend du choix explicite de démonstration, de sa propagation au PDF et des barres sans retard déduit. Vérification sur Chrome des trois pages et du portefeuille sur mobile, sans réimport d'Oracle ou SYSOP.

Les ratios supplémentaires, le classement des ministères par plusieurs axes et les données nouvelles des lots 2 et 3 ne font pas partie de ce lot.
