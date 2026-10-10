import type { UseQueryResult } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { ErreurBloc } from "@/components/Source";
import { Squelette } from "@/components/ui/primitives";

/** Chargement / erreur (avec « Réessayer ») pour les réponses d'administration (non enveloppées). */
export function EtatBloc<T>({
  requete,
  children,
  hauteur = "h-48",
}: {
  requete: UseQueryResult<T>;
  children: (data: T) => ReactNode;
  hauteur?: string;
}) {
  if (requete.isPending) return <Squelette className={`${hauteur} w-full`} />;
  if (requete.isError) return <ErreurBloc erreur={requete.error} onReessayer={() => requete.refetch()} />;
  return <>{children(requete.data)}</>;
}
