import { ESPACE_FINE, nombre } from "@/lib/format";
import { cn } from "@/lib/utils";

/** Montant en milliards de GNF : valeur en chiffres tabulaires, unité « Mds » en petit et en gris. */
export function Montant({
  gnf,
  decimales = 1,
  className,
}: {
  gnf: number | null | undefined;
  decimales?: number;
  className?: string;
}) {
  if (gnf === null || gnf === undefined || Number.isNaN(gnf)) return <span className={className}>—</span>;
  return (
    <span className={cn("chiffres whitespace-nowrap", className)}>
      {nombre(gnf / 1e9, decimales)}
      {ESPACE_FINE}
      <abbr title="milliards de francs guinéens" className="text-sm font-normal text-ink-3 no-underline">
        Mds
      </abbr>
    </span>
  );
}

/** Pourcentage avec « % » en petit. */
export function Pourcentage({ ratio, className }: { ratio: number | null | undefined; className?: string }) {
  if (ratio === null || ratio === undefined || Number.isNaN(ratio))
    return <span className={className}>—</span>;
  return (
    <span className={cn("chiffres whitespace-nowrap", className)}>
      {nombre(Math.round(ratio * 100))}
      {ESPACE_FINE}
      <span className="text-sm font-normal text-ink-3">%</span>
    </span>
  );
}
