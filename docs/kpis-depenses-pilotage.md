# KPI complémentaires de la page Dépenses

Les indicateurs respectent l’exercice, la date de situation, le ministère et la nature de dépense sélectionnés. Ils utilisent uniquement le dernier chargement réussi de ce périmètre. Le mode de calcul des soldes ajustés ne modifie pas les montants bruts des nouvelles analyses.

## Disponibilité

- Crédits réservés et crédits bloqués : montants déclarés par la source.
- Crédits non engagés : crédits actuels moins engagé.
- Part réservée ou bloquée : (réservé + bloqué) / crédits actuels. Un dénominateur nul rend le ratio indisponible.
- Solde calculé : crédits actuels moins engagé, réservé et bloqué. Ce calcul est présenté séparément du disponible déclaré, avec leur écart lorsqu’ils sont tous les deux renseignés.

Un champ absent ou une mesure partiellement renseignée ne devient pas un zéro confirmé. Les nouveaux imports enregistrent les colonnes reçues et les montants absents par ligne. Pour les anciens imports sans manifeste, seuls les champs obligatoires ou attestés par une valeur non nulle sont exploités. Le disponible Oracle reste indisponible lorsqu’il n’a pas été extrait.

## Délais

Deux étapes : création vers visa CF, puis visa CF vers visa ministre. Les délais sont exprimés en jours calendaires. La médiane et le 90e percentile portent sur les paires complètes dont les dates sont cohérentes et ne dépassent pas la situation sélectionnée. Le percentile suit le rang supérieur : rang `ceil(0,9 × nombre de paires)`.

La couverture correspond au nombre de paires valides divisé par le nombre de lignes d’engagement reçues dans le périmètre. Les dates manquantes, délais négatifs et dates futures sont comptés séparément. Une absence de date n’est pas qualifiée de blocage. Des visas enregistrés le même jour ne prouvent pas une absence de temps de traitement entre deux services.

## APAD et régies

La table `dw.fait_apad` conserve l’imputation, le gestionnaire, les numéros APAD et marché, le libellé du projet, le montant, sa présence, la date de création et le numéro de ligne source. Les APAD ne sont jamais additionnées aux engagements, aux ordonnancements ou aux paiements.

La page présente le total APAD, sa comparaison avec la colonne « Avance de démarrage » de la situation, une ventilation par ministère et le détail par projet et marché. Les numéros APAD ou marché ne sont pas supposés uniques indépendamment du gestionnaire et de l’exercice. Les régies sont présentées comme des enregistrements, sans certifier leur paiement ou leur justification.

Un détail non extrait, absent ou vide reste indisponible. Une ligne reçue avec un montant explicitement nul permet, elle, d’afficher un zéro. Le suivi de l’encours non apuré demande des états, paiements, récupérations et justifications supplémentaires.

## Rapprochements

La situation et les engagements sont agrégés séparément avant comparaison, afin de ne pas multiplier les crédits par le nombre de dossiers. Le contrôle porte sur les codes d’imputation communs, le programme et la nature de flux lorsqu’ils sont disponibles. La régulation non fournie par la liste des engagements ne peut pas faire partie d’une clé commune. Le contrôle complet réalisé à l’import Oracle est conservé.

Le tableau présente les montants de référence et du détail, leur écart, le nombre de clés en écart et, dans les exports, la somme des écarts absolus. Des écarts qui se compensent ne donnent donc pas un statut concordant. Les exclusions Oracle E9N/procédure 52 s’appliquent uniquement à l’engagé et seulement lorsqu’elles ont été validées à l’import. Les autres phases comparent le détail brut reçu.

## Imports et exports

Les imports Excel reconnaissent désormais APAD, en plus de la situation, des engagements, des opérations et des régies. Les exports Dépenses PDF et Excel, ainsi que le rapport complet PDF, reprennent les nouveaux blocs.

Pour compléter un ancien chargement Excel sans réimporter ses dépenses :

```powershell
backend\.venv\Scripts\python.exe backend\manage.py completer_details_depense --chargement IDENTIFIANT --apercu
backend\.venv\Scripts\python.exe backend\manage.py completer_details_depense --chargement IDENTIFIANT
```

La commande utilise le fichier brut archivé. `--fichier CHEMIN` permet de fournir la même pièce si nécessaire. L’empreinte SHA-256, les effectifs et les clés doivent correspondre à l’import historique. Le complément est transactionnel, journalisé et ne recharge pas les dépenses. Une seconde exécution ne duplique pas les APAD. Les clés ambiguës ou un contenu différent font échouer le complément.
