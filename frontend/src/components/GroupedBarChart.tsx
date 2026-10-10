import { Table2 } from "lucide-react";
import { useId, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipProps,
} from "recharts";

import { nombre, pct } from "@/lib/format";

import { Montant } from "./Montant";
import { Bouton } from "./ui/primitives";

export interface Serie {
  cle: string;
  libelle: string;
  /** Couleurs de données validées : var(--serie-1), var(--serie-2), rampe var(--phase-n). */
  couleur: string;
}

const AXE = { fill: "var(--ink-3)", fontSize: 12 };

/**
 * Barres groupées (un seul axe vertical, en milliards de GNF), ligne de seuil optionnelle,
 * infobulle « mois, valeur, part » et bouton « Voir le tableau » pour l'accessibilité et l'impression.
 */
export function GroupedBarChart<T extends Record<string, unknown>>({
  donnees,
  categorie,
  series,
  seuil,
  miseEnEvidence,
  hauteur = 240,
  libelle,
}: {
  donnees: T[];
  categorie: keyof T & string;
  series: Serie[];
  seuil?: { valeur: number; libelle: string };
  miseEnEvidence?: (ligne: T, serie: Serie) => string | undefined;
  hauteur?: number;
  libelle: string;
}) {
  const [tableau, setTableau] = useState(false);
  const idTableau = useId();
  const totaux = useMemo(
    () =>
      Object.fromEntries(
        series.map((s) => [s.cle, donnees.reduce((t, d) => t + (Number(d[s.cle]) || 0), 0)]),
      ),
    [donnees, series],
  );

  return (
    <figure className="w-full min-w-0">
      <figcaption className="sr-only">{libelle} (en milliards de GNF)</figcaption>
      <div
        role="img"
        aria-label={`${libelle}, en milliards de GNF`}
        style={{ height: hauteur }}
        className="w-full"
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={donnees}
            barGap={2}
            barCategoryGap="24%"
            margin={{ top: 8, right: 4, left: 0, bottom: 0 }}
          >
            <CartesianGrid vertical={false} stroke="var(--grid)" />
            <XAxis
              dataKey={categorie}
              tickLine={false}
              axisLine={false}
              tick={AXE}
              interval="preserveStartEnd"
              minTickGap={8}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              width={48}
              tick={AXE}
              tickFormatter={(v: number) => nombre(v)}
            />
            <Tooltip
              cursor={{ fill: "var(--hover)" }}
              content={<InfobulleMds totaux={totaux} />}
              isAnimationActive={false}
            />
            {series.length > 1 && (
              <Legend
                verticalAlign="top"
                align="left"
                iconType="square"
                iconSize={10}
                wrapperStyle={{ fontSize: 13, paddingBottom: 8 }}
                formatter={(valeur: string) => <span style={{ color: "var(--ink-2)" }}>{valeur}</span>}
              />
            )}

            {series.map((s) => (
              <Bar
                key={s.cle}
                dataKey={s.cle}
                name={s.libelle}
                fill={s.couleur}
                radius={[4, 4, 0, 0]}
                maxBarSize={20}
                isAnimationActive={false}
              >
                {miseEnEvidence &&
                  donnees.map((d, i) => <Cell key={i} fill={miseEnEvidence(d, s) ?? s.couleur} />)}
              </Bar>
            ))}
            {seuil && (
              <ReferenceLine
                y={seuil.valeur}
                stroke="var(--objectif)"
                strokeWidth={2}
                strokeDasharray="5 4"
                ifOverflow="extendDomain"
              />
            )}
          </BarChart>
        </ResponsiveContainer>
      </div>
      {seuil && (
        <p className="mt-2 flex items-center gap-2 text-sm text-ink-2">
          <svg width="22" height="6" aria-hidden className="shrink-0">
            <line
              x1="0"
              y1="3"
              x2="22"
              y2="3"
              stroke="var(--objectif)"
              strokeWidth="2"
              strokeDasharray="5 4"
            />
          </svg>
          <span>
            {seuil.libelle} : <Montant gnf={seuil.valeur * 1e9} />
          </span>
        </p>
      )}
      <div className="sans-impression mt-2 flex justify-end">
        <Bouton
          variante="discret"
          onClick={() => setTableau((t) => !t)}
          aria-expanded={tableau}
          aria-controls={idTableau}
        >
          <Table2 className="h-4 w-4" aria-hidden /> {tableau ? "Masquer le tableau" : "Voir le tableau"}
        </Bouton>
      </div>
      {/* Le tableau est toujours imprimé : il remplace les infobulles sur papier. */}
      <div id={idTableau} className={tableau ? "mt-2 overflow-x-auto" : "seulement-impression mt-2"}>
        <table className="w-full text-sm">
          <caption className="sr-only">{libelle}</caption>
          <thead>
            <tr className="border-b border-border">
              <th scope="col" className="etiquette py-1 pr-3 text-left">
                Période
              </th>
              {series.map((s) => (
                <th key={s.cle} scope="col" className="etiquette py-1 pl-3 text-right">
                  {s.libelle}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {donnees.map((d, i) => (
              <tr key={i} className="border-b border-border last:border-0">
                <th scope="row" className="py-1 pr-3 text-left font-normal text-ink">
                  {String(d[categorie])}
                </th>
                {series.map((s) => (
                  <td key={s.cle} className="py-1 pl-3 text-right text-ink">
                    <Montant gnf={(Number(d[s.cle]) || 0) * 1e9} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </figure>
  );
}

function InfobulleMds({
  active,
  payload,
  label,
  totaux,
}: TooltipProps<number, string> & { totaux: Record<string, number> }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="carte px-3 py-2 text-sm">
      <p className="font-bold text-ink">{label}</p>
      {payload.map((p) => {
        const valeur = Number(p.value ?? 0);
        const total = totaux[String(p.dataKey)] || 0;
        return (
          <p key={String(p.dataKey)} className="flex items-center gap-2 text-ink">
            <span aria-hidden className="h-2 w-2 rounded-sm" style={{ background: p.color }} />
            {p.name} : <Montant gnf={valeur * 1e9} />
            <span className="chiffres text-ink-2">({pct(total ? valeur / total : null)} du total)</span>
          </p>
        );
      })}
    </div>
  );
}
