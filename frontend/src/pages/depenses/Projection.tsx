import { useDonnees } from "@/api/hooks";
import { DataTable } from "@/components/DataTable";
import { Montant } from "@/components/Montant";
import { BlocProjection, type Projection } from "@/components/Projection";
import { Carte } from "@/components/ui/primitives";
import { nombre, pct } from "@/lib/format";

import { EtatBloc } from "../commun";

interface ProjectionDepenses {
  engagement: Projection;
  seuil: number;
  sous_le_seuil: boolean;
  ministeres: {
    code: string;
    libelle: string;
    credit_actuel: number;
    credit_engage: number;
    taux_engagement: number | null;
    projete: number;
    taux_projete: number | null;
    fiable: boolean;
    plafonne: boolean;
  }[];
  nb_ministeres_sous_le_seuil: number;
}

/** Projection de fin d'exercice ; partagée avec la page Synthèse. */
export function BlocProjectionDepenses({ onSection }: { onSection: (code: string) => void }) {
  const r = useDonnees<ProjectionDepenses>("/depense/projection/");
  return (
    <Carte
      id="projection"
      titre="Projection de fin d'exercice"
      sousTitre="Engagement cumulé constaté, puis prolongé jusqu'au 31 décembre"
    >
      <EtatBloc requete={r} hauteur="h-80">
        {(d) => (
          // Demi-largeur (à côté des soldes non payés) : projection et tableau l'un sous l'autre.
          <div className="flex flex-col gap-6">
            <BlocProjection
              p={d.engagement}
              grandeur="engagés"
              libelleCible="Crédits actuels"
              libelleRealise="Engagé (cumul)"
              sousLeSeuil={d.sous_le_seuil}
              seuil={d.seuil}
            />
            {d.ministeres.length > 0 && (
              <div className="min-w-0">
                <h3 className="etiquette mb-2">
                  Ministères les plus éloignés de leurs crédits · {nombre(d.nb_ministeres_sous_le_seuil)} sous{" "}
                  {pct(d.seuil)} en fin d'exercice
                </h3>
                <DataTable
                  donnees={d.ministeres.slice(0, 10)}
                  recherche={false}
                  libelle="Engagement projeté en fin d'exercice par ministère"
                  onLigne={(m) => onSection(m.code)}
                  colonnes={[
                    { header: "Ministère", accessorKey: "libelle" },
                    {
                      header: "Crédits",
                      accessorKey: "credit_actuel",
                      cell: ({ getValue }) => <Montant gnf={getValue() as number} />,
                      meta: { numerique: true },
                    },
                    {
                      header: "Engagé",
                      accessorKey: "taux_engagement",
                      cell: ({ getValue }) => pct(getValue() as number | null),
                      meta: { numerique: true },
                    },
                    {
                      header: "Projeté",
                      accessorKey: "taux_projete",
                      cell: ({ row }) => (
                        <span
                          title={row.original.fiable ? undefined : "Trop peu d'engagements pour projeter"}
                        >
                          {pct(row.original.taux_projete)}
                          {row.original.fiable ? "" : " *"}
                        </span>
                      ),
                      meta: { numerique: true },
                    },
                  ]}
                />
                <p className="mt-2 text-sm text-ink-2">
                  Ministères de plus de <Montant gnf={20e9} decimales={0} /> de crédits. * Engagements trop
                  récents ou absents : le taux projeté est le taux actuel.
                </p>
              </div>
            )}
          </div>
        )}
      </EtatBloc>
    </Carte>
  );
}
