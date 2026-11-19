/** Parts des anneaux de répartition : couleurs en ordre fixe et regroupement en « Autres ». */

/** Teintes catégorielles dans un ordre fixe (tokens.css) ; au-delà de 6 parts : « Autres ». */
export const COULEURS_CATEGORIES = [
  "var(--categ-1)",
  "var(--categ-2)",
  "var(--categ-3)",
  "var(--categ-4)",
  "var(--categ-5)",
  "var(--categ-6)",
];
export const COULEUR_AUTRES = "var(--categ-autres)";
export const MAX_PARTS = 6;

export interface PartAnneau {
  code: string;
  libelle: string;
  valeur: number;
  couleur: string;
  /** Une part cliquable filtre la page (ex. le titre). */
  cliquable?: boolean;
}

/**
 * Regroupe au-delà de MAX_PARTS. Le choix des parts affichées et leurs couleurs suivent `rang`
 * (ex. l'engagé) : basculer de mesure ne repeint pas une catégorie.
 */
export function plierParts<T extends { code: string; libelle: string }>(
  lignes: T[],
  valeur: (l: T) => number,
  rang: (l: T) => number,
  cliquable = false,
): PartAnneau[] {
  const ordonnees = [...lignes].sort((a, b) => rang(b) - rang(a));
  const visibles = ordonnees.length > MAX_PARTS ? ordonnees.slice(0, MAX_PARTS) : ordonnees;
  const reste = ordonnees.slice(visibles.length);
  const parts: PartAnneau[] = visibles.map((l, i) => ({
    code: l.code,
    libelle: l.libelle,
    valeur: valeur(l),
    couleur: i < COULEURS_CATEGORIES.length ? COULEURS_CATEGORIES[i] : COULEUR_AUTRES,
    cliquable,
  }));
  if (reste.length) {
    parts.push({
      code: "__autres",
      libelle: `Autres (${reste.length})`,
      valeur: reste.reduce((s, l) => s + valeur(l), 0),
      couleur: COULEUR_AUTRES,
    });
  }
  return parts;
}
