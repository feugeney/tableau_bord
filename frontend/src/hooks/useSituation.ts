import { useQuery } from "@tanstack/react-query";
import { useLocation, useSearchParams } from "react-router-dom";

import { api } from "@/api/client";

import { useFiltres } from "./useFiltres";

interface Situations {
  exercices: { exercice: number; dates: string[] }[];
}

/** Source de chaque vue de la page Pilotage (le Trésor public n'est pas encore raccordé). */
const SOURCES_PILOTAGE: Record<string, string> = { tresor: "scie", plan: "plan_engagement", tofe: "tofe" };

/** Exercice et date de situation effectifs (filtres de l'URL, sinon dernière situation chargée). */
export function useSituation() {
  const { filtres } = useFiltres();
  const { pathname } = useLocation();
  const [params] = useSearchParams();
  const source = pathname.startsWith("/pilotage")
    ? (SOURCES_PILOTAGE[params.get("vue") ?? ""] ?? "tofe")
    : pathname.startsWith("/portefeuille") ||
        (pathname.startsWith("/recettes") && params.get("vue") === "administratives")
      ? "sysop"
      : undefined;
  const requete = useQuery({
    queryKey: ["situations", source],
    queryFn: () => api.get<Situations>("/situations/", { source }),
  });
  const exercices = requete.data?.exercices ?? [];
  const exercice = filtres.exercice ? Number(filtres.exercice) : exercices[0]?.exercice;
  const dates = exercices.find((e) => e.exercice === exercice)?.dates ?? [];
  const dateSituation = filtres.date_situation ?? dates[0];
  return { exercices, exercice, dates, dateSituation, chargement: requete.isPending };
}
