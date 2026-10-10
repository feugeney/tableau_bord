/** Barres en HTML : légères, accessibles (valeurs écrites en texte), sans débordement sur mobile. */
import { pct } from "@/lib/format";

import { ETATS } from "./Indicateurs";
import { Montant } from "./Montant";
import { Infobulle } from "./ui/primitives";

export interface LigneHBar {
  cle?: string;
  libelle: string;
  valeur: number;
  objectif?: number | null;
  complement?: string;
  onClick?: () => void;
}

/**
 * Barres horizontales de type « bullet » : barre = réalisé, trait = objectif.
 * Sous `seuil` × objectif, la barre passe à l'état « sérieux » et la ligne l'indique en toutes lettres.
 */
export function HBarList({
  lignes,
  seuil = 0.8,
  reference = "de l'objectif",
  retard = "en retard",
}: {
  lignes: LigneHBar[];
  seuil?: number;
  /** Ce que représente le trait : « de l'objectif », « des crédits »… */
  reference?: string;
  /** Mention écrite sous le seuil (la couleur n'est jamais seule). */
  retard?: string;
}) {
  const max = Math.max(1, ...lignes.map((l) => Math.max(l.valeur, l.objectif ?? 0)));
  return (
    <ul className="flex flex-col gap-3">
      {lignes.map((l) => {
        const ratio = l.objectif ? l.valeur / l.objectif : null;
        const enRetard = ratio !== null && ratio < seuil;
        const contenu = (
          <>
            <span className="flex items-baseline justify-between gap-3 text-base">
              <span className="min-w-0 truncate text-ink" title={l.libelle}>
                {l.libelle}
              </span>
              <span className="shrink-0 text-ink">
                <Montant gnf={l.valeur} />
                {ratio !== null && (
                  <span className="chiffres ml-2 text-sm text-ink-2">
                    {pct(ratio)} {reference}
                    {enRetard ? ` · ${retard}` : ""}
                  </span>
                )}
              </span>
            </span>
            <span className="relative mt-1 block h-2 w-full rounded-full bg-grid" aria-hidden>
              <span
                className="jauge-remplie block h-2 rounded-full"
                style={{
                  width: `${(l.valeur / max) * 100}%`,
                  background: enRetard ? ETATS.serieux.couleur : "var(--serie-1)",
                }}
              />
              {l.objectif != null && (
                <span
                  className="absolute -top-1 block h-4 w-0.5 rounded-full bg-[var(--objectif)]"
                  style={{ left: `calc(${(l.objectif / max) * 100}% - 1px)` }}
                />
              )}
            </span>
            {l.complement && <span className="mt-0.5 block text-sm text-ink-2">{l.complement}</span>}
          </>
        );
        return (
          <li key={l.cle ?? l.libelle}>
            {l.onClick ? (
              <button
                type="button"
                onClick={l.onClick}
                className="block w-full rounded-sm text-left hover:bg-hover"
              >
                {contenu}
              </button>
            ) : (
              <div>{contenu}</div>
            )}
          </li>
        );
      })}
    </ul>
  );
}

export interface SegmentEmpile {
  code: string;
  libelle: string;
  valeur: number;
  couleur: string;
}

export const SEGMENTS_EXECUTION = [
  { code: "paye", libelle: "Payé", couleur: "var(--phase-6)" },
  { code: "ordonnance_non_paye", libelle: "Ordonnancé non payé", couleur: "var(--phase-4)" },
  { code: "engage_non_ordonnance", libelle: "Engagé non ordonnancé", couleur: "var(--phase-2)" },
  { code: "disponible", libelle: "Disponible", couleur: "var(--grid)" },
];

/** Barre empilée (2 px d'espace entre segments) : payé / ordonnancé non payé / engagé non ordonnancé / disponible. */
export function StackedProgress({ segments, libelle }: { segments: SegmentEmpile[]; libelle: string }) {
  const total = segments.reduce((s, x) => s + x.valeur, 0) || 1;
  return (
    <div
      role="img"
      aria-label={`${libelle} : ${segments.map((s) => `${s.libelle} ${pct(s.valeur / total)}`).join(", ")}`}
      className="flex h-3 w-full gap-0.5"
    >
      {segments
        .filter((s) => s.valeur > 0)
        .map((s) => (
          <Infobulle
            key={s.code}
            contenu={
              <>
                {s.libelle} : <Montant gnf={s.valeur} className="[&_abbr]:text-on-navy-2" /> (
                {pct(s.valeur / total)})
              </>
            }
          >
            <span
              className="block h-3 first:rounded-l-full last:rounded-r-full"
              style={{ width: `${(s.valeur / total) * 100}%`, background: s.couleur }}
            />
          </Infobulle>
        ))}
    </div>
  );
}

export function Legende({ elements }: { elements: { libelle: string; couleur: string }[] }) {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-ink-2">
      {elements.map((e) => (
        <li key={e.libelle} className="flex items-center gap-1.5">
          <span
            aria-hidden
            className="h-2.5 w-2.5 rounded-sm border border-border"
            style={{ background: e.couleur }}
          />
          {e.libelle}
        </li>
      ))}
    </ul>
  );
}

const PHASES = ["--phase-1", "--phase-2", "--phase-3", "--phase-4", "--phase-5", "--phase-6"];

/** Phases de la dépense : rampe bleue du clair au foncé, montant et taux écrits sur chaque ligne. */
export function PipelineBars({
  phases,
}: {
  phases: { code: string; libelle: string; montant: number; taux: number | null }[];
}) {
  const max = Math.max(1, ...phases.map((p) => p.montant));
  return (
    <ol className="flex flex-col gap-2">
      {phases.map((p, i) => (
        <li
          key={p.code}
          className="grid grid-cols-[7.5rem_minmax(0,1fr)] items-center gap-3 sm:grid-cols-[10rem_minmax(0,1fr)_9rem]"
        >
          <span className="text-base text-ink">{p.libelle}</span>
          <span className="h-3 rounded-full bg-grid" aria-hidden>
            <span
              className="jauge-remplie block h-3 rounded-full"
              style={{
                width: `${(p.montant / max) * 100}%`,
                background: `var(${PHASES[i % PHASES.length]})`,
              }}
            />
          </span>
          <span className="col-start-2 text-right text-base text-ink sm:col-start-auto">
            <Montant gnf={p.montant} decimales={0} />
            <span className="chiffres ml-2 inline-block w-10 text-sm text-ink-2">
              {i > 0 ? pct(p.taux) : ""}
            </span>
          </span>
        </li>
      ))}
    </ol>
  );
}
