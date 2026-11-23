import { screen, waitFor, within } from "@testing-library/react";
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

  it("un clic sur une alerte de dossier ouvre sa fiche et son PDF structuré", async () => {
    const appels = simulerApi({
      "/alertes/": [
        {
          ...alerte(3, "critique", "Arbitrage : T5 · Investissement · Santé · 12,0 Mds"),
          valeur: "12,0 Mds",
          lien: "/depenses?vue_titre=5",
          donnees: {
            numero: "4521",
            libelle_titre: "T5 · Investissement",
            ministere: "Santé",
            beneficiaire: "ENTREPRISE BETA",
            objet: "Construction d'un hôpital",
            etat: "Nouvel engagement",
            etape: "Visa du contrôle financier",
            acteur: "Contrôle financier",
            jours: 26,
          },
        },
      ],
      "/sources/": [],
    });
    rendre(<NotificationAlertes domaine="depense" libelle="Dépenses" />);
    await userEvent.click(await screen.findByRole("button", { name: /Points d'attention/ }));
    const panneau = await screen.findByRole("dialog");
    const ligne = within(panneau).getByRole("button", { name: /Arbitrage : T5/ });
    expect(ligne).toHaveAttribute("aria-haspopup", "dialog");
    await userEvent.click(ligne);
    // La fiche s'ouvre dans une fenêtre dédiée, au-dessus du panneau.
    const fenetre = await screen.findByRole("dialog", { name: "Fiche de suivi · dossier n° 4521" });
    expect(within(fenetre).getByText("Dossier n° 4521")).toBeInTheDocument();
    expect(within(fenetre).getByText("Construction d'un hôpital")).toBeInTheDocument();
    expect(within(fenetre).getByText("26 jours")).toBeInTheDocument();
    expect(within(fenetre).getByRole("link", { name: /Ouvrir le détail du T5/ })).toHaveAttribute(
      "href",
      "/depenses?vue_titre=5",
    );
    // Le PDF structuré est produit par le serveur et téléchargé avec l'authentification de la session.
    URL.createObjectURL = vi.fn(() => "blob:fiche");
    URL.revokeObjectURL = vi.fn();
    await userEvent.click(within(fenetre).getByRole("button", { name: "Télécharger la fiche PDF" }));
    await waitFor(() => expect(URL.createObjectURL).toHaveBeenCalledOnce());
    expect(appels.mock.calls.some(([url]) => String(url).includes("/alertes/3/fiche-pdf/"))).toBe(true);
    expect(within(fenetre).queryByText("PDF indisponible")).not.toBeInTheDocument();
    await userEvent.click(within(fenetre).getByRole("button", { name: "Fermer la fenêtre" }));
    expect(screen.queryByRole("dialog", { name: /Fiche de suivi/ })).not.toBeInTheDocument();
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
