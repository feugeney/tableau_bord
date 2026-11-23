import { lazy, Suspense, useEffect, useRef } from "react";
import { Navigate, NavLink, Route, Routes, useLocation } from "react-router-dom";

import { Squelette } from "@/components/ui/primitives";
import { cn } from "@/lib/utils";

import { TitrePage } from "../commun";

const Sources = lazy(() => import("./Sources"));
const EtatSources = lazy(() => import("./EtatSources"));
const Alimentation = lazy(() => import("./Alimentation"));
const FluxETL = lazy(() => import("./FluxETL"));
const Chargements = lazy(() => import("./Chargements"));
const Mappings = lazy(() => import("./Mappings"));
const Utilisateurs = lazy(() => import("./Utilisateurs"));
const Partages = lazy(() => import("./Partages"));
const Regles = lazy(() => import("./Regles"));
const Notifications = lazy(() => import("./Notifications"));
const Parametres = lazy(() => import("./Parametres"));
const Entrepot = lazy(() => import("./Entrepot"));
const Journal = lazy(() => import("./Journal"));

const RUBRIQUES = [
  { chemin: "vue-ensemble", libelle: "Vue d'ensemble", element: <Alimentation /> },
  { chemin: "etat-sources", libelle: "État des sources", element: <EtatSources /> },
  { chemin: "sources", libelle: "Connexions aux sources", element: <Sources /> },
  { chemin: "flux-etl", libelle: "Flux ETL", element: <FluxETL /> },
  { chemin: "chargements", libelle: "Exécutions et qualité", element: <Chargements /> },
  { chemin: "mappings", libelle: "Mappings de colonnes", element: <Mappings /> },
  { chemin: "donnees", libelle: "Base centrale", element: <Entrepot /> },
  { chemin: "donnees-test", libelle: "Données de test", element: <Entrepot tests /> },
  { chemin: "utilisateurs", libelle: "Utilisateurs et accès", element: <Utilisateurs /> },
  { chemin: "partages", libelle: "Partage de données (API)", element: <Partages /> },
  { chemin: "regles", libelle: "Règles d'alerte", element: <Regles /> },
  { chemin: "notifications", libelle: "Notifications et mails", element: <Notifications /> },
  { chemin: "parametres", libelle: "Paramètres et seuils", element: <Parametres /> },
  { chemin: "journal", libelle: "Journal d'audit", element: <Journal /> },
];

/** Administration des connexions, de l'alimentation et des accès. */
export default function Administration() {
  const { pathname } = useLocation();
  const liste = useRef<HTMLUListElement>(null);
  useEffect(() => {
    // Sur mobile, la rubrique active est ramenée dans la zone visible.
    liste.current
      ?.querySelector<HTMLElement>('[aria-current="page"]')
      ?.scrollIntoView?.({ block: "nearest", inline: "center" });
  }, [pathname]);
  return (
    <>
      <TitrePage
        titre="Administration du tableau de bord"
        sousTitre="Réservé aux administrateurs DNSI · toutes les actions sont journalisées"
      />
      <div className="grid gap-6 lg:grid-cols-[220px_minmax(0,1fr)]">
        <nav
          aria-label="Rubriques d'administration"
          className="sans-impression max-lg:defilement-fondu min-w-0"
        >
          <ul ref={liste} className="flex gap-1 overflow-x-auto lg:flex-col lg:overflow-visible">
            {RUBRIQUES.map((r) => (
              <li key={r.chemin} className="shrink-0">
                <NavLink
                  to={r.chemin}
                  className={({ isActive }) =>
                    cn(
                      "block whitespace-nowrap rounded-sm border-l-[3px] px-3 py-2 text-base",
                      isActive
                        ? "border-gold bg-surface font-bold text-ink"
                        : "border-transparent text-ink-2 hover:bg-hover hover:text-ink",
                    )
                  }
                >
                  {r.libelle}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <div className="min-w-0">
          <Suspense fallback={<Squelette className="h-64 w-full" />}>
            <Routes>
              <Route index element={<Navigate to="vue-ensemble" replace />} />
              <Route path="entrepot" element={<Navigate to="../donnees" replace />} />
              {RUBRIQUES.map((r) => (
                <Route key={r.chemin} path={r.chemin} element={r.element} />
              ))}
            </Routes>
          </Suspense>
        </div>
      </div>
    </>
  );
}
