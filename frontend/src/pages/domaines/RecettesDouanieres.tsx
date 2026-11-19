import { useDonnees } from "@/api/hooks";
import { HBarList, Legende, StackedProgress } from "@/components/Barres";
import { DataTable } from "@/components/DataTable";
import { GroupedBarChart } from "@/components/GroupedBarChart";
import { BandeauKpi, KpiCard } from "@/components/Indicateurs";
import { Montant, Pourcentage } from "@/components/Montant";
import { BlocProjection, type Projection } from "@/components/Projection";
import { Carte } from "@/components/ui/primitives";
import { nombre, pct } from "@/lib/format";

import { EtatPage, Zone } from "../commun";
import { ContenuPrevu, serieMois, type LigneObjectif } from "./commun";

interface Donnees {
  indicateurs: {
    recouvre: number;
    objectif: number;
    taux: number | null;
    exonerations: number;
    part_exonerations: number | null;
    declarations: number;
    delai_moyen_jours: number | null;
  };
  par_nature: LigneObjectif[];
  mensuel: { mois: number; objectif: number; recouvre: number }[];
  /** Absente d'une réponse mise en cache avant l'ajout des projections. */
  projection?: Projection;
  par_bureau: LigneObjectif[];
  circuits: { circuit: "vert" | "jaune" | "rouge"; nombre: number; part: number | null }[];
  exonerations_par_regime: { libelle: string; montant: number }[];
  seuil_retard: number;
}

// Les circuits portent le nom d'une couleur, mais ne sont pas des états : rampe bleue neutre et libellés.
const CIRCUITS = {
  vert: { libelle: "Circuit vert (sans contrôle)", couleur: "var(--phase-2)" },
  jaune: { libelle: "Circuit jaune (contrôle documentaire)", couleur: "var(--phase-4)" },
  rouge: { libelle: "Circuit rouge (visite physique)", couleur: "var(--phase-6)" },
};

export default function RecettesDouanieres() {
  const r = useDonnees<Donnees>("/douanes/");
  return (
    <>
      <EtatPage requete={r} vide={<ContenuPrevu cle="recettes-douanieres" />} indicateurs={4}>
        {(d, env) => {
          const i = d.indicateurs;
          return (
            <div className="flex flex-col gap-6">
              <Zone titre="Indicateurs clés">
                <BandeauKpi colonnes={4}>
                  <KpiCard
                    libelle={`Recouvré en ${env.meta.exercice}`}
                    valeur={<Montant gnf={i.recouvre} />}
                    contexte={
                      <>
                        <Pourcentage ratio={i.taux} /> de l'objectif de la période (
                        <Montant gnf={i.objectif} />)
                      </>
                    }
                    jauge={{ valeur: i.taux, repere: d.seuil_retard }}
                    etat={i.taux !== null && i.taux < d.seuil_retard ? "serieux" : undefined}
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle="Exonérations"
                    valeur={<Montant gnf={i.exonerations} />}
                    contexte={`${pct(i.part_exonerations)} des droits liquidés`}
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle="Déclarations traitées"
                    valeur={<span className="chiffres">{nombre(i.declarations)}</span>}
                    contexte="Depuis le début de l'exercice"
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle="Délai moyen de dédouanement"
                    valeur={
                      <span className="chiffres">
                        {nombre(i.delai_moyen_jours, 1)}{" "}
                        <span className="text-sm font-normal text-ink-3">jours</span>
                      </span>
                    }
                    contexte="De l'enregistrement à la mainlevée"
                    meta={env.meta}
                  />
                </BandeauKpi>
              </Zone>

              <Zone titre="Analyses">
                <div className="grid gap-4 lg:grid-cols-2">
                  <Carte
                    id="par-nature"
                    titre="Recettes par nature de droit"
                    sousTitre="Barre : recouvré · trait : objectif de la période"
                  >
                    <HBarList
                      lignes={d.par_nature.map((x) => ({
                        libelle: x.libelle,
                        valeur: x.recouvre,
                        objectif: x.objectif,
                      }))}
                      seuil={d.seuil_retard}
                    />
                  </Carte>
                  <Carte
                    id="mensuel"
                    titre="Recouvrement mensuel"
                    sousTitre="En milliards de GNF, face à l'objectif"
                  >
                    <GroupedBarChart
                      libelle="Recouvrement douanier mensuel"
                      donnees={serieMois(env.meta.exercice, d.mensuel, ["objectif", "recouvre"])}
                      categorie="libelle"
                      series={[
                        { cle: "objectif", libelle: "Objectif", couleur: "var(--serie-2)" },
                        { cle: "recouvre", libelle: "Recouvré", couleur: "var(--serie-1)" },
                      ]}
                    />
                  </Carte>
                </div>
              </Zone>

              {d.projection && (
                <Zone titre="Projection">
                  <Carte
                    id="projection"
                    titre="Projection de fin d'exercice"
                    sousTitre="Recouvrement cumulé constaté, puis prolongé jusqu'au 31 décembre"
                  >
                    <BlocProjection
                      p={d.projection}
                      grandeur="recouvrés"
                      libelleCible="Objectif annuel"
                      libelleRealise="Recouvré (cumul)"
                    />
                  </Carte>
                </Zone>
              )}

              <Zone titre="Détail">
                <div className="grid gap-4 lg:grid-cols-2">
                  <Carte id="bureaux" titre="Recettes par bureau">
                    <HBarList
                      lignes={d.par_bureau.map((x) => ({
                        libelle: x.libelle,
                        valeur: x.recouvre,
                        objectif: x.objectif,
                      }))}
                      seuil={d.seuil_retard}
                    />
                  </Carte>
                  <Carte id="circuits" titre="Déclarations par circuit de contrôle">
                    <StackedProgress
                      libelle="Répartition des déclarations par circuit"
                      segments={d.circuits.map((c) => ({
                        code: c.circuit,
                        libelle: CIRCUITS[c.circuit].libelle,
                        valeur: c.nombre,
                        couleur: CIRCUITS[c.circuit].couleur,
                      }))}
                    />
                    <div className="mt-3">
                      <Legende elements={Object.values(CIRCUITS)} />
                    </div>
                    <DataTable
                      donnees={d.circuits}
                      recherche={false}
                      libelle="Déclarations par circuit"
                      colonnes={[
                        { header: "Circuit", id: "c", accessorFn: (c) => CIRCUITS[c.circuit].libelle },
                        {
                          header: "Déclarations",
                          accessorKey: "nombre",
                          cell: ({ getValue }) => nombre(getValue() as number),
                          meta: { numerique: true },
                        },
                        {
                          header: "Part",
                          accessorKey: "part",
                          cell: ({ getValue }) => pct(getValue() as number),
                          meta: { numerique: true },
                        },
                      ]}
                    />
                  </Carte>
                  <Carte id="exonerations" titre="Exonérations par régime" className="lg:col-span-2">
                    <HBarList
                      lignes={d.exonerations_par_regime.map((x) => ({
                        libelle: x.libelle,
                        valeur: x.montant,
                      }))}
                    />
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
