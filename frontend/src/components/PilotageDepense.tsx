import { useDonnees } from "@/api/hooks";
import type { PilotageDepense as Donnees } from "@/api/types";
import { nombre, pct } from "@/lib/format";
import { EtatBloc, Zone } from "@/pages/commun";

import { DataTable } from "./DataTable";
import { BandeauKpi, KpiCard, Note, StatusPill } from "./Indicateurs";
import { Montant } from "./Montant";
import { Carte } from "./ui/primitives";

type Partie = "delais" | "avances" | "concordance";

/** `parties` : zones affichées (la concordance est rangée dans la section repliée « Qualité des données »). */
export function PilotageDepense({ parties = ["delais", "avances", "concordance"] }: { parties?: Partie[] }) {
  const requete = useDonnees<Donnees>("/depense/pilotage/");
  return (
    <EtatBloc requete={requete}>
      {(d) => {
        return (
          <div className="flex min-w-0 flex-col gap-6">
            {parties.includes("delais") && (
              <Zone titre="Délais de traitement">
                <Carte
                  titre="Délais de visa"
                  sousTitre="Jours calendaires · dossiers reçus avec deux dates valides à la date de situation"
                >
                  <DataTable
                    donnees={d.delais}
                    libelle="Délais de visa"
                    recherche={false}
                    nomExport="delais-visas"
                    colonnes={[
                      { accessorKey: "libelle", header: "Étape" },
                      {
                        accessorKey: "mediane_jours",
                        header: "Médiane (jours)",
                        cell: ({ row }) => nombre(row.original.mediane_jours),
                        meta: { numerique: true },
                      },
                      {
                        accessorKey: "p90_jours",
                        header: "90e percentile (jours)",
                        cell: ({ row }) => nombre(row.original.p90_jours),
                        meta: { numerique: true },
                      },
                      { accessorKey: "paires_valides", header: "Paires datées", meta: { numerique: true } },
                      {
                        accessorKey: "couverture",
                        header: "Couverture",
                        cell: ({ row }) => pct(row.original.couverture),
                        meta: { numerique: true },
                      },
                      {
                        accessorKey: "sans_date_fin",
                        header: "Sans date de visa",
                        meta: { numerique: true },
                      },
                    ]}
                  />
                  <p className="mt-3 text-sm text-ink-2">
                    Une date manquante ne prouve pas un blocage. Les délais négatifs et dates postérieures à
                    la situation sont exclus.
                    {d.delais.some((r) => r.delais_negatifs > 0 || r.dates_futures > 0) &&
                      " Des dates incohérentes sont à vérifier."}
                    {d.delais.some(
                      (r) => r.libelle.includes("ministre") && r.paires_valides > 0 && r.p90_jours === 0,
                    ) &&
                      " Les visas CF et ministre sont datés du même jour sur les paires observées ; vérifier la signification des horodatages."}
                  </p>
                </Carte>
              </Zone>
            )}
            {parties.includes("avances") && (
              <Zone titre="Avances et régies">
                <BandeauKpi colonnes={3}>
                  <KpiCard
                    libelle="Avances APAD enregistrées"
                    valeur={<Montant gnf={d.apad.avance_demarrage} />}
                    contexte={
                      d.apad.renseigne
                        ? `${nombre(d.apad.nb_lignes)} lignes de détail APAD`
                        : "Détail APAD non fourni pour cette situation"
                    }
                  />
                  <KpiCard
                    libelle="Écart APAD / situation"
                    valeur={<Montant gnf={d.apad.ecart} />}
                    contexte="Détail APAD moins avances de la situation courante"
                  />
                  <KpiCard
                    libelle="Régies enregistrées"
                    valeur={<Montant gnf={d.regies.montant_regie} />}
                    contexte={
                      d.regies.nb_lignes == null
                        ? "Détail des régies non fourni"
                        : `${nombre(d.regies.nb_lignes)} lignes reçues`
                    }
                  />
                </BandeauKpi>
                <Note>
                  Ces montants ne s'ajoutent pas aux dépenses payées. Le paiement, la justification et
                  l'apurement des avances ou régies doivent être établis séparément.
                </Note>
                {d.apad.ministeres.length > 0 && (
                  <Carte
                    titre="APAD par ministère et institution"
                    sousTitre="Avances enregistrées, sans présumer leur paiement"
                  >
                    <DataTable
                      donnees={d.apad.ministeres}
                      libelle="APAD par ministère"
                      nomExport="apad-ministeres"
                      colonnes={[
                        { accessorKey: "libelle", header: "Ministère ou institution" },
                        {
                          accessorKey: "montant",
                          header: "Avances enregistrées",
                          cell: ({ row }) => <Montant gnf={row.original.montant} />,
                          meta: { numerique: true },
                        },
                      ]}
                    />
                  </Carte>
                )}
              </Zone>
            )}
            {parties.includes("concordance") && (
              <Zone titre="Concordance des montants">
                <Carte
                  titre="Situation budgétaire et détail des engagements"
                  sousTitre="Comparaison sur les codes d'imputation communs, programme et nature de flux lorsqu'ils sont renseignés"
                >
                  <DataTable
                    donnees={d.rapprochements}
                    recherche={false}
                    libelle="Rapprochement des phases"
                    nomExport="rapprochements-depenses"
                    colonnes={[
                      { accessorKey: "libelle", header: "Phase" },
                      {
                        accessorKey: "reference",
                        header: "Situation",
                        cell: ({ row }) => <Montant gnf={row.original.reference} />,
                        meta: { numerique: true },
                      },
                      {
                        accessorKey: "detail_comparable",
                        header: "Détail comparable",
                        cell: ({ row }) => <Montant gnf={row.original.detail_comparable} />,
                        meta: { numerique: true },
                      },
                      {
                        accessorKey: "ecart",
                        header: "Écart situation − détail",
                        cell: ({ row }) => <Montant gnf={row.original.ecart} />,
                        meta: { numerique: true },
                      },
                      {
                        accessorKey: "cles_en_ecart",
                        header: "Contrôle",
                        cell: ({ row }) =>
                          row.original.cles_en_ecart == null ? (
                            "Non renseigné"
                          ) : (
                            <StatusPill
                              etat={row.original.cles_en_ecart > 0 ? "vigilance" : "bon"}
                              libelle={
                                row.original.cles_en_ecart > 0
                                  ? `${nombre(row.original.cles_en_ecart)} clés en écart`
                                  : "Concordant"
                              }
                            />
                          ),
                      },
                    ]}
                  />
                  <p className="mt-3 text-sm text-ink-2">
                    Une égalité globale ne suffit pas : le contrôle vérifie aussi les écarts par imputation.
                    Les exclusions de dossiers abandonnés et de dégagements s'appliquent uniquement à l'engagé
                    lorsqu'elles ont été validées à l'import. Les autres phases utilisent le détail brut reçu.
                  </p>
                </Carte>
              </Zone>
            )}
          </div>
        );
      }}
    </EtatBloc>
  );
}
