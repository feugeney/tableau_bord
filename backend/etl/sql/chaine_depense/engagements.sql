-- Correspondances utilisées par le profil Oracle de la Chaîne Dépense.
-- Bind obligatoire : exercice (2025 pour le premier test).
-- Chaque référentiel est joint sur sa clé primaire complète.
SELECT
    e.NO_EX AS "exercice",
    e.CD_GRPADM AS "groupe_administratif",
    e.NO_ENG AS "numero",
    e.CD_SECTION AS "section",
    s.LIBELLE_LONG_SECTION AS "libelle_section",
    s.LIBELLE_COURT_SECTION AS "libelle_court_section",
    COALESCE(TRIM(sv.LIBELLE_LONG_SERVICE), TRIM(ss.LIBELLE_LONG_SOUS_SECTION)) AS "libelle_sous_section",
    e.CD_SS_SECTION AS "sous_section",
    e.CD_PROGRAMME AS "programme",
    e.CD_NATURE_FLUX AS "nature_flux",
    e.CD_TYPE_BUDGET AS "type_budget",
    e.CD_TITRE AS "titre",
    e.CD_CHAP AS "chapitre",
    e.CD_ART AS "article",
    e.CD_PARAGRAPHE AS "paragraphe",
    e.CD_SS_PARAGRAPHE AS "sous_paragraphe",
    e.CD_SOURCE_FIN AS "source_financement",
    e.CD_GROUPE_BAIL AS "groupe_bailleur",
    e.CD_BAILLEUR AS "bailleur",
    e.TY_ENG AS "code_type_procedure",
    t.LB_L_TYENG AS "type_procedure",
    e.ET_DOSS AS "code_etat_dossier",
    d.LB_ETDOSS AS "etat_dossier",
    e.TY_BENEF AS "type_beneficiaire",
    e.NO_BENEF AS "numero_beneficiaire",
    COALESCE(TRIM(b.LB_RAISON), TRIM(b.LB_NOM || ' ' || b.LB_PN)) AS "beneficiaire",
    e.LB_OBJ AS "objet",
    e.MT_INIT_ENG AS "montant_initial",
    e.MT_ENG AS "montant_engage",
    e.MT_ENG_CF AS "montant_engage_cf",
    e.MT_RETENU AS "montant_retenu",
    e.MT_LIQ AS "montant_liquide",
    e.MT_ORD AS "montant_ordonnance",
    e.MT_VBP AS "montant_vbp",
    e.MT_ECP AS "montant_ecp",
    e.MT_PAYE AS "montant_paye",
    e.MT_DEVISE AS "montant_devise",
    e.CD_DEVISE AS "devise",
    e.DT_CRE AS "date_creation",
    e.DT_VISA_CF AS "date_visa_cf",
    e.DT_VISA_MINISTRE AS "date_visa_ministre",
    e.DT_ETAT AS "date_etat",
    e.DT_MAJ AS "date_maj"
FROM GDEP.ENGAGEMENT e
LEFT JOIN GDEP.TC_SECTION s
    ON s.NO_EX = e.NO_EX AND s.CODE_SECTION = e.CD_SECTION
LEFT JOIN GDEP.TC_SOUS_SECTION ss
    ON ss.NO_EX=e.NO_EX AND ss.CODE_SECTION=e.CD_SECTION AND ss.CODE_SOUS_SECTION=e.CD_SS_SECTION
LEFT JOIN GDEP.TC_SERVICE sv ON sv.CODE_SERVICE=ss.CODE_SERVICE
LEFT JOIN GDEP.BENEFICIAIRE b
    ON b.TY_BENEF = e.TY_BENEF AND b.NO_BENEF = e.NO_BENEF
LEFT JOIN GDEP.ETAT_DOSS d
    ON d.ET_DOSS = e.ET_DOSS
LEFT JOIN GDEP.TYPE_ENG t
    ON t.TY_ENG = e.TY_ENG
WHERE e.NO_EX = :exercice
