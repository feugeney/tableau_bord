/** Critères d'acceptation de la charte, vérifiés sur le code source. */
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

const RACINE = path.resolve(__dirname, "..");

function fichiers(dossier: string): string[] {
  return readdirSync(dossier).flatMap((nom) => {
    const chemin = path.join(dossier, nom);
    return statSync(chemin).isDirectory() ? fichiers(chemin) : [chemin];
  });
}

const SOURCES = fichiers(RACINE).filter(
  (f) => /\.(tsx?|css)$/.test(f) && !f.includes(`${path.sep}test${path.sep}`),
);
const relatif = (f: string) => path.relative(RACINE, f).split(path.sep).join("/");

describe("charte graphique", () => {
  it("n'utilise les couleurs du drapeau que dans les fichiers de signature", () => {
    const fautifs = SOURCES.filter((f) => /--gn-/.test(readFileSync(f, "utf8")))
      .map(relatif)
      .filter((f) => !["theme/tokens.css", "theme/signature.css"].includes(f));
    expect(fautifs).toEqual([]);
  });

  it("n'écrit aucune couleur en dur dans les composants", () => {
    const fautifs = SOURCES.filter((f) => /\.tsx?$/.test(f))
      .filter((f) =>
        /#[0-9a-fA-F]{3,8}\b|rgba?\(|\b(text|bg|border)-(white|black)\b/.test(readFileSync(f, "utf8")),
      )
      .map(relatif);
    expect(fautifs).toEqual([]);
  });

  it("déclare les jetons imposés en clair et en sombre", () => {
    const jetons = readFileSync(path.join(RACINE, "theme/tokens.css"), "utf8");
    for (const j of ["--navy", "--gold", "--bg", "--surface", "--ink", "--ink-2", "--ink-3"]) {
      expect(jetons.match(new RegExp(`${j}:`, "g"))?.length).toBeGreaterThanOrEqual(2);
    }
  });
});
