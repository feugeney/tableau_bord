import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";

import { Cadre } from "@/components/cadre/Cadre";
import * as auth from "@/hooks/useAuth";
import { ONGLETS } from "@/lib/onglets";
import { rendre, simulerApi } from "@/test/rendu";

import RecettesFiscales from "./domaines/RecettesFiscales";
import Pilotage from "./Pilotage";
import Recettes from "./Recettes";
import Tofe from "./domaines/Tofe";

const META_NR = {
  source: "safig",
  application: "SAFIG",
  date_situation: null,
  statut_source: "non_raccorde",
  genere_le: "",
};

function connecter(est_admin: boolean) {
  vi.spyOn(auth, "useAuth").mockReturnValue({
    utilisateur: {
      id: 1,
      identifiant: "c",
      nom: "Cabinet",
      role: "ministre_cabinet",
      role_libelle: "Ministre / Cabinet",
      structure: "",
      domaines: ONGLETS.flatMap((o) => o.domaines),
      peut_exporter: true,
      est_admin,
      peut_explorer: est_admin,
      exige_2fa: true,
      a_2fa: true,
    },
    chargement: false,
    connecter: vi.fn(),
    deconnecter: vi.fn(),
    appliquerConnexion: vi.fn(),
  });
}

describe("pages", () => {
  beforeEach(() => connecter(false));

  it("une source non raccordée affiche un état vide explicite, sans erreur", async () => {
    simulerApi({ "/recettes-fiscales/": { meta: META_NR, data: null }, "/sources/": [] });
    rendre(<RecettesFiscales />);
    expect(await screen.findByText("Source non raccordée")).toBeInTheDocument();
    expect(screen.getByText("Contenu prévu dès le raccordement")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("une source en illustration affiche le bandeau et la pastille « illustration »", async () => {
    simulerApi({
      "/recettes-fiscales/": {
        meta: { ...META_NR, statut_source: "demo", date_situation: "2026-08-16", exercice: 2026 },
        data: {
          indicateurs: {
            recouvre: 1e12,
            objectif: 1.2e12,
            taux: 0.83,
            restes_a_recouvrer: 1e11,
            contentieux: 1e10,
            dossiers_contentieux: 3,
            contribuables_actifs: 10,
            taux_teledeclaration: 0.5,
          },
          par_impot: [],
          mensuel: [],
          par_centre: [],
          par_secteur: [],
          restes_par_anciennete: [],
          contentieux_par_stade: [],
          seuil_retard: 0.8,
        },
      },
      "/sources/": [],
    });
    rendre(<RecettesFiscales />);
    expect(await screen.findByRole("note")).toHaveTextContent("Données d'illustration");
    expect(screen.getAllByText(/illustration/).length).toBeGreaterThan(1);
  });

  it.each([
    [false, 10],
    [true, 10],
  ])(
    "le cadre affiche les 10 onglets et le lien d'administration seulement aux administrateurs (admin : %s)",
    async (admin, n) => {
      simulerApi({ "/situations/": { exercices: [{ exercice: 2025, dates: ["2026-09-15"] }] } });
      connecter(admin);
      rendre(
        <Routes>
          <Route element={<Cadre />}>
            <Route path="/synthese" element={<p>contenu</p>} />
          </Route>
        </Routes>,
        "/synthese",
      );
      const nav = screen.getByRole("navigation", { name: "Pages du tableau de bord" });
      expect(nav.querySelectorAll("ul a")).toHaveLength(n);
      expect(screen.getByRole("link", { name: "Synthèse" })).toHaveAttribute("aria-current", "page");
      // Lien dans la barre d'onglets (le menu du profil en contient un second).
      expect(nav.querySelectorAll('a[href="/administration"]')).toHaveLength(admin ? 1 : 0);
      expect((await screen.findAllByText(/situation au 15\/09\/2026/)).length).toBeGreaterThan(0);
    },
  );

  it("le TOFE signale le scénario fictif et présente les conventions de financement", async () => {
    simulerApi({
      "/sources/": [],
      "/tofe/": {
        meta: {
          ...META_NR,
          source: "tofe",
          statut_source: "demo",
          exercice: 2026,
          date_situation: "2026-11-13",
        },
        data: {
          indicateurs: {
            recettes_dons: 400e9,
            depenses: 500e9,
            solde_global: -100e9,
            solde_primaire: -80e9,
            solde_caisse: -110e9,
            besoin_financement: 110e9,
            financement: 110e9,
            ecart_financement: 0,
            pib: 360000e9,
            ratio_solde_pib: -0.001,
            pression_fiscale: 0.1,
            taux_recettes: 0.9,
            taux_depenses: 0.8,
          },
          lignes: [
            {
              code: "solde_global",
              libelle: "Solde global, dons compris (A − D)",
              niveau: 0,
              agregat: true,
              lfi: -90e9,
              lfr: -110e9,
              objectif_cumule: -110e9,
              realise: -100e9,
              realise_n1: -85e9,
              ecart: 10e9,
              taux: null,
            },
          ],
          mensuel: [],
          verifications: [{ libelle: "Équilibre du financement", ecart: 0, reussi: true }],
          references: [
            { titre: "Cadre officiel", url: "https://mbudget.gov.gn/", usage: "Structure uniquement" },
          ],
          perimetre: "Scénario autonome entièrement fictif",
          methode: "L'amortissement est déduit des tirages.",
        },
      },
    });
    rendre(<Tofe />, "/tofe");
    expect(await screen.findByRole("note")).toHaveTextContent(
      "budgets, réalisations et le PIB sont tous fictifs",
    );
    expect(screen.getByRole("columnheader", { name: "LFI annuelle simulée" })).toBeInTheDocument();
    expect(screen.getByRole("rowheader", { name: "Solde global, dons compris (A − D)" })).toBeInTheDocument();
    expect(screen.getByText("L'amortissement est déduit des tirages.")).toBeInTheDocument();
    expect(screen.getByText(/Vérifié · Équilibre du financement/)).toBeInTheDocument();
  });

  it.each([
    ["", "tofe"],
    ["?vue=tofe", "tofe"],
    ["?vue=plan", "plan_engagement"],
  ])("le sélecteur de Pilotage%s demande les périodes de la source %s", async (requete, source) => {
    const appels = simulerApi({ "/situations/": { exercices: [{ exercice: 2026, dates: ["2026-11-13"] }] } });
    rendre(
      <Routes>
        <Route element={<Cadre />}>
          <Route path="/pilotage" element={<p>Pilotage</p>} />
        </Route>
      </Routes>,
      `/pilotage${requete}`,
    );
    expect((await screen.findAllByText(/situation au 13\/11\/2026/)).length).toBeGreaterThan(0);
    expect(appels.mock.calls.some(([url]) => String(url).includes(`/situations/?source=${source}`))).toBe(
      true,
    );
  });

  it("Pilotage propose trois vues, TOFE par défaut, et le Trésor public en contenu prévu", async () => {
    simulerApi({ "/sources/": [], "/tofe/": { meta: { ...META_NR, source: "tofe" }, data: null } });
    rendre(<Pilotage />, "/pilotage");
    const vues = screen.getByRole("radiogroup", { name: "Tableau de pilotage" });
    expect(Array.from(vues.querySelectorAll("button")).map((b) => b.textContent)).toEqual([
      "Tableau du Trésor public",
      "Plan d'engagement",
      "TOFE",
    ]);
    expect(screen.getByRole("radio", { name: "TOFE" })).toHaveAttribute("aria-checked", "true");
    await userEvent.click(screen.getByRole("radio", { name: "Tableau du Trésor public" }));
    expect(screen.getByRole("heading", { name: "Tableau du Trésor public" })).toBeInTheDocument();
    expect(screen.getByText("Contenu prévu dès le raccordement")).toBeInTheDocument();
  });

  it("le plan d'engagement présente l'état du plan, les plafonds et les dépassements", async () => {
    const titre = (t: string, l: string, plafond: number, engage: number) => ({
      titre: t,
      libelle: l,
      plafond,
      engage_periode: engage,
      taux: engage / plafond,
      depassement: engage > plafond,
    });
    simulerApi({
      "/sources/": [],
      "/pilotage/plan-engagement/": {
        meta: {
          ...META_NR,
          source: "plan_engagement",
          statut_source: "reel",
          exercice: 2019,
          date_situation: "2026-11-18",
        },
        data: {
          periode: "T1",
          libelle_periode: "1er trimestre",
          periodes: [
            {
              code: "T1",
              libelle: "1er trimestre",
              etat_code: "PE6",
              etat_libelle: "Plan eng validé",
              courante: false,
              a_des_plafonds: true,
              plafond: 300e9,
              engage_periode: 330e9,
              taux: 1.1,
            },
          ],
          entete: {
            etat_code: "PE6",
            etat_libelle: "Plan eng validé",
            reference_arrete: "2019/527/MB/CAB",
            date_validation: "2019-02-18",
            date_ouverture: "2019-02-18",
            courante: false,
            montant_mobilisable: 300e9,
            montant_imprevu: 0,
            montant_obligatoire_titre2: 100e9,
            montant_repartissable: 200e9,
          },
          indicateurs: {
            plafond: 300e9,
            engage_periode: 330e9,
            taux: 1.1,
            marge: -30e9,
            credit: 1000e9,
            engage_ouverture: 50e9,
            nb_sections: 1,
            nb_depassements: 1,
          },
          methode_engage: { code: "ouverture_suivante", libelle: "Engagé visé CF entre deux ouvertures" },
          titres: [titre("3", "Biens et services", 300e9, 330e9)],
          sections: [
            {
              code: "18",
              libelle: "Ministère de la Santé",
              plafond: 300e9,
              engage_periode: 330e9,
              taux: 1.1,
              marge: -30e9,
              depassement: true,
              credit: 1000e9,
              engage_ouverture: 50e9,
              titres: [titre("3", "Biens et services", 300e9, 330e9)],
            },
          ],
          ajustements: [],
          circuit: [
            { code: "PE1", libelle: "Paramétrage", description: "", atteint: true },
            { code: "PE6", libelle: "Plan validé", description: "", atteint: true },
          ],
          references: [{ titre: "Décret D/2013/015/PRG/SGG", usage: "Base juridique" }],
        },
      },
    });
    rendre(<Pilotage />, "/pilotage?vue=plan");
    expect(await screen.findByText(/Arrêté 2019\/527\/MB\/CAB/)).toBeInTheDocument();
    expect(screen.getByLabelText("Circuit de validation du plan")).toHaveTextContent("Plan validé");
    expect(screen.getByText(/Dépassement global/)).toBeInTheDocument();
    expect(screen.getAllByText("Dépassement").length).toBeGreaterThan(0);
    expect(screen.getByText("Ministère de la Santé")).toBeInTheDocument();
  });

  it("Recettes regroupe trois vues, filtrées selon les domaines de l'utilisateur", async () => {
    simulerApi({
      "/sources/": [],
      "/recettes-fiscales/": { meta: META_NR, data: null },
      "/recettes-administratives/": {
        meta: {
          ...META_NR,
          source: "sysop",
          statut_source: "reel",
          exercice: 2025,
          date_situation: "2026-11-13",
        },
        data: {
          indicateurs: {
            dividendes_votes: 5e9,
            dividendes_encaisses: 2e9,
            taux_recouvrement: 0.4,
            reste_a_encaisser: 3e9,
            nb_societes: 1,
            nb_non_verses: 1,
          },
          societes: [
            {
              libelle: "Fonds Hypothécaire de Guinée",
              sigle: "FGH",
              tutelle: "",
              vote: 5e9,
              encaisse: 2e9,
              reste: 3e9,
              taux: 0.4,
              statut: "partiel",
            },
          ],
          perimetre: "Dividendes des sociétés publiques (SYSOP).",
        },
      },
    });
    rendre(<Recettes />, "/recettes");
    const vues = screen.getByRole("radiogroup", { name: "Nature des recettes" });
    expect(Array.from(vues.querySelectorAll("button")).map((b) => b.textContent)).toEqual([
      "Recettes fiscales",
      "Recettes douanières",
      "Recettes administratives",
    ]);
    expect(screen.getByRole("radio", { name: "Recettes fiscales" })).toHaveAttribute("aria-checked", "true");
    expect(await screen.findByText("Source non raccordée")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "Recettes administratives" }));
    expect(await screen.findByText("Fonds Hypothécaire de Guinée")).toBeInTheDocument();
    expect(screen.getByText("Versement partiel")).toBeInTheDocument();
  });

  it("un utilisateur des seules douanes ne voit pas les recettes fiscales", () => {
    vi.spyOn(auth, "useAuth").mockReturnValue({
      ...auth.useAuth(),
      utilisateur: { ...auth.useAuth().utilisateur!, domaines: ["douanes"] },
    });
    simulerApi({ "/sources/": [], "/douanes/": { meta: { ...META_NR, source: "sydonia" }, data: null } });
    rendre(<Recettes />, "/recettes?vue=fiscales");
    expect(screen.queryByRole("radio", { name: "Recettes fiscales" })).not.toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Recettes douanières" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });
});
