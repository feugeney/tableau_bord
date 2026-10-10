import { useQuery } from "@tanstack/react-query";
import { ChevronDown } from "lucide-react";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import { api } from "@/api/client";
import { useAlertes, useDonnees } from "@/api/hooks";
import type {
  Beneficiaires,
  Chaine,
  Controle,
  Enveloppe,
  IndicateursDepense,
  Mensuel,
  Nature,
  Procedure,
  RestesAPayer,
  SectionDetail,
  SectionLigne,
} from "@/api/types";
import { ListeAlertes } from "@/components/Alertes";
import { HBarList, Legende, PipelineBars, SEGMENTS_EXECUTION, StackedProgress } from "@/components/Barres";
import { DataTable, type Colonne } from "@/components/DataTable";
import { GroupedBarChart } from "@/components/GroupedBarChart";
import { BandeauKpi, Jauge, KpiCard, Note, StatusPill, type Etat } from "@/components/Indicateurs";
import { Montant, Pourcentage } from "@/components/Montant";
import { SourceBadge } from "@/components/Source";
import { Carte, Infobulle, Segment } from "@/components/ui/primitives";
import { Sheet } from "@/components/ui/sheet";
import { useFiltres, type ModePaiement, type Nature as TNature } from "@/hooks/useFiltres";
import { enMds, moisCourt, nombre, pct } from "@/lib/format";

import { EtatBloc, EtatPage, TitrePage, Zone } from "./commun";

const NATURES: { valeur: TNature; libelle: string }[] = [
  { valeur: "", libelle: "Toutes" },
  { valeur: "personnel", libelle: "Personnel" },
  { valeur: "biens_services", libelle: "Biens et services" },
  { valeur: "transferts", libelle: "Transferts" },
  { valeur: "investissement", libelle: "Investissement" },
  { valeur: "dette", libelle: "Dette" },
];
const TITRE_VERS_NATURE: Record<string, TNature> = {
  "1": "dette",
  "2": "personnel",
  "3": "biens_services",
  "4": "transferts",
  "5": "investissement",
};
const AIDE_PAIEMENT =
  "Paiements ajustés : les salaires (procédure Solde) et la dette (débit d'office) sont payés hors de la chaîne. " +
  "Ils sont exclus pour ne pas faire apparaître un faux reste à payer. « Bruts » les réintègre.";

export default function Depenses() {
  const { filtres, definir } = useFiltres();
  const indicateurs = useDonnees<IndicateursDepense>("/depense/indicateurs/");

  return (
    <>
      <TitrePage
        exporter="depenses"
        titre="Dépenses"
        sousTitre="Exécution du budget de l'État · Chaîne Dépense"
      >
        <Segment
          libelle="Nature de dépense"
          valeur={filtres.nature}
          options={NATURES}
          onChange={(v) => definir({ nature: v })}
        />
        <div className="flex items-center gap-1">
          <Segment<ModePaiement>
            libelle="Paiements"
            valeur={filtres.paiement}
            options={[
              { valeur: "ajuste", libelle: "Paiements ajustés" },
              { valeur: "brut", libelle: "Bruts" },
            ]}
            onChange={(v) => definir({ paiement: v })}
          />
          <Infobulle contenu={AIDE_PAIEMENT} />
        </div>
      </TitrePage>
      <EtatPage requete={indicateurs}>{(i, env) => <Contenu i={i} env={env} />}</EtatPage>
    </>
  );
}

function Contenu({ i, env }: { i: IndicateursDepense; env: Enveloppe<IndicateursDepense> }) {
  const { filtres, definir } = useFiltres();
  const [params, setParams] = useSearchParams();
  const meta = env.meta;
  const alertes = useAlertes({ domaine: "depense", statut: "nouvelle,vue" });
  const brut = filtres.paiement === "brut";
  const ministere = params.get("ministere");

  function ouvrirMinistere(code: string | null) {
    setParams(
      (avant) => {
        const p = new URLSearchParams(avant);
        if (code) p.set("ministere", code);
        else p.delete("ministere");
        return p;
      },
      { replace: true },
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <Zone titre="Indicateurs clés">
        <BandeauKpi>
          <KpiCard
            libelle="Crédits actuels"
            valeur={<Montant gnf={i.credit_actuel} />}
            contexte={
              <>
                LFI <Montant gnf={i.credit_initial_lfi} /> ·{" "}
                {i.variation_lfi != null && i.variation_lfi >= 0 ? "+" : ""}
                {pct(i.variation_lfi)}
              </>
            }
            meta={meta}
          />
          <KpiCard
            libelle="Taux d'engagement"
            valeur={<Pourcentage ratio={i.taux_engagement} />}
            contexte={
              <>
                <Montant gnf={i.credit_engage} /> engagés
              </>
            }
            jauge={{ valeur: i.taux_engagement }}
            meta={meta}
          />
          <KpiCard
            libelle="Taux d'ordonnancement"
            valeur={<Pourcentage ratio={i.taux_ordonnancement} />}
            contexte={
              <>
                <Montant gnf={i.montant_ordonnance} /> ordonnancés
              </>
            }
            jauge={{ valeur: i.taux_ordonnancement }}
            meta={meta}
          />
          <KpiCard
            libelle={brut ? "Payé / ordonnancé (brut)" : "Payé / ordonnancé ajusté"}
            valeur={<Pourcentage ratio={i.paiement.paye_sur_ordonnance} />}
            contexte={
              <>
                <Montant gnf={i.paiement.paye} /> sur <Montant gnf={i.paiement.ordonnance} />
              </>
            }
            jauge={{ valeur: i.paiement.paye_sur_ordonnance }}
            aide={AIDE_PAIEMENT}
            meta={meta}
          />
          <KpiCard
            libelle={brut ? "Reste à payer (brut)" : "Reste à payer ajusté"}
            valeur={<Montant gnf={i.paiement.reste_a_payer} />}
            contexte={
              brut ? (
                "Procédures hors chaîne incluses"
              ) : (
                <>
                  Hors chaîne exclu : <Montant gnf={i.hors_chaine.ordonnance} />
                </>
              )
            }
            aide={AIDE_PAIEMENT}
            meta={meta}
          />
          <KpiCard
            libelle="Crédits non engagés"
            valeur={<Montant gnf={i.credits_non_engages} />}
            contexte={
              <>
                {pct(i.credit_actuel ? i.credits_non_engages / i.credit_actuel : null)} des crédits ·
                disponible <Montant gnf={i.credit_disponible} />
              </>
            }
            meta={meta}
          />
        </BandeauKpi>
      </Zone>

      <Zone titre="Points d'attention">
        <div className="grid gap-4 lg:grid-cols-12">
          <section id="attention" aria-labelledby="attention-titre" className="carte p-4 lg:col-span-7">
            {alertes.data ? (
              <ListeAlertes
                alertes={alertes.data}
                limite={4}
                filtres={false}
                titre="Alertes des dépenses"
                titreId="attention-titre"
              />
            ) : (
              <h2 id="attention-titre" className="text-md font-bold text-ink">
                Alertes des dépenses
              </h2>
            )}
          </section>
          <BlocChaine />
        </div>
      </Zone>

      <Zone titre="Analyses">
        <BlocNatures onNature={(t) => definir({ nature: TITRE_VERS_NATURE[t] ?? "" })} />
        <div className="grid gap-4 lg:grid-cols-2">
          <BlocMensuel />
          <BlocRestes />
        </div>
      </Zone>

      <Zone titre="Détail">
        <BlocSections actif={ministere} onSection={ouvrirMinistere} />
        <div className="grid gap-4 lg:grid-cols-2">
          <BlocProcedures />
          <BlocBeneficiaires />
        </div>
        <PanneauQualite nbLfiAbsent={i.nb_lfi_absent} />
      </Zone>

      <DetailMinistere code={ministere} onFermer={() => ouvrirMinistere(null)} />
    </div>
  );
}

function BlocChaine() {
  const r = useDonnees<Chaine>("/depense/chaine/");
  return (
    <Carte
      id="chaine"
      titre="Chaîne de la dépense"
      sousTitre="Montant et taux de chaque phase sur les crédits actuels"
      className="lg:col-span-5"
    >
      <EtatBloc requete={r}>
        {(c) => (
          <>
            <PipelineBars phases={c.phases} />
            {c.liquide_depasse_engage && (
              <Note etat="vigilance">
                Le liquidé dépasse l'engagé : {nombre(c.nb_lignes_liquide_sup_engage)} lignes à vérifier
                (régularisations ou liquidations sans engagement préalable).
              </Note>
            )}
          </>
        )}
      </EtatBloc>
    </Carte>
  );
}

function BlocNatures({ onNature }: { onNature: (titre: string) => void }) {
  const r = useDonnees<Nature[]>("/depense/natures/", { nature: undefined });
  return (
    <Carte
      id="natures"
      titre="Exécution par nature économique"
      sousTitre="Cliquer sur une nature filtre toute la page"
      actions={<Legende elements={SEGMENTS_EXECUTION} />}
    >
      <EtatBloc requete={r}>
        {(natures) => (
          <ul className="flex flex-col gap-2">
            {natures.map((n) => (
              <li key={n.titre}>
                <button
                  type="button"
                  onClick={() => onNature(n.titre)}
                  className="flex w-full flex-col gap-1 rounded-sm p-1 text-left hover:bg-hover"
                >
                  <span className="flex flex-wrap items-baseline justify-between gap-x-3 text-base">
                    <span className="font-bold text-ink">{n.libelle}</span>
                    <span className="text-ink-2">
                      <Montant gnf={n.credit_actuel} /> · engagé {pct(n.taux_engagement)}
                    </span>
                  </span>
                  <StackedProgress
                    libelle={n.libelle}
                    segments={SEGMENTS_EXECUTION.map((s) => ({
                      ...s,
                      valeur: n.empile[s.code as keyof Nature["empile"]],
                    }))}
                  />
                </button>
              </li>
            ))}
          </ul>
        )}
      </EtatBloc>
    </Carte>
  );
}

const colonnesSections: Colonne<SectionLigne>[] = [
  {
    header: "Ministère / institution",
    id: "libelle",
    accessorFn: (s) => s.libelle_court,
    cell: ({ row }) => <span title={row.original.libelle}>{row.original.libelle_court}</span>,
  },
  {
    header: "Crédits",
    accessorKey: "credit_actuel",
    cell: ({ getValue }) => <Montant gnf={getValue() as number} />,
    meta: { numerique: true, exporter: (s) => String(enMds(s.credit_actuel)) },
  },
  {
    header: "Engagé",
    accessorKey: "taux_engagement",
    cell: ({ row }) => (
      <span className="flex min-w-[8rem] flex-col gap-1">
        <span>
          <Montant gnf={row.original.credit_engage} /> · {pct(row.original.taux_engagement)}
        </span>
        <Jauge
          valeur={row.original.taux_engagement}
          libelle={`Taux d'engagement ${row.original.libelle_court}`}
        />
      </span>
    ),
    meta: { numerique: true, exporter: (s) => String(s.taux_engagement ?? "") },
  },
  {
    header: "Payé / ordonnancé",
    accessorKey: "paye_sur_ordonnance",
    cell: ({ row }) => (
      <span className="flex min-w-[6rem] flex-col gap-1">
        <span>{pct(row.original.paye_sur_ordonnance)}</span>
        <Jauge
          valeur={row.original.paye_sur_ordonnance}
          libelle={`Payé sur ordonnancé ${row.original.libelle_court}`}
        />
      </span>
    ),
    meta: { numerique: true, exporter: (s) => String(s.paye_sur_ordonnance ?? "") },
  },
  {
    header: "Disponible",
    accessorKey: "credit_disponible",
    cell: ({ getValue }) => <Montant gnf={getValue() as number} />,
    meta: { numerique: true, exporter: (s) => String(enMds(s.credit_disponible)) },
  },
  {
    header: "Reste à payer",
    accessorKey: "reste_a_payer",
    cell: ({ getValue }) => <Montant gnf={getValue() as number} />,
    meta: { numerique: true, exporter: (s) => String(enMds(s.reste_a_payer)) },
  },
  {
    header: "Statut",
    id: "statut",
    accessorFn: (s) => ({ critique: 0, serieux: 1, vigilance: 2, bon: 3 })[s.statut.severite],
    cell: ({ row }) => (
      <StatusPill etat={row.original.statut.severite as Etat} libelle={row.original.statut.libelle} />
    ),
    meta: { exporter: (s) => s.statut.libelle },
  },
];

function BlocSections({ actif, onSection }: { actif: string | null; onSection: (code: string) => void }) {
  const r = useDonnees<SectionLigne[]>("/depense/sections/");
  return (
    <Carte
      id="ministeres"
      titre="Ministères et institutions"
      sousTitre="Choisir un ministère ouvre son détail dans un panneau latéral"
    >
      <EtatBloc requete={r} hauteur="h-96">
        {(s) => (
          <DataTable
            donnees={s}
            colonnes={colonnesSections}
            libelle="Exécution par ministère et institution"
            onLigne={(l) => onSection(l.code)}
            ligneActive={(l) => l.code === actif}
            nomExport="depenses-ministeres"
            triInitial={[{ id: "credit_actuel", desc: true }]}
          />
        )}
      </EtatBloc>
    </Carte>
  );
}

function DetailMinistere({ code, onFermer }: { code: string | null; onFermer: () => void }) {
  const r = useDonnees<SectionDetail>(`/depense/sections/${code}/`, {}, { actif: Boolean(code) });
  const d = r.data?.data;
  return (
    <Sheet
      ouvert={Boolean(code)}
      onChange={(o) => !o && onFermer()}
      titre={d?.libelle_court ?? "Détail du ministère"}
      description={d?.libelle}
    >
      <EtatBloc requete={r} hauteur="h-96">
        {(d, env) => (
          <div className="flex flex-col gap-6">
            <SourceBadge meta={env.meta} />
            <section>
              <h3 className="etiquette mb-2">Par nature</h3>
              <HBarList
                lignes={d.natures.map((n) => ({
                  libelle: n.libelle,
                  valeur: n.credit_engage,
                  objectif: n.credit_actuel,
                }))}
                seuil={0.5}
                reference="des crédits engagés"
                retard="faible engagement"
              />
              <p className="mt-2 text-sm text-ink-2">Barre : engagé · trait : crédits actuels.</p>
            </section>
            <section>
              <h3 className="etiquette mb-2">Principaux services (8 premiers par crédits)</h3>
              <ul className="flex flex-col gap-3">
                {d.top_sous_sections.map((s) => (
                  <li key={s.code} className="flex flex-col gap-1">
                    <span className="flex items-baseline justify-between gap-3 text-base">
                      <span className="min-w-0 text-ink">{s.libelle}</span>
                      <span className="shrink-0 text-ink-2">
                        <Montant gnf={s.credit_actuel} /> · {pct(s.taux_engagement)}
                      </span>
                    </span>
                    <Jauge valeur={s.taux_engagement} libelle={`Taux d'engagement ${s.libelle}`} />
                  </li>
                ))}
              </ul>
            </section>
            <section>
              <h3 className="etiquette mb-2">Lignes en dépassement ({d.lignes_depassement.length})</h3>
              {d.lignes_depassement.length ? (
                <DataTable
                  donnees={d.lignes_depassement}
                  recherche={false}
                  libelle="Lignes en dépassement"
                  colonnes={[
                    { header: "Service", accessorKey: "sous_section" },
                    { header: "Imputation", accessorKey: "nature_code" },
                    {
                      header: "Disponible",
                      accessorKey: "credit_disponible",
                      cell: ({ getValue }) => <Montant gnf={getValue() as number} decimales={2} />,
                      meta: { numerique: true },
                    },
                  ]}
                />
              ) : (
                <p className="text-base text-ink-2">Aucune ligne en dépassement.</p>
              )}
            </section>
          </div>
        )}
      </EtatBloc>
    </Sheet>
  );
}

function BlocMensuel() {
  const r = useDonnees<Mensuel>("/depense/mensuel/");
  return (
    <Carte
      id="rythme"
      titre="Rythme mensuel des engagements"
      sousTitre="En milliards de GNF, par mois de création"
    >
      <EtatBloc requete={r} hauteur="h-64">
        {(m) => (
          <>
            <GroupedBarChart
              libelle="Engagements par mois de création"
              donnees={m.mois.map((x) => ({
                ...x,
                libelle: moisCourt(x.mois, x.periode_complementaire),
                engage: enMds(x.montant_engage),
              }))}
              categorie="libelle"
              series={[{ cle: "engage", libelle: "Engagé", couleur: "var(--phase-3)" }]}
              miseEnEvidence={(l) =>
                l.decembre ? "var(--phase-6)" : l.periode_complementaire ? "var(--serie-2)" : undefined
              }
            />
            <Legende
              elements={[
                { libelle: "Mois de l'exercice", couleur: "var(--phase-3)" },
                { libelle: "Décembre", couleur: "var(--phase-6)" },
                { libelle: "Période complémentaire", couleur: "var(--serie-2)" },
              ]}
            />
            {m.engage_periode_complementaire > 0 && (
              <Note>
                <Montant gnf={m.engage_periode_complementaire} /> d'engagements créés pendant la période
                complémentaire (après le 31 décembre).
              </Note>
            )}
          </>
        )}
      </EtatBloc>
    </Carte>
  );
}

function BlocRestes() {
  const r = useDonnees<RestesAPayer>("/depense/restes-a-payer/anciennete/");
  return (
    <Carte
      id="restes"
      titre="Restes à payer par ancienneté"
      sousTitre="Ordonnancé non payé, par mois de création de l'engagement"
    >
      <EtatBloc requete={r} hauteur="h-64">
        {(x) => (
          <>
            <GroupedBarChart
              libelle="Restes à payer par mois de création"
              donnees={x.mois.map((m) => ({
                ...m,
                libelle: moisCourt(m.mois_creation, true),
                reste: enMds(m.reste_a_payer),
              }))}
              categorie="libelle"
              series={[{ cle: "reste", libelle: "Reste à payer", couleur: "var(--phase-3)" }]}
              miseEnEvidence={(m) => (m.risque_arriere ? "var(--phase-6)" : undefined)}
            />
            <Legende
              elements={[
                { libelle: "Récent", couleur: "var(--phase-3)" },
                { libelle: `Plus de ${x.seuil_mois} mois : risque d'arriérés`, couleur: "var(--phase-6)" },
              ]}
            />
            {x.reste_a_payer_risque_arriere > 0 && (
              <Note etat="critique">
                <Montant gnf={x.reste_a_payer_risque_arriere} /> restent à payer depuis plus de {x.seuil_mois}{" "}
                mois.
              </Note>
            )}
          </>
        )}
      </EtatBloc>
    </Carte>
  );
}

function BlocProcedures() {
  const r = useDonnees<Procedure[]>("/depense/procedures/");
  return (
    <Carte id="procedures" titre="Procédures d'exécution">
      <EtatBloc requete={r}>
        {(p) => (
          <DataTable
            donnees={p}
            recherche={false}
            libelle="Procédures d'exécution"
            colonnes={[
              {
                header: "Procédure",
                accessorKey: "procedure",
                cell: ({ row }) => (
                  <span className="flex flex-wrap items-center gap-2">
                    {row.original.procedure}
                    {row.original.hors_chaine && (
                      <span className="rounded-sm border border-dashed border-gold px-1.5 text-xs font-bold text-ink">
                        hors chaîne
                      </span>
                    )}
                  </span>
                ),
              },
              {
                header: "Engag.",
                accessorKey: "nb_engagements",
                meta: { numerique: true },
                cell: ({ getValue }) => nombre(getValue() as number),
              },
              {
                header: "Engagé",
                accessorKey: "montant_engage",
                meta: { numerique: true },
                cell: ({ getValue }) => <Montant gnf={getValue() as number} />,
              },
              {
                header: "Payé / ordo.",
                accessorKey: "paye_sur_ordonnance",
                meta: { numerique: true },
                cell: ({ getValue }) => pct(getValue() as number),
              },
            ]}
            triInitial={[{ id: "montant_engage", desc: true }]}
          />
        )}
      </EtatBloc>
    </Carte>
  );
}

function BlocBeneficiaires() {
  const r = useDonnees<Beneficiaires>("/depense/beneficiaires/", { top: 10 });
  return (
    <Carte id="beneficiaires" titre="Dix premiers bénéficiaires" sousTitre="Part dans le total engagé">
      <EtatBloc requete={r} hauteur="h-80">
        {(b) => (
          <HBarList
            lignes={b.beneficiaires.map((x) => ({
              cle: String(x.beneficiaire_id ?? x.beneficiaire),
              libelle: x.beneficiaire,
              valeur: x.montant_engage,
              complement: `${pct(x.part)} du total engagé · ${nombre(x.nb_engagements)} engagements`,
            }))}
          />
        )}
      </EtatBloc>
    </Carte>
  );
}

function PanneauQualite({ nbLfiAbsent }: { nbLfiAbsent: number }) {
  const [ouvert, setOuvert] = useState(false);
  const r = useQuery({
    queryKey: ["qualite"],
    queryFn: () => api.get<Enveloppe<{ controles: Controle[] }>>("/qualite/"),
    enabled: ouvert,
  });
  const controles = r.data?.data?.controles ?? [];
  return (
    <section id="qualite" aria-labelledby="qualite-titre" className="carte">
      <h2 id="qualite-titre" className="text-md font-bold">
        <button
          type="button"
          aria-expanded={ouvert}
          aria-controls="qualite-contenu"
          onClick={() => setOuvert((o) => !o)}
          className="flex w-full items-center justify-between rounded p-4 text-left hover:bg-hover"
        >
          Qualité des données
          <ChevronDown className={`h-5 w-5 transition-transform ${ouvert ? "rotate-180" : ""}`} aria-hidden />
        </button>
      </h2>
      {ouvert && (
        <div id="qualite-contenu" className="px-4 pb-4">
          <ul className="divide-y divide-border">
            {controles.map((c) => (
              <li key={c.code} className="flex flex-wrap items-center justify-between gap-3 py-2 text-base">
                <span className="flex items-center gap-2">
                  <StatusPill
                    etat={c.reussi ? "bon" : c.niveau === "bloquant" ? "critique" : "vigilance"}
                    libelle={c.reussi ? "Conforme" : c.niveau === "bloquant" ? "Bloquant" : "À vérifier"}
                  />
                  {c.libelle}
                </span>
                <span className="chiffres text-ink-2">
                  {c.nombre != null
                    ? nombre(c.nombre)
                    : c.valeur != null
                      ? `${nombre(Number(c.valeur))} GNF`
                      : ""}
                </span>
              </li>
            ))}
          </ul>
          {nbLfiAbsent > 0 && (
            <Note>{nombre(nbLfiAbsent)} lignes sans crédit LFI : comptées pour 0 dans les calculs.</Note>
          )}
        </div>
      )}
    </section>
  );
}
