SELECT
    a.NO_EX AS "exercice", a.CODE_PERIODE AS "periode",
    a.CD_SECTION_SOURCE AS "section_source", a.CD_TITRE_SOURCE AS "titre_source",
    a.CD_SECTION_DEST AS "section_destination", a.CD_TITRE_DEST AS "titre_destination",
    a.MONTANT AS "montant", a.OBSERVATION AS "observation", a.DT_CRE AS "date_ajustement"
FROM GDEP.TD_PLAN_ENG_AJUSTEMENT a
WHERE a.NO_EX = :exercice
