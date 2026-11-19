import { useDonnees } from "@/api/hooks";
import { HBarList } from "@/components/Barres";
import { GroupedBarChart } from "@/components/GroupedBarChart";
import { BandeauKpi, KpiCard } from "@/components/Indicateurs";
import { Montant, Pourcentage } from "@/components/Montant";
import { Carte } from "@/components/ui/primitives";
import { enMds, pct } from "@/lib/format";

import { EtatPage, TitrePage, Zone } from "../commun";
import { ContenuPrevu, type Bloc } from "./commun";

interface Donnees {
  indicateurs: {
    encours: number;
    exterieure: number;
    interieure: number;
    pib: number | null;
    ratio: number | null;
    seuil: number;
    depasse: boolean;
  };
  interets_engages: Bloc<number>;
  composition: { libelle: string; encours: number }[];
  echeancier: { annee: number; principal: number; interets: number }[];
}

export default function DettePublique() {
  const r = useDonnees<Donnees>("/dette/");
  return (
    <>
      <TitrePage exporter="dette-publique" titre="Dette publique" sousTitre="SIGAD · Direction de la dette" />
      <EtatPage
        requete={r}
        vide={<ContenuPrevu cle="dette-publique" />}
        indicateurs={4}
        precisionDemo="Le service de la dette engagé vient de la Chaîne Dépense (réel)."
      >
        {(d, env) => {
          const i = d.indicateurs;
          return (
            <div className="flex flex-col gap-6">
              <Zone titre="Indicateurs clés">
                <BandeauKpi colonnes={4}>
                  <KpiCard
                    libelle="Encours total"
                    valeur={<Montant gnf={i.encours} />}
                    contexte={
                      <>
                        <Pourcentage ratio={i.ratio} /> du PIB · seuil CEDEAO {pct(i.seuil)}
                      </>
                    }
                    jauge={{ valeur: i.ratio, repere: i.seuil }}
                    etat={i.depasse ? "critique" : undefined}
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle="Dette extérieure"
                    valeur={<Montant gnf={i.exterieure} />}
                    contexte={`${pct(i.encours ? i.exterieure / i.encours : null)} de l'encours`}
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle="Dette intérieure"
                    valeur={<Montant gnf={i.interieure} />}
                    contexte={`${pct(i.encours ? i.interieure / i.encours : null)} de l'encours`}
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle="Service de la dette engagé"
                    valeur={<Montant gnf={d.interets_engages.donnees} />}
                    contexte="Chaîne Dépense, titre 1 (dette), engagé de l'exercice"
                    meta={d.interets_engages.meta}
                  />
                </BandeauKpi>
                <p className="text-sm text-ink-2">
                  Jauge : ratio dette / PIB ; le trait marque le seuil de convergence CEDEAO.
                </p>
              </Zone>
              <Zone titre="Analyses">
                <div className="grid gap-4 lg:grid-cols-2">
                  <Carte id="composition" titre="Composition de l'encours par type de créancier">
                    <HBarList
                      lignes={d.composition.map((c) => ({ libelle: c.libelle, valeur: c.encours }))}
                    />
                  </Carte>
                  <Carte
                    id="echeancier"
                    titre="Échéancier du service de la dette"
                    sousTitre="Cinq prochaines années, en milliards de GNF"
                  >
                    <GroupedBarChart
                      libelle="Échéancier du service de la dette sur cinq ans"
                      donnees={d.echeancier.map((e) => ({
                        libelle: String(e.annee),
                        principal: enMds(e.principal),
                        interets: enMds(e.interets),
                      }))}
                      categorie="libelle"
                      series={[
                        { cle: "principal", libelle: "Principal", couleur: "var(--serie-1)" },
                        { cle: "interets", libelle: "Intérêts", couleur: "var(--serie-2)" },
                      ]}
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
