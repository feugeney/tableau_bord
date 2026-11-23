import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { IndicateursDepense } from "@/api/types";
import { NotificationAlertes } from "@/components/NotificationAlertes";
import { rendre, simulerApi } from "@/test/rendu";

import { IndicateursExecution } from "./IndicateursExecution";
import { EncadreArbitrages, TableauTitres } from "./Titres";

it("rapporte chaque étape à sa base dans les cadres de la chaîne", async () => {
  rendre(
    <IndicateursExecution
      i={
        {
          credit_actuel: 23648e9,
          credit_initial_lfi: 23648e9,
          variation_lfi: 0,
          credit_engage: 4427e9,
          taux_engagement: 0.187,
          montant_liquide: 2858e9,
          taux_liquidation: 2858 / 4427,
          taux_liquidation_sur_credits: 0.121,
          montant_ordonnance: 2825e9,
          taux_ordonnancement: 2825 / 2858,
          taux_ordonnancement_sur_credits: 0.119,
          montant_paye: 942e9,
          taux_paiement: 942 / 2825,
          taux_paiement_sur_credits: 0.04,
          montant_vbp: 2800e9,
          taux_vbp: 2800 / 2825,
        } as IndicateursDepense
      }
      n1={null}
    />,
  );
  const paiement = screen.getByRole("heading", { name: "Payé enregistré" }).closest("article")!;
  expect(paiement).toHaveTextContent("33,3 % de l’ordonnancé");
  expect(paiement).not.toHaveTextContent("4,0 % des crédits actuels");
  expect(screen.getByRole("heading", { name: "Liquidé" }).closest("article")).toHaveTextContent(
    "64,6 % de l’engagé",
  );
  expect(screen.getByRole("heading", { name: "Ordonnancé" }).closest("article")).toHaveTextContent(
    "98,8 % du liquidé",
  );
  expect(screen.getByRole("heading", { name: "Engagé" }).closest("article")).toHaveTextContent(
    "18,7 % des crédits actuels",
  );
  expect(screen.getByRole("heading", { name: "Vu bon à payer" }).closest("article")).toHaveTextContent(
    "99,1 % de l’ordonnancé",
  );
  expect(screen.getAllByRole("article").map((a) => within(a).getByRole("heading").textContent)).toEqual([
    "Crédits actuels",
    "Engagé",
    "Liquidé",
    "Ordonnancé",
    "Vu bon à payer",
    "Payé enregistré",
  ]);
  await userEvent.click(screen.getByText("Comprendre le passage entre les étapes"));
  const passage = screen.getByText("Payé enregistré / ordonnancé").closest("div")!;
  expect(passage).toHaveTextContent("33,3 %");
});

it("ouvre le détail du titre sans appliquer le filtre de nature à la comparaison", async () => {
  const api = simulerApi({
    "/depense/titres/": {
      meta: {},
      data: {
        titres: [
          {
            titre: "1",
            libelle_titre: "T1 · Dette",
            credit_actuel: 3837e9,
            credit_engage: 1000e9,
            montant_paye: 0,
            taux_engagement: 0.26,
            taux_paiement: null,
            paiement_suivi: false,
            voyant: null,
          },
          {
            titre: "5",
            libelle_titre: "T5 · Investissement",
            credit_actuel: 23648e9,
            credit_engage: 4427e9,
            montant_paye: 942e9,
            taux_engagement: 0.187,
            taux_paiement: 0.04,
            paiement_suivi: true,
            voyant: "critique",
          },
        ],
      },
    },
  });
  const ouvrir = vi.fn();
  rendre(<TableauTitres onOuvrir={ouvrir} />, "/depenses?nature=investissement&exercice=2026");
  const dette = await screen.findByRole("rowheader", { name: /T1/ });
  expect(within(dette.closest("tr")!).getByText("Non suivi dans la chaîne")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Voir le détail de T5 · Investissement" }));
  expect(ouvrir).toHaveBeenCalledWith("5");
  const url = new URL(String(api.mock.calls[0][0]), "http://localhost");
  expect(url.searchParams.has("nature")).toBe(false);
  expect(url.searchParams.get("exercice")).toBe("2026");
});

it("ne présente pas une panne des arbitrages comme une absence de dossier", async () => {
  simulerApi({});
  rendre(<EncadreArbitrages onOuvrir={vi.fn()} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Arbitrages indisponibles");
  expect(screen.queryByText(/Aucun dossier/)).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Réessayer" })).toBeInTheDocument();
});

it("signale une erreur des notifications dans la cloche et dans le panneau", async () => {
  simulerApi({});
  rendre(<NotificationAlertes domaine="depense" libelle="Dépenses" />);
  await userEvent.click(
    await screen.findByRole("button", { name: "Points d'attention : alertes indisponibles" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent("Leur absence ne peut pas être confirmée");
  expect(screen.queryByText("Aucune alerte ouverte.")).not.toBeInTheDocument();
});
