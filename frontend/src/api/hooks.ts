import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useFiltres } from "@/hooks/useFiltres";

import { api } from "./client";
import type { Alerte, Enveloppe, Source } from "./types";

type Params = Record<string, string | number | undefined | null>;

/** Données d'un point d'accès de page, avec les filtres communs de l'URL. */
export function useDonnees<T>(chemin: string, extra: Params = {}, options: { actif?: boolean } = {}) {
  const { requete } = useFiltres();
  const params = { ...requete, ...extra };
  return useQuery({
    queryKey: [chemin, params],
    queryFn: () => api.get<Enveloppe<T>>(chemin, params),
    placeholderData: keepPreviousData,
    enabled: options.actif ?? true,
  });
}

export function useSources() {
  return useQuery({ queryKey: ["sources"], queryFn: () => api.get<Source[]>("/sources/") });
}

export function useAlertes(filtres: Params = {}) {
  return useQuery({
    queryKey: ["alertes", filtres],
    queryFn: () => api.get<Alerte[]>("/alertes/", filtres),
  });
}

export function useStatutAlerte() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, statut }: { id: number; statut: Alerte["statut"] }) =>
      api.patch<Alerte>(`/alertes/${id}/`, { statut }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["alertes"] });
      client.invalidateQueries({ queryKey: ["/synthese/"] });
    },
  });
}
