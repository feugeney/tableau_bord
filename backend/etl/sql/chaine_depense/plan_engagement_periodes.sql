SELECT
    p.NO_EX AS "exercice", p.CODE_PERIODE AS "periode",
    p.ET_DOSS AS "etat_code", d.LB_ETDOSS AS "etat_libelle",
    p.MONTANT_MOBILISABLE AS "montant_mobilisable", p.MONTANT_IMPREVU AS "montant_imprevu",
    p.MONTANT_OBLIG_TITRE2 AS "montant_obligatoire_titre2",
    p.MONTANT_REPARTISSABLE AS "montant_repartissable",
    p.REFERENCE_ARRETE AS "reference_arrete", p.DATE_VALIDATION AS "date_validation",
    p.DATE_OUVERTURE AS "date_ouverture",
    p.FLAG_PERIODE_COURANTE AS "periode_courante", p.FLAG_PERIODE_EXECUTION AS "periode_execution"
FROM GDEP.TD_PLAN_ENG_PARAMETRE p
LEFT JOIN GDEP.ETAT_DOSS d ON d.ET_DOSS = p.ET_DOSS
WHERE p.NO_EX = :exercice
