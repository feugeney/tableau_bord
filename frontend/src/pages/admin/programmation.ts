/** Programmation des chargements : choix simples ↔ expression cron (fuseau Africa/Conakry). */

export type Frequence = "manuel" | "quotidien" | "ouvres" | "hebdomadaire" | "avance";
export const FREQUENCES: [Frequence, string][] = [
  ["manuel", "Manuel uniquement"],
  ["quotidien", "Tous les jours"],
  ["ouvres", "Du lundi au vendredi"],
  ["hebdomadaire", "Une fois par semaine"],
  ["avance", "Avancé (expression cron)"],
];
export const JOURS: [string, string][] = [
  ["1", "lundi"],
  ["2", "mardi"],
  ["3", "mercredi"],
  ["4", "jeudi"],
  ["5", "vendredi"],
  ["6", "samedi"],
  ["0", "dimanche"],
];
export interface Programmation {
  frequence: Frequence;
  heure: string;
  jour: string;
  avance: string;
}

/** Expression cron → choix simple, quand elle en relève (sinon mode avancé). */
export function lireProgrammation(cron: string): Programmation {
  const defaut = { heure: "02:00", jour: "6", avance: cron };
  if (!cron.trim()) return { ...defaut, frequence: "manuel" };
  const m = /^(\d{1,2}) (\d{1,2}) \* \* (\*|1-5|[0-6])$/.exec(cron.trim());
  if (!m || Number(m[1]) > 59 || Number(m[2]) > 23) return { ...defaut, frequence: "avance" };
  const heure = `${m[2].padStart(2, "0")}:${m[1].padStart(2, "0")}`;
  if (m[3] === "*") return { ...defaut, heure, frequence: "quotidien" };
  if (m[3] === "1-5") return { ...defaut, heure, frequence: "ouvres" };
  return { ...defaut, heure, jour: m[3], frequence: "hebdomadaire" };
}

/** Choix simple → expression cron enregistrée (minute heure jour mois jour-de-semaine). */
export function ecrireProgrammation(p: Programmation): string {
  if (p.frequence === "manuel") return "";
  if (p.frequence === "avance") return p.avance.trim();
  const [h, min] = (p.heure || "02:00").split(":").map(Number);
  const semaine = { quotidien: "*", ouvres: "1-5", hebdomadaire: p.jour }[p.frequence];
  return `${min} ${h} * * ${semaine}`;
}
