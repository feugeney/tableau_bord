import { useDonnees } from "@/api/hooks";
import type { Meta } from "@/api/types";
import { DataTable } from "@/components/DataTable";
import { GroupedBarChart } from "@/components/GroupedBarChart";
import { BandeauKpi, KpiCard, Note } from "@/components/Indicateurs";
import { Montant } from "@/components/Montant";
import { SourceBadge } from "@/components/Source";
import { Carte } from "@/components/ui/primitives";
import { dateFr, enMds, nombre } from "@/lib/format";

import { EtatPage, TitrePage, Zone } from "../commun";
import { ContenuPrevu, serieMois } from "./commun";

interface LigneTofe {
  poste: string;
  sens: "recette" | "financement" | "depense";
  meta: Meta;
  donnees: number | null;
}

interface Donnees {
  indicateurs: {
    encaissements: number;
    decaissements: number;
    solde: number;
    jour_solde: string | null;
    jours_de_decaissements: number | null;
    sous_seuil: boolean;
    delai_moyen_paiement: number | null;
  };
  flux_mensuels: { mois: number; encaissements: number; decaissements: number }[];
  solde_mensuel: { mois: number; solde: number }[];
  seuil: { valeur: number; mois: number };
  tofe: LigneTofe[];
}

const SENS = { recette: "Recettes", financement: "Financement", depense: "Dépenses" };

export default function Tresorerie() {
  const r = useDonnees<Donnees>("/tresor/");
  return (
    <>
      <TitrePage exporter="tresorerie" titre="Trésorerie" sousTitre="SCIE · Trésor public" />
      <EtatPage
        requete={r}
        vide={<ContenuPrevu cle="tresorerie" />}
        indicateurs={4}
        precisionDemo="Les dépenses du tableau des opérations financières viennent de la Chaîne Dépense (réel)."
      >
        {(d, env) => {
          const i = d.indicateurs;
          return (
            <div className="flex flex-col gap-6">
              <Zone titre="Indicateurs clés">
                <BandeauKpi colonnes={4}>
                  <KpiCard
                    libelle="Encaissements"
                    valeur={<Montant gnf={i.encaissements} />}
                    contexte="Depuis le début de l'exercice"
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle="Décaissements"
                    valeur={<Montant gnf={i.decaissements} />}
                    contexte="Depuis le début de l'exercice"
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle="Solde de fin de période"
                    valeur={<Montant gnf={i.solde} />}
                    contexte={`${nombre(i.jours_de_decaissements)} jours de décaissements · au ${dateFr(i.jour_solde)}`}
                    jauge={{ valeur: (i.jours_de_decaissements ?? 0) / 60, repere: 30 / 60 }}
                    etat={i.sous_seuil ? "critique" : undefined}
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle="Délai moyen de paiement"
                    valeur={
                      <span className="chiffres">
                        {nombre(i.delai_moyen_paiement)}{" "}
                        <span className="text-sm font-normal text-ink-3">jours</span>
                      </span>
                    }
                    contexte="Du mandat au paiement"
                    meta={env.meta}
                  />
                </BandeauKpi>
                <p className="text-sm text-ink-2">
                  Jauge du solde : 60 jours au maximum ; le trait marque le seuil d'un mois de décaissements.
                </p>
              </Zone>

              <Zone titre="Analyses">
                <div className="grid gap-4 lg:grid-cols-2">
                  <Carte id="flux" titre="Flux mensuels" sousTitre="En milliards de GNF">
                    <GroupedBarChart
                      libelle="Encaissements et décaissements mensuels"
                      donnees={serieMois(env.meta.exercice, d.flux_mensuels, [
                        "encaissements",
                        "decaissements",
                      ])}
                      categorie="libelle"
                      series={[
                        { cle: "encaissements", libelle: "Encaissements", couleur: "var(--serie-1)" },
                        { cle: "decaissements", libelle: "Décaissements", couleur: "var(--serie-2)" },
                      ]}
                    />
                  </Carte>
                  <Carte id="solde" titre="Solde de fin de mois" sousTitre="En milliards de GNF">
                    <GroupedBarChart
                      libelle="Solde de trésorerie de fin de mois"
                      donnees={serieMois(env.meta.exercice, d.solde_mensuel, ["solde"])}
                      categorie="libelle"
                      series={[{ cle: "solde", libelle: "Solde", couleur: "var(--phase-4)" }]}
                      seuil={{ valeur: enMds(d.seuil.valeur), libelle: "Seuil : 1 mois de décaissements" }}
                    />
                    {i.sous_seuil && (
                      <Note etat="critique">Le solde est inférieur à un mois de décaissements moyens.</Note>
                    )}
                  </Carte>
                </div>
              </Zone>

              <Zone titre="Détail">
                <Carte
                  id="tofe"
                  titre="Tableau des opérations financières (simplifié)"
                  sousTitre="La source de chaque ligne est indiquée : les recettes et le financement peuvent être illustratifs, les dépenses sont réelles."
                >
                  <DataTable
                    donnees={d.tofe}
                    recherche={false}
                    libelle="Tableau des opérations financières simplifié"
                    colonnes={[
                      {
                        header: "Rubrique",
                        id: "sens",
                        accessorFn: (l) => SENS[l.sens],
                        enableSorting: false,
                      },
                      { header: "Poste", accessorKey: "poste", enableSorting: false },
                      {
                        header: "Montant",
                        id: "montant",
                        accessorFn: (l) => l.donnees,
                        cell: ({ row }) => <Montant gnf={row.original.donnees} />,
                        meta: { numerique: true },
                        enableSorting: false,
                      },
                      {
                        header: "Source",
                        id: "source",
                        cell: ({ row }) => <SourceBadge meta={row.original.meta} />,
                        enableSorting: false,
                      },
                    ]}
                  />
                </Carte>
              </Zone>
            </div>
          );
        }}
      </EtatPage>
    </>
  );
}
