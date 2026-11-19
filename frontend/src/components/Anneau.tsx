import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip, type TooltipProps } from "recharts";

import { mds, pct } from "@/lib/format";
import { cn } from "@/lib/utils";

import type { PartAnneau } from "@/lib/anneau";

import { Montant } from "./Montant";

/**
 * Anneau de répartition (part d'un tout, ≤ 6 parts + « Autres »).
 * Chaque part est aussi écrite à côté (nom, % et montant) : l'identité ne repose jamais sur la couleur
 * seule, et les teintes sous 3:1 de contraste restent lisibles.
 */
export function Anneau({
  libelle,
  parts,
  onPart,
  actif,
}: {
  libelle: string;
  parts: PartAnneau[];
  onPart?: (code: string) => void;
  actif?: string | null;
}) {
  const total = parts.reduce((s, p) => s + Math.max(0, p.valeur), 0);
  // Une part négative (dégagements) ne se dessine pas ; elle reste écrite dans la liste.
  const dessin = parts.filter((p) => p.valeur > 0);
  const resume = parts.map((p) => `${p.libelle} ${pct(total ? p.valeur / total : null)}`).join(", ");
  return (
    <div className="flex min-w-0 flex-col gap-3">
      <div className="relative h-44" role="img" aria-label={`${libelle} : ${resume}`}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={dessin}
              dataKey="valeur"
              nameKey="libelle"
              innerRadius="62%"
              outerRadius="96%"
              startAngle={90}
              endAngle={-270}
              stroke="var(--surface)"
              strokeWidth={2}
              isAnimationActive={false}
              onClick={(d: { payload?: PartAnneau }) =>
                d.payload?.cliquable && onPart ? onPart(d.payload.code) : undefined
              }
            >
              {dessin.map((p) => (
                <Cell
                  key={p.code}
                  fill={p.couleur}
                  cursor={p.cliquable && onPart ? "pointer" : undefined}
                  opacity={actif && actif !== p.code ? 0.35 : 1}
                />
              ))}
            </Pie>
            <Tooltip content={<Infobulle total={total} />} isAnimationActive={false} />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="chiffres text-base font-bold text-ink">{mds(total)}</span>
          <span className="text-xs text-ink-2">total</span>
        </div>
      </div>
      <ul className="flex flex-col gap-1 text-sm">
        {parts.map((p) => {
          const contenu = (
            <>
              <span
                aria-hidden
                className="mt-1 h-2.5 w-2.5 shrink-0 rounded-sm"
                style={{ background: p.couleur }}
              />
              <span className="min-w-0 flex-1 text-ink" title={p.libelle}>
                {p.libelle}
              </span>
              <span className="chiffres shrink-0 text-right">
                <span className="font-bold text-ink">{pct(total ? p.valeur / total : null)}</span>{" "}
                <span className="text-ink-2">{mds(p.valeur)}</span>
              </span>
            </>
          );
          return (
            <li key={p.code}>
              {p.cliquable && onPart ? (
                <button
                  type="button"
                  onClick={() => onPart(p.code)}
                  aria-pressed={actif === p.code}
                  className={cn(
                    "flex w-full items-start gap-2 rounded-sm px-1 text-left hover:bg-hover",
                    actif === p.code && "bg-gold-tint",
                  )}
                >
                  {contenu}
                </button>
              ) : (
                <div className="flex items-start gap-2 px-1">{contenu}</div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function Infobulle({ active, payload, total }: TooltipProps<number, string> & { total: number }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload as PartAnneau;
  return (
    <div className="carte px-3 py-2 text-sm">
      <p className="font-bold text-ink">{p.libelle}</p>
      <p className="text-ink">
        <Montant gnf={p.valeur} />{" "}
        <span className="chiffres text-ink-2">({pct(total ? p.valeur / total : null)} du total)</span>
      </p>
    </div>
  );
}
