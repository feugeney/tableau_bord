import { FileSpreadsheet } from "lucide-react";
import { useState } from "react";

import { telecharger } from "@/api/client";
import { useAuth } from "@/hooks/useAuth";
import { useFiltres } from "@/hooks/useFiltres";

import { Bouton } from "./ui/primitives";

/** Export Excel de la page courante, avec les filtres affichés (journalisé côté serveur). */
export function BoutonExport({ page }: { page: string }) {
  const { utilisateur } = useAuth();
  const { requete } = useFiltres();
  const [etat, setEtat] = useState<"repos" | "encours" | "erreur">("repos");
  if (!utilisateur?.peut_exporter) return null;
  async function exporter() {
    setEtat("encours");
    try {
      await telecharger(`/export/${page}.xlsx`, requete);
      setEtat("repos");
    } catch {
      setEtat("erreur");
    }
  }
  return (
    <span className="inline-flex items-center gap-2">
      <Bouton onClick={exporter} disabled={etat === "encours"}>
        <FileSpreadsheet className="h-4 w-4" aria-hidden />
        {etat === "encours" ? "Export en cours…" : "Exporter (Excel)"}
      </Bouton>
      {etat === "erreur" && (
        <span role="alert" className="text-sm font-bold text-ink">
          Export impossible. Réessayez.
        </span>
      )}
    </span>
  );
}
