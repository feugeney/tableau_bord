import * as RadixTooltip from "@radix-ui/react-tooltip";
import { Info } from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

/** Carte de section : bordure fine, rayon 6 px, sans ombre. L'id alimente le sommaire latéral. */
export function Carte({
  id,
  titre,
  sousTitre,
  actions,
  children,
  className,
  pied,
}: {
  id?: string;
  titre?: ReactNode;
  sousTitre?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  pied?: ReactNode;
}) {
  return (
    <section
      id={id}
      aria-labelledby={titre && id ? `${id}-titre` : undefined}
      className={cn("carte flex min-w-0 flex-col p-4", className)}
    >
      {(titre || actions) && (
        <header className="mb-3 flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
          <div className="min-w-0">
            {titre && (
              <h2 id={id ? `${id}-titre` : undefined} className="text-md font-bold text-ink">
                {titre}
              </h2>
            )}
            {sousTitre && <p className="text-sm text-ink-2">{sousTitre}</p>}
          </div>
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className="min-w-0 flex-1">{children}</div>
      {pied && <div className="mt-3 border-t border-border pt-3">{pied}</div>}
    </section>
  );
}

export function Bouton({
  variante = "secondaire",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variante?: "primaire" | "secondaire" | "discret" }) {
  return (
    <button
      type="button"
      className={cn(
        "inline-flex min-h-8 items-center justify-center gap-1.5 rounded-sm px-3 text-sm font-bold disabled:opacity-50",
        variante === "primaire" && "bg-navy text-on-navy hover:opacity-90",
        variante === "secondaire" && "border border-border bg-surface text-ink hover:bg-hover",
        variante === "discret" && "text-ink-2 hover:bg-hover hover:text-ink",
        className,
      )}
      {...props}
    />
  );
}

/** Contrôle segmenté exclusif (filtres) ; la sélection est portée par l'or. */
export function Segment<T extends string>({
  valeur,
  options,
  onChange,
  libelle,
}: {
  valeur: T;
  options: { valeur: T; libelle: string }[];
  onChange: (v: T) => void;
  libelle: string;
}) {
  return (
    <div role="radiogroup" aria-label={libelle} className="flex flex-wrap gap-1">
      {options.map((o) => {
        const choisi = valeur === o.valeur;
        return (
          <button
            key={o.valeur}
            type="button"
            role="radio"
            aria-checked={choisi}
            onClick={() => onChange(o.valeur)}
            className={cn(
              "min-h-8 rounded-sm border px-3 text-sm",
              choisi
                ? "border-gold bg-gold-tint font-bold text-ink"
                : "border-border bg-surface text-ink-2 hover:bg-hover hover:text-ink",
            )}
          >
            {o.libelle}
          </button>
        );
      })}
    </div>
  );
}

export function Infobulle({ contenu, children }: { contenu: ReactNode; children?: ReactNode }) {
  return (
    <RadixTooltip.Root delayDuration={150}>
      <RadixTooltip.Trigger asChild>
        {children ?? (
          <button
            type="button"
            aria-label="Explication"
            className="sans-impression rounded-sm text-ink-3 hover:text-ink"
          >
            <Info className="h-4 w-4" aria-hidden />
          </button>
        )}
      </RadixTooltip.Trigger>
      <RadixTooltip.Portal>
        <RadixTooltip.Content
          sideOffset={6}
          className="z-50 max-w-xs rounded-sm bg-navy px-3 py-2 text-sm text-on-navy"
        >
          {contenu}
          <RadixTooltip.Arrow className="fill-navy" />
        </RadixTooltip.Content>
      </RadixTooltip.Portal>
    </RadixTooltip.Root>
  );
}

export const TooltipProvider = RadixTooltip.Provider;

export function Squelette({ className }: { className?: string }) {
  return <div aria-hidden className={cn("animate-pulse rounded-sm bg-grid", className)} />;
}
