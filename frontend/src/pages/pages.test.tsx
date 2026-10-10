import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";

import { Cadre } from "@/components/cadre/Cadre";
import * as auth from "@/hooks/useAuth";
import { ONGLETS } from "@/lib/onglets";
import { rendre, simulerApi } from "@/test/rendu";

import RecettesFiscales from "./domaines/RecettesFiscales";

const META_NR = {
  source: "safig",
  application: "SAFIG",
  date_situation: null,
  statut_source: "non_raccorde",
  genere_le: "",
};

function connecter(est_admin: boolean) {
  vi.spyOn(auth, "useAuth").mockReturnValue({
    utilisateur: {
      id: 1,
      identifiant: "c",
      nom: "Cabinet",
      role: "ministre_cabinet",
      role_libelle: "Ministre / Cabinet",
      structure: "",
      domaines: ONGLETS.map((o) => o.domaine),
      peut_exporter: true,
      est_admin,
      peut_explorer: est_admin,
      exige_2fa: true,
      a_2fa: true,
    },
    chargement: false,
    connecter: vi.fn(),
    deconnecter: vi.fn(),
    appliquerConnexion: vi.fn(),
  });
}

describe("pages", () => {
  beforeEach(() => connecter(false));

  it("une source non raccordée affiche un état vide explicite, sans erreur", async () => {
    simulerApi({ "/recettes-fiscales/": { meta: META_NR, data: null }, "/sources/": [] });
    rendre(<RecettesFiscales />);
    expect(await screen.findByText("Source non raccordée")).toBeInTheDocument();
    expect(screen.getByText("Contenu prévu dès le raccordement")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("une source en illustration affiche le bandeau et la pastille « illustration »", async () => {
    simulerApi({
      "/recettes-fiscales/": {
        meta: { ...META_NR, statut_source: "demo", date_situation: "2026-08-16", exercice: 2026 },
        data: {
          indicateurs: {
            recouvre: 1e12,
            objectif: 1.2e12,
            taux: 0.83,
            restes_a_recouvrer: 1e11,
            contentieux: 1e10,
            dossiers_contentieux: 3,
            contribuables_actifs: 10,
            taux_teledeclaration: 0.5,
          },
          par_impot: [],
          mensuel: [],
          par_centre: [],
          par_secteur: [],
          restes_par_anciennete: [],
          contentieux_par_stade: [],
          seuil_retard: 0.8,
        },
      },
      "/sources/": [],
    });
    rendre(<RecettesFiscales />);
    expect(await screen.findByRole("note")).toHaveTextContent("Données d'illustration");
    expect(screen.getAllByText(/illustration/).length).toBeGreaterThan(1);
  });

  it.each([
    [false, 10],
    [true, 10],
  ])(
    "le cadre affiche les 10 onglets et le lien d'administration seulement aux administrateurs (admin : %s)",
    async (admin, n) => {
      simulerApi({ "/situations/": { exercices: [{ exercice: 2025, dates: ["2026-09-15"] }] } });
      connecter(admin);
      rendre(
        <Routes>
          <Route element={<Cadre />}>
            <Route path="/synthese" element={<p>contenu</p>} />
          </Route>
        </Routes>,
        "/synthese",
      );
      const nav = screen.getByRole("navigation", { name: "Pages du tableau de bord" });
      expect(nav.querySelectorAll("ul a")).toHaveLength(n);
      expect(screen.getByRole("link", { name: "Synthèse" })).toHaveAttribute("aria-current", "page");
      // Lien dans la barre d'onglets (le menu du profil en contient un second).
      expect(nav.querySelectorAll('a[href="/administration"]')).toHaveLength(admin ? 1 : 0);
      expect((await screen.findAllByText(/situation au 15\/09\/2026/)).length).toBeGreaterThan(0);
    },
  );
});
