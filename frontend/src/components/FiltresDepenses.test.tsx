import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { useLocation } from "react-router-dom";

import { rendre, simulerApi } from "@/test/rendu";

import { BoutonFiltres, PanneauFiltres } from "./FiltresDepenses";

const META = { source: "chaine_depense", statut_source: "reel", date_situation: "2026-08-16", genere_le: "" };
const valeur = (code: string, libelle: string) => ({ code, libelle, nb_lignes: 3, credit: 10e9 });

function Page() {
  const [ouvert, setOuvert] = useState(false);
  const { search } = useLocation();
  return (
    <>
      <BoutonFiltres ouvert={ouvert} onBascule={() => setOuvert((o) => !o)} />
      <PanneauFiltres ouvert={ouvert} />
      <output data-testid="url">{search}</output>
    </>
  );
}

describe("filtres à critères multiples", () => {
  const api = () =>
    simulerApi({
      "/depense/criteres/": {
        meta: META,
        data: {
          criteres: [
            {
              cle: "ministeres",
              libelle: "Ministère / institution",
              valeurs: [valeur("18", "Santé"), valeur("20", "Enseignement")],
              disponible: true,
              raison: null,
            },
            {
              cle: "zones",
              libelle: "Zone d'exécution",
              valeurs: [],
              disponible: false,
              raison: "Absent de la situation chargée (fourni par l'extraction Oracle).",
            },
          ],
        },
      },
    });

  it("coche plusieurs valeurs, les garde dans l'adresse et les affiche en étiquettes", async () => {
    api();
    rendre(<Page />, "/depenses");
    await userEvent.click(screen.getByRole("button", { name: /Filtres/ }));
    expect(await screen.findByText(/fourni par l'extraction Oracle/)).toBeInTheDocument();
    await userEvent.click(screen.getByText("Ministère / institution", { selector: "summary span" }));
    await userEvent.click(screen.getByRole("checkbox", { name: /Santé/ }));
    await userEvent.click(screen.getByRole("checkbox", { name: /Enseignement/ }));
    expect(screen.getByTestId("url")).toHaveTextContent("ministeres=18%2C20");
    expect(screen.getByRole("button", { name: "Retirer Santé" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Filtres/ })).toHaveTextContent("1");
    await userEvent.click(screen.getByRole("button", { name: "Tout effacer" }));
    expect(screen.getByTestId("url")).toBeEmptyDOMElement();
  });

  it("garde les filtres actifs visibles panneau fermé", async () => {
    api();
    rendre(<Page />, "/depenses?ministeres=20");
    expect(await screen.findByRole("button", { name: "Retirer Enseignement" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Retirer Enseignement" }));
    expect(screen.getByTestId("url")).toBeEmptyDOMElement();
  });
});
