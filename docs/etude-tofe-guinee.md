# TOFE — cadrage guinéen et scénario d'illustration

Étude fonctionnelle du 13 novembre 2026. Le module ajouté au dashboard reprend une structure de TOFE adaptée au contexte guinéen. **Tous les montants affichés dans cet onglet sont inventés**, y compris les budgets, réalisations, comparaisons N−1 et le PIB. Les références ci-dessous établissent le cadre de présentation ; elles ne servent pas de source aux montants de démonstration.

## 1. Objet, périmètre et cadre budgétaire

Le TOFE permet de lire ensemble les ressources de l'État, ses dépenses, les soldes et leur financement. Il complète une page d'exécution des dépenses : un montant engagé ou ordonnancé ne représente pas à lui seul une sortie de trésorerie. Les publications du Ministère du Budget identifient expressément ce tableau dans les documents financiers. [Ministère du Budget — TOFE](https://mbudget.gov.gn/tableau-des-operations-financieres-de-letat/).

La DGB distingue la LFI, qui autorise le budget initial, la LFR, qui le modifie en cours d'année, et la loi de règlement, qui constate le résultat final. Le module sépare donc les enveloppes annuelles initiale/révisée du réalisé cumulé ; la prévision cumulée de démonstration ne constitue pas une autorisation légale de dépense. [DGB — lois de finances](https://dgb.gov.gn/lois/lois-de-finances/).

Le décret D/2013/015/PRG/SGG définit les règles d'exécution, de comptabilité et de contrôle des budgets publics et cite la loi organique L/2012/012/CNT. Il concerne l'État et ses établissements publics administratifs. Le périmètre choisi pour la démonstration est plus limité : l'administration centrale budgétaire, sans consolidation automatique des EPA, collectivités ou sociétés publiques. [DGB — Règlement général de gestion budgétaire et de comptabilité publique](https://dgb.gov.gn/wp-content/uploads/2024/12/1-DECRET-D-2013-015-PRG-SGG-PORTANT-REGLEMENT-GENERAL-DE-GESTION-BUDGETAIRE-ET-DE-COMPTABILITE-PUBLIQUE.pdf).

L'arrêté portant nomenclature budgétaire prévoit différentes classifications des opérations, dont la classification économique et la présentation par programme. Le TOFE proposé suit une lecture économique ; il ne remplace pas les ventilations administratives ou par programme. [DGB — nomenclature budgétaire](https://dgb.gov.gn/wp-content/uploads/2024/12/ARRETE-A-2014-5262-MEF-SGG-PORTANT-NOMENCLATURE-BUDGETAIRE-DE-LETAT.pdf).

En 2026, la DGI annonce l'adoption de la LFI et le passage au mode programme. Cette évolution justifie de prévoir ultérieurement un rapprochement avec les programmes, sans confondre leurs autorisations avec les flux statistiques du TOFE. Les chiffres annoncés ne sont pas repris dans le scénario. [DGI — adoption de la LFI 2026, 31 mars 2026](https://dgi.gov.gn/2026/03/31/adoption-de-la-loi-de-finance-initiales-lfi-2026/).

## 2. Lecture économique retenue

Les publications de conjoncture de la DNPEC analysent les recettes, les charges et les transactions sur actifs non financiers, avec des comparaisons infra-annuelles. Le module distingue ces ensembles et présente une série de flux mensuels, séparée des cumuls. [DNPEC — Tableau de bord de l'économie, février 2025, section finances publiques](https://www.mef.gov.gn/wp-content/uploads/2025/05/Tableau-de-Bord-Economie-fevrier-2025-.pdf).

La présentation du FMI pour la Guinée distingue notamment les ressources minières/non minières, les dons, les charges de personnel, biens et services, transferts et intérêts, ainsi que le financement domestique et extérieur. La maquette retient ces distinctions utiles, sans prétendre reproduire toutes les rubriques ou la base statistique d'une publication officielle. [FMI — rapport pays 24/130, tableau 3a, page imprimée 34](https://www.imf.org/-/media/files/publications/cr/2024/english/1ginea2024001.pdf).

Le rapport de politique monétaire de la BCRG traite séparément recettes, dépenses, soldes et financement. Cette articulation motive le tableau de passage du solde au financement net. Il faut conserver la distinction entre la dette de l'État et les propres comptes de la banque centrale ; le budget de fonctionnement de la BCRG n'est pas celui de l'État. [BCRG — troisième trimestre 2025, sections 1.2.2.1 à 1.2.2.3](https://www.bcrg-guinee.org/wp-content/uploads/2026/03/Rapport-CPM-du-2025T3.pdf).

## 3. Tableau et conventions de calcul

| Ensemble | Rubriques du scénario |
|---|---|
| Recettes et dons | Fiscalité minière, fiscalité non minière, recettes non fiscales, dons-projets et dons budgétaires |
| Charges | Personnel, biens et services, subventions/transferts, intérêts intérieurs et extérieurs |
| Actifs non financiers | Acquisition nette, distinguée selon financement intérieur ou extérieur |
| Soldes | Gestion, global dons compris, primaire et caisse simplifiée |
| Financement intérieur | Position nette BCRG, banques commerciales, financement non bancaire |
| Financement extérieur | Tirages sur prêts-projets et prêts-programmes, moins amortissement du principal |
| Ajustement de caisse | Variation des arriérés ; autres ajustements supposés nuls dans ce scénario |

Conventions de la maquette, exposées dans l'interface :

- Solde net de gestion = recettes et dons − charges.
- Dépenses totales = charges + acquisition nette d'actifs non financiers.
- Solde global = recettes et dons − dépenses totales.
- Solde primaire = solde global + intérêts. Il ne s'agit pas du « solde budgétaire de base », dont le périmètre demanderait une définition distincte.
- Variation des arriérés positive = accumulation ; négative = apurement.
- Solde caisse simplifié = solde global + variation des arriérés.
- Besoin de financement = opposé du solde caisse ; une valeur négative représente une capacité.
- Financement extérieur net = tirages − amortissement ; les intérêts restent dans les charges.
- Besoin résiduel = besoin de financement − financement intérieur net − financement extérieur net.

Les acquisitions nettes d'actifs financiers et les autres ajustements sont supposés nuls dans cette illustration. Avant un raccordement réel, il faudra préciser leur traitement, les dates de comptabilisation et les règles de consolidation. Le cadre statistique du FMI fournit des concepts à rapprocher des pratiques nationales, et non une preuve de conformité automatique de la maquette. [FMI — manuels et cadres de statistiques de finances publiques](https://www.imf.org/en/data/statistics/government-finance-statistics-manual/gfs).

## 4. Hypothèses entièrement fictives

Scénario de référence 2026, en milliards GNF :

| Indicateur annuel | LFI simulée | LFR simulée | Exécution annuelle de scénario |
|---|---:|---:|---:|
| Recettes et dons | 43 500 | 46 400 | 43 600 |
| Charges | 28 800 | 30 000 | 28 450 |
| Actifs non financiers | 21 000 | 23 000 | 20 900 |
| Dépenses totales | 49 800 | 53 000 | 49 350 |
| Solde global | −6 300 | −6 600 | −5 750 |
| Variation des arriérés | −400 | −500 | −350 |
| Besoin de financement | 6 700 | 7 100 | 6 100 |
| Financement net | 6 700 | 7 100 | 6 100 |

Le PIB annuel fictif est de 360 000 milliards GNF. Ces valeurs ne sont ni des estimations ni des prévisions pour la Guinée.

Le profil mensuel commun est : 6 %, 6 %, 7 %, 7 %, 8 %, 8 %, 9 %, 9 %, 9 %, 9 %, 10 %, 12 %. Il sert uniquement à montrer les mécanismes ; aucune saisonnalité économique observée n'est affirmée. Le mois courant est proratisé aux jours écoulés. Le comparateur N−1 vaut 90 % de l'exécution de scénario sur une période équivalente. Une échelle pédagogique de 8 % par année permet de générer d'autres exercices, sans valeur de prévision macroéconomique.

Les taux d'exécution utilisent le prévu cumulé, pas le budget annuel ; les soldes et financements nets n'ont pas de taux d'exécution. Le ratio solde/PIB rapporte le cumul à un PIB annuel fictif : il n'est pas annualisé.

## 5. Traçabilité et futur raccordement

Une source dédiée `tofe`, de statut `demo`, contient un scénario versionné dans le journal des chargements. Sa génération est indépendante de SYSOP, d'Oracle et des autres sources ; recharger cette illustration ne modifie pas leurs données. La version courante ne constitue pas un nouveau connecteur TOFE réel.

Pour préparer les échanges réels, le rapprochement fonctionnel suivant reste à valider avec les producteurs :

| Données | Producteurs/flux à rapprocher | Risque à traiter |
|---|---|---|
| Autorisations LFI/LFR | Budget et référentiels officiels | Versions, périmètres et dates d'effet |
| Recettes | Régies fiscales/douanières et Trésor | Éviter de compter deux fois les mêmes encaissements |
| Charges et investissements | Chaîne Dépense et comptabilité du Trésor | Engagement, ordonnancement et paiement ne sont pas interchangeables |
| Financement | Dette, Trésor et données de position bancaire | Distinguer flux, stocks, intérêts et principal |
| Dons et projets | Flux des partenaires rapprochés de la comptabilité | Identifier le financement extérieur hors chaîne |
| Arriérés et ajustements | Situations de trésorerie validées | Ne pas assimiler tout reste à payer à un arriéré |
| PIB | Millésime macroéconomique officiel validé | Identifier la révision et conserver le même dénominateur |

Le portefeuille SYSOP ne doit pas être ajouté globalement aux dépenses du TOFE : les subventions ou dividendes peuvent déjà être enregistrés dans d'autres flux. La consolidation demande une table de correspondance et des éliminations vérifiables.

## 6. Validation et utilisation

Le module contrôle l'équilibre recettes/dépenses/solde, le passage à la caisse, le financement et la concordance du cumul avec les mois. Les tests couvrent aussi les droits d'accès, l'absence de données pour une période non chargée et les unités de l'export Excel. Un équilibre fictif démontre le fonctionnement du tableau, pas la qualité d'une donnée nationale.

Chargement explicite, depuis `backend` :

```powershell
.\.venv\Scripts\python.exe manage.py seed_demo --sources tofe --exercice 2026 --date-situation 2026-11-13
```

La page est accessible sous `/tofe`, uniquement aux comptes autorisés sur le domaine `tofe` ou disposant d'un accès global. Les références et conventions sont également accessibles dans la page et dans l'export Excel.
