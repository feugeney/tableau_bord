import { AlertCircle, AlertOctagon, AlertTriangle, CheckCircle2 } from "lucide-react";
import type { ReactNode } from "react";

import type { Meta, Severite } from "@/api/types";
import { pct } from "@/lib/format";
import { cn } from "@/lib/utils";

import { SourceBadge } from "./Source";
import { Infobulle, Squelette } from "./ui/primitives";

export type Etat = Severite | "bon";

/** États réservés aux alertes et statuts : couleur + pictogramme + libellé, jamais la couleur seule. */
export const ETATS: Record<
  Etat,
  { libelle: string; couleur: string; Icone: typeof CheckCircle2; rang: number }
> = {
  critique: { libelle: "Critique", couleur: "var(--etat-critique)", Icone: AlertOctagon, rang: 0 },
  serieux: { libelle: "Sérieux", couleur: "var(--etat-serieux)", Icone: AlertTriangle, rang: 1 },
  vigilance: { libelle: "Vigilance", couleur: "var(--etat-vigilance)", Icone: AlertCircle, rang: 2 },
  bon: { libelle: "Bon", couleur: "var(--etat-bon)", Icone: CheckCircle2, rang: 3 },
};

/** Pictogramme d'état : carré à la couleur de l'état, glyphe en encre (lisible dans les deux thèmes). */
export function PastilleEtat({ etat, taille = "md" }: { etat: Etat; taille?: "sm" | "md" }) {
  const { Icone, couleur } = ETATS[etat];
  return (
    <span
      aria-hidden
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-sm text-sur-etat",
        taille === "sm" ? "h-4 w-4" : "h-6 w-6",
      )}
      style={{ background: couleur }}
    >
      <Icone className={taille === "sm" ? "h-3 w-3" : "h-4 w-4"} strokeWidth={2.25} />
    </span>
  );
}

export function StatusPill({ etat, libelle }: { etat: Etat; libelle?: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-sm border border-border bg-surface py-0.5 pl-0.5 pr-2 text-xs font-bold text-ink">
      <PastilleEtat etat={etat} taille="sm" />
      {libelle ?? ETATS[etat].libelle}
    </span>
  );
}

/** Jauge fine ; `repere` place un trait (objectif, seuil). */
export function Jauge({
  valeur,
  repere,
  etat,
  libelle,
}: {
  valeur: number | null | undefined;
  repere?: number;
  etat?: Etat;
  libelle: string;
}) {
  const v = Math.max(0, Math.min(1, valeur ?? 0));
  return (
    <div
      role="meter"
      aria-label={libelle}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round((valeur ?? 0) * 100)}
      aria-valuetext={pct(valeur)}
      className="relative h-1.5 w-full rounded-full bg-grid"
    >
      <div
        className="jauge-remplie h-1.5 rounded-full"
        style={{ width: `${v * 100}%`, background: etat ? ETATS[etat].couleur : "var(--serie-1)" }}
      />
      {repere !== undefined && (
        <div
          aria-hidden
          className="absolute -top-1 h-3.5 w-0.5 rounded-full bg-[var(--objectif)]"
          style={{ left: `calc(${Math.min(1, repere) * 100}% - 1px)` }}
        />
      )}
    </div>
  );
}

/** Indicateur clé : libellé, valeur, contexte, jauge fine, pastille de source. */
export function KpiCard({
  libelle,
  valeur,
  contexte,
  jauge,
  meta,
  aide,
  chargement,
  etat,
}: {
  libelle: string;
  valeur: ReactNode;
  contexte?: ReactNode;
  jauge?: { valeur: number | null | undefined; repere?: number; etat?: Etat };
  meta?: Meta | null;
  aide?: ReactNode;
  chargement?: boolean;
  etat?: Etat;
}) {
  return (
    <article className="flex min-w-0 flex-col gap-2 bg-surface p-4">
      <div className="flex items-start justify-between gap-2">
        <h3 className="etiquette min-h-8">{libelle}</h3>
        {aide && <Infobulle contenu={aide} />}
      </div>
      {chargement ? (
        <Squelette className="h-8 w-32" />
      ) : (
        <p className="chiffres flex flex-wrap items-center gap-2 text-xl font-bold leading-none text-ink">
          {valeur}
        </p>
      )}
      {etat && etat !== "bon" && (
        <p>
          <StatusPill etat={etat} />
        </p>
      )}
      {contexte && <p className="text-sm text-ink-2">{contexte}</p>}
      {jauge && !chargement && <Jauge {...jauge} libelle={libelle} />}
      <div className="mt-auto pt-2">
        <SourceBadge meta={meta} />
      </div>
    </article>
  );
}

/**
 * Bandeau d'indicateurs : cellules de même hauteur séparées par des filets,
 * à la manière du tableau de tête d'un bulletin statistique officiel.
 */
export function BandeauKpi({ children, colonnes = 6 }: { children: ReactNode; colonnes?: 3 | 4 | 6 }) {
  return (
    <div
      className={cn(
        "grid grid-cols-1 gap-px overflow-hidden rounded border border-border bg-border sm:grid-cols-2",
        colonnes === 6 && "lg:grid-cols-3 xl:grid-cols-6 print:grid-cols-6",
        colonnes === 4 && "xl:grid-cols-4 print:grid-cols-4",
        colonnes === 3 && "lg:grid-cols-3 print:grid-cols-3",
      )}
    >
      {children}
    </div>
  );
}

export function Note({ children, etat }: { children: ReactNode; etat?: Etat }) {
  return (
    <p className="mt-3 flex items-start gap-2 rounded-sm bg-zebra px-3 py-2 text-sm text-ink-2">
      {etat ? <PastilleEtat etat={etat} taille="sm" /> : null}
      <span>{children}</span>
    </p>
  );
}
