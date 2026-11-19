export interface DefinitionDomaine {
  titre: string;
  source: string;
  api: string; // point d'accès /api/v1/…
  contenu: string[]; // blocs prévus, affichés tant que la source n'est pas raccordée
}

export const DOMAINES: Record<string, DefinitionDomaine> = {
  tofe: {
    titre: "Tableau des opérations financières de l'État",
    source: "TOFE · illustration du cadre guinéen",
    api: "/tofe/",
    contenu: [
      "Recettes et dons, charges et acquisition nette d'actifs non financiers",
      "Soldes global et primaire, passage à la caisse, financement intérieur et extérieur",
      "LFI/LFR simulées, réalisé cumulé, période équivalente N−1 et contrôles d'équilibre",
    ],
  },
  "tresor-public": {
    titre: "Tableau du Trésor public",
    source: "Trésor public · à raccorder",
    api: "",
    contenu: [
      "Position de trésorerie de l'État : solde du compte unique du Trésor et des comptes de l'État",
      "Plan de trésorerie mensuel : encaissements et décaissements prévus et réalisés",
      "Instances de paiement et délais de règlement",
      "Cohérence avec le plan d'engagement : plafonds trimestriels et capacité de paiement",
    ],
  },
  "recettes-administratives": {
    titre: "Recettes administratives",
    source: "Ministères collecteurs et Trésor public · à raccorder",
    api: "",
    contenu: [
      "Droits et frais administratifs : passeports, visas, cartes grises, permis, actes et certificats",
      "Redevances, produits du domaine de l'État, amendes et pénalités",
      "Recouvrement par ministère collecteur comparé à l'objectif de la loi de finances",
      "Reversement au Trésor public et écart entre montants perçus et reversés",
    ],
  },
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
    source: "SIGAD · Direction de la dette",
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
