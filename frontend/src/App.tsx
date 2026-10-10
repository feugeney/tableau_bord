import { lazy, type ReactElement } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { Cadre } from "@/components/cadre/Cadre";
import { Squelette } from "@/components/ui/primitives";
import { useAuth } from "@/hooks/useAuth";
import { ONGLETS } from "@/lib/onglets";
import { Activer2FA, Connexion } from "@/pages/Connexion";

// Chargement différé : chaque page et ses graphiques dans un paquet séparé.
const Synthese = lazy(() => import("@/pages/Synthese"));
const Depenses = lazy(() => import("@/pages/Depenses"));
const Investissements = lazy(() => import("@/pages/Investissements"));
const PageIntrouvable = lazy(() => import("@/pages/PageIntrouvable"));
const RecettesFiscales = lazy(() => import("@/pages/domaines/RecettesFiscales"));
const RecettesDouanieres = lazy(() => import("@/pages/domaines/RecettesDouanieres"));
const Tresorerie = lazy(() => import("@/pages/domaines/Tresorerie"));
const DettePublique = lazy(() => import("@/pages/domaines/DettePublique"));
const Patrimoine = lazy(() => import("@/pages/domaines/Patrimoine"));
const Portefeuille = lazy(() => import("@/pages/domaines/Portefeuille"));
const MarchesPublics = lazy(() => import("@/pages/domaines/MarchesPublics"));
const Administration = lazy(() => import("@/pages/admin/Administration"));
const Exploration = lazy(() => import("@/pages/Exploration"));

const PAGES: Record<string, ReactElement> = {
  "/synthese": <Synthese />,
  "/depenses": <Depenses />,
  "/recettes-fiscales": <RecettesFiscales />,
  "/recettes-douanieres": <RecettesDouanieres />,
  "/tresorerie": <Tresorerie />,
  "/dette-publique": <DettePublique />,
  "/investissements": <Investissements />,
  "/patrimoine": <Patrimoine />,
  "/portefeuille": <Portefeuille />,
  "/marches-publics": <MarchesPublics />,
};

export function App() {
  const { utilisateur, chargement } = useAuth();
  if (chargement) return <Squelette className="m-8 h-40" />;
  if (!utilisateur) return <Connexion />;
  if (utilisateur.exige_2fa && !utilisateur.a_2fa) return <Activer2FA />;

  const autorises = ONGLETS.filter((o) => utilisateur.domaines.includes(o.domaine));
  return (
    <Routes>
      <Route element={<Cadre />}>
        <Route index element={<Navigate to={autorises[0]?.chemin ?? "/synthese"} replace />} />
        {autorises.map((o) => (
          <Route key={o.chemin} path={o.chemin} element={PAGES[o.chemin]} />
        ))}
        {utilisateur.est_admin && <Route path="/administration/*" element={<Administration />} />}
        {utilisateur.peut_explorer && <Route path="/exploration" element={<Exploration />} />}
        <Route path="*" element={<PageIntrouvable />} />
      </Route>
    </Routes>
  );
}
