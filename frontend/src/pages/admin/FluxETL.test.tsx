import { fireEvent, screen, waitFor } from "@testing-library/react";

import { rendre } from "@/test/rendu";

import FluxETL from "./FluxETL";
import { ecrireProgrammation, lireProgrammation } from "./programmation";

it("conserve l'exception pendant l'enregistrement puis la remet à zéro après un lancement", async () => {
  const flux = {
    id: 2,
    code: "oracle-chaine-depense",
    nom: "Oracle · Chaîne Dépense",
    source: "chaine_depense",
    profil: "oracle_chaine_depense",
    exercice: 2025,
    actif: false,
    planification_cron: "",
    requetes: [],
    derniere_execution: null,
    derniere_execution_planifiee: null,
    prochaine_execution: null,
  };
  const lancements: Record<string, unknown>[] = [];
  const configurations: Record<string, unknown>[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (entree, options) => {
    if (options?.method === "PATCH") {
      const configuration = JSON.parse(String(options.body));
      configurations.push(configuration);
      Object.assign(flux, configuration);
      return new Response(JSON.stringify(flux));
    }
    if (String(entree).includes("/planificateur/")) return new Response(JSON.stringify({ actif: true }));
    if (String(entree).endsWith("/lancer/")) {
      lancements.push(JSON.parse(String(options?.body)));
      return new Response(
        JSON.stringify({
          id: lancements.length,
          statut: "apercu",
          lignes_lues: 20,
          lignes_chargees: 0,
          message: "",
          detail: { controles: [] },
        }),
      );
    }
    return new Response(JSON.stringify([flux]));
  });
  rendre(<FluxETL />);
  // Flux replié par défaut : une ligne de résumé, le formulaire au clic.
  const entete = await screen.findByRole("button", { name: /^Oracle · Chaîne Dépense/ });
  expect(entete).toHaveAttribute("aria-expanded", "false");
  expect(screen.queryByRole("button", { name: "Vérifier un aperçu" })).not.toBeInTheDocument();
  fireEvent.click(entete);
  const apercu = await screen.findByRole("button", { name: "Vérifier un aperçu" });
  fireEvent.click(screen.getByLabelText("Autoriser l'alimentation réelle par ce flux"));
  fireEvent.click(screen.getByLabelText(/Autoriser ce lancement Oracle ponctuel/));
  expect(apercu).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Enregistrer la configuration" }));
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Actualiser les données · 2025" })).toBeEnabled(),
  );
  expect(configurations[0]).not.toHaveProperty("exception_horaire_ponctuelle");
  expect(screen.getByLabelText(/Autoriser ce lancement Oracle ponctuel/)).toBeChecked();
  fireEvent.click(screen.getByRole("button", { name: "Vérifier un aperçu" }));
  await waitFor(() =>
    expect(screen.getByLabelText(/Autoriser ce lancement Oracle ponctuel/)).not.toBeChecked(),
  );
  expect(lancements[0]).toEqual({ apercu: true, exception_horaire_ponctuelle: true });
  expect(await screen.findByText(/aucune donnée métier enregistrée/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Vérifier un aperçu" }));
  await waitFor(() => expect(lancements).toHaveLength(2));
  expect(lancements[1]).toEqual({ apercu: true, exception_horaire_ponctuelle: false });
});

it("traduit les choix simples en expression cron et inversement", () => {
  expect(lireProgrammation("")).toMatchObject({ frequence: "manuel" });
  expect(lireProgrammation("0 2 * * *")).toMatchObject({ frequence: "quotidien", heure: "02:00" });
  expect(lireProgrammation("30 3 * * 1-5")).toMatchObject({ frequence: "ouvres", heure: "03:30" });
  expect(lireProgrammation("15 22 * * 6")).toMatchObject({
    frequence: "hebdomadaire",
    jour: "6",
    heure: "22:15",
  });
  expect(lireProgrammation("*/10 1-4 * * *")).toMatchObject({
    frequence: "avance",
    avance: "*/10 1-4 * * *",
  });
  for (const cron of ["", "0 2 * * *", "30 3 * * 1-5", "15 22 * * 0"]) {
    expect(ecrireProgrammation(lireProgrammation(cron))).toBe(cron);
  }
});

it("enregistre la programmation choisie et signale un planificateur arrêté", async () => {
  const flux = {
    id: 3,
    code: "sysop-portefeuille",
    nom: "SYSOP · Portefeuille",
    source: "sysop",
    profil: "sysop_portefeuille",
    exercice: 2025,
    actif: true,
    planification_cron: "",
    requetes: [],
    derniere_execution: null,
    derniere_execution_planifiee: null,
    prochaine_execution: null as string | null,
  };
  const configurations: Record<string, unknown>[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (entree, options) => {
    if (String(entree).includes("/planificateur/")) return new Response(JSON.stringify({ actif: false }));
    if (options?.method === "PATCH") {
      const configuration = JSON.parse(String(options.body));
      configurations.push(configuration);
      Object.assign(flux, configuration, { prochaine_execution: "2026-11-17T03:30:00+00:00" });
      return new Response(JSON.stringify(flux));
    }
    return new Response(JSON.stringify([flux]));
  });
  rendre(<FluxETL />);
  fireEvent.click(await screen.findByRole("button", { name: /^SYSOP · Portefeuille/ }));
  fireEvent.change(await screen.findByLabelText("Chargement automatique"), { target: { value: "ouvres" } });
  fireEvent.change(screen.getByLabelText("Heure (Conakry)"), { target: { value: "03:30" } });
  fireEvent.click(screen.getByRole("button", { name: "Enregistrer la configuration" }));
  await waitFor(() => expect(configurations).toHaveLength(1));
  expect(configurations[0]).toMatchObject({ planification_cron: "30 3 * * 1-5" });
  expect(await screen.findByText(/Prochain chargement automatique/)).toBeInTheDocument();
  expect(await screen.findByText(/Le planificateur n'est pas démarré/)).toBeInTheDocument();
});

it("présente le flux du plan d'engagement avec sa connexion Oracle et sa page", async () => {
  const flux = {
    id: 3,
    code: "oracle-plan-engagement",
    nom: "Oracle · Plan d'engagement",
    source: "plan_engagement",
    profil: "oracle_plan_engagement",
    exercice: 2023,
    actif: true,
    planification_cron: "",
    requetes: [],
    derniere_execution: null,
    derniere_execution_planifiee: null,
    prochaine_execution: null,
  };
  vi.spyOn(globalThis, "fetch").mockImplementation(async (entree) =>
    String(entree).includes("/planificateur/")
      ? new Response(JSON.stringify({ actif: true }))
      : new Response(JSON.stringify([flux])),
  );
  rendre(<FluxETL />);
  const entete = await screen.findByRole("button", { name: /^Oracle · Plan d'engagement/ });
  expect(entete).toHaveTextContent("Oracle Chaîne Dépense · plan d'engagement trimestriel");
  expect(entete).toHaveTextContent("Exercice 2023");
  fireEvent.click(entete);
  expect(screen.getByText(/TD_PLAN_ENG → plafonds par section et titre/)).toBeInTheDocument();
  // Exception horaire disponible ; pas de détail des requêtes de la Chaîne Dépense.
  expect(screen.getByLabelText(/Autoriser ce lancement Oracle ponctuel/)).toBeInTheDocument();
  expect(screen.queryByText("Requêtes et correspondances Oracle utilisées")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Actualiser les données · 2023" })).toBeEnabled();
  expect(screen.getByRole("link", { name: "Voir le plan d'engagement · 2023" })).toHaveAttribute(
    "href",
    "/pilotage?vue=plan&exercice=2023",
  );
});
