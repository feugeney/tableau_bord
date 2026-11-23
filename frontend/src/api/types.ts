export type StatutSource = "reel" | "demo" | "non_raccorde";
export type Severite = "critique" | "serieux" | "vigilance";

export interface Meta {
  source: string;
  application?: string;
  date_situation: string | null;
  exercice?: number | null;
  statut_source: StatutSource;
  genere_le: string;
  paiement?: "ajuste" | "brut";
  test_non_reconcilie?: boolean;
  indicateurs_indisponibles?: string[];
  origine?: string;
  date_extraction?: string | null;
}

export interface Enveloppe<T> {
  meta: Meta;
  data: T | null;
}

export interface Utilisateur {
  id: number;
  identifiant: string;
  nom: string;
  role: "ministre_cabinet" | "directeur" | "dnsi_admin" | "lecteur";
  role_libelle: string;
  structure: string;
  domaines: string[];
  peut_exporter: boolean;
  est_admin: boolean;
  peut_explorer: boolean;
  exige_2fa: boolean;
  a_2fa: boolean;
}

export interface Alerte {
  id: number;
  date: string;
  domaine: string;
  source: string | null;
  source_code: string | null;
  date_situation: string | null;
  severite: Severite;
  titre: string;
  message: string;
  valeur: string;
  action_recommandee: string;
  lien: string;
  statut: "nouvelle" | "vue" | "traitee";
  regle_code?: string | null;
  /** Alertes par dossier (arbitrages) : titre, ministère, acteur, montant (GNF, texte), jours… */
  donnees?: Record<string, string | number | null>;
  notifiee_le?: string | null;
  relancee_le?: string | null;
}

export interface Source {
  code: string;
  domaine: string;
  domaine_libelle: string;
  application: string;
  structure: string;
  statut: StatutSource;
  connecteur: string;
  en_production_depuis: string | null;
  remarque: string;
  dernier_chargement: {
    id: number;
    date: string;
    statut: "en_cours" | "succes" | "echec" | "apercu";
    fichier: string;
    lignes_chargees: number;
    message_erreur: string;
  } | null;
  derniere_date_situation: string | null;
}

export interface Paiement {
  mode: "ajuste" | "brut";
  ordonnance: number;
  paye: number;
  reste_a_payer: number;
  paye_sur_ordonnance: number | null;
}

export interface IndicateursDepense {
  qualite?: {
    engage_sup_credits: number;
    liquide_sup_engage: number;
    soldes_negatifs: { section: string; montant: number }[];
  };
  credit_initial_lfi: number;
  credit_actuel: number;
  variation_lfi: number | null;
  credit_engage: number;
  taux_engagement: number | null;
  montant_liquide: number;
  taux_liquidation: number | null;
  taux_liquidation_sur_credits: number | null;
  montant_ordonnance: number;
  taux_ordonnancement: number | null;
  taux_ordonnancement_sur_credits: number | null;
  montant_vbp: number;
  taux_vbp: number | null;
  montant_paye: number;
  taux_paiement: number | null;
  taux_paiement_sur_credits: number | null;
  credit_disponible: number | null;
  credits_non_engages: number;
  paiement: Paiement;
  hors_chaine: { ordonnance: number; paye: number };
  nb_lignes: number;
  nb_engagements: number;
  nb_lfi_absent: number;
  nb_lignes_depassement: number | null;
}

export interface PilotageDepense {
  disponibilite: {
    credit_actuel: number | null;
    credit_engage: number | null;
    credit_disponible: number | null;
    credit_reserve: number | null;
    montant_bloque: number | null;
    credits_non_engages: number | null;
    disponible_reconstitue: number | null;
    ecart_disponibilite: number | null;
    part_immobilisee: number | null;
  };
  delais: {
    libelle: string;
    nb_engagements: number;
    paires_valides: number;
    couverture: number | null;
    mediane_jours: number | null;
    p90_jours: number | null;
    delais_negatifs: number;
    dates_futures: number;
    sans_date_fin: number;
  }[];
  rapprochements: {
    libelle: string;
    reference: number | null;
    detail_brut: number;
    detail_comparable: number;
    ecart: number | null;
    cles_en_ecart: number | null;
    ecart_absolu: number | null;
    perimetre: string;
  }[];
  apad: {
    renseigne: boolean;
    nb_lignes: number | null;
    nb_marches: number | null;
    avance_demarrage: number | null;
    reference: number | null;
    ecart: number | null;
    ministeres: { libelle: string; montant: number | null }[];
    dossiers: {
      ministere: string;
      gestionnaire: string;
      numero_apad: string;
      numero_marche: string;
      sous_section_id: string | null;
      libelle_projet: string;
      date_creation: string | null;
      avance_demarrage: number | null;
    }[];
  };
  regies: { nb_lignes: number | null; montant_regie: number | null };
}

export interface PilierSimandou {
  pilier: string | null;
  libelle: string;
  nb_lignes: number;
  nb_ministeres: number;
  credit_actuel: number;
  credit_engage: number;
  montant_ordonnance: number;
  montant_paye: number;
  part: number | null;
  taux_engagement: number | null;
  taux_paiement: number | null;
  empile: Nature["empile"];
  principaux_ministeres: { code: string; libelle_court: string; credit_actuel: number }[];
}

export interface Simandou {
  piliers: PilierSimandou[];
  hors_pilier: PilierSimandou | null;
  credit_simandou: number;
  part_simandou: number | null;
  taux_engagement_simandou: number | null;
  green: {
    nb_lignes: number;
    credit_actuel: number;
    credit_engage: number;
    part: number | null;
    taux_engagement: number | null;
  };
}

export interface Phase {
  code: string;
  libelle: string;
  montant: number;
  taux: number | null;
}

export interface Chaine {
  phases: Phase[];
  liquide_depasse_engage: boolean;
  nb_lignes_liquide_sup_engage: number;
}

export interface Nature {
  titre: string;
  libelle: string;
  credit_actuel: number;
  credit_engage: number;
  montant_ordonnance: number;
  montant_paye: number;
  credit_disponible: number | null;
  taux_engagement: number | null;
  empile: { paye: number; ordonnance_non_paye: number; engage_non_ordonnance: number; disponible: number };
  reste_a_payer: number;
}

/** Voyant des acteurs de la fiche d'un titre (note à la Ministre). */
export type Voyant = "bon" | "vigilance" | "critique";

/** Fiche d'un titre (vue 2). */
export interface FicheTitre {
  titre: string;
  libelle_titre: string;
  paiement_suivi: boolean;
  chaine: { code: string; libelle: string; montant: number | null; taux: number | null }[];
  ministeres: {
    code: string;
    libelle: string;
    credit_actuel: number;
    credit_engage: number;
    montant_paye: number;
    taux_engagement: number | null;
    taux_paiement: number | null;
  }[];
  nb_ministeres: number;
  acteurs: { code: string; acteur: string; voyant: Voyant | null; texte: string; raccorde?: boolean }[];
  alertes: { severite: Severite; texte: string }[];
}

export interface StatutMinistere {
  code: "sous_execution" | "paiements_retard" | "a_suivre" | "bon_rythme";
  libelle: string;
  severite: Severite | "bon";
}

export interface SectionLigne {
  code: string;
  libelle: string;
  libelle_court: string;
  type: string | null;
  credit_actuel: number;
  credit_engage: number;
  taux_engagement: number | null;
  montant_liquide: number;
  montant_ordonnance: number;
  montant_vbp: number;
  montant_paye: number;
  paye_sur_ordonnance: number | null;
  credit_disponible: number | null;
  reste_a_payer: number;
  nb_lignes_depassement: number | null;
  statut: StatutMinistere;
}

export interface SectionDetail {
  code: string;
  libelle: string;
  libelle_court: string;
  natures: Nature[];
  top_sous_sections: {
    code: string;
    libelle: string;
    credit_actuel: number;
    credit_engage: number;
    montant_ordonnance: number;
    montant_paye: number;
    taux_engagement: number | null;
  }[];
  lignes_depassement: {
    sous_section_code: string;
    sous_section: string;
    nature_code: string;
    nature: string;
    credit_actuel: number;
    credit_engage: number;
    credit_disponible: number | null;
  }[];
}

export interface Mensuel {
  mois: {
    mois: string;
    montant_engage: number;
    montant_engage_brut?: number;
    nb_engagements: number;
    periode_complementaire: boolean;
    decembre: boolean;
  }[];
  engage_periode_complementaire: number;
  rapprochement?: {
    perimetre: string;
    brut: number;
    comparable: number;
    reference: number;
    ecart_perimetre: number;
    ecart_reference: number;
    concordant: boolean;
  };
}

export interface RestesAPayer {
  mois: {
    mois_creation: string;
    reste_a_payer: number;
    nb_engagements: number;
    anciennete_mois: number | null;
    risque_arriere: boolean;
  }[];
  reste_a_payer_risque_arriere: number;
  seuil_mois: number;
}

export interface Procedure {
  procedure: string;
  hors_chaine: boolean;
  nb_engagements: number;
  montant_engage: number;
  montant_ordonnance: number;
  montant_paye: number;
  paye_sur_ordonnance: number | null;
}

export interface Beneficiaires {
  total_engage: number;
  beneficiaires: {
    beneficiaire_id: number | null;
    beneficiaire: string;
    nb_engagements: number;
    montant_engage: number;
    montant_paye: number;
    part: number | null;
  }[];
}

export interface Projet {
  section_code: string;
  sous_section_code: string;
  projet: string;
  ministere?: string;
  credit_initial_lfi: number;
  credit_actuel: number;
  credit_engage: number;
  montant_ordonnance: number;
  montant_paye: number;
  sans_engagement: boolean;
  taux_engagement: number | null;
}

export interface Investissement {
  credit_initial_lfi: number;
  credit_actuel: number;
  credit_engage: number;
  montant_ordonnance: number;
  montant_paye: number;
  taux_engagement: number | null;
  nb_projets: number;
  nb_projets_sans_engagement: number;
  credits_projets_sans_engagement: number;
  grands_projets: Projet[];
  top_ministeres: {
    code: string;
    libelle_court: string;
    credit_actuel: number;
    credit_engage: number;
    taux_engagement: number | null;
  }[];
}

export interface KpiSynthese {
  code: string;
  libelle: string;
  valeur?: number | null;
  taux?: number | null;
  reference?: number | null;
  masque?: boolean;
  raison_indisponibilite?: string;
  jours?: number | null;
  sous_seuil?: boolean;
  depasse?: boolean;
  nombre?: number;
  bande?: "tresorerie" | "recettes" | "execution" | "dette";
  meta: Meta;
}

/** Exercice précédent à la même date (engagement) et taux de clôture N−1 (autres phases). */
export interface ComparaisonN1 {
  disponible: boolean;
  motif?: string;
  exercice?: number;
  date?: string;
  taux_engagement?: number | null;
  par_section?: Record<string, number | null>;
  cloture?: Record<string, number | null>;
  methode?: string;
}

export interface Synthese {
  mode_synthese?: "decision" | "demonstration";
  avertissements?: string[];
  rapprochement_mensuel?: Mensuel["rapprochement"];
  indicateurs: KpiSynthese[];
  alertes: Alerte[];
  serie_mensuelle: {
    indicateur: "depense_engagee" | "recettes_fiscales" | "recettes_douanieres";
    source: string;
    mois: string;
    realise: number;
    objectif: number | null;
  }[];
  sources: Source[];
  alertes_compte?: Partial<Record<"critique" | "serieux" | "vigilance", number>>;
  execution?: {
    indicateurs: IndicateursDepense;
    comparaison_n1: ComparaisonN1;
  } | null;
  plan_engagement?: {
    exercice: number;
    periode: string;
    etat: string;
    plafond: number;
    engage_periode: number | null;
    taux: number | null;
    nb_depassements: number;
  } | null;
}

export interface Controle {
  code: string;
  libelle: string;
  niveau: "bloquant" | "avertissement" | "info";
  reussi: boolean;
  valeur: string | null;
  nombre: number | null;
  detail: Record<string, unknown>;
}
