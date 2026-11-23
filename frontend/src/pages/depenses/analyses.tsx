/**
 * Blocs d'analyse de la page Dépenses (validés le 19/11/2026) : fraîcheur, chaîne des montants,
 * comparaison N−1, courbe d'exécution cumulée, matrice des ministères, concentration du non-engagé
 * et balance âgée des soldes non payés.
 */
import { ArrowDown, ArrowRight, ArrowUp, Clock } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
  type TooltipProps,
} from "recharts";

import { useDonnees } from "@/api/hooks";
import type { IndicateursDepense, Meta, RestesAPayer, SectionLigne } from "@/api/types";
import { HBarList } from "@/components/Barres";
import { Note } from "@/components/Indicateurs";
import { Montant } from "@/components/Montant";
import { SourceBadge } from "@/components/Source";
import { Carte, Segment } from "@/components/ui/primitives";
import { dateFr, mds, moisCourt, nombre, pct } from "@/lib/format";
import { cn } from "@/lib/utils";

import { EtatBloc } from "../commun";

export type { ComparaisonN1 } from "./comparaison";

const AXE = { fill: "var(--ink-3)", fontSize: 12 };

// ------------------------------------------------------------------------------------- fraîcheur (P3)

/**
 * Source et ancienneté de la situation, une seule fois pour toute la page (les cadres ne répètent pas
 * la source : toutes les données de la page viennent de la Chaîne Dépense). Au-delà de 30 jours, la lecture
 * doit en tenir compte.
 */
export function BandeauFraicheur({ meta }: { meta: Meta }) {
  const date = meta.date_situation;
  if (!date) return null;
  const jours = Math.floor((Date.now() - new Date(`${date}T00:00:00`).getTime()) / 86_400_000);
  const ancienne = jours > 30;
  return (
    <p
      role="status"
      className={cn(
        "flex flex-wrap items-center gap-2 rounded-sm border px-3 py-2 text-sm",
        ancienne
          ? "border-[var(--etat-vigilance)] bg-gold-tint text-ink"
          : "border-border bg-surface text-ink-2",
      )}
    >
      <Clock className="h-4 w-4 shrink-0" aria-hidden />
      <span>
        <strong className="text-ink">Situation au {dateFr(date)}</strong> · {nombre(jours)} jour(s)
        {" · "}
        <SourceBadge meta={meta} className="align-middle" />
        {ancienne ? " : données anciennes, à actualiser avant toute décision." : "."}
      </span>
    </p>
  );
}

// ----------------------------------------------------------------------------- chaîne des montants (P1)

/** Les montants de la chaîne en grand ; le taux de passage d'une étape à la suivante entre eux. */
export function ChaineMontants({ i, brut }: { i: IndicateursDepense; brut: boolean }) {
  const etapes: { libelle: string; montant: number; taux?: number | null }[] = [
    { libelle: "Crédits actuels", montant: i.credit_actuel },
    { libelle: "Engagé", montant: i.credit_engage, taux: i.taux_engagement },
    { libelle: "Liquidé", montant: i.montant_liquide, taux: i.taux_liquidation },
    { libelle: "Ordonnancé", montant: i.montant_ordonnance, taux: i.taux_ordonnancement },
    { libelle: "Payé", montant: i.montant_paye, taux: i.taux_paiement },
  ];
  return (
    <section aria-label="Chaîne des montants de la dépense" className="carte p-4">
      <ol className="flex flex-wrap items-stretch gap-x-2 gap-y-3">
        {etapes.map((e, n) => (
          <li key={e.libelle} className="flex items-center gap-2">
            {n > 0 && (
              <span
                className="flex flex-col items-center text-xs text-ink-2"
                aria-label={`${pct(e.taux)} de l'étape précédente`}
              >
                <ArrowRight className="h-4 w-4" aria-hidden />
                <span className="chiffres">{pct(e.taux)}</span>
              </span>
            )}
            <span className="flex min-w-[7.5rem] flex-col">
              <span className="text-sm text-ink-2">{e.libelle}</span>
              <span className="chiffres text-xl font-bold leading-tight text-ink">
                <Montant gnf={e.montant} />
              </span>
            </span>
          </li>
        ))}
        <li className="flex items-center gap-2 border-border sm:ml-auto sm:border-l sm:pl-4">
          <span className="flex min-w-[7.5rem] flex-col">
            <span className="text-sm text-ink-2">{brut ? "Reste à payer brut" : "Reste à payer ajusté"}</span>
            <span className="chiffres text-xl font-bold leading-tight text-ink">
              <Montant gnf={i.paiement.reste_a_payer} />
            </span>
            <span className="text-xs text-ink-2">Ordonnancé − payé · à rapprocher avec le Trésor</span>
          </span>
        </li>
      </ol>
    </section>
  );
}

// ------------------------------------------------------------------------------ comparaison N−1 (P2)

/** Écart à l'exercice précédent, écrit (jamais la couleur seule). */
export function EcartN1({
  taux,
  reference,
  libelle,
}: {
  taux: number | null | undefined;
  reference: number | null | undefined;
  libelle: string;
}) {
  if (reference == null) return null;
  const ecart = taux == null ? null : Math.round((taux - reference) * 100);
  const Icone = ecart == null || ecart === 0 ? null : ecart > 0 ? ArrowUp : ArrowDown;
  return (
    <span className="mt-1 flex items-center gap-1 text-xs text-ink-2">
      {Icone && <Icone className="h-3.5 w-3.5 text-ink" aria-hidden />}
      <span>
        {libelle} : <span className="chiffres">{pct(reference)}</span>
        {ecart != null && (
          <span className="chiffres font-bold text-ink">
            {" "}
            · {ecart > 0 ? "+" : ""}
            {ecart} pts
          </span>
        )}
      </span>
    </span>
  );
}

// ------------------------------------------------------------------------- courbe d'exécution (P4)

interface Courbe {
  date_situation: string | null;
  engage_serie: number;
  engage_situation: number;
  concordant: boolean;
  exercice: number;
  exercice_precedent: number | null;
  points: { mois: number; n: number | null; n1: number | null; prorata: number }[];
  methode: string;
}

/** Engagé cumulé en % des crédits, exercice courant et précédent ; prorata en simple repère. */
export function CourbeExecution({ parMois }: { parMois: ReactNode }) {
  const r = useDonnees<Courbe>("/depense/courbe/");
  const [vue, setVue] = useState<"cumul" | "mois">("cumul");
  return (
    <Carte
      id="courbe"
      titre="Trajectoire de l'engagement"
      sousTitre="Engagé cumulé en % des crédits, mois par mois · comparaison avec l'exercice précédent"
      actions={
        <Segment<"cumul" | "mois">
          libelle="Présentation"
          valeur={vue}
          options={[
            { valeur: "cumul", libelle: "Cumul" },
            { valeur: "mois", libelle: "Par mois" },
          ]}
          onChange={setVue}
        />
      }
    >
      {vue === "mois" ? (
        parMois
      ) : (
        <EtatBloc requete={r} hauteur="h-72">
          {(c) => {
            const donnees = c.points.map((p) => ({
              libelle: moisCourt(`${c.exercice}-${String(p.mois).padStart(2, "0")}-01`),
              n: p.n == null ? null : p.n * 100,
              n1: p.n1 == null ? null : p.n1 * 100,
              prorata: p.prorata * 100,
            }));
            const dernier = [...c.points].reverse().find((p) => p.n != null);
            const memeMois = dernier ? c.points.find((p) => p.mois === dernier.mois) : undefined;
            return (
              <>
                <div
                  className="h-72 w-full"
                  role="img"
                  aria-label={`Engagé cumulé en % des crédits, ${c.exercice} et ${c.exercice_precedent ?? "sans exercice précédent"}`}
                >
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={donnees} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                      <CartesianGrid vertical={false} stroke="var(--grid)" />
                      <XAxis dataKey="libelle" tickLine={false} axisLine={false} tick={AXE} />
                      <YAxis
                        tickLine={false}
                        axisLine={false}
                        width={44}
                        tick={AXE}
                        domain={[0, (max: number) => Math.max(100, Math.ceil(max / 10) * 10)]}
                        tickFormatter={(v: number) => `${v} %`}
                      />
                      <Tooltip content={<InfobulleCourbe />} isAnimationActive={false} />
                      <Legend
                        verticalAlign="top"
                        align="left"
                        iconType="plainline"
                        wrapperStyle={{ fontSize: 13, paddingBottom: 8 }}
                        formatter={(v: string) => <span style={{ color: "var(--ink-2)" }}>{v}</span>}
                      />
                      <Line
                        dataKey="prorata"
                        name="Prorata temporel (repère)"
                        stroke="var(--ink-3)"
                        strokeDasharray="4 4"
                        strokeWidth={1}
                        dot={false}
                        isAnimationActive={false}
                      />
                      {c.exercice_precedent && (
                        <Line
                          dataKey="n1"
                          name={String(c.exercice_precedent)}
                          stroke="var(--serie-2)"
                          strokeWidth={2}
                          dot={false}
                          isAnimationActive={false}
                        />
                      )}
                      <Line
                        dataKey="n"
                        name={String(c.exercice)}
                        stroke="var(--serie-1)"
                        strokeWidth={2}
                        dot={{ r: 4, strokeWidth: 2, stroke: "var(--surface)", fill: "var(--serie-1)" }}
                        connectNulls={false}
                        isAnimationActive={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                {dernier && memeMois?.n1 != null && (
                  <p className="mt-2 text-sm text-ink">
                    {c.date_situation
                      ? `Au ${dateFr(c.date_situation)}`
                      : `Fin ${moisCourt(`${c.exercice}-${String(dernier.mois).padStart(2, "0")}-01`)}`}{" "}
                    : <strong className="chiffres">{pct(dernier.n)}</strong> des crédits engagés en{" "}
                    {c.exercice}, contre <strong className="chiffres">{pct(memeMois.n1)}</strong> pour{" "}
                    {moisCourt(`${c.exercice}-${String(dernier.mois).padStart(2, "0")}-01`)} en{" "}
                    {c.exercice_precedent}.
                  </p>
                )}
                {!dernier && (
                  <p role="status" className="mt-2 text-sm text-ink-2">
                    Trajectoire indisponible : engagements datés ou crédits de référence manquants à la date
                    de situation.
                  </p>
                )}
                {c.concordant === false && (
                  <Note>
                    Le cumul daté (<Montant gnf={c.engage_serie} />) diffère de l'engagé de la situation (
                    <Montant gnf={c.engage_situation} />) : écart de{" "}
                    <Montant gnf={c.engage_serie - c.engage_situation} />. La courbe ne reconstitue pas le
                    total officiel engagé.
                  </Note>
                )}
                <p className="mt-1 text-xs text-ink-2">{c.methode}</p>
              </>
            );
          }}
        </EtatBloc>
      )}
    </Carte>
  );
}

function InfobulleCourbe({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;
  return (
    <div className="carte px-3 py-2 text-sm">
      <p className="font-bold text-ink">{label}</p>
      {payload
        .filter((p) => p.value != null)
        .map((p) => (
          <p key={String(p.dataKey)} className="flex items-center gap-2 text-ink">
            <span aria-hidden className="h-0.5 w-3" style={{ background: p.color }} />
            {p.name} : <span className="chiffres">{nombre(Number(p.value), 1)} %</span>
          </p>
        ))}
    </div>
  );
}

// ------------------------------------------------------------------------ matrice des ministères (P5)

interface Point {
  code: string;
  nom: string;
  x: number;
  y: number;
  z: number;
  etiquette: boolean;
}

function mediane(v: number[]) {
  if (!v.length) return 0;
  const t = [...v].sort((a, b) => a - b);
  const m = Math.floor(t.length / 2);
  return t.length % 2 ? t[m] : (t[m - 1] + t[m]) / 2;
}

/** Engagement (horizontal) × paiement de l'ordonnancé (vertical), taille = crédits ; quadrants aux médianes. */
export function MatriceMinisteres({ onSection }: { onSection: (code: string) => void }) {
  const r = useDonnees<SectionLigne[]>("/depense/sections/");
  return (
    <Carte
      id="matrice"
      titre="Où agir : engagement et paiement par ministère"
      sousTitre="Taille du point = crédits · lignes en pointillé = médianes · cliquer ouvre la fiche du ministère"
    >
      <EtatBloc requete={r} hauteur="h-80">
        {(sections) => <Matrice sections={sections} onSection={onSection} />}
      </EtatBloc>
    </Carte>
  );
}

function Matrice({ sections, onSection }: { sections: SectionLigne[]; onSection: (code: string) => void }) {
  const { points, mx, my, exclus } = useMemo(() => {
    const avec = sections.filter(
      (s) => s.credit_actuel > 0 && s.taux_engagement != null && s.paye_sur_ordonnance != null,
    );
    const grands = new Set(
      [...avec]
        .sort((a, b) => b.credit_actuel - a.credit_actuel)
        .slice(0, 8)
        .map((s) => s.code),
    );
    const pts: Point[] = avec.map((s) => ({
      code: s.code,
      nom: s.libelle_court,
      x: Math.min((s.taux_engagement ?? 0) * 100, 150),
      y: Math.min((s.paye_sur_ordonnance ?? 0) * 100, 150),
      z: s.credit_actuel,
      etiquette: grands.has(s.code),
    }));
    return {
      points: pts,
      mx: mediane(pts.map((p) => p.x)),
      my: mediane(pts.map((p) => p.y)),
      exclus: sections.length - avec.length,
    };
  }, [sections]);
  const quadrant = (p: Point) =>
    p.x >= mx
      ? p.y >= my
        ? "Engage et paie"
        : "Engage, paie peu"
      : p.y >= my
        ? "Engage peu, paie"
        : "Engage peu, paie peu";
  const effectifs = points.reduce<Record<string, number>>(
    (a, p) => ({ ...a, [quadrant(p)]: (a[quadrant(p)] ?? 0) + 1 }),
    {},
  );
  return (
    <>
      <div
        className="h-80 w-full"
        role="img"
        aria-label={`Matrice de ${points.length} ministères : taux d'engagement et taux de paiement`}
      >
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 12, right: 16, left: 0, bottom: 16 }}>
            <CartesianGrid stroke="var(--grid)" />
            <XAxis
              type="number"
              dataKey="x"
              name="Engagé / crédits"
              unit=" %"
              tick={AXE}
              tickLine={false}
              axisLine={false}
              label={{
                value: "Engagé / crédits",
                position: "insideBottom",
                offset: -8,
                fill: "var(--ink-2)",
                fontSize: 12,
              }}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="Payé / ordonnancé"
              unit=" %"
              width={52}
              tick={AXE}
              tickLine={false}
              axisLine={false}
              label={{
                value: "Payé / ordonnancé",
                angle: -90,
                position: "insideLeft",
                fill: "var(--ink-2)",
                fontSize: 12,
              }}
            />
            <ZAxis type="number" dataKey="z" range={[40, 900]} name="Crédits" />
            <ReferenceLine x={mx} stroke="var(--ink-3)" strokeDasharray="4 4" />
            <ReferenceLine y={my} stroke="var(--ink-3)" strokeDasharray="4 4" />
            <Tooltip content={<InfobulleMatrice />} isAnimationActive={false} />
            <Scatter
              data={points}
              fill="var(--serie-1)"
              fillOpacity={0.55}
              stroke="var(--surface)"
              strokeWidth={2}
              isAnimationActive={false}
              cursor="pointer"
              onClick={(p: { payload?: Point }) => p.payload && onSection(p.payload.code)}
              label={({ x, y, index }: { x: number; y: number; index: number }) => (
                <text x={x + 10} y={y + 4} fontSize={11} fill="var(--ink-2)">
                  {points[index]?.etiquette ? points[index].nom : ""}
                </text>
              )}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <ul className="mt-2 grid gap-1 text-sm text-ink-2 sm:grid-cols-2">
        {["Engage et paie", "Engage, paie peu", "Engage peu, paie", "Engage peu, paie peu"].map((q) => (
          <li key={q}>
            <strong className="text-ink">{q}</strong> : {nombre(effectifs[q] ?? 0)} ministère(s)
          </li>
        ))}
      </ul>
      <p className="mt-1 text-xs text-ink-2">
        Médianes : {nombre(mx, 0)} % engagé, {nombre(my, 0)} % payé.
        {exclus > 0 ? ` ${nombre(exclus)} ministère(s) sans ordonnancement ne sont pas placés.` : ""} Le
        détail chiffré figure dans le tableau des ministères.
      </p>
    </>
  );
}

function InfobulleMatrice({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload as Point;
  return (
    <div className="carte px-3 py-2 text-sm">
      <p className="font-bold text-ink">{p.nom}</p>
      <p className="text-ink">
        Engagé {nombre(p.x, 0)} % · payé {nombre(p.y, 0)} % de l'ordonnancé
      </p>
      <p className="text-ink-2">
        Crédits <Montant gnf={p.z} />
      </p>
    </div>
  );
}

// --------------------------------------------------------------- concentration du non-engagé (P6)

/** Ministères portant le plus de crédits non engagés (dix par défaut), avec la part cumulée. */
export function ConcentrationNonEngage({
  onSection,
  limite = 10,
}: {
  onSection: (code: string) => void;
  limite?: number;
}) {
  const r = useDonnees<SectionLigne[]>("/depense/sections/");
  return (
    <Carte
      id="concentration"
      titre="Concentration des crédits non engagés"
      sousTitre={`${limite === 10 ? "Dix" : nombre(limite)} ministères portant le plus de crédits non engagés · cliquer ouvre la fiche`}
    >
      <EtatBloc requete={r} hauteur="h-80">
        {(sections) => {
          const lignes = sections
            .map((s) => ({ ...s, non_engage: Math.max(s.credit_actuel - s.credit_engage, 0) }))
            .sort((a, b) => b.non_engage - a.non_engage);
          const total = lignes.reduce((t, s) => t + s.non_engage, 0);
          let cumul = 0;
          const top = lignes.slice(0, limite).map((s) => {
            cumul += s.non_engage;
            return { ...s, cumul: total ? cumul / total : null };
          });
          const trois = top.slice(0, 3).reduce((t, s) => t + s.non_engage, 0);
          return (
            <>
              <p className="mb-3 text-sm text-ink">
                <strong className="chiffres">{mds(total)}</strong> de crédits non engagés · les 3 premiers
                ministères en portent{" "}
                <strong className="chiffres">{pct(total ? trois / total : null)}</strong>.
              </p>
              <HBarList
                seuil={null}
                lignes={top.map((s) => ({
                  cle: s.code,
                  libelle: s.libelle_court,
                  valeur: s.non_engage,
                  complement: `${pct(total ? s.non_engage / total : null)} du non-engagé · cumul ${pct(s.cumul)} · engagé ${pct(s.taux_engagement)}`,
                  onClick: () => onSection(s.code),
                }))}
              />
            </>
          );
        }}
      </EtatBloc>
    </Carte>
  );
}

// ---------------------------------------------------------------------------- balance âgée (P7)

const TRANCHES = [
  { cle: "0-3", libelle: "Moins de 3 mois", min: 0, max: 3, couleur: "var(--phase-2)" },
  { cle: "3-6", libelle: "3 à 6 mois", min: 3, max: 6, couleur: "var(--phase-3)" },
  { cle: "6-12", libelle: "6 à 12 mois", min: 6, max: 12, couleur: "var(--phase-5)" },
  { cle: "12+", libelle: "Plus de 12 mois", min: 12, max: Infinity, couleur: "var(--phase-6)" },
];

/** Balance âgée : soldes non payés regroupés en quatre tranches d'ancienneté de l'engagement. */
export function BalanceAgee({ x }: { x: RestesAPayer }) {
  const tranches = TRANCHES.map((t) => {
    const lignes = x.mois.filter(
      (m) => (m.anciennete_mois ?? 0) >= t.min && (m.anciennete_mois ?? 0) < t.max,
    );
    return {
      ...t,
      montant: lignes.reduce((s, m) => s + m.reste_a_payer, 0),
      nb: lignes.reduce((s, m) => s + m.nb_engagements, 0),
    };
  });
  const total = tranches.reduce((s, t) => s + t.montant, 0);
  return (
    <>
      <p className="mb-2 text-sm text-ink">
        <strong className="chiffres">{mds(total)}</strong> ordonnancés non payés
      </p>
      <div
        className="flex h-4 w-full gap-0.5"
        role="img"
        aria-label={tranches.map((t) => `${t.libelle} ${pct(total ? t.montant / total : null)}`).join(", ")}
      >
        {tranches
          .filter((t) => t.montant > 0)
          .map((t) => (
            <span
              key={t.cle}
              className="block first:rounded-l last:rounded-r"
              style={{ width: `${(t.montant / (total || 1)) * 100}%`, background: t.couleur }}
            />
          ))}
      </div>
      <ul className="mt-3 flex flex-col gap-1 text-sm">
        {tranches.map((t) => (
          <li key={t.cle} className="flex items-center gap-2">
            <span aria-hidden className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ background: t.couleur }} />
            <span className="flex-1 text-ink">{t.libelle}</span>
            <span className="chiffres text-right">
              <strong className="text-ink">{mds(t.montant)}</strong>{" "}
              <span className="text-ink-2">
                · {pct(total ? t.montant / total : null)} · {nombre(t.nb)} engagement(s)
              </span>
            </span>
          </li>
        ))}
      </ul>
      {x.reste_a_payer_risque_arriere > 0 && (
        <Note etat="critique">
          <Montant gnf={x.reste_a_payer_risque_arriere} /> sont associés à des engagements créés depuis plus
          de {x.seuil_mois} mois. L'exigibilité et le retard de paiement ne sont pas établis par cette date.
        </Note>
      )}
    </>
  );
}
