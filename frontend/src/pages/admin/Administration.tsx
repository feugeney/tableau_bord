import { lazy, Suspense, useEffect, useRef } from "react";
import { Navigate, NavLink, Route, Routes, useLocation } from "react-router-dom";

import { Squelette } from "@/components/ui/primitives";
import { cn } from "@/lib/utils";

import { TitrePage } from "../commun";

const Sources = lazy(() => import("./Sources"));
const Chargements = lazy(() => import("./Chargements"));
const Mappings = lazy(() => import("./Mappings"));
const Utilisateurs = lazy(() => import("./Utilisateurs"));
const Partages = lazy(() => import("./Partages"));
const Regles = lazy(() => import("./Regles"));
const Parametres = lazy(() => import("./Parametres"));
const Entrepot = lazy(() => import("./Entrepot"));
const Journal = lazy(() => import("./Journal"));

const RUBRIQUES = [
  { chemin: "sources", libelle: "Sources et connecteurs", element: <Sources /> },
  { chemin: "chargements", libelle: "Imports et chargements", element: <Chargements /> },
  { chemin: "mappings", libelle: "Mappings de colonnes", element: <Mappings /> },
  { chemin: "entrepot", libelle: "Entrepôt et illustration", element: <Entrepot /> },
  { chemin: "utilisateurs", libelle: "Utilisateurs et accès", element: <Utilisateurs /> },
  { chemin: "partages", libelle: "Partage de données (API)", element: <Partages /> },
  { chemin: "regles", libelle: "Règles d'alerte", element: <Regles /> },
  { chemin: "parametres", libelle: "Paramètres et seuils", element: <Parametres /> },
  { chemin: "journal", libelle: "Journal d'audit", element: <Journal /> },
];

/** Administration technique de l'entrepôt (rôle DNSI, double authentification). */
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
        titre="Administration de l'entrepôt"
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
              <Route index element={<Navigate to="sources" replace />} />
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
