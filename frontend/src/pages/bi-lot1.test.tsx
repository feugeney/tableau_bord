import { fireEvent, screen, waitFor } from "@testing-library/react";

import * as auth from "@/hooks/useAuth";
import { HBarList } from "@/components/Barres";
import { rendre } from "@/test/rendu";
import Synthese from "./Synthese";

it("la synthèse démarre en réel et exige un choix explicite pour afficher l'illustration", async () => {
  vi.spyOn(auth, "useAuth").mockReturnValue({
    utilisateur: null,
    chargement: false,
    connecter: vi.fn(),
    deconnecter: vi.fn(),
    appliquerConnexion: vi.fn(),
  });
  const fetchApi = vi.spyOn(globalThis, "fetch").mockImplementation(async (entree) => {
    const demonstration = String(entree).includes("mode_synthese=demonstration");
    const meta = {
      source: "chaine_depense",
      statut_source: "reel",
      date_situation: "2026-11-13",
      genere_le: "",
    };
    return new Response(
      JSON.stringify({
        meta,
        data: {
          indicateurs: [
            {
              code: "recettes",
              libelle: "Recettes fiscales et douanières",
              valeur: demonstration ? 1e9 : null,
              reference: demonstration ? 2e9 : null,
              taux: demonstration ? 0.5 : null,
              raison_indisponibilite: "Données réelles non disponibles pour cette période.",
              meta: { ...meta, source: "safig", statut_source: "demo" },
            },
          ],
          mode_synthese: demonstration ? "demonstration" : "decision",
          alertes: [],
          serie_mensuelle: [],
          sources: [],
        },
      }),
    );
  });
  rendre(<Synthese />);
  // Bloc sans donnée réelle : regroupé sur la ligne « En attente », pas un grand cadre vide.
  expect(await screen.findByText(/En attente de données réelles/)).toBeInTheDocument();
  expect(screen.getByText(/Total fiscal et douanier \(SAFIG\)/)).toBeInTheDocument();
  expect(screen.queryByText("50 % de l'objectif", { exact: false })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("radio", { name: "Démonstration" }));
  await waitFor(() =>
    expect(fetchApi.mock.calls.some(([url]) => String(url).includes("mode_synthese=demonstration"))).toBe(
      true,
    ),
  );
  expect(await screen.findByText(/Mode démonstration :/)).toBeInTheDocument();
  expect(screen.getByText(/de l'objectif/)).toBeInTheDocument();
});

it("les barres du portefeuille n'inventent pas un retard lorsque les échéances sont inconnues", () => {
  rendre(
    <HBarList
      lignes={[{ libelle: "Organisme renseigné", valeur: 10, objectif: 100 }]}
      seuil={null}
      reference="du prévu renseigné"
    />,
  );
  expect(screen.getByText(/10 % du prévu renseigné/)).toBeInTheDocument();
  expect(screen.queryByText(/en retard/)).not.toBeInTheDocument();
});
