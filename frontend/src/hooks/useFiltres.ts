import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

export type Nature = "" | "personnel" | "biens_services" | "transferts" | "investissement" | "dette";
export type ModePaiement = "ajuste" | "brut";

export interface Filtres {
  exercice?: string;
  date_situation?: string;
  nature: Nature;
  section?: string;
  paiement: ModePaiement;
}

/** Filtres portés par l'URL : partageables et conservés en changeant d'onglet. */
export function useFiltres() {
  const [params, setParams] = useSearchParams();

  const filtres: Filtres = useMemo(
    () => ({
      exercice: params.get("exercice") ?? undefined,
      date_situation: params.get("date_situation") ?? undefined,
      nature: (params.get("nature") ?? "") as Nature,
      section: params.get("section") ?? undefined,
      paiement: (params.get("paiement") as ModePaiement) || "ajuste",
    }),
    [params],
  );

  const definir = useCallback(
    (maj: Partial<Filtres>) => {
      setParams(
        (avant) => {
          const suivant = new URLSearchParams(avant);
          Object.entries(maj).forEach(([k, v]) => {
            const defaut = (k === "paiement" && v === "ajuste") || v === "" || v === undefined;
            if (defaut) suivant.delete(k);
            else suivant.set(k, String(v));
          });
          if ("exercice" in maj) suivant.delete("date_situation");
          return suivant;
        },
        { replace: true },
      );
    },
    [setParams],
  );

  /** Paramètres transmis à l'API. */
  const requete = useMemo(
    () => ({
      exercice: filtres.exercice,
      date_situation: filtres.date_situation,
      nature: filtres.nature || undefined,
      section: filtres.section,
      paiement: filtres.paiement,
    }),
    [filtres],
  );

  /** Chaîne de requête des filtres globaux, à propager dans les liens d'onglets. */
  const global = useMemo(() => {
    const q = new URLSearchParams();
    if (filtres.exercice) q.set("exercice", filtres.exercice);
    if (filtres.date_situation) q.set("date_situation", filtres.date_situation);
    const s = q.toString();
    return s ? `?${s}` : "";
  }, [filtres.exercice, filtres.date_situation]);

  return { filtres, definir, requete, global };
}
