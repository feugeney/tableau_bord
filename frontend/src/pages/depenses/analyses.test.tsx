import { screen } from "@testing-library/react";

import { rendre } from "@/test/rendu";

import { BalanceAgee, BandeauFraicheur, EcartN1 } from "./analyses";

describe("blocs d'analyse des dépenses", () => {
  it("regroupe les soldes non payés en quatre tranches d'ancienneté", () => {
    const mois = (anciennete: number, reste: number) => ({
      mois_creation: "2026-01-01",
      reste_a_payer: reste,
      nb_engagements: 1,
      anciennete_mois: anciennete,
      risque_arriere: anciennete > 12,
    });
    rendre(
      <BalanceAgee
        x={{
          mois: [mois(1, 10e9), mois(2, 10e9), mois(4, 20e9), mois(8, 40e9), mois(14, 20e9)],
          reste_a_payer_risque_arriere: 20e9,
          seuil_mois: 12,
        }}
      />,
    );
    expect(
      screen.getByRole("img", {
        name: /Moins de 3 mois 20.%.*3 à 6 mois 20.%.*6 à 12 mois 40.%.*Plus de 12 mois 20.%/,
      }),
    ).toBeInTheDocument();
    expect(screen.getByText(/2 engagement\(s\)/)).toBeInTheDocument();
  });

  it("écrit l'écart à l'exercice précédent en points", () => {
    rendre(<EcartN1 taux={0.128} reference={0.382} libelle="2025 au 16/08/2025" />);
    expect(screen.getByText(/2025 au 16\/08\/2025/)).toHaveTextContent("38 %");
    expect(screen.getByText(/−?-25 pts/)).toBeInTheDocument();
  });

  it("signale une situation de plus de 30 jours", () => {
    rendre(
      <BandeauFraicheur
        meta={{
          source: "chaine_depense",
          statut_source: "reel",
          date_situation: "2026-01-01",
          genere_le: "",
        }}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent(/données anciennes/);
    // La source est indiquée une fois, dans ce bandeau.
    expect(screen.getByRole("status")).toHaveTextContent(/Chaîne Dépense/);
  });
});
