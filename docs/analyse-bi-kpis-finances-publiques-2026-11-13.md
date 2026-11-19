# Analyse BI des KPI — Synthèse, Dépenses et Portefeuille de l'État

Analyse du 13 novembre 2026, soumise à validation. Aucune modification fonctionnelle réalisée dans le cadre de cette analyse.

## Périmètre et méthode

Lecture des formules backend, des requêtes et des vues de restitution, des libellés frontend et des agrégats déjà chargés dans la base centrale. Aucun nouvel import ni appel aux bases métier pendant cette analyse. Les données analysées décrivent les extraits disponibles ; elles ne suffisent pas à certifier une exécution nationale exhaustive.

Références méthodologiques consultées :

- Ministère du Budget, [Manuel de procédures d'exécution de la dépense publique, juillet 2019](https://mbudget.gov.gn/wp-content/uploads/2022/01/Revue-_Manuel-de-procedures-depenses-1.pdf).
- FMI, [Guinée : budget programme, reporting financier et risques budgétaires, septembre 2025](https://www.imf.org/-/media/files/publications/tar/2025/french/tarfa2025103-source-pdf.pdf), notamment les paragraphes 32–39 et 66–73.
- FMI, [SOE Health Check Tool](https://www.imf.org/en/topics/fiscal-policies/fiscal-risks/fiscal-risks-toolkit/fiscal-risks-toolkit-soe-hct).
- DGPEIP, [présentation du portefeuille de l'État](https://www.dgpeip.gov.gn/portefeuille).

## Diagnostic général

Les agrégats de la situation budgétaire et leurs taux sont calculables et traçables. Les principaux risques de lecture concernent le périmètre, la couverture, les dates et la signification des ratios. La présence d'une valeur réelle ne garantit ni l'exhaustivité du phénomène économique, ni sa comparabilité avec un autre KPI.

| Ensemble | Situation constatée |
|---|---|
| Chaîne Dépense 2025 | Oracle, extraction du 13 novembre 2026, chargement 25, 13 395 lignes budgétaires et 24 958 engagements |
| Chaîne Dépense 2026 | Ancien import Excel, situation du 16 août 2026 ; ce n'est pas une extraction Oracle 2026 |
| SYSOP 2025 | Référentiel de 152 EPA et 80 sociétés ; données financières renseignées pour une partie de ce référentiel |
| Recettes, trésorerie et dette 2026 | Sources actuellement en illustration dans la base locale |

## 1. Synthèse

### S1 — Séparer les données réelles de l'illustration — priorité immédiate

Constat : la Synthèse 2026 présente recettes, trésorerie et dette issues de sources d'illustration, aux côtés des dépenses réelles. Les pastilles de source existent mais ne constituent pas une séparation suffisante pour une lecture décisionnelle rapide.

Recommandation : un mode décisionnel fondé sur les seules données réelles ; afficher « non disponible en données réelles » pour les autres domaines. Conserver l'illustration dans un mode de démonstration explicite. L'état technique des sources reste en administration.

### S2 — Unifier les périodes — priorité immédiate

Constat : la Synthèse choisit la dernière situation de chaque source pour l'exercice, sans appliquer la date de situation demandée. Les blocs peuvent donc présenter des dates différentes. Un bloc de page mixte peut aussi revenir à un autre exercice lorsque celui demandé manque.

Recommandation : appliquer la date choisie, signaler les écarts de période et ne pas substituer silencieusement un autre exercice. Séparer exercice budgétaire, date d'observation et date d'extraction. Pour 2025 extrait en novembre 2026, éviter toute présentation comme exécution courante de 2026.

### S3 — Sélectionner des KPI qui conduisent à une décision

Proposition de six cartes, à ajuster avec le cabinet :

1. Crédits engagés / crédits actuels, avec montants et périmètre.
2. Paiements enregistrés, avec taux sur crédits et couverture des paiements hors chaîne.
3. Restes à payer rapprochés, ou solde ajusté provisoire explicitement qualifié tant que le rapprochement manque.
4. Exécution financière des investissements ; aucune assimilation à un avancement physique.
5. Subventions aux EPA renseignés : prévu LFR, versé et couverture.
6. Dividendes encaissés : attendu, couverture et éventuelles échéances dépassées disponibles.

Les recettes, la trésorerie et la dette retrouveront leurs cartes dès qu'elles seront alimentées en données réelles suffisamment complètes.

### S4 — Qualifier la comparaison recettes / dépenses

Le graphique juxtapose des recettes recouvrées et des engagements. Il ne mesure pas un déficit budgétaire ni une position de trésorerie. Afficher des bases homogènes si l'objectif devient un solde ; sinon présenter explicitement deux suivis d'activité indépendants, avec leurs sources et couvertures. Un futur solde doit suivre le périmètre et les conventions du TOFE validé.

## 2. Dépenses

### D1 — Rendre les dénominateurs visibles — priorité immédiate

Sur l'extrait Oracle 2025 :

| Ratio | Formule | Valeur |
|---|---|---:|
| Engagement des crédits | Engagé / crédits actuels | 58,72 % |
| Ordonnancement des engagements | Ordonnancé / engagé | 93,48 % |
| Paiement des engagements | Payé enregistré / engagé | 21,84 % |
| Paiement sur crédits | Payé enregistré / crédits actuels | 12,82 % |
| Paiement des ordonnancements ajustés | Payé ajusté / ordonnancé ajusté | 31,62 % |

Ces taux répondent à des questions différentes. Conserver les ratios du rapport RCD1105A et les nommer précisément. Ajouter les taux sur crédits pour la lecture budgétaire, sans les substituer aux ratios déjà validés. Les paiements observés dans la Chaîne ne doivent pas être présentés comme tous les paiements nationaux avant raccordement des opérations hors chaîne.

La liquidation / crédits actuels est actuellement un ratio sur budget. Pour expliquer la chaîne, un second ratio liquidé / engagé peut être utile, sous réserve du même périmètre. Le VBP / engagé reste un indicateur de traitement ; il ne mesure pas un stock d'arriérés.

### D2 — Rapprocher le mensuel et le total engagé — priorité immédiate

Constat chiffré : le cumul mensuel est de 33 375,7 milliards GNF, contre 29 705,3 milliards GNF pour la situation LBUDG, soit 3 670,4 milliards GNF de différence. La vue mensuelle utilise les engagements bruts regroupés par date de création. Le rapprochement de la situation retient un périmètre comparable excluant E9N et la procédure 52 ; ces lignes restent conservées dans le détail.

Recommandation : distinguer série brute et série comparable ; définir le périmètre de chaque mesure ; afficher une table de passage entre les deux et imposer un contrôle somme des mois / KPI comparable. Une cohorte de dossiers par date de création n'est pas un historique des paiements mensuels. Conserver séparément les mouvements d'annulation et de régularisation ; ne pas les supprimer arbitrairement.

### D3 — Séparer restes à payer, ancienneté et arriérés — priorité immédiate

Constat : le RAP ajusté agrégé est de 14 029,6 milliards GNF. Une section présente un solde ajusté négatif d'environ 91,5 millions GNF. L'ancienneté est calculée depuis la création de l'engagement, avec un seuil de risque fixé à douze mois.

Le rapport FMI de septembre 2025 décrit le cadre guinéen de l'instruction 0683/2020 en référence aux dépenses liquidées non réglées au-delà de 90 jours et aux obligations échues non honorées. Ce point démontre que douze mois depuis la création de l'engagement ne constitue pas la même mesure. La version applicable de l'instruction et son point de départ doivent être confirmés avec le Trésor avant implémentation réglementaire.

Recommandation : conserver provisoirement un indicateur d'ancienneté des engagements ; calculer les arriérés seulement après disponibilité des dates et rapprochements requis. Présenter stock d'ouverture, nouvelles obligations, paiements/apurements et stock de clôture. Isoler les soldes négatifs comme anomalies de rapprochement ; éviter leur compensation avec les montants dus, sans écrêter automatiquement les sources.

### D4 — Clarifier les crédits non engagés et les anomalies

Le crédit disponible Oracle n'est pas fourni par la requête actuelle et il est déjà masqué dans les réponses de page. En revanche, une partie des barres appelle « Disponible » la différence crédits actuels moins engagé. Renommer cette différence « Crédits non engagés » ; elle ne démontre pas une disponibilité après réservations, blocages, régulation ou plafonds de trésorerie.

Signaux à rendre visibles sans conclure automatiquement à une irrégularité : 17 lignes engagé supérieur aux crédits actuels, six lignes liquidé supérieur à engagé, 125 lignes sans LFI renseignée, et le solde ajusté négatif. La variation par rapport à la LFI doit préciser sa couverture et distinguer dotation initiale nulle et information manquante.

### D5 — Améliorer le classement des ministères

Les seuils actuels d'engagement, de paiement et de montant sont fixes. Un seul statut prioritaire peut masquer un second problème. Recommandation : deux axes distincts, exécution et paiement ; comparer au plan d'engagement et au calendrier de décaissement plutôt qu'à un seuil uniforme. Pour 2025, proposer une lecture de bilan d'exécution, et non une alerte de rythme de l'exercice en cours. Les plans non raccordés ne doivent pas être remplacés automatiquement par une règle linéaire mensuelle.

## 3. Portefeuille de l'État

### P1 — Corriger le périmètre des transferts — priorité immédiate

La carte actuelle utilise l'ensemble du titre 4 de la Chaîne : 7 563,4 milliards GNF ordonnancés sur 11 179,0 milliards de crédits. Ce périmètre n'est pas limité aux organismes du portefeuille.

Les données SYSOP de subventions portent sur 47 EPA et totalisent 567,5 milliards GNF prévus LFR et 213,4 milliards versés. Ces deux ensembles ne doivent ni être additionnés, ni être traités comme le même périmètre.

Recommandation : remplacer la carte par les subventions aux EPA renseignés, ou expliciter immédiatement que le titre 4 est un contexte budgétaire global. À terme, rapprocher les organismes et bénéficiaires avec des identifiants stables, à exercice et période identiques.

### P2 — Afficher la couverture du taux de dividendes — priorité immédiate

Le taux est de 100 % parce qu'une seule société dispose d'une ligne : 5 milliards GNF attendus et 5 milliards encaissés. Ce calcul ne démontre pas le recouvrement de toutes les sociétés du portefeuille.

Afficher montant encaissé, attendu, nombre de sociétés renseignées et nombre de sociétés effectivement redevables. Ne pas utiliser automatiquement les 80 sociétés comme dénominateur d'obligation. Le champ source est une prévision ; le terme « voté » exige la confirmation d'une décision d'assemblée générale. Séparer exercice de bénéfice, date de décision et année d'encaissement. Les montants non encaissés ne deviennent des retards qu'après leur échéance.

### P3 — Séparer référentiel et complétude financière — priorité immédiate

Les 232 organismes sont recensés dans le référentiel chargé ; ils ne sont pas 232 dossiers financiers complets pour 2025. La requête d'inventaire n'applique pas de sélection d'activité propre à cet exercice. Aucune ligne de résultat net exploitable et aucun organisme satisfaisant le critère actuel de validation ne sont présents dans l'import.

La valeur 0 % mesure la règle actuelle de validation, pas une preuve de non-transmission de tous les documents. Distinguer : attendu, reçu, incomplet, en contrôle, rejeté, validé. Définir les documents attendus par type d'organisme avec la DGPEIP. Afficher la couverture avant toute appréciation de performance financière.

### P4 — Développer les KPI budgétaires déjà calculables

Proposition : taux de versement des subventions = versé / prévision LFR renseignée, soit 37,61 % pour le périmètre importé. Compléter par montant prévu non versé, concentration des subventions et classement par écart en montant. Sept lignes ont une prévision nulle ; leur taux individuel doit rester non calculable. Le montant prévu non versé n'est pas à lui seul une dette exigible de l'État.

### P5 — Adapter la santé financière au statut des organismes

Pour les sociétés : résultat net, liquidité, capitaux propres, endettement, capacité à servir la dette, dividendes et dépendance aux soutiens publics. Pour les EPA : couverture des charges, ressources propres, dépendance aux subventions, réalisation des missions et résultats de service public. Un déficit d'EPA ne suffit pas à conclure à une mauvaise performance.

La démarche est cohérente avec le SOE Health Check du FMI, qui combine informations de résultat et de bilan et s'intéresse à l'exposition budgétaire de l'État. Aucun score global de santé financière n'est justifiable avec le seul signe d'un résultat net, a fortiori absent.

À raccorder avant calcul : bilans et comptes de résultat validés, échéanciers, garanties, emprunts rétrocédés, recapitalisations, participations de l'État et données de gouvernance. Les banques nécessitent une grille adaptée à leur activité. Un indicateur de contribution budgétaire nette doit avoir un périmètre explicite et ne pas compenser silencieusement dépenses, dividendes et risques contingents.

## Validation proposée

### Lot 1 — Cohérence et lisibilité avec les données présentes

- Modes réel/illustration, périodes et provenance par KPI.
- Dénominateurs explicites ; crédit disponible distinct des crédits non engagés.
- RAP provisoire distinct d'arriérés ; anomalies visibles.
- Transferts du portefeuille, couverture des dividendes et des états financiers.
- Mise en cohérence de la série mensuelle et du KPI, après validation de la table de passage.

### Lot 2 — Compléments calculables après validation métier

- Taux complémentaires sur crédits et par étape.
- Versement des subventions et concentration, avec couverture.
- Classement des ministères sur plusieurs axes ; écart au plan lorsque ce dernier existe.
- Fiche de chaque KPI : objectif, formule, unité, périmètre, exercice, date d'observation, date d'extraction, source, couverture, exclusions et responsable.

### Lot 3 — Données nouvelles

- Paiements hors chaîne et rapprochement Trésor pour une vision complète de trésorerie.
- Dates de liquidation et échéances nécessaires aux délais et arriérés.
- Plans d'engagement et de trésorerie, budgets et documents financiers des organismes.
- Garanties, dette rétrocédée, gouvernance et résultats de service public.

Décisions métier à obtenir : DGB pour crédits, ratios et plans ; Trésor pour paiements, dates et arriérés ; DGPEIP pour périmètre des organismes, obligations de dividendes et statuts de validation. Les seuils ne deviennent pas réglementaires du seul fait de leur présence dans le logiciel.

## Principaux points de code examinés

- `backend/apps/core/synthese.py` : sélection des périodes, agrégation et composition des KPI.
- `backend/apps/depense/services.py`, `backend/apps/core/regles.py` : taux, paiements ajustés, ancienneté et statuts.
- `backend/apps/depense/migrations/0002_vues_mart.py` : périmètres des vues mensuelles et du RAP.
- `backend/apps/portefeuille/services.py`, `backend/etl/connecteurs/sysop.py` : couverture, transferts, dividendes et validation.
- `frontend/src/pages/Synthese.tsx`, `frontend/src/pages/Depenses.tsx`, `frontend/src/pages/domaines/Portefeuille.tsx` : libellés et interprétation visuelle.

Les agrégats de diagnostic local sont conservés dans `tmp/audit-kpis-finances.json`. Ils ne constituent pas une certification des comptes de l'État.
