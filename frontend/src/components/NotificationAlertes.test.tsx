import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { rendre, simulerApi } from "@/test/rendu";

import { BoutonColonnes, PanneauColonnes } from "./ChoixColonnes";
import { NotificationAlertes } from "./NotificationAlertes";

const alerte = (id: number, severite: string, titre: string) => ({
  id,
  date: "2026-11-19",
  domaine: "depense",
  source: null,
  source_code: null,
  date_situation: null,
  severite,
  titre,
  message: "Détail",
  valeur: "",
  action_recommandee: "",
  lien: "",
  statut: "nouvelle",
});

describe("points d'attention en notification", () => {
  beforeEach(() => sessionStorage.clear());

  it("la cloche compte les alertes, l'annonce signale les graves et le panneau les liste", async () => {
    simulerApi({
      "/alertes/": [alerte(1, "vigilance", "Rythme lent"), alerte(2, "critique", "Dépassement Santé")],
      "/sources/": [],
    });
    rendre(<NotificationAlertes domaine="depense" libelle="Dépenses" />);
    const cloche = await screen.findByRole("button", {
      name: /Points d'attention : 2 alerte\(s\).*1 critique/,
    });
    const annonce = await screen.findByRole("status");
    expect(annonce).toHaveTextContent("Dépassement Santé");
    await userEvent.click(cloche);
    const panneau = await screen.findByRole("dialog");
    expect(within(panneau).getByText("Rythme lent")).toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("sans alerte grave, pas d'annonce", async () => {
    simulerApi({ "/alertes/": [alerte(1, "vigilance", "Rythme lent")], "/sources/": [] });
    rendre(<NotificationAlertes domaine="depense" libelle="Dépenses" />);
    expect(await screen.findByRole("button", { name: /1 alerte\(s\)/ })).toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});

describe("choix des colonnes", () => {
  it("décoche et recoche une colonne en gardant l'ordre ; la dernière ne peut être retirée", async () => {
    const colonnes = [
      { id: "a", libelle: "Crédits" },
      { id: "b", libelle: "Engagé" },
    ];
    const changements: string[][] = [];
    const { rerender } = rendre(
      <PanneauColonnes
        id="p"
        colonnes={colonnes}
        visibles={["a", "b"]}
        onChange={(v) => changements.push(v)}
        onRetablir={() => {}}
      />,
    );
    await userEvent.click(screen.getByRole("checkbox", { name: "Crédits" }));
    expect(changements.at(-1)).toEqual(["b"]);
    rerender(
      <PanneauColonnes
        id="p"
        colonnes={colonnes}
        visibles={["b"]}
        onChange={(v) => changements.push(v)}
        onRetablir={() => {}}
      />,
    );
    expect(screen.getByRole("checkbox", { name: "Engagé" })).toBeDisabled();
    await userEvent.click(screen.getByRole("checkbox", { name: "Crédits" }));
    expect(changements.at(-1)).toEqual(["a", "b"]);
  });

  it("le bouton indique le nombre de colonnes masquées", () => {
    rendre(<BoutonColonnes ouvert={false} onBascule={() => {}} masquees={3} controle="p" />);
    expect(screen.getByRole("button", { name: /Colonnes/ })).toHaveTextContent("−3");
  });
});
