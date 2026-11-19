SELECT
    t.NO_EX AS "exercice", t.CODE_PERIODE AS "periode", t.CD_SECTION AS "section",
    COALESCE(TRIM(s.LIBELLE_LONG_SECTION), TRIM(s.LIBELLE_COURT_SECTION)) AS "libelle_section",
    t.CD_TITRE AS "titre",
    t.MONTANT_CREDIT AS "credit", t.MONTANT_ENGAGEMENT AS "engage_ouverture",
    t.MONTANT_REPARTISSABLE AS "plafond",
    t.MONTANT_PROPOSE AS "montant_propose", t.MONTANT_ARBITRAGE AS "montant_arbitrage"
FROM GDEP.TD_PLAN_ENG t
LEFT JOIN GDEP.TC_SECTION s ON s.NO_EX = t.NO_EX AND s.CODE_SECTION = t.CD_SECTION
WHERE t.NO_EX = :exercice
