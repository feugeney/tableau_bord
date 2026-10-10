"""Couche de restitution « mart » : vues matérialisées rafraîchies après chaque chargement.

Seul le dernier chargement réussi par (source, exercice, date de situation) est
retenu (mart.v_chargements_actifs) : recharger un même fichier ne double pas les montants,
et les situations de dates différentes restent empilées.
"""

from django.db import migrations

ACTIFS = "chargement_id IN (SELECT id FROM mart.v_chargements_actifs)"

SQL = f"""
CREATE VIEW mart.v_chargements_actifs AS
SELECT DISTINCT ON (source_id, exercice, date_situation) id, source_id, exercice, date_situation
FROM public.core_chargement
WHERE statut = 'succes'
ORDER BY source_id, exercice, date_situation, fin DESC NULLS LAST, id DESC;

CREATE MATERIALIZED VIEW mart.mv_depense_par_section_titre AS
WITH sit AS (
    SELECT exercice, date_situation, section_code, titre,
           count(*) AS nb_lignes,
           sum(credit_initial_lfi) AS credit_initial_lfi, sum(credit_lfr) AS credit_lfr,
           sum(credit_actuel) AS credit_actuel, sum(credit_disponible) AS credit_disponible,
           sum(credit_reserve) AS credit_reserve, sum(credit_engage) AS credit_engage,
           sum(credit_engage_projet) AS credit_engage_projet, sum(credit_engage_cf) AS credit_engage_cf,
           sum(montant_liquide) AS montant_liquide, sum(montant_ordonnance) AS montant_ordonnance,
           sum(montant_vbp) AS montant_vbp, sum(montant_encours_paiement) AS montant_encours_paiement,
           sum(montant_paye) AS montant_paye, sum(montant_bloque) AS montant_bloque,
           sum(montant_delegation) AS montant_delegation, sum(avance_demarrage) AS avance_demarrage,
           sum(montant_regie) AS montant_regie,
           count(*) FILTER (WHERE lfi_absent) AS nb_lfi_absent
    FROM dw.fait_situation_ligne WHERE {ACTIFS}
    GROUP BY 1, 2, 3, 4
), eng AS (
    SELECT e.exercice, e.date_situation, e.section_code, e.titre,
           count(*) AS nb_engagements,
           sum(e.montant_engage) AS eng_montant_engage,
           sum(e.montant_ordonnance) AS eng_montant_ordonnance,
           sum(e.montant_paye) AS eng_montant_paye,
           coalesce(sum(e.montant_ordonnance) FILTER (WHERE p.paiement_hors_chaine), 0) AS ordonnance_hors_chaine,
           coalesce(sum(e.montant_paye) FILTER (WHERE p.paiement_hors_chaine), 0) AS paye_hors_chaine
    FROM dw.fait_engagement e
    LEFT JOIN ref.ref_type_procedure p ON p.id = e.type_procedure_id
    WHERE e.{ACTIFS}
    GROUP BY 1, 2, 3, 4
)
SELECT coalesce(s.exercice, e.exercice) AS exercice,
       coalesce(s.date_situation, e.date_situation) AS date_situation,
       coalesce(s.section_code, e.section_code) AS section_code,
       coalesce(s.titre, e.titre) AS titre,
       coalesce(s.nb_lignes, 0) AS nb_lignes,
       coalesce(s.credit_initial_lfi, 0) AS credit_initial_lfi, coalesce(s.credit_lfr, 0) AS credit_lfr,
       coalesce(s.credit_actuel, 0) AS credit_actuel, coalesce(s.credit_disponible, 0) AS credit_disponible,
       coalesce(s.credit_reserve, 0) AS credit_reserve, coalesce(s.credit_engage, 0) AS credit_engage,
       coalesce(s.credit_engage_projet, 0) AS credit_engage_projet,
       coalesce(s.credit_engage_cf, 0) AS credit_engage_cf, coalesce(s.montant_liquide, 0) AS montant_liquide,
       coalesce(s.montant_ordonnance, 0) AS montant_ordonnance, coalesce(s.montant_vbp, 0) AS montant_vbp,
       coalesce(s.montant_encours_paiement, 0) AS montant_encours_paiement,
       coalesce(s.montant_paye, 0) AS montant_paye, coalesce(s.montant_bloque, 0) AS montant_bloque,
       coalesce(s.montant_delegation, 0) AS montant_delegation,
       coalesce(s.avance_demarrage, 0) AS avance_demarrage, coalesce(s.montant_regie, 0) AS montant_regie,
       coalesce(s.nb_lfi_absent, 0) AS nb_lfi_absent,
       coalesce(e.nb_engagements, 0) AS nb_engagements,
       coalesce(e.eng_montant_engage, 0) AS eng_montant_engage,
       coalesce(e.eng_montant_ordonnance, 0) AS eng_montant_ordonnance,
       coalesce(e.eng_montant_paye, 0) AS eng_montant_paye,
       coalesce(e.ordonnance_hors_chaine, 0) AS ordonnance_hors_chaine,
       coalesce(e.paye_hors_chaine, 0) AS paye_hors_chaine
FROM sit s
FULL OUTER JOIN eng e
  ON e.exercice = s.exercice AND e.date_situation = s.date_situation
 AND e.section_code = s.section_code AND e.titre = s.titre;
CREATE INDEX ON mart.mv_depense_par_section_titre (exercice, date_situation, section_code);

CREATE MATERIALIZED VIEW mart.mv_depense_synthese AS
SELECT exercice, date_situation,
       sum(nb_lignes) AS nb_lignes, sum(nb_engagements) AS nb_engagements,
       sum(credit_initial_lfi) AS credit_initial_lfi, sum(credit_actuel) AS credit_actuel,
       sum(credit_disponible) AS credit_disponible, sum(credit_engage) AS credit_engage,
       sum(montant_liquide) AS montant_liquide, sum(montant_ordonnance) AS montant_ordonnance,
       sum(montant_vbp) AS montant_vbp, sum(montant_paye) AS montant_paye,
       sum(ordonnance_hors_chaine) AS ordonnance_hors_chaine, sum(paye_hors_chaine) AS paye_hors_chaine
FROM mart.mv_depense_par_section_titre
GROUP BY 1, 2;

CREATE MATERIALIZED VIEW mart.mv_depense_mensuelle AS
SELECT e.exercice, e.date_situation, e.section_code, e.titre,
       date_trunc('month', e.date_creation)::date AS mois,
       coalesce(p.paiement_hors_chaine, false) AS hors_chaine,
       count(*) AS nb_engagements,
       sum(e.montant_engage) AS montant_engage,
       sum(e.montant_ordonnance) AS montant_ordonnance,
       sum(e.montant_paye) AS montant_paye
FROM dw.fait_engagement e
LEFT JOIN ref.ref_type_procedure p ON p.id = e.type_procedure_id
WHERE e.{ACTIFS} AND e.date_creation IS NOT NULL
GROUP BY 1, 2, 3, 4, 5, 6;
CREATE INDEX ON mart.mv_depense_mensuelle (exercice, date_situation);

CREATE MATERIALIZED VIEW mart.mv_restes_a_payer_anciennete AS
SELECT e.exercice, e.date_situation, e.section_code, e.titre,
       date_trunc('month', e.date_creation)::date AS mois_creation,
       coalesce(p.paiement_hors_chaine, false) AS hors_chaine,
       count(*) AS nb_engagements,
       sum(e.montant_ordonnance - e.montant_paye) AS reste_a_payer
FROM dw.fait_engagement e
LEFT JOIN ref.ref_type_procedure p ON p.id = e.type_procedure_id
WHERE e.{ACTIFS} AND e.montant_ordonnance > e.montant_paye
GROUP BY 1, 2, 3, 4, 5, 6;
CREATE INDEX ON mart.mv_restes_a_payer_anciennete (exercice, date_situation);

CREATE MATERIALIZED VIEW mart.mv_depense_procedures AS
SELECT e.exercice, e.date_situation, e.section_code, e.titre,
       p.id AS type_procedure_id, coalesce(p.libelle, '(non renseigné)') AS procedure,
       coalesce(p.paiement_hors_chaine, false) AS hors_chaine,
       count(*) AS nb_engagements,
       sum(e.montant_engage) AS montant_engage,
       sum(e.montant_ordonnance) AS montant_ordonnance,
       sum(e.montant_paye) AS montant_paye
FROM dw.fait_engagement e
LEFT JOIN ref.ref_type_procedure p ON p.id = e.type_procedure_id
WHERE e.{ACTIFS}
GROUP BY 1, 2, 3, 4, 5, 6, 7;
CREATE INDEX ON mart.mv_depense_procedures (exercice, date_situation);

CREATE MATERIALIZED VIEW mart.mv_depense_beneficiaires AS
SELECT e.exercice, e.date_situation, e.section_code, e.titre,
       e.beneficiaire_id, coalesce(b.nom_affiche, '(non renseigné)') AS beneficiaire,
       count(*) AS nb_engagements,
       sum(e.montant_engage) AS montant_engage,
       sum(e.montant_paye) AS montant_paye
FROM dw.fait_engagement e
LEFT JOIN ref.ref_beneficiaire b ON b.id = e.beneficiaire_id
WHERE e.{ACTIFS}
GROUP BY 1, 2, 3, 4, 5, 6;
CREATE INDEX ON mart.mv_depense_beneficiaires (exercice, date_situation);

CREATE MATERIALIZED VIEW mart.mv_investissement_projets AS
SELECT l.exercice, l.date_situation, l.section_code, l.sous_section_code,
       coalesce(ss.libelle, l.sous_section_code) AS projet,
       count(*) AS nb_lignes,
       sum(l.credit_initial_lfi) AS credit_initial_lfi, sum(l.credit_actuel) AS credit_actuel,
       sum(l.credit_disponible) AS credit_disponible, sum(l.credit_engage) AS credit_engage,
       sum(l.montant_ordonnance) AS montant_ordonnance, sum(l.montant_paye) AS montant_paye
FROM dw.fait_situation_ligne l
LEFT JOIN ref.ref_sous_section ss ON ss.code = l.sous_section_code
WHERE l.{ACTIFS} AND l.titre = '5'
GROUP BY 1, 2, 3, 4, 5;
CREATE INDEX ON mart.mv_investissement_projets (exercice, date_situation);

CREATE MATERIALIZED VIEW mart.mv_synthese_globale AS
SELECT exercice, date_situation, 'depense_engagee'::text AS indicateur, mois,
       sum(montant_engage) AS realise, NULL::numeric AS objectif
FROM mart.mv_depense_mensuelle
GROUP BY 1, 2, 3, 4
UNION ALL
SELECT exercice, date_situation, 'recettes_fiscales', make_date(exercice, mois, 1),
       sum(recouvre), sum(objectif)
FROM dw.fait_recouvrement_fiscal WHERE {ACTIFS}
GROUP BY 1, 2, 3, 4
UNION ALL
SELECT exercice, date_situation, 'recettes_douanieres', make_date(exercice, mois, 1),
       sum(recouvre), sum(objectif)
FROM dw.fait_recette_douane WHERE {ACTIFS}
GROUP BY 1, 2, 3, 4;
"""

SQL_INVERSE = """
DROP MATERIALIZED VIEW IF EXISTS mart.mv_synthese_globale;
DROP MATERIALIZED VIEW IF EXISTS mart.mv_investissement_projets;
DROP MATERIALIZED VIEW IF EXISTS mart.mv_depense_beneficiaires;
DROP MATERIALIZED VIEW IF EXISTS mart.mv_depense_procedures;
DROP MATERIALIZED VIEW IF EXISTS mart.mv_restes_a_payer_anciennete;
DROP MATERIALIZED VIEW IF EXISTS mart.mv_depense_mensuelle;
DROP MATERIALIZED VIEW IF EXISTS mart.mv_depense_synthese;
DROP MATERIALIZED VIEW IF EXISTS mart.mv_depense_par_section_titre;
DROP VIEW IF EXISTS mart.v_chargements_actifs;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("depense", "0001_initial"),
        ("core", "0001_initial"),
        ("referentiels", "0001_initial"),
        ("recettes_fiscales", "0001_initial"),
        ("douanes", "0001_initial"),
    ]

    operations = [migrations.RunSQL(SQL, SQL_INVERSE)]
