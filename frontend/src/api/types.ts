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
  credit_initial_lfi: number;
  credit_actuel: number;
  variation_lfi: number | null;
  credit_engage: number;
  taux_engagement: number | null;
  montant_liquide: number;
  montant_ordonnance: number;
  taux_ordonnancement: number | null;
  montant_paye: number;
  taux_paiement: number | null;
  credit_disponible: number;
  credits_non_engages: number;
  paiement: Paiement;
  hors_chaine: { ordonnance: number; paye: number };
  nb_lignes: number;
  nb_engagements: number;
  nb_lfi_absent: number;
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
  credit_disponible: number;
  taux_engagement: number | null;
  empile: { paye: number; ordonnance_non_paye: number; engage_non_ordonnance: number; disponible: number };
  reste_a_payer: number;
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
  montant_ordonnance: number;
  montant_paye: number;
  paye_sur_ordonnance: number | null;
  credit_disponible: number;
  reste_a_payer: number;
  nb_lignes_depassement: number;
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
    credit_disponible: number;
  }[];
}

export interface Mensuel {
  mois: {
    mois: string;
    montant_engage: number;
    nb_engagements: number;
    periode_complementaire: boolean;
    decembre: boolean;
  }[];
  engage_periode_complementaire: number;
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
  jours?: number | null;
  sous_seuil?: boolean;
  depasse?: boolean;
  meta: Meta;
}

export interface Synthese {
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
