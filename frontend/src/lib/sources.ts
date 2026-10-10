const NOMS: Record<string, string> = {
  chaine_depense: "Chaîne Dépense",
  safig: "SAFIG",
  sydonia: "SYDONIA",
  scie: "SCIE",
  dette: "Dette",
  sigpip: "SIGPIP",
  fugas: "FUGAS",
  sicom: "SICOM",
  sysop: "SYSOP",
  telemo: "Telemo",
  pleb: "PLEB",
};

export function nomSource(code: string) {
  return NOMS[code] ?? code;
}

export const DOMAINES_LIBELLES: Record<string, string> = {
  depense: "Dépenses",
  recettes_fiscales: "Recettes fiscales",
  douanes: "Recettes douanières",
  tresor: "Trésorerie",
  dette: "Dette publique",
  investissement: "Investissements",
  patrimoine: "Patrimoine",
  portefeuille: "Portefeuille",
  paie: "Masse salariale",
  marches_publics: "Marchés publics",
};
