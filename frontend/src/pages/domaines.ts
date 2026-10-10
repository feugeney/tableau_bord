export interface DefinitionDomaine {
  titre: string;
  source: string;
  api: string; // point d'accès /api/v1/…
  contenu: string[]; // blocs prévus, affichés tant que la source n'est pas raccordée
}

export const DOMAINES: Record<string, DefinitionDomaine> = {
  "recettes-fiscales": {
    titre: "Recettes fiscales",
    source: "SAFIG · Direction générale des impôts",
    api: "/recettes-fiscales/indicateurs/",
    contenu: [
      "Recouvré / objectif, restes à recouvrer, contentieux, contribuables actifs et télédéclaration",
      "Recouvrement par impôt et par mois, comparé à l'objectif",
      "Répartition par centre de gestion et par secteur d'activité",
    ],
  },
  "recettes-douanieres": {
    titre: "Recettes douanières",
    source: "SYDONIA · Direction générale des douanes",
    api: "/douanes/indicateurs/",
    contenu: [
      "Recouvré / objectif, exonérations, déclarations traitées, délai moyen de dédouanement",
      "Recettes par nature de droit et par bureau ; recouvrement mensuel",
      "Déclarations par circuit de contrôle (vert, jaune, rouge)",
    ],
  },
  tresorerie: {
    titre: "Trésorerie",
    source: "SCIE · Trésor public",
    api: "/tresor/indicateurs/",
    contenu: [
      "Encaissements, décaissements, solde en jours de décaissements, délai moyen de paiement",
      "Flux et solde mensuels avec le seuil « 1 mois de décaissements »",
      "Tableau des opérations financières simplifié, source affichée ligne par ligne",
    ],
  },
  "dette-publique": {
    titre: "Dette publique",
    source: "Application de la dette · Direction de la dette",
    api: "/dette/indicateurs/",
    contenu: [
      "Encours total en % du PIB face au seuil CEDEAO de 70 %, dette extérieure et intérieure",
      "Intérêts de l'exercice engagés (Chaîne Dépense, titre 1)",
      "Composition par type de créancier ; échéancier sur cinq ans",
    ],
  },
  patrimoine: {
    titre: "Patrimoine de l'État",
    source: "SICOM · DNSI / DNCM",
    api: "/patrimoine/indicateurs/",
    contenu: [
      "Valeurs nette et brute, amortissement, biens immatriculés, véhicules en service, institutions déployées",
      "Valeur par catégorie et par ministère ; parc automobile par état",
      "Contrôles : biens non inventoriés, sans détenteur, véhicules à réformer, écart avec le SCIE",
    ],
  },
  portefeuille: {
    titre: "Portefeuille de l'État",
    source: "SYSOP · DGPEIP",
    api: "/portefeuille/indicateurs/",
    contenu: [
      "Organismes suivis, transferts de l'État (titre 4), dividendes, transmission des états financiers",
      "Subventions aux EPA et dividendes : réalisé face au prévu",
      "Santé financière et points de gouvernance",
    ],
  },
  "masse-salariale": {
    titre: "Masse salariale",
    source: "Chaîne Dépense (titre 2) · FUGAS",
    api: "/paie/indicateurs/",
    contenu: [
      "Crédits de personnel, ordonnancé, masse mensuelle moyenne, agents payés et coût moyen",
      "Dépenses de personnel par ministère",
      "Contrôles de paie : doublons, agents sans NIF ou sans affectation, départs à la retraite",
    ],
  },
  "marches-publics": {
    titre: "Marchés publics",
    source: "Telemo",
    api: "/marches-publics/",
    contenu: [
      "Flux Chaîne de dépenses ↔ Telemo : réservations de crédit (F3), marchés immatriculés (F4), paiements BCRG (F5)",
      "Montant des marchés immatriculés, part de l'entente directe, délais réservation → immatriculation → paiement",
      "Contrôles de cohérence : marchés sans réservation ou au-delà du crédit réservé, paiements au-delà du marché",
      "Modes de passation, types de marché, autorités contractantes, titulaires regroupés par NIF",
    ],
  },
};
