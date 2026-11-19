import { ChevronDown, SlidersHorizontal, X } from "lucide-react";
import { useMemo, useState } from "react";

import { useDonnees } from "@/api/hooks";
import { useFiltres, type Critere } from "@/hooks/useFiltres";
import { mds } from "@/lib/format";
import { cn } from "@/lib/utils";

interface Valeur {
  code: string;
  libelle: string;
  nb_lignes: number;
  credit: number;
}

interface DefinitionCritere {
  cle: Critere;
  libelle: string;
  valeurs: Valeur[];
  disponible: boolean;
  raison: string | null;
}

/** Bouton « Filtres » : ouvre le panneau des critères multiples ; le nombre de critères actifs y figure. */
export function BoutonFiltres({ ouvert, onBascule }: { ouvert: boolean; onBascule: () => void }) {
  const { filtres } = useFiltres();
  const actifs = Object.values(filtres.criteres).filter((v) => v?.length).length;
  return (
    <button
      type="button"
      onClick={onBascule}
      aria-expanded={ouvert}
      aria-controls="panneau-filtres"
      className={cn(
        "inline-flex min-h-8 items-center gap-1.5 rounded-sm border px-3 text-sm font-bold",
        actifs ? "border-gold bg-gold-tint text-ink" : "border-border bg-surface text-ink hover:bg-hover",
      )}
    >
      <SlidersHorizontal className="h-4 w-4" aria-hidden />
      Filtres
      {actifs > 0 && (
        <span className="chiffres rounded-full bg-navy px-1.5 text-xs text-on-navy">{actifs}</span>
      )}
      <ChevronDown className={cn("h-4 w-4 transition-transform", ouvert && "rotate-180")} aria-hidden />
    </button>
  );
}

/**
 * Panneau des critères multiples (ministère, programme, titre, fonction, pilier, BAS, zone, source, bailleur).
 * Plusieurs valeurs par critère (OU), critères cumulés (ET). Les critères actifs restent affichés en étiquettes,
 * panneau fermé, pour que la page ne paraisse jamais non filtrée.
 */
export function PanneauFiltres({ ouvert }: { ouvert: boolean }) {
  const { filtres, definirCritere } = useFiltres();
  const r = useDonnees<{ criteres: DefinitionCritere[] }>("/depense/criteres/");
  const definitions = useMemo(() => r.data?.data?.criteres ?? [], [r.data]);
  const libelles = useMemo(() => {
    const m = new Map<string, string>();
    for (const d of definitions) for (const v of d.valeurs) m.set(`${d.cle}:${v.code}`, v.libelle);
    return m;
  }, [definitions]);
  const actifs = (Object.entries(filtres.criteres) as [Critere, string[]][]).filter(([, v]) => v.length);

  return (
    <div className="mb-4 flex flex-col gap-3">
      {ouvert && (
        <section id="panneau-filtres" aria-label="Filtres à critères multiples" className="carte p-4">
          <p className="mb-3 text-sm text-ink-2">
            Plusieurs valeurs par critère ; les critères se cumulent. Toute la page est recalculée, exports
            compris.
          </p>
          {r.isPending ? (
            <p className="text-sm text-ink-2">Chargement des critères…</p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {definitions.map((d) => (
                <ChoixCritere
                  key={d.cle}
                  definition={d}
                  selection={filtres.criteres[d.cle] ?? []}
                  onChange={(v) => definirCritere(d.cle, v)}
                />
              ))}
            </div>
          )}
        </section>
      )}
      {actifs.length > 0 && (
        <div className="flex flex-wrap items-center gap-2" aria-label="Filtres actifs">
          <span className="text-sm text-ink-2">Filtres actifs :</span>
          {actifs.flatMap(([cle, valeurs]) => {
            const def = definitions.find((d) => d.cle === cle);
            return valeurs.map((code) => (
              <span
                key={`${cle}:${code}`}
                className="inline-flex items-center gap-1 rounded-full border border-gold bg-gold-tint py-0.5 pl-2.5 pr-1 text-sm text-ink"
              >
                <span className="text-ink-2">{def?.libelle ?? cle} :</span>{" "}
                {libelles.get(`${cle}:${code}`) ?? code}
                <button
                  type="button"
                  onClick={() =>
                    definirCritere(
                      cle,
                      valeurs.filter((v) => v !== code),
                    )
                  }
                  className="rounded-full p-0.5 hover:bg-hover"
                  aria-label={`Retirer ${libelles.get(`${cle}:${code}`) ?? code}`}
                >
                  <X className="h-3.5 w-3.5" aria-hidden />
                </button>
              </span>
            ));
          })}
          <button
            type="button"
            onClick={() => definirCritere(null)}
            className="text-sm font-bold text-navy underline dark:text-ink"
          >
            Tout effacer
          </button>
        </div>
      )}
    </div>
  );
}

function ChoixCritere({
  definition: d,
  selection,
  onChange,
}: {
  definition: DefinitionCritere;
  selection: string[];
  onChange: (valeurs: string[]) => void;
}) {
  const [recherche, setRecherche] = useState("");
  const visibles = d.valeurs.filter((v) => v.libelle.toLowerCase().includes(recherche.trim().toLowerCase()));
  const resume = !selection.length
    ? "Tous"
    : selection.length === 1
      ? (d.valeurs.find((v) => v.code === selection[0])?.libelle ?? selection[0])
      : `${selection.length} sélectionnés`;

  if (!d.disponible) {
    return (
      <div className="rounded-sm border border-border p-2">
        <p className="text-sm font-bold text-ink-2">{d.libelle}</p>
        <p className="text-xs text-ink-2">{d.raison}</p>
      </div>
    );
  }
  return (
    <details className="group rounded-sm border border-border bg-surface open:border-gold">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 p-2">
        <span className="min-w-0">
          <span className="block text-sm font-bold text-ink">{d.libelle}</span>
          <span className={cn("block truncate text-xs", selection.length ? "text-ink" : "text-ink-2")}>
            {resume}
          </span>
        </span>
        <ChevronDown className="h-4 w-4 shrink-0 text-ink-2 group-open:rotate-180" aria-hidden />
      </summary>
      <div className="border-t border-border p-2">
        {d.valeurs.length > 8 && (
          <input
            type="search"
            value={recherche}
            onChange={(e) => setRecherche(e.target.value)}
            placeholder="Rechercher…"
            aria-label={`Rechercher dans ${d.libelle}`}
            className="mb-2 h-8 w-full rounded-sm border border-border bg-surface px-2 text-sm text-ink"
          />
        )}
        <fieldset>
          <legend className="sr-only">{d.libelle}</legend>
          <ul className="flex max-h-56 flex-col gap-0.5 overflow-y-auto">
            {visibles.map((v) => {
              const coche = selection.includes(v.code);
              return (
                <li key={v.code}>
                  <label className="flex cursor-pointer items-start gap-2 rounded-sm px-1 py-0.5 text-sm hover:bg-hover">
                    <input
                      type="checkbox"
                      checked={coche}
                      onChange={() =>
                        onChange(coche ? selection.filter((c) => c !== v.code) : [...selection, v.code])
                      }
                      className="mt-0.5 accent-[var(--navy)]"
                    />
                    <span className="min-w-0 flex-1 text-ink">{v.libelle}</span>
                    <span className="chiffres shrink-0 text-xs text-ink-2">{mds(v.credit)}</span>
                  </label>
                </li>
              );
            })}
          </ul>
        </fieldset>
        {selection.length > 0 && (
          <button
            type="button"
            onClick={() => onChange([])}
            className="mt-2 text-xs font-bold text-navy underline dark:text-ink"
          >
            Tout désélectionner
          </button>
        )}
      </div>
    </details>
  );
}
