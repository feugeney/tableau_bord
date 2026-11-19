import { ChevronDown, Columns3 } from "lucide-react";

import { cn } from "@/lib/utils";

import { Case } from "./ui/formulaire";

export interface ColonneChoisissable {
  id: string;
  libelle: string;
}

/** Bouton « Colonnes » : ouvre la liste des colonnes à afficher ; le nombre de colonnes masquées y figure. */
export function BoutonColonnes({
  ouvert,
  onBascule,
  masquees,
  controle,
}: {
  ouvert: boolean;
  onBascule: () => void;
  masquees: number;
  controle: string;
}) {
  return (
    <button
      type="button"
      onClick={onBascule}
      aria-expanded={ouvert}
      aria-controls={controle}
      className={cn(
        "inline-flex min-h-8 items-center gap-1.5 rounded-sm border px-3 text-sm font-bold",
        masquees ? "border-gold bg-gold-tint text-ink" : "border-border bg-surface text-ink hover:bg-hover",
      )}
    >
      <Columns3 className="h-4 w-4" aria-hidden />
      Colonnes
      {masquees > 0 && (
        <span className="chiffres rounded-full bg-navy px-1.5 text-xs text-on-navy" title="Colonnes masquées">
          −{masquees}
        </span>
      )}
      <ChevronDown className={cn("h-4 w-4 transition-transform", ouvert && "rotate-180")} aria-hidden />
    </button>
  );
}

/**
 * Cases à cocher des colonnes d'un tableau. Au moins une colonne reste affichée ; « Rétablir » revient
 * au jeu par défaut.
 */
export function PanneauColonnes({
  id,
  colonnes,
  visibles,
  onChange,
  onRetablir,
}: {
  id: string;
  colonnes: ColonneChoisissable[];
  visibles: string[];
  onChange: (visibles: string[]) => void;
  onRetablir: () => void;
}) {
  const ensemble = new Set(visibles);
  return (
    <fieldset id={id} className="mb-3 rounded border border-border bg-surface p-3">
      <legend className="etiquette px-1">Colonnes affichées et exportées</legend>
      <div className="grid gap-x-4 gap-y-1 sm:grid-cols-2 lg:grid-cols-4">
        {colonnes.map((c) => {
          const coche = ensemble.has(c.id);
          return (
            <Case
              key={c.id}
              libelle={c.libelle}
              checked={coche}
              disabled={coche && ensemble.size === 1}
              onChange={() =>
                onChange(
                  // L'ordre du tableau est conservé, quel que soit l'ordre des clics.
                  colonnes.map((x) => x.id).filter((x) => (x === c.id ? !coche : ensemble.has(x))),
                )
              }
            />
          );
        })}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-3 text-sm">
        <button
          type="button"
          onClick={onRetablir}
          className="font-bold text-ink underline underline-offset-2"
        >
          Rétablir les colonnes par défaut
        </button>
        <span className="text-ink-2">Le ministère reste toujours affiché.</span>
      </div>
    </fieldset>
  );
}
