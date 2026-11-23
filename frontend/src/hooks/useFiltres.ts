import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

export type Nature = "" | "personnel" | "biens_services" | "transferts" | "investissement" | "dette";
export type ModePaiement = "ajuste" | "brut";

/** Critères multiples de la page Dépenses (paramètres d'URL, valeurs séparées par des virgules). */
export const CRITERES = [
  "ministeres",
  "programmes",
  "titres",
  "fonctions",
  "piliers",
  "types_budget",
  "zones",
  "sources",
  "bailleurs",
] as const;
export type Critere = (typeof CRITERES)[number];

export interface Filtres {
  exercice?: string;
  date_situation?: string;
  nature: Nature;
  section?: string;
  paiement: ModePaiement;
  mode_synthese?: "decision" | "demonstration";
  criteres: Partial<Record<Critere, string[]>>;
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
      // Paiement de la Chaîne Dépense par défaut ; « ajuste » ne reste accessible que par l'adresse.
      paiement: (params.get("paiement") as ModePaiement) || "brut",
      mode_synthese: (params.get("mode_synthese") as Filtres["mode_synthese"]) || undefined,
      criteres: Object.fromEntries(
        CRITERES.map((c) => [c, (params.get(c) ?? "").split(",").filter(Boolean)]).filter(
          ([, v]) => v.length,
        ),
      ),
    }),
    [params],
  );

  /** Remplace les valeurs d'un critère (liste vide : critère retiré) ; `null` efface tous les critères. */
  const definirCritere = useCallback(
    (critere: Critere | null, valeurs: string[] = []) => {
      setParams(
        (avant) => {
          const suivant = new URLSearchParams(avant);
          for (const c of critere ? [critere] : CRITERES) suivant.delete(c);
          if (critere && valeurs.length) suivant.set(critere, valeurs.join(","));
          return suivant;
        },
        { replace: true },
      );
    },
    [setParams],
  );

  const definir = useCallback(
    (maj: Partial<Filtres>) => {
      setParams(
        (avant) => {
          const suivant = new URLSearchParams(avant);
          Object.entries(maj).forEach(([k, v]) => {
            const defaut = (k === "paiement" && v === "brut") || v === "" || v === undefined;
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
      mode_synthese: filtres.mode_synthese,
      ...Object.fromEntries(Object.entries(filtres.criteres).map(([c, v]) => [c, v.join(",")])),
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

  return { filtres, definir, definirCritere, requete, global };
}
