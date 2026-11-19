import { useDonnees } from "@/api/hooks";
import type { ComparaisonN1 } from "@/api/types";

export type { ComparaisonN1 };

/** Comparaison avec l'exercice précédent, partagée par les indicateurs et le tableau des ministères. */
export function useComparaisonN1() {
  return useDonnees<ComparaisonN1>("/depense/comparaison-n1/");
}
