import { screen } from "@testing-library/react";

import { rendre } from "@/test/rendu";

import { BandeauKpi, KpiCard, StatusPill } from "./Indicateurs";
import { Montant } from "./Montant";
import { SourceBadge } from "./Source";

const META = {
  source: "chaine_depense",
  statut_source: "reel" as const,
  date_situation: "2026-09-15",
  genere_le: "",
};

describe("composants", () => {
  it("la pastille de source indique source, statut et date", () => {
    rendre(<SourceBadge meta={META} />);
    expect(screen.getByTitle(/Source/)).toHaveTextContent("Chaîne Dépense ·réel ·15/09/2026");
  });

  it("la pastille d'illustration est signalée", () => {
    rendre(<SourceBadge meta={{ ...META, source: "safig", statut_source: "demo" }} />);
    expect(screen.getByTitle(/Source/)).toHaveTextContent("SAFIG ·illustration");
  });

  it("le statut porte un libellé, pas seulement une couleur", () => {
    rendre(<StatusPill etat="critique" libelle="Sous-exécution" />);
    expect(screen.getByText("Sous-exécution")).toBeInTheDocument();
  });

  it("le montant affiche l'unité Mds à part", () => {
    rendre(<Montant gnf={36_444_680_000_000} />);
    expect(screen.getByTitle("milliards de francs guinéens")).toHaveTextContent("Mds");
  });

  it("KpiCard affiche valeur, jauge et source", () => {
    rendre(
      <BandeauKpi>
        <KpiCard libelle="Taux d'engagement" valeur="71 %" jauge={{ valeur: 0.71 }} meta={META} />
      </BandeauKpi>,
    );
    expect(screen.getByRole("meter")).toHaveAttribute("aria-valuenow", "71");
    expect(screen.getByRole("heading", { name: "Taux d'engagement" })).toBeInTheDocument();
  });
});
