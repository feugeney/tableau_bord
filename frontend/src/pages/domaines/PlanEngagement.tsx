import { Check } from "lucide-react";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useDonnees } from "@/api/hooks";
import { HBarList } from "@/components/Barres";
import { DataTable, type Colonne } from "@/components/DataTable";
import { GroupedBarChart } from "@/components/GroupedBarChart";
import { BandeauKpi, Jauge, KpiCard, Note, StatusPill } from "@/components/Indicateurs";
import { Montant } from "@/components/Montant";
import { Carte, Segment } from "@/components/ui/primitives";
import { dateFr, enMds, mds, pct } from "@/lib/format";
import { cn } from "@/lib/utils";

import { EtatPage, Zone } from "../commun";

type Periode = "T1" | "T2" | "T3" | "T4";

interface LigneTitre {
  titre: string;
  libelle: string;
  plafond: number;
  engage_periode: number | null;
  taux: number | null;
  depassement?: boolean;
}

interface LigneSection {
  code: string;
  libelle: string;
  plafond: number;
  engage_periode: number | null;
  taux: number | null;
  marge: number | null;
  depassement: boolean;
  credit: number;
  engage_ouverture: number;
  titres: LigneTitre[];
}

interface Donnees {
  periode: Periode;
  libelle_periode: string;
  periodes: {
    code: Periode;
    libelle: string;
    etat_code: string;
    etat_libelle: string;
    courante: boolean;
    a_des_plafonds: boolean;
    plafond: number;
    engage_periode: number | null;
    taux: number | null;
  }[];
  entete: {
    etat_code: string;
    etat_libelle: string;
    reference_arrete: string;
    date_validation: string | null;
    date_ouverture: string | null;
    courante: boolean;
    montant_mobilisable: number | null;
    montant_imprevu: number | null;
    montant_obligatoire_titre2: number | null;
    montant_repartissable: number | null;
  };
  indicateurs: {
    plafond: number;
    engage_periode: number | null;
    taux: number | null;
    marge: number | null;
    credit: number;
    engage_ouverture: number;
    nb_sections: number;
    nb_depassements: number;
  };
  methode_engage: { code: string | null; libelle: string };
  titres: LigneTitre[];
  sections: LigneSection[];
  ajustements: {
    section_source: string;
    libelle_source: string;
    titre_source: string;
    section_destination: string;
    libelle_destination: string;
    titre_destination: string;
    montant: number;
    observation: string;
    date: string | null;
  }[];
  circuit: { code: string; libelle: string; description: string; atteint: boolean }[];
  references: { titre: string; usage: string }[];
}

const PERIODES: Periode[] = ["T1", "T2", "T3", "T4"];

export default function PlanEngagement() {
  const [params, setParams] = useSearchParams();
  const demandee = params.get("periode");
  const periode = PERIODES.includes(demandee as Periode) ? (demandee as Periode) : undefined;
  const r = useDonnees<Donnees>("/pilotage/plan-engagement/", { periode });
  const [section, setSection] = useState<string | null>(null);

  function choisirPeriode(p: Periode) {
    setSection(null);
    setParams(
      (avant) => {
        const suivant = new URLSearchParams(avant);
        suivant.set("periode", p);
        return suivant;
      },
      { replace: true },
    );
  }

  return (
    <EtatPage
      requete={r}
      indicateurs={4}
      vide={
        <p className="text-base text-ink-2">
          Aucun plan d'engagement chargé. Il provient de la Chaîne Dépense (tables GDEP.TD_PLAN_ENG*) et se
          charge par la commande <code>import_plan_engagement</code>.
        </p>
      }
    >
      {(d, env) => {
        const i = d.indicateurs;
        const e = d.entete;
        const sansPlafond = i.plafond === 0;
        const choisie = d.sections.find((s) => s.code === section) ?? null;
        const depasse = i.taux !== null && i.taux > 1;
        return (
          <div className="flex flex-col gap-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-ink-2">
                Exercice {env.meta.exercice} · extrait de la Chaîne Dépense le{" "}
                {dateFr(env.meta.date_situation)} · montants en milliards de GNF.
              </p>
              <Segment<Periode>
                libelle="Trimestre du plan d'engagement"
                valeur={d.periode}
                options={d.periodes.map((p) => ({
                  valeur: p.code,
                  libelle: `${p.code}${p.courante ? " · en cours" : ""}`,
                }))}
                onChange={choisirPeriode}
              />
            </div>

            <Carte
              id="plan-etat"
              titre={`Plan d'engagement du ${d.libelle_periode} ${env.meta.exercice}`}
              sousTitre={
                <>
                  {e.reference_arrete ? `Arrêté ${e.reference_arrete}` : "Arrêté non référencé"}
                  {e.date_validation ? ` · validé le ${dateFr(e.date_validation)}` : ""}
                  {e.date_ouverture ? ` · trimestre ouvert le ${dateFr(e.date_ouverture)}` : ""}
                </>
              }
              actions={
                <StatusPill etat={e.etat_code === "PE6" ? "bon" : "vigilance"} libelle={e.etat_libelle} />
              }
            >
              <ol
                className="grid gap-2 sm:grid-cols-2 lg:grid-cols-7"
                aria-label="Circuit de validation du plan"
              >
                {d.circuit.map((c, n) => (
                  <li
                    key={c.code}
                    className={cn(
                      "flex flex-col gap-1 rounded-sm border p-2 text-sm",
                      c.atteint ? "border-gold bg-gold-tint text-ink" : "border-border text-ink-2",
                    )}
                    title={c.description}
                  >
                    <span className="flex items-center gap-1.5 font-bold">
                      {c.atteint ? (
                        <Check className="h-4 w-4 shrink-0" aria-hidden />
                      ) : (
                        <span aria-hidden className="w-4 text-center">
                          {n + 1}
                        </span>
                      )}
                      {c.libelle}
                    </span>
                    <span className="text-xs text-ink-2">{c.description}</span>
                    <span className="sr-only">{c.atteint ? "étape franchie" : "étape non franchie"}</span>
                  </li>
                ))}
              </ol>
            </Carte>

            <Zone titre="Vue d'ensemble du trimestre">
              <BandeauKpi colonnes={4}>
                <KpiCard
                  libelle="Enveloppe mobilisable"
                  valeur={e.montant_mobilisable === null ? "—" : <Montant gnf={e.montant_mobilisable} />}
                  contexte={`Imprévus ${mds(e.montant_imprevu)} · dépenses obligatoires de personnel ${mds(e.montant_obligatoire_titre2)}`}
                  aide="Montant que la trésorerie permet d'engager sur le trimestre, fixé au paramétrage du plan."
                  meta={env.meta}
                />
                <KpiCard
                  libelle="Plafonds d'engagement"
                  valeur={<Montant gnf={i.plafond} />}
                  contexte={`${i.nb_sections} ministères et institutions · répartis par titre`}
                  aide="Montant répartissable de chaque section et titre : les régulations du trimestre ne peuvent pas le dépasser."
                  meta={env.meta}
                />
                <KpiCard
                  libelle="Engagé du trimestre"
                  valeur={i.engage_periode === null ? "—" : <Montant gnf={i.engage_periode} />}
                  contexte={
                    i.engage_periode === null
                      ? "Non disponible pour ce trimestre"
                      : `Engagé visé CF · à l'ouverture : ${mds(i.engage_ouverture)}`
                  }
                  aide={d.methode_engage.libelle}
                  meta={env.meta}
                />
                <KpiCard
                  libelle="Consommation des plafonds"
                  valeur={pct(i.taux)}
                  contexte={
                    i.marge === null
                      ? "Calculée dès que l'engagé du trimestre est connu"
                      : i.marge >= 0
                        ? `Marge restante : ${mds(i.marge)}`
                        : `Dépassement global : ${mds(-i.marge)}`
                  }
                  jauge={{ valeur: i.taux, repere: 1, etat: depasse ? "serieux" : undefined }}
                  etat={depasse ? "serieux" : i.nb_depassements ? "vigilance" : undefined}
                  meta={env.meta}
                />
              </BandeauKpi>
              {sansPlafond ? (
                <Note etat="vigilance">
                  Les plafonds de ce trimestre ne sont pas encore générés : le plan est au stade «
                  {e.etat_libelle} ». Choisissez un autre trimestre ou un autre exercice.
                </Note>
              ) : (
                <Note etat={i.nb_depassements ? "vigilance" : undefined}>
                  {d.methode_engage.libelle}.{" "}
                  {i.engage_periode !== null &&
                    `${i.nb_depassements} ministère(s) dépassent le plafond d'au moins un titre. Lecture indicative : les deux ouvertures ne coïncident pas toujours avec les bornes du trimestre.`}
                </Note>
              )}
            </Zone>

            {!sansPlafond && (
              <Zone titre="Plafonds et engagé">
                <div className="grid gap-4 lg:grid-cols-2">
                  <Carte
                    id="plan-titres"
                    titre="Par nature économique (titre)"
                    sousTitre={
                      i.engage_periode === null
                        ? "Plafond du trimestre"
                        : "Barre : engagé du trimestre · trait : plafond"
                    }
                  >
                    <HBarList
                      seuil={null}
                      reference="du plafond"
                      lignes={d.titres.map((t) => ({
                        cle: t.titre,
                        libelle: `${t.titre} · ${t.libelle}`,
                        valeur: t.engage_periode ?? t.plafond,
                        objectif: t.engage_periode === null ? null : t.plafond,
                        complement: t.engage_periode === null ? undefined : `Plafond ${mds(t.plafond)}`,
                      }))}
                    />
                  </Carte>
                  <Carte
                    id="plan-trimestres"
                    titre="Trimestres de l'exercice"
                    sousTitre="Plafond et engagé de chaque trimestre ouvert"
                  >
                    <GroupedBarChart
                      libelle="Plafonds et engagé par trimestre"
                      donnees={d.periodes.map((p) => ({
                        libelle: `${p.code} · ${p.etat_libelle}`,
                        plafond: enMds(p.plafond),
                        engage: p.engage_periode === null ? 0 : enMds(p.engage_periode),
                      }))}
                      categorie="libelle"
                      series={[
                        { cle: "plafond", libelle: "Plafond", couleur: "var(--serie-1)" },
                        { cle: "engage", libelle: "Engagé du trimestre", couleur: "var(--serie-2)" },
                      ]}
                    />
                  </Carte>
                </div>
              </Zone>
            )}

            {!sansPlafond && (
              <Carte
                id="plan-sections"
                titre="Plafonds par ministère et institution"
                sousTitre="Cliquer sur une ligne pour le détail par titre · dépassement apprécié par titre"
              >
                <DataTable
                  donnees={d.sections}
                  colonnes={COLONNES}
                  libelle="Plafonds du plan d'engagement par ministère"
                  onLigne={(l) => setSection(l.code === section ? null : l.code)}
                  ligneActive={(l) => l.code === section}
                  nomExport={`plan-engagement-${env.meta.exercice}-${d.periode}`}
                  triInitial={[{ id: "plafond", desc: true }]}
                />
                {choisie && (
                  <div className="mt-4 border-t border-border pt-3">
                    <h3 className="text-base font-bold text-ink">{choisie.libelle}</h3>
                    <table className="mt-2 w-full text-sm">
                      <caption className="sr-only">Plafond et engagé par titre de {choisie.libelle}</caption>
                      <thead>
                        <tr className="border-b border-border text-ink-2">
                          <th scope="col" className="py-1 text-left">
                            Titre
                          </th>
                          <th scope="col" className="py-1 text-right">
                            Plafond
                          </th>
                          <th scope="col" className="py-1 text-right">
                            Engagé du trimestre
                          </th>
                          <th scope="col" className="py-1 text-right">
                            Consommation
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {choisie.titres.map((t) => (
                          <tr key={t.titre} className="border-b border-border text-ink">
                            <th scope="row" className="py-1 text-left font-normal">
                              {t.titre} · {t.libelle}
                            </th>
                            <td className="chiffres py-1 text-right">
                              <Montant gnf={t.plafond} />
                            </td>
                            <td className="chiffres py-1 text-right">
                              {t.engage_periode === null ? "—" : <Montant gnf={t.engage_periode} />}
                            </td>
                            <td className="chiffres py-1 text-right">
                              {pct(t.taux)}
                              {t.depassement && (
                                <span className="ml-2">
                                  <StatusPill etat="serieux" libelle="Dépassement" />
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Carte>
            )}

            {d.ajustements.length > 0 && (
              <Carte
                id="plan-ajustements"
                titre="Ajustements de plafonds"
                sousTitre="Virements de plafond entre ministères ou titres, avec leur motif"
              >
                <ul className="divide-y divide-border">
                  {d.ajustements.map((a, n) => (
                    <li key={n} className="flex flex-wrap items-baseline justify-between gap-3 py-2 text-sm">
                      <span className="text-ink">
                        {a.libelle_source} (titre {a.titre_source}) → {a.libelle_destination} (titre{" "}
                        {a.titre_destination})
                        <span className="block text-ink-2">
                          {a.observation}
                          {a.date ? ` · ${dateFr(a.date)}` : ""}
                        </span>
                      </span>
                      <span className="chiffres font-bold text-ink">
                        <Montant gnf={a.montant} />
                      </span>
                    </li>
                  ))}
                </ul>
              </Carte>
            )}

            <Carte id="plan-methode" titre="Cadre et méthode">
              <p className="text-sm leading-relaxed text-ink-2">
                Le plan d'engagement régule chaque trimestre les engagements selon les possibilités de
                trésorerie. L'enveloppe mobilisable, diminuée des imprévus et des dépenses obligatoires, est
                répartie entre ministères et titres au prorata de leurs crédits disponibles. La Chaîne Dépense
                refuse toute régulation qui dépasserait le plafond du trimestre.
              </p>
              <ul className="mt-3 flex flex-col gap-2">
                {d.references.map((ref) => (
                  <li key={ref.titre} className="text-sm">
                    <span className="font-bold text-ink">{ref.titre}</span>
                    <span className="block text-ink-2">{ref.usage}</span>
                  </li>
                ))}
              </ul>
            </Carte>
          </div>
        );
      }}
    </EtatPage>
  );
}

const COLONNES: Colonne<LigneSection>[] = [
  {
    header: "Ministère / institution",
    id: "libelle",
    accessorFn: (s) => s.libelle,
    cell: ({ row }) => <span className="block min-w-[16rem]">{row.original.libelle}</span>,
  },
  {
    header: "Plafond",
    accessorKey: "plafond",
    cell: ({ getValue }) => <Montant gnf={getValue() as number} />,
    meta: { numerique: true, exporter: (s) => String(enMds(s.plafond)) },
  },
  {
    header: "Engagé du trimestre",
    accessorKey: "engage_periode",
    cell: ({ row }) =>
      row.original.engage_periode === null ? "—" : <Montant gnf={row.original.engage_periode} />,
    meta: {
      numerique: true,
      exporter: (s) => (s.engage_periode === null ? "" : String(enMds(s.engage_periode))),
    },
  },
  {
    header: "Consommation",
    accessorKey: "taux",
    cell: ({ row }) => (
      <span className="flex min-w-[8rem] flex-col gap-1">
        <span>
          {pct(row.original.taux)}
          {row.original.depassement && (
            <span className="ml-2">
              <StatusPill etat="serieux" libelle="Dépassement" />
            </span>
          )}
        </span>
        <Jauge
          valeur={row.original.taux}
          repere={1}
          etat={row.original.taux !== null && row.original.taux > 1 ? "serieux" : undefined}
          libelle={`Consommation du plafond ${row.original.libelle}`}
        />
      </span>
    ),
    meta: { numerique: true, exporter: (s) => String(s.taux ?? "") },
  },
  {
    header: "Marge",
    accessorKey: "marge",
    cell: ({ row }) => (row.original.marge === null ? "—" : <Montant gnf={row.original.marge} />),
    meta: { numerique: true, exporter: (s) => (s.marge === null ? "" : String(enMds(s.marge))) },
  },
  {
    header: "Crédits",
    accessorKey: "credit",
    cell: ({ getValue }) => <Montant gnf={getValue() as number} />,
    meta: { numerique: true, exporter: (s) => String(enMds(s.credit)) },
  },
];
