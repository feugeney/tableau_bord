import { AlertTriangle, Database, Info, PlugZap, RotateCw } from "lucide-react";
import type { ReactNode } from "react";

import { useSources } from "@/api/hooks";
import type { Meta } from "@/api/types";
import { dateFr, dateHeureFr } from "@/lib/format";
import { nomSource } from "@/lib/sources";
import { cn } from "@/lib/utils";

import { Bouton } from "./ui/primitives";

const LIBELLES = { reel: "réel", demo: "illustration", non_raccorde: "non raccordée" } as const;

/**
 * Pastille de source, identique partout :
 * « Chaîne Dépense · réel · 15/09/2026 », « SAFIG · illustration », « SCIE · non raccordée ».
 */
export function SourceBadge({
  meta,
  className,
}: {
  meta?: Pick<Meta, "source" | "statut_source" | "date_situation" | "application"> | null;
  className?: string;
}) {
  if (!meta) return null;
  const demo = meta.statut_source === "demo";
  const Icone = meta.statut_source === "reel" ? Database : demo ? Info : PlugZap;
  const parties = [
    nomSource(meta.source),
    LIBELLES[meta.statut_source],
    meta.statut_source === "reel" && meta.date_situation ? dateFr(meta.date_situation) : null,
  ].filter(Boolean) as string[];
  return (
    <span
      className={cn(
        "inline-flex max-w-full items-start gap-1 rounded-sm border px-1.5 py-0.5 text-xs text-ink-2 [&>svg]:mt-0.5",
        demo ? "border-dashed border-gold bg-gold-tint" : "border-border bg-surface",
        className,
      )}
      title={`Source : ${meta.application ?? nomSource(meta.source)}`}
      translate="no"
    >
      <Icone className="h-3 w-3 shrink-0" aria-hidden />
      {/* Passe à la ligne entre deux éléments plutôt que de tronquer la date. */}
      <span className="flex min-w-0 flex-wrap gap-x-1">
        {parties.map((p, i) => (
          <span key={p} className="whitespace-nowrap">
            {p}
            {i < parties.length - 1 ? " ·" : ""}
          </span>
        ))}
      </span>
    </span>
  );
}

/** Bandeau des pages alimentées par des données d'illustration : visible sans agresser. */
export function DemoBanner({ source, precision }: { source: string; precision?: ReactNode }) {
  const sources = useSources();
  const s = sources.data?.find((x) => x.code === source);
  const nom = s ? `${nomSource(source)} (${s.structure})` : nomSource(source);
  return (
    <div
      role="note"
      className="mb-4 flex items-start gap-2 rounded border border-dashed border-gold bg-gold-tint px-4 py-2 text-sm text-ink"
    >
      <Info className="mt-0.5 h-4 w-4 shrink-0 text-ink-2" aria-hidden />
      <p>
        <strong>Données d'illustration.</strong> Cette page sera alimentée par {nom} une fois l'application
        raccordée à l'entrepôt. Les chiffres montrent la forme de l'information, pas la situation réelle ; les
        organismes cités sont fictifs.{precision ? <> {precision}</> : null}
      </p>
    </div>
  );
}

/** État vide explicite : « Source non raccordée · dernière tentative le … ». */
export function EtatVide({ meta, children }: { meta?: Meta | null; children?: ReactNode }) {
  const sources = useSources();
  const source = sources.data?.find((s) => s.code === meta?.source);
  const tentative = source?.dernier_chargement;
  const nonRaccorde = !meta || meta.statut_source === "non_raccorde";
  return (
    <div className="carte px-6 py-8">
      <div className="flex items-start gap-3">
        <PlugZap className="mt-1 h-5 w-5 shrink-0 text-ink-2" aria-hidden />
        <div className="min-w-0">
          <h2 className="text-md font-bold text-ink">
            {nonRaccorde ? "Source non raccordée" : "Aucune situation pour ces filtres"}
          </h2>
          <p className="text-base text-ink-2">
            {nonRaccorde ? (
              <>
                {source?.application ?? (meta ? nomSource(meta.source) : "Cette application")}
                {source?.structure ? ` (${source.structure})` : ""}
                {" · "}
                {tentative
                  ? `dernière tentative le ${dateHeureFr(tentative.date)}${tentative.statut === "echec" ? " (échec)" : ""}`
                  : "aucune tentative de chargement"}
              </>
            ) : (
              "Aucune donnée pour l'exercice et la date de situation choisis."
            )}
          </p>
          {source?.remarque && <p className="text-sm text-ink-3">{source.remarque}</p>}
        </div>
      </div>
      {children && <div className="mt-4">{children}</div>}
    </div>
  );
}

export function ErreurBloc({ erreur, onReessayer }: { erreur: unknown; onReessayer?: () => void }) {
  const message = erreur instanceof Error ? erreur.message : "Erreur inattendue.";
  return (
    <div role="alert" className="carte flex flex-wrap items-center gap-3 px-4 py-3 text-base">
      <AlertTriangle className="h-4 w-4 shrink-0 text-ink-2" aria-hidden />
      <p className="min-w-0 flex-1">
        <strong>Données indisponibles.</strong> {message}
      </p>
      {onReessayer && (
        <Bouton onClick={onReessayer}>
          <RotateCw className="h-4 w-4" aria-hidden /> Réessayer
        </Bouton>
      )}
    </div>
  );
}
