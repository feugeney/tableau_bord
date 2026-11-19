import { screen } from "@testing-library/react";

import * as auth from "@/hooks/useAuth";
import { rendre, simulerApi } from "@/test/rendu";

import Synthese from "./Synthese";

const meta = (source: string, statut_source = "reel") => ({
  source,
  statut_source,
  date_situation: "2026-11-13",
  exercice: 2025,
  genere_le: "",
});

it("organise la synthèse en bandes et regroupe les blocs sans donnée", async () => {
  vi.spyOn(auth, "useAuth").mockReturnValue({
    utilisateur: {
      id: 1,
      identifiant: "c",
      nom: "Cabinet",
      role: "ministre_cabinet",
      role_libelle: "",
      structure: "",
      domaines: ["synthese", "portefeuille"],
      peut_exporter: false,
      est_admin: false,
      peut_explorer: false,
      exige_2fa: false,
      a_2fa: false,
    },
    chargement: false,
    connecter: vi.fn(),
    deconnecter: vi.fn(),
    appliquerConnexion: vi.fn(),
  });
  simulerApi({
    "/synthese/": {
      meta: meta("chaine_depense"),
      data: {
        indicateurs: [
          {
            code: "tresorerie",
            libelle: "Trésorerie",
            valeur: null,
            bande: "tresorerie",
            meta: meta("scie", "demo"),
          },
          {
            code: "recettes_administratives",
            libelle: "Recettes administratives",
            valeur: 5e9,
            reference: 5e9,
            taux: 1,
            nombre: 1,
            bande: "recettes",
            meta: meta("sysop"),
          },
        ],
        mode_synthese: "decision",
        alertes: [],
        alertes_compte: { critique: 2, serieux: 1, vigilance: 0 },
        serie_mensuelle: [],
        sources: [],
        execution: null,
        plan_engagement: null,
      },
    },
  });
  rendre(<Synthese />);
  expect(await screen.findByRole("heading", { name: "Recettes" })).toBeInTheDocument();
  // Pas de grand cadre vide : la trésorerie est listée « en attente ».
  expect(screen.queryByRole("heading", { name: "Trésorerie" })).not.toBeInTheDocument();
  expect(screen.getByText(/En attente de données réelles/).parentElement).toHaveTextContent(
    "Trésorerie (SCIE)",
  );
  expect(screen.getByText("Recettes administratives (dividendes)")).toBeInTheDocument();
  expect(screen.getByText(/2 critique/)).toBeInTheDocument();
  // Sans le domaine Dépenses : ni tendance ni « où agir ».
  expect(screen.queryByText("Trajectoire de l'engagement")).not.toBeInTheDocument();
});
