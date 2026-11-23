import { fireEvent, screen, waitFor } from "@testing-library/react";

import { rendre } from "@/test/rendu";

import Notifications from "./Notifications";

it("affiche un échec SMTP et actualise le suivi après le test", async () => {
  const tentatives: object[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url, options) => {
    if (String(url).includes("modeles/"))
      return new Response(
        JSON.stringify([
          { code: "depense_arbitrage_ministre", titre: "Retard de traitement — Dossiers en attente" },
        ]),
      );
    if (String(url).includes("apercu/"))
      return new Response(
        JSON.stringify({
          sujet: "Vérification du service de notification",
          texte: "Madame, Monsieur",
          html: "<p>Madame, Monsieur</p>",
        }),
      );
    if (String(url).includes("configuration/"))
      return new Response(
        JSON.stringify({
          smtp: true,
          hote: "smtp.gmail.com",
          port: 587,
          tls: true,
          ssl: false,
          expediteur: "test@example.org",
          authentification_configuree: true,
          url_application: "http://127.0.0.1:8000",
          planificateur_actif: true,
          verification_active: true,
          derniere_verification: null,
          compteurs: {},
        }),
      );
    if (options?.method === "POST") {
      expect(JSON.parse(String(options.body))).toEqual({
        destinataire: "essai@example.org",
        modele: "depense_arbitrage_ministre",
        categorie: "alerte",
      });
      const trace = {
        id: 1,
        date: "2026-11-22T12:00:00Z",
        type: "test",
        statut: "echec",
        sujet: "Test de notification",
        destinataires: ["essai@example.org"],
        utilisateur: "admin",
        regle: null,
        erreur: "Authentification SMTP refusée.",
      };
      tentatives.push(trace);
      return new Response(JSON.stringify(trace));
    }
    return new Response(JSON.stringify({ count: tentatives.length, results: tentatives }));
  });
  rendre(<Notifications />);
  expect(await screen.findByText("smtp.gmail.com · port 587 · TLS")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Adresse destinataire"), { target: { value: "essai@example.org" } });
  fireEvent.click(screen.getByRole("button", { name: "Envoyer le mail de test" }));
  expect(await screen.findByText("Test de notification")).toBeInTheDocument();
  expect(screen.getAllByText("Authentification SMTP refusée.").length).toBeGreaterThan(0);
  expect(screen.getByRole("button", { name: "Envoyer le mail de test" })).toBeEnabled();
});

it("prévisualise une relance et envoie uniquement le modèle choisi à l’adresse saisie", async () => {
  const envois: object[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url, options) => {
    const chemin = String(url);
    if (chemin.includes("modeles/"))
      return new Response(
        JSON.stringify([
          { code: "test", titre: "Vérification du service de notification" },
          { code: "depense_arbitrage_ministre", titre: "Retard de traitement — Dossiers en attente" },
          { code: "paie_doublons", titre: "Masse salariale — Doublons à vérifier" },
        ]),
      );
    if (chemin.includes("apercu/")) {
      const relance = chemin.includes("categorie=relance");
      return new Response(
        JSON.stringify({
          sujet: relance ? "[TEST] Relance — Masse salariale" : "Exemple de notification",
          texte: "Données fictives d’illustration",
          html: "<p>Données fictives d’illustration</p>",
        }),
      );
    }
    if (chemin.includes("configuration/")) return new Response(JSON.stringify({ compteurs: {} }));
    if (options?.method === "POST") {
      envois.push(JSON.parse(String(options.body)));
      return new Response(JSON.stringify({ statut: "envoye" }));
    }
    return new Response(JSON.stringify({ count: 0, results: [] }));
  });
  rendre(<Notifications />);
  const choix = await screen.findByLabelText("Modèle de notification");
  expect(choix).toHaveValue("depense_arbitrage_ministre");
  fireEvent.change(choix, { target: { value: "paie_doublons" } });
  fireEvent.change(await screen.findByLabelText("Nature du message"), { target: { value: "relance" } });
  expect(await screen.findByText("[TEST] Relance — Masse salariale")).toBeInTheDocument();
  expect(screen.getByTitle("Aperçu du mail institutionnel")).toHaveAttribute("sandbox", "");
  expect(envois).toHaveLength(0);
  fireEvent.change(screen.getByLabelText("Format de prévisualisation"), { target: { value: "texte" } });
  expect(screen.getByText("Données fictives d’illustration")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Adresse destinataire"), {
    target: { value: "destinataire@example.org" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Envoyer le mail de test" }));
  await waitFor(() =>
    expect(envois).toEqual([
      { destinataire: "destinataire@example.org", modele: "paie_doublons", categorie: "relance" },
    ]),
  );
});
