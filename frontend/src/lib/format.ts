/** Formats français : espace fine insécable pour les milliers, montants en milliards de GNF. */

export const ESPACE_FINE = String.fromCharCode(0x202f);
// Espaces de groupement possibles selon le navigateur : insécable, fine insécable, espace.
const ESPACES = new RegExp(`[${String.fromCharCode(0xa0, 0x202f)} ]`, "g");
const MILLIARD = 1e9;

function grouper(n: number, decimales: number): string {
  return new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: decimales,
    maximumFractionDigits: decimales,
  })
    .format(n)
    .replace(ESPACES, ESPACE_FINE);
}

export function nombre(n: number | null | undefined, decimales = 0): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return grouper(n, decimales);
}

/** 36 444 680 000 000 GNF → « 36 444,7 Mds » */
export function mds(gnf: number | null | undefined, decimales = 1): string {
  if (gnf === null || gnf === undefined || Number.isNaN(gnf)) return "—";
  return `${grouper(gnf / MILLIARD, decimales)}${ESPACE_FINE}Mds`;
}

/** Valeur brute en milliards (graphiques). */
export function enMds(gnf: number | null | undefined): number {
  return gnf ? gnf / MILLIARD : 0;
}

/** Ratio 0,712 → « 71 % » (sans décimale). */
export function pct(ratio: number | null | undefined, decimales = 0): string {
  if (ratio === null || ratio === undefined || Number.isNaN(ratio)) return "—";
  return `${grouper(decimales === 0 ? Math.round(ratio * 100) : ratio * 100, decimales)}${ESPACE_FINE}%`;
}

const MOIS = new Intl.DateTimeFormat("fr-FR", { month: "short", timeZone: "UTC" });
const DATE = new Intl.DateTimeFormat("fr-FR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  timeZone: "UTC",
});
const DATE_HEURE = new Intl.DateTimeFormat("fr-FR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function dateUtc(iso: string): Date {
  const [a, m, j] = iso.slice(0, 10).split("-").map(Number);
  return new Date(Date.UTC(a, (m || 1) - 1, j || 1));
}

/** "2025-12-01" → « déc. » (ou « déc. 2025 » avec l'année). */
export function moisCourt(iso: string, avecAnnee = false): string {
  const d = dateUtc(iso);
  const mois = MOIS.format(d);
  return avecAnnee ? `${mois} ${d.getUTCFullYear()}` : mois;
}

/** "2026-09-15" → « 15/09/2026 » (date calendaire, sans décalage de fuseau). */
export function dateFr(iso: string | null | undefined): string {
  return iso ? DATE.format(dateUtc(iso)) : "—";
}

/** Horodatage → « 28/09/2026 15:22 » (heure locale). */
export function dateHeureFr(iso: string | null | undefined): string {
  return iso ? DATE_HEURE.format(new Date(iso)).replace(",", "") : "—";
}
