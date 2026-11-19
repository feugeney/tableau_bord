import { BookOpen, FileSpreadsheet, FileText } from "lucide-react";
import { useState } from "react";

import { telecharger } from "@/api/client";
import { useAuth } from "@/hooks/useAuth";
import { useFiltres } from "@/hooks/useFiltres";

import { Bouton } from "./ui/primitives";

/** Exports avec les mêmes filtres et droits que la page, journalisés côté serveur. */
export function BoutonExport({ page }: { page: string }) {
  const { utilisateur } = useAuth();
  const { requete } = useFiltres();
  const [encours, setEncours] = useState<string | null>(null);
  const [erreur, setErreur] = useState(false);
  if (!utilisateur?.peut_exporter) return null;
  async function exporter(format: "xlsx" | "pdf", rubrique = page) {
    setEncours(`${rubrique}.${format}`);
    setErreur(false);
    try {
      await telecharger(`/export/${rubrique}.${format}`, requete);
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
        {encours === `${page}.xlsx` ? "Export en cours…" : "Exporter (Excel)"}
      </Bouton>
      <Bouton onClick={() => exporter("pdf")} disabled={encours !== null}>
        <FileText className="h-4 w-4" aria-hidden />
        {encours === `${page}.pdf` ? "PDF en cours…" : "Exporter (PDF)"}
      </Bouton>
      {page === "synthese" && (
        <Bouton onClick={() => exporter("pdf", "rapport")} disabled={encours !== null}>
          <BookOpen className="h-4 w-4" aria-hidden />
          {encours === "rapport.pdf" ? "Rapport en cours…" : "Rapport complet (PDF)"}
        </Bouton>
      )}
      {erreur && (
        <span role="alert" className="text-sm font-bold text-ink">
          Export impossible. Réessayez.
        </span>
      )}
    </span>
  );
}
