export interface Onglet {
  chemin: string;
  libelle: string;
  domaine: string;
}

export const ONGLETS: Onglet[] = [
  { chemin: "/synthese", libelle: "Synthèse", domaine: "synthese" },
  { chemin: "/depenses", libelle: "Dépenses", domaine: "depense" },
  { chemin: "/tresorerie", libelle: "Trésorerie", domaine: "tresor" },
  { chemin: "/recettes-fiscales", libelle: "Recettes fiscales", domaine: "recettes_fiscales" },
  { chemin: "/recettes-douanieres", libelle: "Recettes douanières", domaine: "douanes" },
  { chemin: "/dette-publique", libelle: "Dette publique", domaine: "dette" },
  { chemin: "/investissements", libelle: "Investissements", domaine: "investissement" },
  { chemin: "/patrimoine", libelle: "Patrimoine de l'État", domaine: "patrimoine" },
  { chemin: "/portefeuille", libelle: "Portefeuille de l'État", domaine: "portefeuille" },
  { chemin: "/marches-publics", libelle: "Marchés publics", domaine: "marches_publics" },
];

export function ongletCourant(chemin: string): Onglet | undefined {
  if (chemin.startsWith("/administration"))
    return { chemin: "/administration", libelle: "Administration", domaine: "" };
  if (chemin.startsWith("/exploration"))
    return { chemin: "/exploration", libelle: "Exploration des données", domaine: "" };
  return ONGLETS.find((o) => chemin.startsWith(o.chemin));
}
