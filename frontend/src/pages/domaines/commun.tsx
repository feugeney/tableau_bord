import type { ReactNode } from "react";

import type { Meta } from "@/api/types";
import { SourceBadge } from "@/components/Source";
import { enMds, moisCourt } from "@/lib/format";

import { DOMAINES } from "../domaines";

/** Bloc de page portant sa propre source (pages mêlant réel et illustration). */
export interface Bloc<T> {
  meta: Meta;
  donnees: T | null;
}

/** Liste des contenus prévus, affichée tant que la source n'est pas raccordée. */
export function ContenuPrevu({ cle }: { cle: string }) {
  const def = DOMAINES[cle];
  return (
    <div className="border-t border-border pt-4">
      <h3 className="etiquette mb-2">Contenu prévu dès le raccordement</h3>
      <ul className="list-disc space-y-1 pl-6 text-base text-ink-2">
        {def.contenu.map((c) => (
          <li key={c}>{c}</li>
        ))}
      </ul>
    </div>
  );
}

/** Contenu d'un bloc à source propre ; mention explicite si la source n'est pas raccordée. */
export function ContenuBloc<T>({ bloc, children }: { bloc: Bloc<T>; children: (d: T) => ReactNode }) {
  if (bloc.donnees === null || bloc.donnees === undefined) {
    return (
      <p className="flex flex-wrap items-center gap-2 text-base text-ink-2">
        Aucune donnée : <SourceBadge meta={bloc.meta} />
      </p>
    );
  }
  return <>{children(bloc.donnees)}</>;
}

export function libelleMois(exercice: number | null | undefined, mois: number, avecAnnee = false): string {
  return moisCourt(`${exercice ?? 2000}-${String(mois).padStart(2, "0")}-01`, avecAnnee);
}

/** Série mensuelle { mois, a, b } (GNF) → lignes du graphique (Mds). */
export function serieMois<T extends { mois: number }>(
  exercice: number | null | undefined,
  lignes: T[],
  champs: (keyof T & string)[],
) {
  return lignes.map((l) => ({
    libelle: libelleMois(exercice, l.mois),
    ...Object.fromEntries(champs.map((c) => [c, enMds(Number(l[c]))])),
  }));
}

export interface LigneObjectif {
  libelle: string;
  objectif: number;
  recouvre: number;
  taux?: number | null;
}
