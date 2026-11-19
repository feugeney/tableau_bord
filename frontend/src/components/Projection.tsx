import { Table2 } from "lucide-react";
import { useId, useMemo, useState, type ReactNode } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipProps,
} from "recharts";

import { dateFr, enMds, moisCourt, nombre, pct } from "@/lib/format";

import { Note, StatusPill } from "./Indicateurs";
import { Montant } from "./Montant";
import { Bouton } from "./ui/primitives";

export interface Projection {
  date_situation: string;
  horizon: string;
  realise: number;
  cible: number | null;
  taux_realise: number | null;
  fiable: boolean;
  plafonne: boolean;
  motif?: string;
  methodes: Record<string, number>;
  bas: number | null;
  haut: number | null;
  central: number | null;
  taux_bas: number | null;
  taux_haut: number | null;
  trajectoire: { date: string; realise: number | null; bas: number | null; haut: number | null }[];
  retrospective: { arrete_au: string; prevu: number; realise: number; ecart: number }[];
  erreur_moyenne: number | null;
}

const AXE = { fill: "var(--ink-3)", fontSize: 12 };
const METHODES: Record<string, string> = {
  rythme_moyen: "Rythme moyen depuis le début de l'exécution",
  rythme_recent: "Rythme des trois derniers mois complets",
  profil_precedent: "Profil de fin d'année de l'exercice précédent",
};
const temps = (iso: string) => Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10));
const iso = (t: number) => new Date(t).toISOString().slice(0, 10);

interface Point {
  t: number;
  realise: number | null;
  fourchette: [number, number] | null;
  bas: number | null;
  haut: number | null;
}

/**
 * Cumul constaté (trait plein) et fourchette projetée jusqu'au 31 décembre (bande et bords en tirets) :
 * même mesure, donc même teinte ; le style du trait distingue le constaté du projeté. Un seul axe, en Mds GNF.
 */
function Graphique({
  p,
  libelle,
  libelleCible,
  libelleRealise,
}: {
  p: Projection;
  libelle: string;
  libelleCible: string;
  libelleRealise: string;
}) {
  const [tableau, setTableau] = useState(false);
  const idTableau = useId();
  const points = useMemo<Point[]>(
    () =>
      p.trajectoire.map((x) => ({
        t: temps(x.date),
        realise: x.realise === null ? null : enMds(x.realise),
        bas: x.bas === null ? null : enMds(x.bas),
        haut: x.haut === null ? null : enMds(x.haut),
        fourchette: x.bas === null || x.haut === null ? null : [enMds(x.bas), enMds(x.haut)],
      })),
    [p.trajectoire],
  );
  const annee = +p.horizon.slice(0, 4);
  const graduations = Array.from({ length: 12 }, (_, m) => Date.UTC(annee, m, 1));
  const cible = p.cible === null ? null : enMds(p.cible);

  return (
    <figure className="w-full min-w-0">
      <figcaption className="sr-only">{libelle} (en milliards de GNF)</figcaption>
      <div
        role="img"
        aria-label={`${libelle}, en milliards de GNF`}
        style={{ height: 260 }}
        className="w-full"
      >
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={points} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--grid)" />
            <XAxis
              dataKey="t"
              type="number"
              scale="time"
              domain={[Date.UTC(annee, 0, 1), temps(p.horizon)]}
              ticks={graduations}
              tickFormatter={(t: number) => moisCourt(iso(t))}
              tickLine={false}
              axisLine={false}
              tick={AXE}
              minTickGap={4}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              width={52}
              tick={AXE}
              domain={[0, "auto"]}
              tickFormatter={(v: number) => nombre(v)}
            />
            <Tooltip
              cursor={{ stroke: "var(--ink-3)", strokeWidth: 1 }}
              content={<Infobulle libelleRealise={libelleRealise} />}
              isAnimationActive={false}
            />
            <ReferenceLine x={temps(p.date_situation)} stroke="var(--border)" strokeWidth={1} />
            {cible !== null && (
              <ReferenceLine
                y={cible}
                stroke="var(--objectif)"
                strokeWidth={2}
                strokeDasharray="5 4"
                ifOverflow="extendDomain"
              />
            )}
            <Area
              dataKey="fourchette"
              stroke="none"
              fill="var(--serie-1)"
              fillOpacity={0.16}
              isAnimationActive={false}
              connectNulls={false}
            />
            <Line
              dataKey="haut"
              stroke="var(--serie-1)"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              dot={false}
              isAnimationActive={false}
            />
            <Line
              dataKey="bas"
              stroke="var(--serie-1)"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              dot={false}
              isAnimationActive={false}
            />
            <Line
              dataKey="realise"
              stroke="var(--serie-1)"
              strokeWidth={2}
              dot={{ r: 4, fill: "var(--serie-1)", stroke: "var(--surface)", strokeWidth: 2 }}
              activeDot={{ r: 5 }}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <ul className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm text-ink-2">
        <li className="flex items-center gap-2">
          <svg width="22" height="8" aria-hidden className="shrink-0">
            <line x1="0" y1="4" x2="22" y2="4" stroke="var(--serie-1)" strokeWidth="2" />
            <circle cx="11" cy="4" r="3" fill="var(--serie-1)" />
          </svg>
          {libelleRealise}
        </li>
        {p.fiable && (
          <li className="flex items-center gap-2">
            <svg width="22" height="10" aria-hidden className="shrink-0">
              <rect x="0" y="1" width="22" height="8" fill="var(--serie-1)" fillOpacity="0.16" />
              <line
                x1="0"
                y1="1"
                x2="22"
                y2="1"
                stroke="var(--serie-1)"
                strokeWidth="1.5"
                strokeDasharray="4 4"
              />
              <line
                x1="0"
                y1="9"
                x2="22"
                y2="9"
                stroke="var(--serie-1)"
                strokeWidth="1.5"
                strokeDasharray="4 4"
              />
            </svg>
            Fourchette projetée au {dateFr(p.horizon)}
          </li>
        )}
        {p.cible !== null && (
          <li className="flex items-center gap-2">
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
              {libelleCible} : <Montant gnf={p.cible} />
            </span>
          </li>
        )}
      </ul>
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
                Date
              </th>
              <th scope="col" className="etiquette py-1 pl-3 text-right">
                {libelleRealise}
              </th>
              <th scope="col" className="etiquette py-1 pl-3 text-right">
                Projection basse
              </th>
              <th scope="col" className="etiquette py-1 pl-3 text-right">
                Projection haute
              </th>
            </tr>
          </thead>
          <tbody>
            {p.trajectoire.map((x) => (
              <tr key={x.date} className="border-b border-border last:border-0">
                <th scope="row" className="py-1 pr-3 text-left font-normal text-ink">
                  {dateFr(x.date)}
                </th>
                {[x.realise, x.realise === null ? x.bas : null, x.realise === null ? x.haut : null].map(
                  (v, i) => (
                    <td key={i} className="py-1 pl-3 text-right text-ink">
                      {v === null ? "" : <Montant gnf={v} />}
                    </td>
                  ),
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </figure>
  );
}

function Infobulle({
  active,
  payload,
  libelleRealise,
}: TooltipProps<number, string> & { libelleRealise: string }) {
  const point = payload?.[0]?.payload as Point | undefined;
  if (!active || !point) return null;
  return (
    <div className="carte px-3 py-2 text-sm">
      <p className="font-bold text-ink">{dateFr(iso(point.t))}</p>
      {point.realise !== null && (
        <p className="text-ink">
          {libelleRealise} : <Montant gnf={point.realise * 1e9} />
        </p>
      )}
      {point.realise === null && point.bas !== null && point.haut !== null && (
        <p className="text-ink">
          Projection : entre <Montant gnf={point.bas * 1e9} /> et <Montant gnf={point.haut * 1e9} />
        </p>
      )}
    </div>
  );
}

/** Projection de fin d'exercice : phrase de synthèse, graphique, méthodes et vérification rétrospective. */
export function BlocProjection({
  p,
  grandeur,
  libelleCible,
  libelleRealise,
  sousLeSeuil = false,
  seuil,
  children,
}: {
  p: Projection;
  /** « engagés », « recouvrés »… */
  grandeur: string;
  libelleCible: string;
  libelleRealise: string;
  sousLeSeuil?: boolean;
  seuil?: number;
  children?: ReactNode;
}) {
  const fourchetteNulle = p.bas !== null && p.haut !== null && Math.abs(p.haut - p.bas) < 1e8;
  return (
    <div className="flex flex-col gap-3">
      {p.fiable ? (
        <p className="text-base text-ink">
          Au rythme constaté,{" "}
          <span className="font-bold">
            {fourchetteNulle ? (
              <Montant gnf={p.haut} />
            ) : (
              <>
                entre <Montant gnf={p.bas} /> et <Montant gnf={p.haut} />
              </>
            )}
          </span>{" "}
          seraient {grandeur} au {dateFr(p.horizon)}
          {p.taux_bas !== null && p.taux_haut !== null && (
            <>
              , soit{" "}
              <span className="font-bold">
                {fourchetteNulle ? pct(p.taux_haut) : `${pct(p.taux_bas)} à ${pct(p.taux_haut)}`}
              </span>{" "}
              {libelleCible === "Crédits actuels" ? "des crédits" : "de l'objectif"}
            </>
          )}
          , contre <Montant gnf={p.realise} />
          {p.taux_realise !== null ? ` (${pct(p.taux_realise)})` : ""} au {dateFr(p.date_situation)}.{" "}
          {sousLeSeuil && seuil !== undefined && (
            <StatusPill etat="vigilance" libelle={`Sous le seuil de ${pct(seuil)}`} />
          )}
        </p>
      ) : (
        <p className="text-base text-ink-2">{p.motif ?? "Projection non établie."}</p>
      )}
      <Graphique
        p={p}
        libelle={`Cumul constaté et projection de fin d'exercice`}
        libelleCible={libelleCible}
        libelleRealise={libelleRealise}
      />
      {p.fiable && (
        <>
          <details className="text-sm text-ink-2">
            <summary className="cursor-pointer font-bold text-ink">Méthode et fiabilité</summary>
            <ul className="mt-2 flex flex-col gap-1">
              {Object.entries(p.methodes).map(([cle, valeur]) => (
                <li key={cle} className="flex items-baseline justify-between gap-3">
                  <span>{METHODES[cle] ?? cle}</span>
                  <Montant gnf={valeur} className="text-ink" />
                </li>
              ))}
            </ul>
            {p.plafonne && <p className="mt-2">La projection est plafonnée aux crédits ouverts.</p>}
            {p.retrospective.length > 0 && (
              <>
                <p className="mt-3 font-bold text-ink">Vérification sur l'exercice en cours</p>
                <ul className="mt-1 flex flex-col gap-1">
                  {p.retrospective.map((x) => (
                    <li key={x.arrete_au}>
                      Appliquée au {dateFr(x.arrete_au)}, la méthode aurait prévu{" "}
                      <span className="chiffres text-ink">
                        {nombre(Math.abs(x.ecart) * 100)} % de {x.ecart < 0 ? "moins" : "plus"}
                      </span>{" "}
                      que le montant constaté aujourd'hui.
                    </li>
                  ))}
                </ul>
              </>
            )}
          </details>
          <Note>
            Projection indicative : elle prolonge le rythme constaté. Elle ne tient pas compte des décisions à
            venir
            {"profil_precedent" in p.methodes
              ? "."
              : " ni, faute d'historique chargé, de l'accélération habituelle de fin d'année."}
          </Note>
        </>
      )}
      {children}
    </div>
  );
}
