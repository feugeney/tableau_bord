import { FileSpreadsheet, FileText } from "lucide-react";
import { useState } from "react";

import { telecharger } from "@/api/client";
import { useAuth } from "@/hooks/useAuth";
import { useFiltres } from "@/hooks/useFiltres";

import { Bouton } from "./ui/primitives";

/**
 * Export décideurs du tableau « Ministères et institutions » (Excel et PDF mis en forme),
 * avec les filtres de la page ; réservé aux profils autorisés à exporter, journalisé côté serveur.
 */
export function ExportMinisteres({ colonnes }: { colonnes?: string[] }) {
  const { utilisateur } = useAuth();
  const { requete } = useFiltres();
  const [encours, setEncours] = useState<"xlsx" | "pdf" | null>(null);
  const [erreur, setErreur] = useState(false);
  if (!utilisateur?.peut_exporter) return null;
  async function exporter(format: "xlsx" | "pdf") {
    setEncours(format);
    setErreur(false);
    try {
      // Les fichiers reprennent les colonnes affichées à l'écran.
      await telecharger(`/depense/ministeres.${format}`, { ...requete, colonnes: colonnes?.join(",") });
    } catch {
      setErreur(true);
    } finally {
      setEncours(null);
    }
  }
  return (
    <span className="inline-flex flex-wrap items-center gap-2" aria-busy={encours !== null}>
      <Bouton onClick={() => exporter("xlsx")} disabled={encours !== null}>
        <FileSpreadsheet className="h-4 w-4" aria-hidden />
        {encours === "xlsx" ? "Export en cours…" : "Excel"}
      </Bouton>
      <Bouton onClick={() => exporter("pdf")} disabled={encours !== null}>
        <FileText className="h-4 w-4" aria-hidden />
        {encours === "pdf" ? "PDF en cours…" : "PDF"}
      </Bouton>
      {erreur && (
        <span role="alert" className="text-sm font-bold text-ink">
          Export impossible. Réessayez.
        </span>
      )}
    </span>
  );
}
