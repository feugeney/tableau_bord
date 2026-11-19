import { useDonnees } from "@/api/hooks";
import { GroupedBarChart } from "@/components/GroupedBarChart";
import { BandeauKpi, KpiCard } from "@/components/Indicateurs";
import { Montant } from "@/components/Montant";
import { Carte } from "@/components/ui/primitives";
import { dateFr, enMds, mds, moisCourt, nombre, pct } from "@/lib/format";
import { cn } from "@/lib/utils";

import { EtatPage, Zone } from "../commun";
import { ContenuPrevu } from "./commun";

interface Ligne {
  code: string;
  libelle: string;
  niveau: number;
  agregat: boolean;
  lfi: number;
  lfr: number;
  objectif_cumule: number;
  realise: number;
  realise_n1: number;
  ecart: number;
  taux: number | null;
}

interface Donnees {
  indicateurs: {
    recettes_dons: number;
    depenses: number;
    solde_global: number;
    solde_primaire: number;
    solde_caisse: number;
    besoin_financement: number;
    financement: number;
    ecart_financement: number;
    pib: number;
    ratio_solde_pib: number | null;
    pression_fiscale: number | null;
    taux_recettes: number | null;
    taux_depenses: number | null;
  };
  lignes: Ligne[];
  mensuel: { mois: string; recettes_dons: number; depenses: number; solde_global: number }[];
  verifications: { libelle: string; ecart: number; reussi: boolean }[];
  references: { titre: string; url: string; usage: string }[];
  perimetre: string;
  methode: string;
}

const COLONNES: {
  cle: keyof Pick<Ligne, "lfi" | "lfr" | "objectif_cumule" | "realise" | "realise_n1" | "ecart">;
  libelle: string;
}[] = [
  { cle: "lfi", libelle: "LFI annuelle simulée" },
  { cle: "lfr", libelle: "LFR annuelle simulée" },
  { cle: "objectif_cumule", libelle: "Prévision cumulée" },
  { cle: "realise", libelle: "Réalisé cumulé fictif" },
  { cle: "realise_n1", libelle: "N−1 à période équivalente" },
  { cle: "ecart", libelle: "Écart au prévu cumulé" },
];

/** Contenu du TOFE, affiché dans la page Pilotage (l'en-tête et l'export sont portés par Pilotage). */
export default function Tofe() {
  const r = useDonnees<Donnees>("/tofe/");
  return (
    <>
      <EtatPage
        requete={r}
        vide={<ContenuPrevu cle="tofe" />}
        indicateurs={4}
        precisionDemo="Scénario autonome : les budgets, réalisations et le PIB sont tous fictifs, sans reprise des chiffres réels des autres onglets."
      >
        {(d, env) => {
          const i = d.indicateurs;
          return (
            <div className="flex flex-col gap-6">
              <p className="text-sm text-ink-2">
                Exercice {env.meta.exercice} · cumul au {dateFr(env.meta.date_situation)} · montants en
                milliards de GNF. Les références officielles servent à structurer le tableau ; elles ne sont
                pas la source des montants simulés.
              </p>
              <Zone titre="Vue d'ensemble · illustration">
                <BandeauKpi colonnes={4}>
                  <KpiCard
                    libelle="Recettes et dons"
                    valeur={<Montant gnf={i.recettes_dons} />}
                    contexte={`${pct(i.taux_recettes)} de la prévision cumulée simulée`}
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle="Dépenses totales"
                    valeur={<Montant gnf={i.depenses} />}
                    contexte="Charges et acquisition nette d'actifs non financiers"
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle="Solde global · dons compris"
                    valeur={<Montant gnf={i.solde_global} />}
                    contexte={`${nombre(i.ratio_solde_pib == null ? null : i.ratio_solde_pib * 100, 2)} % du PIB annuel fictif · négatif = déficit`}
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle="Financement net"
                    valeur={<Montant gnf={i.financement} />}
                    contexte={`Besoin résiduel : ${mds(i.ecart_financement)}`}
                    meta={env.meta}
                  />
                </BandeauKpi>
              </Zone>

              <Zone titre="Équilibre et trajectoire">
                <div className="grid gap-4 lg:grid-cols-2">
                  <Carte
                    id="tofe-trajectoire"
                    titre="Recettes et dépenses mensuelles"
                    sousTitre="Flux du scénario · le dernier mois peut être partiel"
                  >
                    <GroupedBarChart
                      libelle="TOFE fictif : recettes et dépenses par mois"
                      donnees={d.mensuel.map((m) => ({
                        libelle: moisCourt(m.mois),
                        recettes: enMds(m.recettes_dons),
                        depenses: enMds(m.depenses),
                      }))}
                      categorie="libelle"
                      series={[
                        { cle: "recettes", libelle: "Recettes et dons", couleur: "var(--serie-1)" },
                        { cle: "depenses", libelle: "Dépenses", couleur: "var(--serie-2)" },
                      ]}
                    />
                  </Carte>
                  <Carte
                    id="tofe-equilibre"
                    titre="Du solde budgétaire au financement"
                    sousTitre="Convention : un financement positif est une ressource nette"
                  >
                    <dl className="divide-y divide-border">
                      {[
                        ["Solde global, dons compris", i.solde_global],
                        ["Solde primaire, hors intérêts", i.solde_primaire],
                        ["Solde base caisse simplifié", i.solde_caisse],
                        ["Besoin (+) / capacité (−) de financement", i.besoin_financement],
                        ["Financement net mobilisé", i.financement],
                        ["Besoin résiduel non financé", i.ecart_financement],
                      ].map(([libelle, valeur]) => (
                        <div key={libelle} className="flex items-baseline justify-between gap-4 py-2">
                          <dt className="text-sm text-ink-2">{libelle}</dt>
                          <dd className="chiffres whitespace-nowrap font-bold text-ink">
                            <Montant gnf={Number(valeur)} />
                          </dd>
                        </div>
                      ))}
                    </dl>
                  </Carte>
                </div>
              </Zone>

              <Carte
                id="tofe-detail"
                titre="TOFE détaillé · scénario fictif"
                sousTitre="Mds GNF · les sous-totaux sont calculés à partir des rubriques détaillées, sans double comptage"
              >
                <p className="mb-2 text-xs text-ink-2 md:hidden">
                  Faites défiler le tableau horizontalement pour comparer les montants.
                </p>
                <div
                  className="overflow-x-auto"
                  tabIndex={0}
                  role="region"
                  aria-label="Tableau TOFE défilant horizontalement"
                >
                  <table className="w-full min-w-[1160px] border-collapse text-sm">
                    <caption className="sr-only">
                      TOFE d'illustration en milliards de francs guinéens : budgets annuels simulés et cumuls
                      à la date de situation.
                    </caption>
                    <thead>
                      <tr className="border-b border-border bg-zebra text-ink-2">
                        <th
                          scope="col"
                          className="sticky left-0 z-10 w-44 min-w-44 max-w-44 bg-surface p-3 text-left md:w-80 md:min-w-80 md:max-w-80"
                        >
                          Rubrique
                        </th>
                        {COLONNES.map((c) => (
                          <th key={c.cle} scope="col" className="min-w-28 p-3 text-right">
                            {c.libelle}
                          </th>
                        ))}
                        <th scope="col" className="p-3 text-right">
                          Réalisé / prévu cumulé
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {d.lignes.map((ligne) => (
                        <tr
                          key={ligne.code}
                          className={cn(
                            "border-b border-border text-ink",
                            ligne.agregat && "font-bold",
                            ligne.niveau === 0 && "border-t-2",
                          )}
                        >
                          <th
                            scope="row"
                            className={cn(
                              "sticky left-0 z-10 w-44 min-w-44 max-w-44 whitespace-normal bg-surface py-2 pr-3 text-left md:w-80 md:min-w-80 md:max-w-80",
                              ligne.niveau === 0 ? "pl-3" : ligne.niveau === 1 ? "pl-6" : "pl-10",
                            )}
                          >
                            {ligne.libelle}
                          </th>
                          {COLONNES.map((c) => (
                            <td key={c.cle} className="chiffres whitespace-nowrap px-3 py-2 text-right">
                              {nombre(enMds(ligne[c.cle]), 1)}
                            </td>
                          ))}
                          <td className="chiffres whitespace-nowrap px-3 py-2 text-right">
                            {pct(ligne.taux)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="mt-3 text-xs text-ink-2">
                  Les écarts sont signés (réalisé − prévision cumulée), sans jugement automatique de
                  performance. Aucun taux d'exécution n'est calculé sur les soldes ou le financement net.
                </p>
              </Carte>

              <Zone titre="Contrôles de cohérence du scénario">
                <ul className="grid gap-3 sm:grid-cols-2">
                  {d.verifications.map((v) => (
                    <li key={v.libelle} className="rounded border border-border bg-surface p-3">
                      <p className="text-sm font-bold text-ink">
                        {v.reussi ? "Vérifié" : "Écart à examiner"} · {v.libelle}
                      </p>
                      <p className="mt-1 text-xs text-ink-2">
                        Écart : {nombre(v.ecart, 2)} GNF. Ce contrôle porte sur la cohérence fictive, pas sur
                        une validation de données officielles.
                      </p>
                    </li>
                  ))}
                </ul>
              </Zone>

              <Carte id="tofe-cadre" titre="Cadre guinéen et méthode">
                <p className="text-sm font-bold text-ink">{d.perimetre}</p>
                <p className="mt-2 text-sm leading-relaxed text-ink-2">{d.methode}</p>
                <p className="mt-3 text-sm text-ink-2">
                  Le tableau distingue les recettes minières et non minières, les dons, les intérêts
                  intérieurs/extérieurs et l'investissement selon son financement. La BCRG figure au
                  financement intérieur ; le principal remboursé est séparé des intérêts.
                </p>
                <details className="mt-4 border-t border-border pt-3">
                  <summary className="cursor-pointer text-sm font-bold text-ink">
                    Références officielles consultées · structure et contexte
                  </summary>
                  <ul className="mt-3 flex flex-col gap-3">
                    {d.references.map((reference) => (
                      <li key={reference.url} className="text-sm">
                        <a
                          href={reference.url}
                          target="_blank"
                          rel="noreferrer"
                          className="font-bold text-navy underline dark:text-ink"
                        >
                          {reference.titre}
                        </a>
                        <p className="mt-1 text-ink-2">{reference.usage}</p>
                      </li>
                    ))}
                  </ul>
                </details>
              </Carte>
            </div>
          );
        }}
      </EtatPage>
    </>
  );
}
