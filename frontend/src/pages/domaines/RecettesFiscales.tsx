import { useDonnees } from "@/api/hooks";
import { HBarList } from "@/components/Barres";
import { GroupedBarChart } from "@/components/GroupedBarChart";
import { BandeauKpi, KpiCard } from "@/components/Indicateurs";
import { Montant, Pourcentage } from "@/components/Montant";
import { Carte } from "@/components/ui/primitives";
import { nombre, pct } from "@/lib/format";

import { EtatPage, TitrePage, Zone } from "../commun";
import { ContenuPrevu, serieMois, type LigneObjectif } from "./commun";

interface Donnees {
  indicateurs: {
    recouvre: number;
    objectif: number;
    taux: number | null;
    restes_a_recouvrer: number;
    contentieux: number;
    dossiers_contentieux: number;
    contribuables_actifs: number;
    taux_teledeclaration: number | null;
  };
  par_impot: (LigneObjectif & { en_retard: boolean })[];
  mensuel: { mois: number; objectif: number; recouvre: number }[];
  par_centre: LigneObjectif[];
  par_secteur: { libelle: string; recouvre: number }[];
  restes_par_anciennete: { libelle: string; montant: number }[];
  contentieux_par_stade: { libelle: string; montant: number; nombre_dossiers: number }[];
  seuil_retard: number;
}

export default function RecettesFiscales() {
  const r = useDonnees<Donnees>("/recettes-fiscales/");
  return (
    <>
      <TitrePage
        exporter="recettes-fiscales"
        titre="Recettes fiscales"
        sousTitre="SAFIG · Direction générale des impôts"
      />
      <EtatPage requete={r} vide={<ContenuPrevu cle="recettes-fiscales" />} indicateurs={4}>
        {(d, env) => {
          const i = d.indicateurs;
          const retard = d.par_impot.filter((x) => x.en_retard);
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
                    libelle="Restes à recouvrer"
                    valeur={<Montant gnf={i.restes_a_recouvrer} />}
                    contexte="Impositions émises non payées"
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle="Contentieux fiscal"
                    valeur={<Montant gnf={i.contentieux} />}
                    contexte={`${nombre(i.dossiers_contentieux)} dossiers en réclamation ou en recours`}
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle="Contribuables actifs"
                    valeur={<span className="chiffres">{nombre(i.contribuables_actifs)}</span>}
                    contexte={
                      <>
                        <Pourcentage ratio={i.taux_teledeclaration} /> de télédéclarations
                      </>
                    }
                    jauge={{ valeur: i.taux_teledeclaration }}
                    meta={env.meta}
                  />
                </BandeauKpi>
              </Zone>

              <Zone titre="Points d'attention">
                <Carte id="retards" titre="Impôts sous le seuil de recouvrement">
                  {retard.length ? (
                    <p className="text-base text-ink">
                      {retard.length} impôt{retard.length > 1 ? "s" : ""} sous {pct(d.seuil_retard)} de
                      l'objectif : {retard.map((x) => `${x.libelle} (${pct(x.taux)})`).join(", ")}.
                    </p>
                  ) : (
                    <p className="text-base text-ink-2">
                      Tous les impôts atteignent au moins {pct(d.seuil_retard)}.
                    </p>
                  )}
                </Carte>
              </Zone>

              <Zone titre="Analyses">
                <div className="grid gap-4 lg:grid-cols-2">
                  <Carte
                    id="par-impot"
                    titre="Recouvrement par impôt"
                    sousTitre="Barre : recouvré · trait : objectif de la période · orangé sous 80 %"
                  >
                    <HBarList
                      lignes={d.par_impot.map((x) => ({
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
                      libelle="Recouvrement mensuel face à l'objectif"
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

              <Zone titre="Détail">
                <div className="grid gap-4 lg:grid-cols-2">
                  <Carte id="centres" titre="Par centre de gestion">
                    <HBarList
                      lignes={d.par_centre.map((x) => ({
                        libelle: x.libelle,
                        valeur: x.recouvre,
                        objectif: x.objectif,
                      }))}
                      seuil={d.seuil_retard}
                    />
                  </Carte>
                  <Carte id="secteurs" titre="Par secteur d'activité">
                    <HBarList
                      lignes={d.par_secteur.map((x) => ({ libelle: x.libelle, valeur: x.recouvre }))}
                    />
                  </Carte>
                  <Carte id="restes" titre="Restes à recouvrer par ancienneté">
                    <HBarList
                      lignes={d.restes_par_anciennete.map((x) => ({ libelle: x.libelle, valeur: x.montant }))}
                    />
                  </Carte>
                  <Carte id="contentieux" titre="Contentieux par stade">
                    <HBarList
                      lignes={d.contentieux_par_stade.map((x) => ({
                        libelle: x.libelle,
                        valeur: x.montant,
                        complement: `${nombre(x.nombre_dossiers)} dossiers`,
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
