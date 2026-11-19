SELECT
    l.NO_EX AS "exercice", l.CD_SECTION AS "section",
    s.LIBELLE_LONG_SECTION AS "libelle_section",
    s.LIBELLE_COURT_SECTION AS "libelle_court_section",
    COALESCE(TRIM(sv.LIBELLE_LONG_SERVICE), TRIM(ss.LIBELLE_LONG_SOUS_SECTION)) AS "libelle_sous_section",
    l.CD_PROGRAMME AS "programme", l.CD_SS_SECTION AS "sous_section",
    l.CD_NATURE_FLUX AS "nature_flux", l.CD_TYPE_BUDGET AS "type_budget",
    l.CD_TITRE AS "titre", l.CD_CHAP AS "chapitre", l.CD_ART AS "article",
    l.CD_PARAGRAPHE AS "paragraphe", l.CD_SS_PARAGRAPHE AS "sous_paragraphe",
    l.CD_SOURCE_FIN AS "source_financement", l.CD_GROUPE_BAIL AS "groupe_bailleur",
    l.CD_BAILLEUR AS "bailleur", l.CD_REGUL AS "regulation",
    l.MT_LFI AS "credit_initial_lfi", l.MT_LFR AS "credit_lfr",
    l.MT_CRED AS "credit_actuel", l.MT_RESRV AS "credit_reserve",
    l.MT_ENG AS "credit_engage", l.MT_ENG_CF AS "credit_engage_cf",
    l.MT_LIQ AS "montant_liquide", l.MT_ORD AS "montant_ordonnance",
    l.MT_VBP AS "montant_vbp", l.MT_ECP AS "montant_encours_paiement",
    l.MT_PAYE AS "montant_paye", l.MT_BLOQUE AS "montant_bloque",
    l.MT_DELEGATION AS "montant_delegation", l.MT_REGIE AS "montant_regie",
    -- Même nom que la colonne de l'extraction Excel, lu par le bloc Simandou et les filtres.
    COALESCE(TRIM(ps.LIBELLE_PILLIER_SIMANDOU), TO_CHAR(l.ID_PILLIER_SIMANDOU)) AS "pillier simandou",
    TRIM(pg.LIBELLE_LONG_PROGRAMME) AS "libelle_programme", TRIM(bl.LIBELLE_BAILLEUR) AS "libelle_bailleur",
    -- Axes de répartition : zone d'exécution, fonction (division COFOG) et type de budget (BAS).
    ss.CODE_ZONE_GEOGRAPHIQUE AS "code_zone_geographique",
    TRIM(z.LIBELLE_ZONE_GEOGRAPHIQUE) AS "zone_geographique",
    sv.CODE_DIVISION AS "code_fonction", TRIM(dv.LIBELLE_DIVISION) AS "fonctionnelle",
    TRIM(tb.LIBELLE) AS "libelle_type_budget"
FROM GDEP.LBUDG l
LEFT JOIN GDEP.TC_SECTION s ON s.NO_EX=l.NO_EX AND s.CODE_SECTION=l.CD_SECTION
LEFT JOIN GDEP.TC_SOUS_SECTION ss
    ON ss.NO_EX=l.NO_EX AND ss.CODE_SECTION=l.CD_SECTION AND ss.CODE_SOUS_SECTION=l.CD_SS_SECTION
LEFT JOIN GDEP.TC_SERVICE sv ON sv.CODE_SERVICE=ss.CODE_SERVICE
LEFT JOIN GDEP.TC_ZONE_GEO z ON z.CODE_ZONE_GEOGRAPHIQUE=ss.CODE_ZONE_GEOGRAPHIQUE
LEFT JOIN GDEP.TC_DIVISION dv ON dv.CODE_DIVISION=sv.CODE_DIVISION
LEFT JOIN GDEP.TC_TYPE_BUDGET tb ON tb.CODE_TYPE_BUDGET=l.CD_TYPE_BUDGET
LEFT JOIN GDEP.TC_PROGRAMME pg ON pg.CODE_PROGRAMME=l.CD_PROGRAMME
LEFT JOIN GDEP.TC_PILLIER_SIMANDOU ps ON ps.ID_PILLIER_SIMANDOU=l.ID_PILLIER_SIMANDOU
LEFT JOIN GDEP.TC_BAILLEUR bl
    ON bl.CODE_SOURCE_FIN=l.CD_SOURCE_FIN AND bl.CODE_GROUPE_BAIL=l.CD_GROUPE_BAIL AND bl.CODE_BAILLEUR=l.CD_BAILLEUR
WHERE l.NO_EX=:exercice
