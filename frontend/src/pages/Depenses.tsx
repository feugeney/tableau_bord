import { useQuery } from "@tanstack/react-query";
import { ChevronDown } from "lucide-react";
import { useState, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";

import { api } from "@/api/client";
import { useDonnees } from "@/api/hooks";
import type {
  Controle,
  Enveloppe,
  IndicateursDepense,
  Mensuel,
  RestesAPayer,
  SectionDetail,
  SectionLigne,
} from "@/api/types";
import { HBarList, Legende } from "@/components/Barres";
import { BoutonColonnes, PanneauColonnes } from "@/components/ChoixColonnes";
import { DataTable, type Colonne } from "@/components/DataTable";
import { ExportMinisteres } from "@/components/ExportMinisteres";
import { BoutonFiltres, PanneauFiltres } from "@/components/FiltresDepenses";
import { GroupedBarChart } from "@/components/GroupedBarChart";
import { Anneau } from "@/components/Anneau";
import { Jauge, Note, StatusPill, type Etat } from "@/components/Indicateurs";
import { Montant } from "@/components/Montant";
import { NotificationAlertes } from "@/components/NotificationAlertes";
import { PilotageDepense } from "@/components/PilotageDepense";
import { Carte, Segment } from "@/components/ui/primitives";
import { Sheet } from "@/components/ui/sheet";
import { useFiltres, type Nature as TNature } from "@/hooks/useFiltres";
import { plierParts } from "@/lib/anneau";
import { enMds, moisCourt, nombre, pct } from "@/lib/format";

import { EtatBloc, EtatPage, TitrePage, Zone } from "./commun";
import { BalanceAgee, CourbeExecution } from "./depenses/analyses";
import { useComparaisonN1, type ComparaisonN1 } from "./depenses/comparaison";
import { IndicateursExecution } from "./depenses/IndicateursExecution";
import { EncadreArbitrages, FicheTitre, TableauTitres } from "./depenses/Titres";

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
const NATURE_VERS_TITRE: Record<string, string> = Object.fromEntries(
  Object.entries(TITRE_VERS_NATURE).map(([t, nature]) => [nature, t]),
);
export default function Depenses() {
  const { filtres, definir } = useFiltres();
  const indicateurs = useDonnees<IndicateursDepense>("/depense/indicateurs/");
  const [filtresOuverts, setFiltresOuverts] = useState(false);

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
        {/* Sélecteur « Paiements ajustés / Bruts » retiré le 23/11/2026 : le paiement affiché est celui enregistré
            dans la Chaîne Dépense (choix de la direction du 21/11/2026). */}
        <BoutonFiltres ouvert={filtresOuverts} onBascule={() => setFiltresOuverts((o) => !o)} />
        {/* Points d'attention : notification (cloche + annonce), plus un bloc figé dans la page. */}
        <NotificationAlertes domaine="depense" libelle="Dépenses" />
      </TitrePage>
      <PanneauFiltres ouvert={filtresOuverts} />
      <EtatPage requete={indicateurs}>{(i, env) => <Contenu i={i} env={env} />}</EtatPage>
    </>
  );
}

function Contenu({ i, env }: { i: IndicateursDepense; env: Enveloppe<IndicateursDepense> }) {
  const { filtres, definir } = useFiltres();
  const [params, setParams] = useSearchParams();
  const meta = env.meta;
  const ministere = params.get("ministere");
  const vueTitre = params.get("vue_titre");
  const comparaison = useComparaisonN1();
  const n1 = comparaison.data?.data?.disponible ? comparaison.data.data : null;

  function basculerParametre(cle: string, valeur: string | null) {
    setParams(
      (avant) => {
        const p = new URLSearchParams(avant);
        if (valeur) p.set(cle, valeur);
        else p.delete(cle);
        return p;
      },
      { replace: true },
    );
  }

  function ouvrirMinistere(code: string | null) {
    basculerParametre("ministere", code);
  }

  function ouvrirTitre(titre: string | null) {
    basculerParametre("vue_titre", titre);
  }

  return (
    <div className="flex flex-col gap-6">
      {meta.test_non_reconcilie && (
        <p className="text-sm text-ink-3" role="status">
          Données en cours de validation.
        </p>
      )}
      {/* Bandeau « Situation au … » retiré le 23/11/2026 : l'exercice et la date figurent dans la barre du haut. */}
      <Zone titre="Indicateurs clés">
        <IndicateursExecution i={i} n1={n1} />
      </Zone>

      <Zone titre="Vue par titre">
        <TableauTitres onOuvrir={ouvrirTitre} />
      </Zone>

      <Zone titre="Arbitrages">
        <EncadreArbitrages onOuvrir={ouvrirTitre} />
      </Zone>

      <Zone titre="Répartition">
        <BlocRepartitions
          titreActif={filtres.nature ? NATURE_VERS_TITRE[filtres.nature] : null}
          onTitre={(t) =>
            definir({
              nature: filtres.nature === TITRE_VERS_NATURE[t] ? "" : (TITRE_VERS_NATURE[t] ?? ""),
            })
          }
        />
      </Zone>

      <Zone titre="Analyses">
        <BlocRestes />
      </Zone>

      <Zone titre="Tendance">
        <CourbeExecution parMois={<BlocMensuel />} />
      </Zone>

      <Zone titre="Détail">
        <BlocSections actif={ministere} onSection={ouvrirMinistere} n1={n1} />
      </Zone>

      <PilotageDepense parties={["delais", "avances"]} />

      {/* Contrôles réservés aux contrôleurs, repliés par défaut (P11). */}
      <PanneauQualite nbLfiAbsent={i.nb_lfi_absent}>
        <p role="note" className="text-sm text-ink-2">
          Les paiements sont ceux enregistrés dans la Chaîne Dépense. Les opérations payées hors chaîne
          (salaires, dette) ne constituent pas des paiements nuls confirmés. Le reste à payer reste à
          rapprocher avec le Trésor et ne certifie pas un stock d'arriérés.
        </p>
        {(i.nb_lfi_absent > 0 ||
          (i.qualite &&
            (i.qualite.engage_sup_credits > 0 ||
              i.qualite.liquide_sup_engage > 0 ||
              i.qualite.soldes_negatifs.length > 0))) && (
          <Carte
            titre="Données à rapprocher"
            sousTitre="Ces contrôles signalent des écarts de données ; ils ne qualifient pas à eux seuls une irrégularité."
          >
            <ul className="list-inside list-disc text-sm text-ink-2">
              {i.nb_lfi_absent > 0 && (
                <li>
                  {nombre(i.nb_lfi_absent)} ligne(s) sans LFI renseignée : la variation sur LFI doit être
                  interprétée avec cette couverture.
                </li>
              )}
              {i.qualite && i.qualite.engage_sup_credits > 0 && (
                <li>
                  {nombre(i.qualite.engage_sup_credits)} ligne(s) avec engagé supérieur aux crédits actuels.
                </li>
              )}
              {i.qualite && i.qualite.liquide_sup_engage > 0 && (
                <li>{nombre(i.qualite.liquide_sup_engage)} ligne(s) avec liquidé supérieur à engagé.</li>
              )}
              {i.qualite?.soldes_negatifs.map((s) => (
                <li key={s.section}>
                  Section {s.section} : solde négatif de <Montant gnf={s.montant} /> à rapprocher ; les
                  montants source restent conservés.
                </li>
              ))}
            </ul>
          </Carte>
        )}
        <PilotageDepense parties={["concordance"]} />
      </PanneauQualite>

      <DetailMinistere code={ministere} onFermer={() => ouvrirMinistere(null)} />
      <FicheTitre
        titre={vueTitre}
        onFermer={() => ouvrirTitre(null)}
        onFiltrer={(t) => {
          setParams(
            (avant) => {
              const p = new URLSearchParams(avant);
              p.delete("vue_titre");
              p.set("nature", TITRE_VERS_NATURE[t] ?? "");
              return p;
            },
            { replace: true },
          );
        }}
      />
    </div>
  );
}

function colonnesSections(n1: ComparaisonN1 | null): Colonne<SectionLigne>[] {
  return [
    {
      header: "Ministère / institution",
      id: "libelle",
      accessorFn: (s) => s.libelle,
      cell: ({ row }) => <span className="block min-w-[18rem]">{row.original.libelle}</span>,
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
      header: n1 ? `Écart ${n1.exercice} (pts)` : "Écart N−1",
      id: "ecart_n1",
      accessorFn: (s) => {
        const ref = n1?.par_section?.[s.code];
        return ref == null || s.taux_engagement == null ? null : Math.round((s.taux_engagement - ref) * 100);
      },
      cell: ({ getValue }) => {
        const v = getValue() as number | null;
        return v == null ? "—" : `${v > 0 ? "+" : ""}${v} pts`;
      },
      meta: { numerique: true, exporter: (s) => String(n1?.par_section?.[s.code] ?? "") },
    },
    {
      header: "Non engagé",
      id: "non_engage",
      accessorFn: (s) => Math.max(s.credit_actuel - s.credit_engage, 0),
      cell: ({ getValue }) => <Montant gnf={getValue() as number} />,
      meta: {
        numerique: true,
        exporter: (s) => String(enMds(Math.max(s.credit_actuel - s.credit_engage, 0))),
      },
    },
    {
      header: "Liquidé",
      accessorKey: "montant_liquide",
      cell: ({ getValue }) => <Montant gnf={getValue() as number} />,
      meta: { numerique: true, exporter: (s) => String(enMds(s.montant_liquide)) },
    },
    {
      header: "Ordonnancé",
      accessorKey: "montant_ordonnance",
      cell: ({ getValue }) => <Montant gnf={getValue() as number} />,
      meta: { numerique: true, exporter: (s) => String(enMds(s.montant_ordonnance)) },
    },
    {
      header: "Vu bon à payer",
      accessorKey: "montant_vbp",
      cell: ({ getValue }) => <Montant gnf={getValue() as number} />,
      meta: { numerique: true, exporter: (s) => String(enMds(s.montant_vbp)) },
    },
    {
      header: "Payé",
      accessorKey: "montant_paye",
      cell: ({ getValue }) => <Montant gnf={getValue() as number} />,
      meta: { numerique: true, exporter: (s) => String(enMds(s.montant_paye)) },
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
      meta: {
        numerique: true,
        exporter: (s) => (s.credit_disponible == null ? "" : String(enMds(s.credit_disponible))),
      },
    },
    {
      header: "Reste à payer",
      accessorKey: "reste_a_payer",
      cell: ({ getValue }) => <Montant gnf={getValue() as number} />,
      meta: { numerique: true, exporter: (s) => String(enMds(s.reste_a_payer)) },
    },
    {
      header: "Lignes en dépassement",
      accessorKey: "nb_lignes_depassement",
      cell: ({ getValue }) => {
        const v = getValue() as number | null;
        return v == null ? "—" : nombre(v);
      },
      meta: { numerique: true },
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
}

/** Colonnes affichées par défaut ; liquidé, ordonnancé, VBP, payé et dépassements s'ajoutent à la demande. */
const COLONNES_MINISTERES_DEFAUT = [
  "credit_actuel",
  "taux_engagement",
  "ecart_n1",
  "non_engage",
  "paye_sur_ordonnance",
  "credit_disponible",
  "reste_a_payer",
  "statut",
];
const CLE_COLONNES_MINISTERES = "tdb.depenses.colonnes-ministeres";

/** Choix des colonnes mémorisé dans ce navigateur (simple confort : sans stockage, jeu par défaut). */
function useColonnesVisibles(possibles: string[]) {
  const [visibles, setVisibles] = useState<string[]>(() => {
    try {
      const lu = JSON.parse(localStorage.getItem(CLE_COLONNES_MINISTERES) ?? "null") as unknown;
      if (Array.isArray(lu)) {
        const valides = possibles.filter((c) => lu.includes(c));
        if (valides.length) return valides;
      }
    } catch {
      /* stockage indisponible : jeu par défaut */
    }
    return COLONNES_MINISTERES_DEFAUT;
  });
  function definir(v: string[]) {
    setVisibles(v);
    try {
      localStorage.setItem(CLE_COLONNES_MINISTERES, JSON.stringify(v));
    } catch {
      /* stockage indisponible : le choix vaut pour la session */
    }
  }
  return [visibles, definir] as const;
}

function BlocSections({
  actif,
  onSection,
  n1,
}: {
  actif: string | null;
  onSection: (code: string) => void;
  n1: ComparaisonN1 | null;
}) {
  const r = useDonnees<SectionLigne[]>("/depense/sections/");
  const colonnes = colonnesSections(n1);
  const choisissables = colonnes
    .map((c) => ({
      id: c.id ?? (c as { accessorKey?: string }).accessorKey ?? "",
      libelle: String(c.header),
    }))
    .filter((c) => c.id && c.id !== "libelle");
  const [visibles, setVisibles] = useColonnesVisibles(choisissables.map((c) => c.id));
  const [choix, setChoix] = useState(false);
  const visibilite = Object.fromEntries(choisissables.map((c) => [c.id, visibles.includes(c.id)]));
  return (
    <Carte
      id="ministeres"
      titre="Ministères et institutions"
      sousTitre="Choisir un ministère ouvre son détail dans un panneau latéral · les exports reprennent les colonnes affichées"
      actions={
        <span className="inline-flex flex-wrap items-center gap-2">
          <BoutonColonnes
            ouvert={choix}
            onBascule={() => setChoix((o) => !o)}
            masquees={choisissables.length - visibles.length}
            controle="colonnes-ministeres"
          />
          <ExportMinisteres colonnes={visibles} />
        </span>
      }
    >
      {choix && (
        <PanneauColonnes
          id="colonnes-ministeres"
          colonnes={choisissables}
          visibles={visibles}
          onChange={setVisibles}
          onRetablir={() => setVisibles(COLONNES_MINISTERES_DEFAUT)}
        />
      )}
      <EtatBloc requete={r} hauteur="h-96">
        {(s) => (
          <DataTable
            donnees={s}
            colonnes={colonnes}
            visibilite={visibilite}
            libelle="Exécution par ministère et institution"
            onLigne={(l) => onSection(l.code)}
            ligneActive={(l) => l.code === actif}
            // Tri par défaut : les crédits non engagés, là où se joue l'exécution.
            triInitial={[{ id: "non_engage", desc: true }]}
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
      titre={d?.libelle ?? "Détail du ministère"}
      description={code ? `Section budgétaire ${code}` : undefined}
    >
      <EtatBloc requete={r} hauteur="h-96">
        {(d) => (
          <div className="flex flex-col gap-6">
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
                <p className="text-base text-ink-2">
                  {r.data?.meta.indicateurs_indisponibles?.includes("credit_disponible")
                    ? "Dépassements non renseignés pour ce chargement."
                    : "Aucune ligne en dépassement."}
                </p>
              )}
            </section>
          </div>
        )}
      </EtatBloc>
    </Sheet>
  );
}

interface Repartitions {
  axes: {
    axe: "pilier" | "titre" | "fonction" | "zone" | "type_budget";
    titre: string;
    disponible: boolean;
    parts: ({ code: string; libelle: string } & Record<MesureRepartie, number>)[];
  }[];
  titre_filtre: string | null;
  indisponible: Record<string, string>;
}

type MesureRepartie = "credit" | "engage" | "liquide" | "ordonnance" | "vbp" | "paye";

/** Les six étapes de la chaîne, dans l'ordre : libellé du sélecteur et titre du cadre. */
const MESURES_REPARTIES: { valeur: MesureRepartie; libelle: string; titre: string }[] = [
  { valeur: "credit", libelle: "Crédit", titre: "Répartition des crédits" },
  { valeur: "engage", libelle: "Engagé", titre: "Répartition de l'engagé" },
  { valeur: "liquide", libelle: "Liquidé", titre: "Répartition du liquidé" },
  { valeur: "ordonnance", libelle: "Ordonnancé", titre: "Répartition de l'ordonnancé" },
  { valeur: "vbp", libelle: "Vu bon à payer", titre: "Répartition du vu bon à payer" },
  { valeur: "paye", libelle: "Payé", titre: "Répartition du payé" },
];

/** Cinq anneaux (pilier Simandou, titre, fonction, zone, BAS) ; un seul sélecteur choisit l'étape de la chaîne répartie. */
export function BlocRepartitions({
  titreActif,
  onTitre,
}: {
  titreActif: string | null;
  onTitre: (titre: string) => void;
}) {
  const r = useDonnees<Repartitions>("/depense/repartitions/");
  const [mesure, setMesure] = useState<MesureRepartie>("engage");
  const choix = MESURES_REPARTIES.find((m) => m.valeur === mesure) ?? MESURES_REPARTIES[0];
  return (
    <Carte
      id="repartitions"
      titre={choix.titre}
      sousTitre="Montants bruts de la situation · cliquer sur un titre filtre toute la page"
      actions={
        <Segment<MesureRepartie>
          libelle="Étape de la chaîne répartie"
          valeur={mesure}
          options={MESURES_REPARTIES.map(({ valeur, libelle }) => ({ valeur, libelle }))}
          onChange={setMesure}
        />
      }
    >
      <EtatBloc requete={r} hauteur="h-72">
        {(d) => (
          <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-5">
            {d.axes.map((a) => (
              <section key={a.axe} aria-labelledby={`repartition-${a.axe}`} className="min-w-0">
                <h3 id={`repartition-${a.axe}`} className="etiquette mb-2">
                  {a.titre}
                  {a.axe !== "titre" && d.titre_filtre ? ` · titre ${d.titre_filtre}` : ""}
                </h3>
                {a.disponible ? (
                  <Anneau
                    libelle={`${choix.libelle} ${a.titre.toLowerCase()}`}
                    // Parts retenues et couleurs fixées par l'engagé : basculer ne repeint rien.
                    parts={plierParts(
                      a.parts,
                      (p) => p[mesure],
                      (p) => p.engage,
                      a.axe === "titre",
                    )}
                    onPart={a.axe === "titre" ? onTitre : undefined}
                    actif={a.axe === "titre" ? titreActif : null}
                  />
                ) : (
                  <p className="text-sm text-ink-2">{d.indisponible[a.axe] ?? "Non disponible."}</p>
                )}
              </section>
            ))}
          </div>
        )}
      </EtatBloc>
    </Carte>
  );
}

function BlocMensuel() {
  const r = useDonnees<Mensuel>("/depense/mensuel/");
  return (
    <Carte
      id="rythme"
      titre="Engagements par mois de création"
      sousTitre="En milliards de GNF · dossiers regroupés par création ; pas un historique des paiements"
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
                { libelle: "Créé après l'exercice", couleur: "var(--serie-2)" },
              ]}
            />
            {m.engage_periode_complementaire > 0 && (
              <Note>
                <Montant gnf={m.engage_periode_complementaire} /> d'engagements créés après le 31 décembre de
                l'exercice.
              </Note>
            )}
            {m.rapprochement && (
              <div className="mt-3 text-sm text-ink-2">
                <p>
                  {m.rapprochement.perimetre}.{" "}
                  {m.rapprochement.concordant
                    ? "Cumul rapproché avec la situation budgétaire."
                    : "Cumul non rapproché : ne pas l'interpréter comme le total officiel engagé."}
                </p>
                <p>
                  Brut : <Montant gnf={m.rapprochement.brut} /> · Comparable :{" "}
                  <Montant gnf={m.rapprochement.comparable} /> · Situation budgétaire :{" "}
                  <Montant gnf={m.rapprochement.reference} />.
                </p>
                {m.rapprochement.ecart_perimetre !== 0 && (
                  <p>
                    Écart de périmètre : <Montant gnf={m.rapprochement.ecart_perimetre} />. Les dossiers
                    restent conservés dans le détail.
                  </p>
                )}
                {!m.rapprochement.concordant && (
                  <p>
                    Écart résiduel : <Montant gnf={m.rapprochement.ecart_reference} />.
                  </p>
                )}
              </div>
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
      titre="Soldes non payés par ancienneté (balance âgée)"
      sousTitre="Ordonnancé non payé par date de création ; cette ancienneté n'est pas celle d'une échéance de paiement"
    >
      <EtatBloc requete={r} hauteur="h-64">
        {(x) => <BalanceAgee x={x} />}
      </EtatBloc>
    </Carte>
  );
}

function PanneauQualite({ nbLfiAbsent, children }: { nbLfiAbsent: number; children?: ReactNode }) {
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
        <div id="qualite-contenu" className="flex flex-col gap-4 px-4 pb-4">
          {children}
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
