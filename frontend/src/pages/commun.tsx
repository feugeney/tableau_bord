import type { UseQueryResult } from "@tanstack/react-query";
import type { ReactNode } from "react";

import type { Enveloppe } from "@/api/types";
import { BoutonExport } from "@/components/BoutonExport";
import { DemoBanner, ErreurBloc, EtatVide } from "@/components/Source";
import { Squelette } from "@/components/ui/primitives";

/** Squelette de la forme finale d'une page : bandeau d'indicateurs puis deux cartes. */
export function SquelettePage({ indicateurs = 6 }: { indicateurs?: number }) {
  return (
    <div aria-busy="true" aria-label="Chargement des données" className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-px overflow-hidden rounded border border-border bg-border sm:grid-cols-2 xl:grid-cols-6">
        {Array.from({ length: indicateurs }).map((_, i) => (
          <div key={i} className="flex flex-col gap-3 bg-surface p-4">
            <Squelette className="h-3 w-24" />
            <Squelette className="h-7 w-28" />
            <Squelette className="h-1.5 w-full" />
            <Squelette className="h-4 w-36" />
          </div>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-12">
        <Squelette className="h-64 lg:col-span-7" />
        <Squelette className="h-64 lg:col-span-5" />
      </div>
    </div>
  );
}

/** Chargement, erreur (avec « Réessayer »), source non raccordée et bandeau d'illustration. */
export function EtatPage<T>({
  requete,
  children,
  vide,
  indicateurs,
  precisionDemo,
}: {
  requete: UseQueryResult<Enveloppe<T>>;
  children: (data: T, env: Enveloppe<T>) => ReactNode;
  vide?: ReactNode;
  indicateurs?: number;
  precisionDemo?: ReactNode;
}) {
  if (requete.isPending) return <SquelettePage indicateurs={indicateurs} />;
  if (requete.isError) return <ErreurBloc erreur={requete.error} onReessayer={() => requete.refetch()} />;
  const env = requete.data;
  if (!env.data) return <EtatVide meta={env.meta}>{vide}</EtatVide>;
  return (
    <>
      {env.meta.statut_source === "demo" && <DemoBanner source={env.meta.source} precision={precisionDemo} />}
      {children(env.data, env)}
    </>
  );
}

/** Contenu d'une carte alimentée par sa propre requête (squelette à la hauteur finale). */
export function EtatBloc<T>({
  requete,
  children,
  hauteur = "h-48",
}: {
  requete: UseQueryResult<Enveloppe<T>>;
  children: (data: T, env: Enveloppe<T>) => ReactNode;
  hauteur?: string;
}) {
  if (requete.isPending) return <Squelette className={`${hauteur} w-full`} />;
  if (requete.isError) return <ErreurBloc erreur={requete.error} onReessayer={() => requete.refetch()} />;
  if (!requete.data.data) return <p className="text-base text-ink-2">Aucune donnée pour ces filtres.</p>;
  return <>{children(requete.data.data, requete.data)}</>;
}

/** Titre de page : nom de la page à gauche, commandes (filtres) à droite ou en dessous. */
export function TitrePage({
  titre,
  sousTitre,
  children,
  exporter,
}: {
  titre: string;
  sousTitre?: ReactNode;
  children?: ReactNode;
  /** Page exportée en Excel (ex. « depenses ») ; le bouton n'apparaît qu'aux profils autorisés. */
  exporter?: string;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
      <div className="min-w-0">
        <h1 className="text-lg font-bold text-navy dark:text-ink">{titre}</h1>
        {sousTitre && <p className="text-sm text-ink-2">{sousTitre}</p>}
      </div>
      {(children || exporter) && (
        <div className="sans-impression sans-presentation flex flex-wrap items-center gap-3">
          {children}
          {exporter && <BoutonExport page={exporter} />}
        </div>
      )}
    </div>
  );
}

/** Intitulé de zone (ordre de page : indicateurs → points d'attention → analyses → détail). */
export function Zone({ titre, children }: { titre: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-3">
      <h2 className="intitule-zone etiquette border-b border-border pb-1 !text-ink-2">{titre}</h2>
      {children}
    </div>
  );
}
