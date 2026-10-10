import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";

import { useFiltres } from "./useFiltres";

interface Situations {
  exercices: { exercice: number; dates: string[] }[];
}

/** Exercice et date de situation effectifs (filtres de l'URL, sinon dernière situation chargée). */
export function useSituation() {
  const { filtres } = useFiltres();
  const requete = useQuery({ queryKey: ["situations"], queryFn: () => api.get<Situations>("/situations/") });
  const exercices = requete.data?.exercices ?? [];
  const exercice = filtres.exercice ? Number(filtres.exercice) : exercices[0]?.exercice;
  const dates = exercices.find((e) => e.exercice === exercice)?.dates ?? [];
  const dateSituation = filtres.date_situation ?? dates[0];
  return { exercices, exercice, dates, dateSituation, chargement: requete.isPending };
}
