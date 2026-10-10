import { Check } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { useSources, useStatutAlerte } from "@/api/hooks";
import type { Alerte, Severite } from "@/api/types";
import { DOMAINES_LIBELLES } from "@/lib/sources";

import { ETATS, PastilleEtat } from "./Indicateurs";
import { SourceBadge } from "./Source";
import { Bouton, Segment } from "./ui/primitives";

type FiltreGravite = "toutes" | Severite;

function LigneAlerte({ a, compact }: { a: Alerte; compact: boolean }) {
  const statut = useStatutAlerte();
  const sources = useSources();
  const statutSource = sources.data?.find((s) => s.code === a.source_code)?.statut ?? "reel";
  const { couleur, libelle } = ETATS[a.severite];
  return (
    <li className="flex gap-3 border-l-4 bg-surface py-2 pl-3 pr-1" style={{ borderLeftColor: couleur }}>
      <PastilleEtat etat={a.severite} />
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-3">
          <h3 className="min-w-0 text-base font-bold text-ink">
            <span className="sr-only">{libelle} : </span>
            {a.lien ? (
              <Link to={a.lien} className="hover:underline">
                {a.titre}
              </Link>
            ) : (
              a.titre
            )}
          </h3>
          {a.valeur && (
            <span className="chiffres shrink-0 whitespace-nowrap text-md font-bold text-ink">{a.valeur}</span>
          )}
        </div>
        {a.action_recommandee && (
          <p className="text-sm font-bold text-ink">Action recommandée : {a.action_recommandee}</p>
        )}
        {!compact && <p className="text-sm text-ink-2">{a.message}</p>}
        <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
          {a.source_code && (
            <SourceBadge
              meta={{ source: a.source_code, statut_source: statutSource, date_situation: a.date_situation }}
            />
          )}
          {a.statut !== "traitee" && (
            <button
              type="button"
              className="sans-presentation sans-impression inline-flex items-center gap-1 rounded-sm px-1 text-xs text-ink-2 hover:bg-hover hover:text-ink"
              onClick={() => statut.mutate({ id: a.id, statut: "traitee" })}
              disabled={statut.isPending}
            >
              <Check className="h-3 w-3" aria-hidden /> Marquer comme traitée
            </button>
          )}
          {compact && (
            <details className="text-sm text-ink-2 open:basis-full">
              <summary className="cursor-pointer select-none rounded-sm px-1 text-xs hover:bg-hover hover:text-ink">
                Détail
              </summary>
              <p className="mt-1 text-sm text-ink-2">{a.message}</p>
            </details>
          )}
        </div>
      </div>
    </li>
  );
}

/** Alertes classées par gravité, filtrables par gravité et par domaine. */
export function ListeAlertes({
  alertes,
  compact = false,
  limite,
  filtres = true,
  titre,
  titreId,
}: {
  alertes: Alerte[];
  compact?: boolean;
  limite?: number;
  filtres?: boolean;
  titre?: string;
  titreId?: string;
}) {
  const [gravite, setGravite] = useState<FiltreGravite>("toutes");
  const [domaine, setDomaine] = useState("");
  const [tout, setTout] = useState(false);

  const domaines = useMemo(() => [...new Set(alertes.map((a) => a.domaine))], [alertes]);
  const filtrees = alertes
    .filter((a) => (gravite === "toutes" || a.severite === gravite) && (!domaine || a.domaine === domaine))
    .sort((x, y) => ETATS[x.severite].rang - ETATS[y.severite].rang);
  const visibles = limite && !tout ? filtrees.slice(0, limite) : filtrees;

  return (
    <div className="flex flex-col gap-2">
      {(titre || (filtres && alertes.length > 0)) && (
        <div className="flex flex-wrap items-center gap-2">
          {titre && (
            <h2 id={titreId} className="mr-auto text-md font-bold text-ink">
              {titre}{" "}
              <span className="chiffres text-sm font-normal text-ink-2" aria-live="polite">
                ({filtrees.length})
              </span>
            </h2>
          )}
          {filtres && alertes.length > 0 && (
            <div className="sans-impression sans-presentation flex flex-wrap items-center gap-2">
              <Segment<FiltreGravite>
                libelle="Filtrer par gravité"
                valeur={gravite}
                onChange={setGravite}
                options={[
                  { valeur: "toutes", libelle: "Toutes" },
                  { valeur: "critique", libelle: "Critiques" },
                  { valeur: "serieux", libelle: "Sérieuses" },
                  { valeur: "vigilance", libelle: "Vigilance" },
                ]}
              />
              {domaines.length > 1 && (
                <label className="flex items-center gap-1.5 text-sm text-ink-2">
                  <span className="sr-only">Filtrer par domaine</span>
                  <select
                    value={domaine}
                    onChange={(e) => setDomaine(e.target.value)}
                    className="min-h-8 rounded-sm border border-border px-2 text-sm"
                  >
                    <option value="">Tous les domaines</option>
                    {domaines.map((d) => (
                      <option key={d} value={d}>
                        {DOMAINES_LIBELLES[d] ?? d}
                      </option>
                    ))}
                  </select>
                </label>
              )}
            </div>
          )}
        </div>
      )}
      {visibles.length ? (
        <ul className="flex flex-col divide-y divide-border">
          {visibles.map((a) => (
            <LigneAlerte key={a.id} a={a} compact={compact} />
          ))}
        </ul>
      ) : (
        <p className="py-2 text-base text-ink-2">Aucune alerte pour ces critères.</p>
      )}
      {limite && filtrees.length > limite && (
        <Bouton
          variante="discret"
          className="sans-impression self-start"
          onClick={() => setTout((t) => !t)}
          aria-expanded={tout}
        >
          {tout
            ? "Afficher moins"
            : filtrees.length - limite === 1
              ? "Voir l'autre alerte"
              : `Voir les ${filtrees.length - limite} autres alertes`}
        </Bouton>
      )}
    </div>
  );
}
