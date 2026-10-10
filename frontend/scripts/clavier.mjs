/**
 * Navigation au clavier (Playwright) : lien d'évitement, focus visible, onglets, panneau latéral.
 *   TDB_ID=… TDB_MDP=… node scripts/clavier.mjs
 */
import { chromium } from "playwright";

const URL_BASE = process.env.TDB_URL ?? "http://localhost:5173";
const echecs = [];
const verifier = (condition, message) => {
  console.log(`${condition ? "OK   " : "ÉCHEC"} ${message}`);
  if (!condition) echecs.push(message);
};

const b = await chromium.launch();
const p = await (await b.newContext({ viewport: { width: 1366, height: 768 } })).newPage();

// Connexion entièrement au clavier.
await p.goto(URL_BASE);
await p.getByLabel("Identifiant").waitFor();
await p.keyboard.press("Tab");
verifier(await p.evaluate(() => document.activeElement?.id === "identifiant"), "connexion : le premier Tab atteint l'identifiant");
await p.keyboard.type(process.env.TDB_ID ?? "essai");
await p.keyboard.press("Tab");
await p.keyboard.type(process.env.TDB_MDP ?? "");
await p.keyboard.press("Enter");
await p.waitForURL(/synthese/);
await p.waitForLoadState("networkidle");
verifier(await p.evaluate(() => document.activeElement?.id === "contenu"), "après la connexion, le focus est placé sur le contenu principal");

// Chargement de page : lien d'évitement, puis parcours des éléments avec contrôle du contour de focus.
await p.reload();
await p.waitForLoadState("networkidle");
await p.keyboard.press("Tab");
const evitement = await p.evaluate(() => document.activeElement?.textContent?.trim());
verifier(evitement === "Aller au contenu", "le premier Tab atteint « Aller au contenu »");
const sansContour = [];
const atteints = [];
for (let i = 0; i < 40; i++) {
  await p.keyboard.press("Tab");
  const info = await p.evaluate(() => {
    const el = document.activeElement;
    const s = getComputedStyle(el);
    const visible = s.outlineStyle !== "none" && parseFloat(s.outlineWidth) >= 2;
    return { nom: (el.getAttribute("aria-label") || el.textContent || el.tagName).trim().slice(0, 40), visible };
  });
  atteints.push(info.nom);
  if (!info.visible) sansContour.push(info.nom);
}
verifier(sansContour.length === 0, `focus visible sur les 40 premiers éléments${sansContour.length ? ` (manque : ${sansContour.join(", ")})` : ""}`);
verifier(atteints.some((n) => n.startsWith("Dépenses")), "les onglets sont atteints au clavier");
verifier(atteints.some((n) => /Passer au thème/.test(n)), "la bascule de thème est atteinte");

// Onglet activé à la touche Entrée.
await p.getByRole("link", { name: "Dépenses", exact: true }).focus();
await p.keyboard.press("Enter");
await p.waitForURL(/depenses/);
verifier(true, "Entrée sur l'onglet « Dépenses » ouvre la page");
await p.waitForLoadState("networkidle");

// Détail d'un ministère : ouverture au clavier, focus dans le panneau, Échap, retour du focus.
const premier = p.locator("#ministeres tbody tr td button").first();
await premier.focus();
const nom = (await premier.textContent())?.trim();
await p.keyboard.press("Enter");
await p.getByRole("dialog").waitFor();
verifier(await p.evaluate(() => Boolean(document.activeElement?.closest('[role="dialog"]'))), `Entrée ouvre le détail de « ${nom} » et le focus entre dans le panneau`);
verifier(new URL(p.url()).searchParams.has("ministere"), "l'état du panneau est dans l'URL");
await p.keyboard.press("Escape");
await p.getByRole("dialog").waitFor({ state: "detached" });
verifier(await p.evaluate(() => document.activeElement?.closest("#ministeres") !== null), "Échap ferme le panneau et rend le focus au tableau");

// Tri d'une colonne au clavier.
const tri = p.locator("#ministeres thead button").nth(2);
await tri.focus();
await p.keyboard.press("Enter");
const sens = await p.locator("#ministeres thead th").nth(2).getAttribute("aria-sort");
verifier(sens === "ascending" || sens === "descending", `tri au clavier (aria-sort = ${sens})`);

// Filtre de nature (groupe radio) au clavier.
await p.getByRole("radio", { name: "Investissement" }).focus();
await p.keyboard.press("Space");
await p.waitForURL(/nature=investissement/);
verifier(true, "le filtre de nature s'active au clavier et se reflète dans l'URL");

await b.close();
console.log(echecs.length ? `\n${echecs.length} échec(s).` : "\nNavigation au clavier conforme.");
process.exit(echecs.length ? 1 : 0);
