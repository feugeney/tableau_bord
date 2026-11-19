import { Link } from "react-router-dom";
import { useAdmin } from "@/api/admin";
import type { Source } from "@/api/types";
import { DataTable } from "@/components/DataTable";
import { SourceBadge } from "@/components/Source";
import { Carte } from "@/components/ui/primitives";
import { EtatBloc } from "./commun";

interface Contrat {
  onglet: string;
  donnees: string;
  tables: string[];
  cle: string;
  sources: Source[];
}
export default function Alimentation() {
  const r = useAdmin<{ onglets: Contrat[]; note: string }>("alimentation/");
  return (
    <EtatBloc requete={r}>
      {(d) => (
        <div className="flex flex-col gap-4">
          <Carte
            titre="Alimentation du tableau de bord"
            sousTitre="Sources externes → flux ETL → base centrale → indicateurs et onglets"
          >
            <p className="text-base text-ink-2">{d.note}</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              {[
                ["1. Connecter", "Définir et tester l'accès aux systèmes d'origine.", "sources"],
                ["2. Alimenter", "Extraire, transformer et contrôler avant d'enregistrer.", "flux-etl"],
                ["3. Superviser", "Consulter les exécutions et les contrôles de qualité.", "chargements"],
              ].map(([titre, description, lien]) => (
                <Link
                  key={lien}
                  to={`/administration/${lien}`}
                  className="rounded border border-border bg-bg p-4 hover:bg-hover"
                >
                  <strong className="text-ink">{titre}</strong>
                  <p className="mt-2 text-sm text-ink-2">{description}</p>
                </Link>
              ))}
            </div>
          </Carte>
          <Carte
            titre="Cartographie des onglets et de leurs données"
            sousTitre="Contrats d'alimentation : une source peut alimenter plusieurs onglets. Les jeux d'illustration sont identifiés séparément."
          >
            <DataTable
              donnees={d.onglets}
              libelle="Cartographie des données du tableau de bord"
              colonnes={[
                { header: "Onglet", accessorKey: "onglet" },
                { header: "Données nécessaires", accessorKey: "donnees" },
                {
                  header: "Sources et situations",
                  id: "sources",
                  cell: ({ row }) => (
                    <div className="flex flex-col items-start gap-2">
                      {row.original.sources.map((s) => (
                        <SourceBadge
                          key={s.code}
                          meta={{
                            source: s.code,
                            application: s.application,
                            statut_source: s.statut,
                            date_situation: s.derniere_date_situation,
                          }}
                        />
                      ))}
                    </div>
                  ),
                },
                {
                  header: "Destination dans la base centrale",
                  id: "tables",
                  cell: ({ row }) => (
                    <div className="flex flex-col gap-1 text-xs">
                      {row.original.tables.map((t) => (
                        <code key={t}>{t}</code>
                      ))}
                    </div>
                  ),
                },
                { header: "Clé et périmètre", accessorKey: "cle" },
              ]}
            />
          </Carte>
        </div>
      )}
    </EtatBloc>
  );
}
