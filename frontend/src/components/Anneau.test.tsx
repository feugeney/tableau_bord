import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { COULEUR_AUTRES, plierParts } from "@/lib/anneau";
import { rendre } from "@/test/rendu";

import { Anneau } from "./Anneau";

const lignes = Array.from({ length: 8 }, (_, i) => ({
  code: String(701 + i),
  libelle: `Fonction ${701 + i}`,
  engage: (8 - i) * 1e9,
  paye: i * 1e9,
}));

describe("anneaux de répartition", () => {
  it("garde 6 parts plus « Autres », choisies et colorées selon l'engagé", () => {
    const engage = plierParts(
      lignes,
      (l) => l.engage,
      (l) => l.engage,
    );
    const paye = plierParts(
      lignes,
      (l) => l.paye,
      (l) => l.engage,
    );
    expect(engage).toHaveLength(7);
    expect(engage[6]).toMatchObject({ libelle: "Autres (2)", valeur: 3e9, couleur: COULEUR_AUTRES });
    // Basculer vers le payé ne repeint ni ne réordonne les catégories.
    expect(paye.map((p) => [p.code, p.couleur])).toEqual(engage.map((p) => [p.code, p.couleur]));
    expect(paye[6].valeur).toBe(13e9);
  });

  it("écrit chaque part (nom, % et montant) et filtre au clic", async () => {
    const onPart = vi.fn();
    const parts = plierParts(
      lignes.slice(0, 2),
      (l) => l.engage,
      (l) => l.engage,
      true,
    );
    rendre(<Anneau libelle="Engagé par titre" parts={parts} onPart={onPart} actif="701" />);
    expect(screen.getByRole("img", { name: /Engagé par titre : Fonction 701 53/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Fonction 701/ })).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(screen.getByRole("button", { name: /Fonction 702/ }));
    expect(onPart).toHaveBeenCalledWith("702");
  });
});
