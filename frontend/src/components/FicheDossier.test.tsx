import { screen, within } from "@testing-library/react";

import type { Alerte } from "@/api/types";
import { rendre } from "@/test/rendu";

import { DetailAlerte } from "./Alertes";

const dossier: Alerte = {
  id: 8,
  date: "2026-11-18",
  domaine: "depense",
  source: null,
  source_code: null,
  date_situation: "2026-11-18",
  severite: "critique",
  statut: "nouvelle",
  titre: "Dossier à examiner",
  message: "En attente de visa",
  valeur: "12,0 Mds GNF",
  action_recommandee: "Confirmer les pièces attendues auprès du service concerné.",
  lien: "/depenses?vue_titre=5",
  donnees: { numero: "8", jours: 0, objet: "Construction et équipement", acteur: "Contrôle financier" },
};

it("structure le dossier en rubriques accessibles avec son action et ses données de suivi", () => {
  rendre(<DetailAlerte a={dossier} id="fiche-8" />);
  const fiche = screen.getByRole("region", { name: "Dossier n° 8" });
  expect(within(fiche).getByRole("region", { name: "Action proposée" })).toHaveTextContent(
    dossier.action_recommandee,
  );
  expect(within(fiche).getByRole("region", { name: "Objet du dossier" })).toHaveTextContent(
    "Construction et équipement",
  );
  expect(within(fiche).getByRole("region", { name: "Situation et traitement" })).toHaveTextContent(
    "Contrôle financier",
  );
  expect(within(fiche).getByRole("region", { name: "Rattachement administratif" })).toBeInTheDocument();
  expect(within(fiche).getByRole("region", { name: "Dates et notifications" })).toBeInTheDocument();
  expect(within(fiche).getByText("0 jours")).toBeInTheDocument();
  expect(within(fiche).getByText("Envoi non renseigné")).toBeInTheDocument();
  expect(within(fiche).getByRole("link", { name: /Ouvrir le détail/ })).toHaveAttribute("href", dossier.lien);
});

it.each([null, "inconnu"])("n'invente pas une ancienneté lorsque les jours valent %s", (jours) => {
  rendre(<DetailAlerte a={{ ...dossier, donnees: { numero: "8", jours } }} id="fiche-8" />);
  expect(screen.getByText("Non renseignée")).toBeInTheDocument();
  expect(screen.queryByText("0 jours")).not.toBeInTheDocument();
  expect(screen.queryByText(/NaN/)).not.toBeInTheDocument();
});
