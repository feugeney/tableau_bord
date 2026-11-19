# Raccordement Oracle de la Chaîne Dépense

## Intégration dans les flux ETL — 13 novembre 2026

La source locale a été rebranchée sur Oracle avec les requêtes et correspondances existantes. Le profil est accessible dans **Administration → Flux ETL → Oracle · Chaîne Dépense**. Les requêtes et champs utilisés sont consultables dans sa fiche. Le test de connexion de l'interface utilise désormais le même client Thick et la même transaction en lecture seule que le connecteur.

L'aperçu 2025 puis le chargement n° 23 ont réussi : 13 395 lignes LBUDG et 24 958 engagements, sans rejet. Le rapprochement par clé budgétaire ne présente aucun écart d'engagement. Six lignes restent signalées par l'avertissement liquidé supérieur à engagé. Les restrictions horaires restent actives pour les lancements ordinaires et planifiés ; l'exception manuelle ponctuelle est distincte et journalisée.

Le [guide de l'administration ETL](administration-base-centrale-etl.md) décrit ce parcours. Les constats ci-dessous restent l'historique de préparation du raccordement.

## État vérifié le 12 novembre 2026

- Connexion au service configuré dans `backend/.env` réussie : Oracle 11.2.0.1.0.
- Python 64 bits, python-oracledb en mode Thick, Instant Client 19 installé localement.
- Diagnostic limité à `SET TRANSACTION READ ONLY` puis `SELECT 1 FROM DUAL`.
- Les métadonnées de LBUDG et ENGAGEMENT ont été consultées ; aucune extraction métier ni import effectué.
- Exercice retenu pour le premier test : **2025**.
- Schéma de travail : **GDEP**, correspondant au compte configuré. Des tables homonymes existent aussi dans GB et GBPROG ; utiliser des noms qualifiés.
- `MT_CRED` est le crédit actuel, `MT_LFI` le crédit initial et `MT_LFR` le montant total après LFR (confirmations utilisateur).

## Correspondances préparatoires

| Source | Colonne Oracle | Champ du tableau de bord |
|---|---|---|
| Les deux tables | NO_EX | exercice |
| Les deux tables | CD_SECTION, CD_SS_SECTION | section, sous_section |
| Les deux tables | CD_TITRE, CD_CHAP, CD_ART | titre, chapitre, article |
| Les deux tables | CD_PARAGRAPHE, CD_SS_PARAGRAPHE | paragraphe, sous_paragraphe |
| Les deux tables | CD_SOURCE_FIN, CD_GROUPE_BAIL, CD_BAILLEUR | source_financement, groupe_bailleur, bailleur |
| Les deux tables | CD_TYPE_BUDGET | type_budget |
| LBUDG | MT_CRED, MT_LFI, MT_LFR | credit_actuel, credit_initial_lfi, credit_lfr |
| LBUDG | MT_ENG, MT_RESRV, MT_ENG_CF | credit_engage, credit_reserve, credit_engage_cf |
| Les deux tables | MT_LIQ, MT_ORD, MT_VBP, MT_PAYE | montant_liquide, montant_ordonnance, montant_vbp, montant_paye |
| LBUDG | MT_ECP | montant_encours_paiement |
| ENGAGEMENT | MT_ECP | montant_ecp |
| LBUDG | MT_BLOQUE, MT_DELEGATION, MT_REGIE | montant_bloque, montant_delegation, montant_regie |
| ENGAGEMENT | NO_ENG | numero |
| ENGAGEMENT | MT_INIT_ENG, MT_ENG, MT_ENG_CF, MT_RETENU | montant_initial, montant_engage, montant_engage_cf, montant_retenu |
| ENGAGEMENT | MT_DEVISE, CD_DEVISE | montant_devise, devise |
| ENGAGEMENT | DT_CRE, DT_VISA_CF, DT_VISA_MINISTRE, DT_ETAT, DT_MAJ | dates correspondantes |

## Corrections nécessaires avant activation

### Référentiels vérifiés

Les colonnes et clés ci-dessous ont été vérifiées dans les métadonnées Oracle. La requête préparatoire est conservée dans `docs/oracle/engagement_referentiels.sql` et n'est pas activée pour l'import.

| Référentiel | Jointure depuis ENGAGEMENT | Libellé |
|---|---|---|
| GDEP.TC_SECTION | NO_EX + CD_SECTION = NO_EX + CODE_SECTION | LIBELLE_LONG_SECTION |
| GDEP.BENEFICIAIRE | TY_BENEF + NO_BENEF | LB_RAISON ; à défaut LB_NOM et LB_PN |
| GDEP.ETAT_DOSS | ET_DOSS | LB_ETDOSS (état du dossier) |
| GDEP.TYPE_ENG | TY_ENG | LB_L_TYENG (procédure/type d'engagement) |

TC_SECTION peut également enrichir LBUDG sur l'exercice et le code section. Les jointures préparées sont des jointures externes : une absence de référentiel ne doit pas supprimer silencieusement un engagement. Les codes bruts sont conservés dans les colonnes de sortie pour diagnostic. Le choix du nom affiché du bénéficiaire reste à valider sur un aperçu ; aucune coordonnée bancaire ni de contact n'est sélectionnée.

La clé primaire complète de chaque référentiel est utilisée, ce qui évite de multiplier les lignes. Les libellés réellement employés pour les états et procédures doivent encore être rapprochés des règles du tableau de bord avant le chargement.

### Modèle et règles

1. **Préserver les clés source** : ENGAGEMENT a pour clé `(NO_EX, CD_GRPADM, NO_ENG)`. Le modèle actuel ne conserve pas CD_GRPADM. LBUDG a une clé de 14 colonnes : NO_EX, CD_SECTION, CD_PROGRAMME, CD_SS_SECTION, CD_NATURE_FLUX, CD_TITRE, CD_CHAP, CD_ART, CD_PARAGRAPHE, CD_SS_PARAGRAPHE, CD_SOURCE_FIN, CD_GROUPE_BAIL, CD_BAILLEUR, CD_TYPE_BUDGET. Le hash actuel des lignes Excel ne correspond pas à cette clé Oracle.
2. **Traduire les référentiels** : TY_ENG et ET_DOSS sont des codes. Le calcul des dépenses valides et les exclusions hors chaîne attendent des libellés. Ne pas charger ces codes comme s'il s'agissait de libellés.
3. **Compléter les libellés** : sections, sous-sections, natures et bénéficiaires nécessitent leurs référentiels. NO_BENEF seul ne constitue pas un nom de bénéficiaire.
4. **Confirmer le disponible** : aucune colonne directement nommée crédit disponible n'a été relevée. La formule doit être validée avant de produire cet indicateur ; ne pas remplacer arbitrairement la valeur par zéro.
5. **Filtrer explicitement** les deux extractions par `NO_EX = :exercice`. Une lecture de montants actuels pour 2025 constitue une situation de cet exercice à la date d'extraction, pas une reconstruction historique au 31 décembre 2025.
6. **Comparer les totaux** sans joindre les deux tables ligne à ligne : cette jointure multiplierait les crédits par le nombre d'engagements. Vérifier le périmètre des états/procédures avant d'exiger la concordance.

## Diagnostic reproductible

Depuis le dossier backend :

```powershell
.venv/Scripts/python.exe manage.py diagnostiquer_oracle
```

Les paramètres et le mot de passe restent dans `.env`, ignoré par Git. Le client Windows est dans `captures/local-runtime/oracle`, également ignoré. Pour Docker, installer un client Oracle 19 Linux dans l'image backend ; le chemin du client Windows ne peut pas être réutilisé.

Le diagnostic n'active ni la source automatique ni une planification. Les extractions de production restent interdites en semaine de 7 h 30 à 18 h 30 par le connecteur existant.
