/** Module d'administration : types et accès à /api/v1/admin/…. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, ErreurApi } from "./client";
import type { StatutSource } from "./types";

export interface SourceAdmin {
  code: string;
  domaine: string;
  application: string;
  structure: string;
  statut: StatutSource;
  connecteur: string;
  configuration: Record<string, unknown>;
  planification_cron: string;
  en_production_depuis: string | null;
  remarque: string;
  connexion_configuree: boolean | null;
  variable_connexion: string | null;
  nb_chargements: number;
}

export interface Mapping {
  id: number;
  source: string;
  table_cible: string;
  onglet: string;
  colonne_source: string;
  champ_cible: string;
  type_donnee: string;
  obligatoire: boolean;
}

export interface TableCible {
  table: string;
  domaine: string;
  libelle: string;
  champs: { nom: string; type: string; obligatoire: boolean; reference: string | null }[];
}

export interface ChargementAdmin {
  id: number;
  uuid: string;
  source: string;
  fichier: string;
  fichier_archive: string;
  empreinte_sha256: string;
  exercice: number | null;
  date_situation: string | null;
  lignes_lues: number;
  lignes_rejetees: number;
  lignes_chargees: number;
  debut: string;
  duree_secondes: number | null;
  statut: "en_cours" | "succes" | "echec" | "apercu";
  message_erreur: string;
  utilisateur: string | null;
  demo: boolean;
  detail: {
    controles?: { code: string; libelle: string; niveau: string; reussi: boolean; nombre: number | null }[];
    /** Numéro d'un chargement antérieur réussi du même contenu (même empreinte). */
    deja_charge?: number;
    /** « depot » : fichier relevé dans le dépôt SFTP. */
    origine?: string;
  };
}

export interface RegleAlerte {
  id: number;
  code: string;
  domaine: string;
  severite: "critique" | "serieux" | "vigilance";
  classe: string;
  seuils: Record<string, unknown>;
  titre_modele: string;
  message_modele: string;
  action_recommandee: string;
  lien: string;
  actif: boolean;
  nb_alertes_ouvertes: number;
}

export interface UtilisateurAdmin {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  role: string;
  domaines: string[];
  structure: string;
  is_active: boolean;
  last_login: string | null;
  date_joined: string;
  a_2fa: boolean;
  mot_de_passe_initial?: string;
}

export interface Jeton {
  id: number;
  nom: string;
  destinataire: string;
  domaines: string[];
  prefixe: string;
  expire_le: string | null;
  actif: boolean;
  cree_le: string;
  cree_par: string | null;
  derniere_utilisation: string | null;
  cle?: string;
}

export interface Parametre {
  code: string;
  valeur: unknown;
  libelle: string;
  unite: string;
  modifie_le: string;
}

export interface EntreeJournal {
  date: string;
  identifiant: string;
  action: string;
  objet: string;
  detail: Record<string, unknown>;
  adresse_ip: string | null;
}

export interface Entrepot {
  tables: { schema: string; table: string; lignes: number }[];
  vues: { vue: string; lignes: number }[];
  taille_base: string;
  zone_brute: { fichiers: number; octets: number };
  depot: {
    dossier: string;
    releve_minutes: number;
    en_attente: { source: string; fichier: string; octets: number }[];
  };
  evenements_amqp: boolean;
  version_cache: number | string;
  sources: { code: string; application: string; statut: StatutSource; chargements: number }[];
}

export interface ListesAdmin {
  roles: { code: string; libelle: string }[];
  domaines: { code: string; libelle: string }[];
  connecteurs: { code: string; libelle: string }[];
  statuts: { code: string; libelle: string }[];
  types_donnee: { code: string; libelle: string }[];
}

export interface Page<T> {
  count: number;
  results: T[];
}

export function useAdmin<T>(chemin: string, params?: Record<string, string | number | undefined>) {
  return useQuery({
    queryKey: ["admin", chemin, params],
    queryFn: () => api.get<T>(`/admin/${chemin}`, params),
  });
}

export function useListesAdmin() {
  return useQuery({
    queryKey: ["admin", "referentiels"],
    queryFn: () => api.get<ListesAdmin>("/admin/referentiels/"),
    staleTime: Infinity,
  });
}

/** Mutation d'administration : invalide les listes d'administration et les données affichées. */
export function useMutationAdmin<V, R = unknown>(fn: (v: V) => Promise<R>) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      client.invalidateQueries();
    },
  });
}

/** Message d'erreur lisible (erreurs de validation DRF comprises). */
export function messageErreur(e: unknown): string {
  if (e instanceof ErreurApi) {
    const corps = e.corps as Record<string, unknown>;
    const parties = Object.entries(corps)
      .filter(([k]) => k !== "code")
      .map(
        ([k, v]) =>
          `${k === "detail" || k === "non_field_errors" ? "" : `${k} : `}${Array.isArray(v) ? v.join(" ") : String(v)}`,
      );
    return parties.join(" · ") || e.message;
  }
  return e instanceof Error ? e.message : "Erreur inattendue.";
}
