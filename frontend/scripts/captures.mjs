/**
 * Captures d'écran des pages (Playwright) : 1366, 768 et 400 px, thèmes clair et sombre.
 * Signale aussi tout défilement horizontal de la page.
 *
 *   node scripts/captures.mjs <dossier> [pages…]
 *   TDB_URL=http://localhost:5173 TDB_ID=essai TDB_MDP=… node scripts/captures.mjs captures/avant
 */
import { mkdirSync } from "node:fs";
import { chromium } from "playwright";

const URL_BASE = process.env.TDB_URL ?? "http://localhost:5173";
const ID = process.env.TDB_ID ?? "essai";
const MDP = process.env.TDB_MDP ?? "";
const dossier = process.argv[2] ?? "captures";
const PAGES = process.argv.slice(3).length
  ? process.argv.slice(3)
  : ["synthese", "depenses", "investissements", "recettes-fiscales"];
const LARGEURS = [
  [1366, 768],
  [768, 1024],
  [400, 860],
];
const THEMES = ["clair", "sombre"];

mkdirSync(dossier, { recursive: true });
const navigateur = await chromium.launch();
const rapport = [];

for (const theme of THEMES) {
  for (const [l, h] of LARGEURS) {
    const contexte = await navigateur.newContext({ viewport: { width: l, height: h }, locale: "fr-FR" });
    await contexte.addInitScript((t) => localStorage.setItem("tdb.theme", t), theme);
    const page = await contexte.newPage();
    await page.goto(URL_BASE);
    await page
      .getByLabel("Identifiant")
      .waitFor({ timeout: 15000 })
      .catch(() => {});
    if (
      await page
        .getByLabel("Identifiant")
        .isVisible()
        .catch(() => false)
    ) {
      await page.screenshot({ path: `${dossier}/connexion-${l}-${theme}.png` });
      await page.getByLabel("Identifiant").fill(ID);
      await page.getByLabel("Mot de passe").fill(MDP);
      await page.getByRole("button", { name: "Se connecter" }).click();
      await page.waitForURL(/synthese/);
    }
    for (const nom of PAGES) {
      await page.goto(`${URL_BASE}/${nom}`);
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(600);
      const debord = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      if (debord > 0) rapport.push(`${nom} ${l}px ${theme} : débordement horizontal de ${debord}px`);
      await page.screenshot({ path: `${dossier}/${nom}-${l}-${theme}.png`, fullPage: l !== 1366 });
      if (l === 1366) {
        await page.screenshot({ path: `${dossier}/${nom}-${l}-${theme}-complet.png`, fullPage: true });
      }
    }
    await contexte.close();
  }
}
await navigateur.close();
console.log(rapport.length ? rapport.join("\n") : "Aucun débordement horizontal.");
