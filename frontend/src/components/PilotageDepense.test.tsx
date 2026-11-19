import { screen, within } from "@testing-library/react";

import type { PilotageDepense as Donnees } from "@/api/types";
import { rendre, simulerApi } from "@/test/rendu";

import { PilotageDepense } from "./PilotageDepense";

const donnees: Donnees = {
  disponibilite: {
    credit_actuel: 100e9,
    credit_engage: 30e9,
    credit_reserve: 10e9,
    montant_bloque: 5e9,
    credits_non_engages: 70e9,
    credit_disponible: null,
    disponible_reconstitue: 55e9,
    ecart_disponibilite: null,
    part_immobilisee: 0.15,
  },
  delais: [
    {
      libelle: "Création → visa CF",
      nb_engagements: 10,
      paires_valides: 2,
      couverture: 0.2,
      mediane_jours: 5,
      p90_jours: 8,
      delais_negatifs: 1,
      dates_futures: 1,
      sans_date_fin: 6,
    },
  ],
  rapprochements: [
    {
      libelle: "Payé enregistré",
      reference: 10e9,
      detail_brut: 10e9,
      detail_comparable: 10e9,
      ecart: 0,
      cles_en_ecart: 2,
      ecart_absolu: 2e9,
      perimetre: "Toutes les lignes reçues",
    },
  ],
  apad: {
    renseigne: false,
    nb_lignes: null,
    nb_marches: null,
    avance_demarrage: null,
    reference: null,
    ecart: null,
    ministeres: [],
    dossiers: [],
  },
  regies: { nb_lignes: null, montant_regie: null },
};

it("distingue le disponible absent du solde calculé et conserve les écarts qui se compensent", async () => {
  simulerApi({
    "/depense/pilotage/": {
      meta: {
        source: "chaine_depense",
        statut_source: "reel",
        exercice: 2026,
        date_situation: "2026-08-16",
        genere_le: "",
      },
      data: donnees,
    },
  });
  rendre(<PilotageDepense />);
  expect(await screen.findByText("Détail APAD non fourni pour cette situation")).toBeInTheDocument();
  // Zone « Disponibilité des crédits » retirée de la page (19/11/2026).
  expect(screen.queryByText("Disponibilité des crédits")).not.toBeInTheDocument();
  const ligne = screen.getByRole("table", { name: "Rapprochement des phases" });
  expect(within(ligne).getByText("2 clés en écart")).toBeInTheDocument();
  expect(within(ligne).queryByText("Concordant")).not.toBeInTheDocument();
  expect(screen.getByText(/ne s'ajoutent pas aux dépenses payées/)).toBeInTheDocument();
  expect(screen.queryByText("Exécution par fonction")).not.toBeInTheDocument();
  expect(screen.queryByText("Exécution par catégorie de projet")).not.toBeInTheDocument();
});

it("une période sans données ne conserve pas les indicateurs d'une autre période", async () => {
  simulerApi({
    "/depense/pilotage/": {
      meta: { source: "chaine_depense", statut_source: "reel", date_situation: null, genere_le: "" },
      data: null,
    },
  });
  rendre(<PilotageDepense />, "/depenses?exercice=2040");
  expect(await screen.findByText(/Aucune donnée/)).toBeInTheDocument();
  expect(screen.queryByText("Crédits réservés")).not.toBeInTheDocument();
});
