import { useSources } from "@/api/hooks";
import type { Source } from "@/api/types";
import { DataTable, type Colonne } from "@/components/DataTable";
import { StatusPill } from "@/components/Indicateurs";
import { SourceBadge } from "@/components/Source";
import { Carte } from "@/components/ui/primitives";
import { dateFr, dateHeureFr } from "@/lib/format";

import { EtatBloc } from "./commun";

const colonnesSources: Colonne<Source>[] = [
  { header: "Domaine", accessorKey: "domaine_libelle" },
  { header: "Application", accessorKey: "application" },
  { header: "Structure", accessorKey: "structure" },
  {
    header: "Dernier chargement",
    id: "dernier",
    accessorFn: (s) => s.dernier_chargement?.date ?? "",
    cell: ({ row }) => {
      const c = row.original.dernier_chargement;
      if (!c) return <span className="text-ink-2">Aucun</span>;
      return (
        <span className="flex flex-col gap-1">
          <span className="chiffres">{dateHeureFr(c.date)}</span>
          {c.statut === "echec" && <StatusPill etat="critique" libelle="Échec du chargement" />}
          {row.original.derniere_date_situation && (
            <span className="text-sm text-ink-2">
              situation au {dateFr(row.original.derniere_date_situation)}
            </span>
          )}
        </span>
      );
    },
  },
  {
    header: "Statut",
    accessorKey: "statut",
    cell: ({ row }) => {
      const s = row.original;
      return (
        <span className="flex flex-col items-start gap-1">
          <SourceBadge
            meta={{ source: s.code, statut_source: s.statut, date_situation: s.derniere_date_situation }}
          />
          {s.remarque && <span className="text-sm text-ink-2">{s.remarque}</span>}
        </span>
      );
    },
  },
];

export default function EtatSources() {
  const requete = useSources();
  return (
    <Carte
      id="etat-sources"
      titre="État des sources"
      sousTitre="Dernier chargement et statut de chaque application"
    >
      <EtatBloc requete={requete}>
        {(sources) => (
          <DataTable
            donnees={sources}
            colonnes={colonnesSources}
            libelle="État des sources"
            recherche={false}
          />
        )}
      </EtatBloc>
    </Carte>
  );
}
