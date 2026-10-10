import { useDonnees } from "@/api/hooks";
import { HBarList } from "@/components/Barres";
import { DataTable } from "@/components/DataTable";
import { GroupedBarChart } from "@/components/GroupedBarChart";
import { BandeauKpi, KpiCard, StatusPill } from "@/components/Indicateurs";
import { Montant, Pourcentage } from "@/components/Montant";
import { SourceBadge } from "@/components/Source";
import { Carte } from "@/components/ui/primitives";
import { nombre } from "@/lib/format";

import { EtatPage, TitrePage, Zone } from "../commun";
import { ContenuBloc, ContenuPrevu, serieMois, type Bloc } from "./commun";

interface Fugas {
  mensuel: { mois: number; effectif: number; masse_brute: number; masse_nette: number }[];
  masse_mensuelle_moyenne: number | null;
  agents: number | null;
  cout_moyen: number | null;
  controles: { controle: string; libelle: string; nombre_agents: number; montant: number }[];
}

interface Donnees {
  credits: Bloc<{
    credit_actuel: number;
    part_budget: number | null;
    montant_ordonnance: number;
    taux_ordonnancement: number | null;
  }>;
  par_ministere: Bloc<
    { libelle: string; credit_actuel: number; credit_engage: number; montant_ordonnance: number }[]
  >;
  fugas: Bloc<Fugas>;
}

const ETAT_CONTROLE = { doublons: "serieux", sans_nif: "vigilance", sans_affectation: "vigilance" } as const;

export default function MasseSalariale() {
  const r = useDonnees<Donnees>("/paie/");
  return (
    <>
      <TitrePage
        exporter="masse-salariale"
        titre="Masse salariale"
        sousTitre="Chaîne Dépense (titre 2) · FUGAS · Gestion de la paie"
      />
      <EtatPage
        requete={r}
        vide={<ContenuPrevu cle="masse-salariale" />}
        indicateurs={4}
        precisionDemo="Les crédits et l'ordonnancé de personnel viennent de la Chaîne Dépense (réel)."
      >
        {(d) => {
          const f = d.fugas.donnees;
          return (
            <div className="flex flex-col gap-6">
              <Zone titre="Indicateurs clés">
                <BandeauKpi colonnes={4}>
                  <KpiCard
                    libelle="Crédits de personnel"
                    valeur={<Montant gnf={d.credits.donnees?.credit_actuel} />}
                    contexte={
                      <>
                        <Pourcentage ratio={d.credits.donnees?.part_budget} /> du budget
                      </>
                    }
                    meta={d.credits.meta}
                  />
                  <KpiCard
                    libelle="Ordonnancé"
                    valeur={<Montant gnf={d.credits.donnees?.montant_ordonnance} />}
                    contexte={
                      <>
                        <Pourcentage ratio={d.credits.donnees?.taux_ordonnancement} /> des crédits de
                        personnel
                      </>
                    }
                    jauge={{ valeur: d.credits.donnees?.taux_ordonnancement }}
                    meta={d.credits.meta}
                  />
                  <KpiCard
                    libelle="Masse mensuelle moyenne"
                    valeur={<Montant gnf={f?.masse_mensuelle_moyenne} />}
                    contexte="Masse brute payée par mois"
                    meta={d.fugas.meta}
                  />
                  <KpiCard
                    libelle="Agents payés"
                    valeur={<span className="chiffres">{f ? nombre(f.agents) : "—"}</span>}
                    contexte={
                      f ? (
                        <>
                          Coût moyen : {nombre((f.cout_moyen ?? 0) / 1e6, 2)}{" "}
                          <span className="text-ink-3">millions GNF par mois</span>
                        </>
                      ) : (
                        "Source non raccordée"
                      )
                    }
                    meta={d.fugas.meta}
                  />
                </BandeauKpi>
              </Zone>

              <Zone titre="Points d'attention">
                <Carte id="controles" titre="Contrôles de paie" actions={<SourceBadge meta={d.fugas.meta} />}>
                  <ContenuBloc bloc={d.fugas}>
                    {(p) => (
                      <DataTable
                        donnees={p.controles}
                        recherche={false}
                        libelle="Contrôles de paie"
                        colonnes={[
                          {
                            header: "Contrôle",
                            id: "libelle",
                            accessorFn: (c) => c.libelle,
                            cell: ({ row }) => {
                              const etat = ETAT_CONTROLE[row.original.controle as keyof typeof ETAT_CONTROLE];
                              return etat && row.original.nombre_agents ? (
                                <StatusPill etat={etat} libelle={row.original.libelle} />
                              ) : (
                                row.original.libelle
                              );
                            },
                          },
                          {
                            header: "Agents",
                            accessorKey: "nombre_agents",
                            cell: ({ getValue }) => nombre(getValue() as number),
                            meta: { numerique: true },
                          },
                          {
                            header: "Montant mensuel",
                            accessorKey: "montant",
                            cell: ({ getValue }) => <Montant gnf={getValue() as number} />,
                            meta: { numerique: true },
                          },
                        ]}
                      />
                    )}
                  </ContenuBloc>
                </Carte>
              </Zone>

              <Zone titre="Analyses">
                <div className="grid gap-4 lg:grid-cols-2">
                  <Carte
                    id="par-ministere"
                    titre="Dépenses de personnel par ministère"
                    sousTitre="Barre : ordonnancé · trait : crédits de personnel"
                    actions={<SourceBadge meta={d.par_ministere.meta} />}
                  >
                    <ContenuBloc bloc={d.par_ministere}>
                      {(lignes) => (
                        <HBarList
                          lignes={lignes.map((m) => ({
                            libelle: m.libelle,
                            valeur: m.montant_ordonnance,
                            objectif: m.credit_actuel,
                          }))}
                          reference="des crédits ordonnancés"
                          retard="faible exécution"
                          seuil={0.5}
                        />
                      )}
                    </ContenuBloc>
                  </Carte>
                  <Carte
                    id="masse"
                    titre="Masse salariale mensuelle"
                    sousTitre="En milliards de GNF"
                    actions={<SourceBadge meta={d.fugas.meta} />}
                  >
                    <ContenuBloc bloc={d.fugas}>
                      {(p) => (
                        <GroupedBarChart
                          libelle="Masse salariale brute et nette par mois"
                          donnees={serieMois(d.fugas.meta.exercice, p.mensuel, [
                            "masse_brute",
                            "masse_nette",
                          ])}
                          categorie="libelle"
                          series={[
                            { cle: "masse_brute", libelle: "Masse brute", couleur: "var(--serie-1)" },
                            { cle: "masse_nette", libelle: "Masse nette", couleur: "var(--serie-2)" },
                          ]}
                        />
                      )}
                    </ContenuBloc>
                  </Carte>
                </div>
              </Zone>
            </div>
          );
        }}
      </EtatPage>
    </>
  );
}
