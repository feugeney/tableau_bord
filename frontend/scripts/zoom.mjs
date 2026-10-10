/** Capture ciblée : node scripts/zoom.mjs <page> <largeur> <clair|sombre> <sortie.png> [sélecteur] [hauteur] */
import { chromium } from "playwright";

const [nom, largeur, theme, sortie, selecteur, hauteur] = process.argv.slice(2);
const URL_BASE = process.env.TDB_URL ?? "http://localhost:5173";
const b = await chromium.launch();
const c = await b.newContext({
  viewport: { width: Number(largeur), height: Number(hauteur ?? 900) },
  locale: "fr-FR",
});
await c.addInitScript((t) => localStorage.setItem("tdb.theme", t), theme);
const p = await c.newPage();
await p.goto(URL_BASE);
await p.getByLabel("Identifiant").fill(process.env.TDB_ID ?? "essai");
await p.getByLabel("Mot de passe").fill(process.env.TDB_MDP ?? "");
await p.getByRole("button", { name: "Se connecter" }).click();
await p.waitForURL(/synthese/);
await p.goto(`${URL_BASE}/${nom}`);
await p.waitForLoadState("networkidle");
await p.waitForTimeout(500);
if (selecteur) {
  await p.locator(selecteur).first().scrollIntoViewIfNeeded();
  await p.locator(selecteur).first().screenshot({ path: sortie });
} else {
  await p.screenshot({ path: sortie });
}
await b.close();
