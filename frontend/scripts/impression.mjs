/** PDF A4 paysage (feuille @media print) et capture du mode présentation. node scripts/impression.mjs <dossier> */
import { mkdirSync } from "node:fs";
import { chromium } from "playwright";

const dossier = process.argv[2] ?? "captures/impression";
const URL_BASE = process.env.TDB_URL ?? "http://localhost:5173";
mkdirSync(dossier, { recursive: true });
const b = await chromium.launch();
const c = await b.newContext({ viewport: { width: 1366, height: 768 }, locale: "fr-FR" });
await c.addInitScript(() => localStorage.setItem("tdb.theme", "sombre")); // l'impression doit repasser en clair
const p = await c.newPage();
await p.goto(URL_BASE);
await p.getByLabel("Identifiant").fill(process.env.TDB_ID ?? "essai");
await p.getByLabel("Mot de passe").fill(process.env.TDB_MDP ?? "");
await p.getByRole("button", { name: "Se connecter" }).click();
await p.waitForURL(/synthese/);
for (const nom of ["synthese", "depenses"]) {
  await p.goto(`${URL_BASE}/${nom}`);
  await p.waitForLoadState("networkidle");
  await p.waitForTimeout(500);
  await p.pdf({ path: `${dossier}/${nom}.pdf`, format: "A4", landscape: true, printBackground: true });
  await p.emulateMedia({ media: "print" });
  await p.setViewportSize({ width: 1123, height: 794 });
  await p.screenshot({ path: `${dossier}/${nom}-apercu-impression.png` });
  await p.emulateMedia({ media: null });
  await p.setViewportSize({ width: 1366, height: 768 });
}
await p.goto(`${URL_BASE}/synthese`);
await p.waitForLoadState("networkidle");
await p.getByRole("button", { name: "Mode présentation" }).click();
await p.waitForTimeout(400);
await p.screenshot({ path: `${dossier}/presentation-synthese.png` });
await b.close();
