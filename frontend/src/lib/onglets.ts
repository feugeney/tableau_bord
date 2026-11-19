export interface Onglet {
  chemin: string;
  libelle: string;
  /** L'onglet est visible si l'utilisateur a au moins un de ces domaines. */
  domaines: string[];
}

export function ongletAutorise(o: Onglet, domaines: string[] | undefined): boolean {
  return o.domaines.some((d) => domaines?.includes(d));
}

export const ONGLETS: Onglet[] = [
  { chemin: "/synthese", libelle: "Synthèse", domaines: ["synthese"] },
  { chemin: "/pilotage", libelle: "Pilotage", domaines: ["tofe"] },
  { chemin: "/depenses", libelle: "Dépenses", domaines: ["depense"] },
  { chemin: "/tresorerie", libelle: "Trésorerie", domaines: ["tresor"] },
  { chemin: "/recettes", libelle: "Recettes", domaines: ["recettes_fiscales", "douanes", "portefeuille"] },
  { chemin: "/dette-publique", libelle: "Dette publique", domaines: ["dette"] },
  { chemin: "/investissements", libelle: "Investissements", domaines: ["investissement"] },
  { chemin: "/patrimoine", libelle: "Patrimoine de l'État", domaines: ["patrimoine"] },
  { chemin: "/portefeuille", libelle: "Portefeuille de l'État", domaines: ["portefeuille"] },
  { chemin: "/marches-publics", libelle: "Marchés publics", domaines: ["marches_publics"] },
];

export function ongletCourant(chemin: string): Onglet | undefined {
  if (chemin.startsWith("/administration"))
    return { chemin: "/administration", libelle: "Administration", domaines: [] };
  if (chemin.startsWith("/exploration"))
    return { chemin: "/exploration", libelle: "Exploration des données", domaines: [] };
  return ONGLETS.find((o) => chemin.startsWith(o.chemin));
}
