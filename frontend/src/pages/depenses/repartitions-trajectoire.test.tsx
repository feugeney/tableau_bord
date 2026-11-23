import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { rendre, simulerApi } from "@/test/rendu";

import { BlocRepartitions } from "../Depenses";
import { CourbeExecution } from "./analyses";

it("place le pilier avant le titre et répartit les six mesures", async () => {
  simulerApi({
    "/depense/repartitions/": {
      meta: {},
      data: {
        axes: ["pilier", "titre", "fonction", "zone", "type_budget"].map((axe) => ({
          axe,
          titre: axe === "pilier" ? "Par pilier Simandou" : `Par ${axe}`,
          disponible: true,
          parts: [
            {
              code: "1",
              libelle: "Exemple",
              credit: 100e9,
              engage: 80e9,
              liquide: 60e9,
              ordonnance: 40e9,
              vbp: 30e9,
              paye: 20e9,
            },
          ],
        })),
        titre_filtre: null,
        indisponible: {},
      },
    },
  });
  rendre(<BlocRepartitions titreActif={null} onTitre={vi.fn()} />);
  expect(await screen.findByRole("heading", { name: "Par pilier Simandou" })).toBeInTheDocument();
  const titres = screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent);
  expect(titres.slice(0, 2)).toEqual(["Par pilier Simandou", "Par titre"]);
  const pilier = screen.getByRole("heading", { name: "Par pilier Simandou" }).closest("section")!;
  for (const [libelle, total] of [
    ["Crédit", "100,0"],
    ["Engagé", "80,0"],
    ["Liquidé", "60,0"],
    ["Ordonnancé", "40,0"],
    ["Vu bon à payer", "30,0"],
    ["Payé", "20,0"],
  ]) {
    await userEvent.click(screen.getByRole("radio", { name: libelle }));
    expect(within(pilier).getByText(/total/).parentElement).toHaveTextContent(total);
  }
});

it("signale le cumul non rapproché et l'absence de points datés", async () => {
  simulerApi({
    "/depense/courbe/": {
      meta: {},
      data: {
        exercice: 2026,
        exercice_precedent: null,
        date_situation: "2026-09-15",
        points: [{ mois: 9, n: null, n1: null, prorata: 0.75 }],
        engage_serie: 0,
        engage_situation: 100e9,
        concordant: false,
        methode: "Méthode de calcul",
      },
    },
  });
  rendre(<CourbeExecution parMois={<p>Mensuel</p>} />);
  expect(await screen.findByRole("status")).toHaveTextContent("Trajectoire indisponible");
  expect(screen.getByText(/La courbe ne reconstitue pas/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("radio", { name: "Par mois" }));
  expect(screen.getByText("Mensuel")).toBeInTheDocument();
});
