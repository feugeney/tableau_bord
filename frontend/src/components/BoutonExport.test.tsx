import { fireEvent, screen, waitFor } from "@testing-library/react";

import * as client from "@/api/client";
import * as auth from "@/hooks/useAuth";
import { rendre } from "@/test/rendu";

import { BoutonExport } from "./BoutonExport";

function connecter(exportAutorise = true) {
  vi.spyOn(auth, "useAuth").mockReturnValue({
    utilisateur: {
      id: 1,
      identifiant: "direction",
      nom: "Direction",
      role: "directeur",
      role_libelle: "Directeur",
      structure: "",
      domaines: ["depense"],
      peut_exporter: exportAutorise,
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
}

describe("exports des rubriques", () => {
  it("le PDF reprend les filtres de la page et conserve le bouton Excel", async () => {
    connecter();
    const download = vi.spyOn(client, "telecharger").mockResolvedValue();
    rendre(<BoutonExport page="depenses" />, "/depenses?exercice=2025&nature=investissement");
    fireEvent.click(screen.getByRole("button", { name: "Exporter (PDF)" }));
    await waitFor(() =>
      expect(download).toHaveBeenCalledWith(
        "/export/depenses.pdf",
        expect.objectContaining({ exercice: "2025", nature: "investissement" }),
      ),
    );
    expect(screen.getByRole("button", { name: "Exporter (Excel)" })).toBeInTheDocument();
  });

  it("la synthèse propose le rapport complet", async () => {
    connecter();
    const download = vi.spyOn(client, "telecharger").mockResolvedValue();
    rendre(<BoutonExport page="synthese" />);
    fireEvent.click(screen.getByRole("button", { name: "Rapport complet (PDF)" }));
    await waitFor(() => expect(download).toHaveBeenCalledWith("/export/rapport.pdf", expect.any(Object)));
  });

  it("le PDF conserve le mode explicite de démonstration de la synthèse", async () => {
    connecter();
    const download = vi.spyOn(client, "telecharger").mockResolvedValue();
    rendre(<BoutonExport page="synthese" />, "/synthese?exercice=2025&mode_synthese=demonstration");
    fireEvent.click(screen.getByRole("button", { name: "Exporter (PDF)" }));
    await waitFor(() =>
      expect(download).toHaveBeenCalledWith(
        "/export/synthese.pdf",
        expect.objectContaining({ exercice: "2025", mode_synthese: "demonstration" }),
      ),
    );
  });

  it("un profil sans droit d'export n'affiche aucun bouton", () => {
    connecter(false);
    rendre(<BoutonExport page="synthese" />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("un échec du téléchargement est indiqué et permet un nouvel essai", async () => {
    connecter();
    vi.spyOn(client, "telecharger").mockRejectedValue(new Error("Indisponible"));
    rendre(<BoutonExport page="tofe" />);
    fireEvent.click(screen.getByRole("button", { name: "Exporter (PDF)" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Export impossible");
    expect(screen.getByRole("button", { name: "Exporter (PDF)" })).not.toBeDisabled();
  });
});
