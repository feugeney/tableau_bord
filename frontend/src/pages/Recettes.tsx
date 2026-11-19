import { useSearchParams } from "react-router-dom";

import { Segment } from "@/components/ui/primitives";
import { useAuth } from "@/hooks/useAuth";

import { TitrePage } from "./commun";
import RecettesAdministratives from "./domaines/RecettesAdministratives";
import RecettesDouanieres from "./domaines/RecettesDouanieres";
import RecettesFiscales from "./domaines/RecettesFiscales";

type VueRecettes = "fiscales" | "douanieres" | "administratives";

const VUES: {
  valeur: VueRecettes;
  libelle: string;
  sousTitre: string;
  /** Domaines donnant accès à la vue (au moins un). */
  domaines: string[];
  exporter?: string;
}[] = [
  {
    valeur: "fiscales",
    libelle: "Recettes fiscales",
    sousTitre: "SAFIG · Direction générale des impôts",
    domaines: ["recettes_fiscales"],
    exporter: "recettes-fiscales",
  },
  {
    valeur: "douanieres",
    libelle: "Recettes douanières",
    sousTitre: "SYDONIA · Direction générale des douanes",
    domaines: ["douanes"],
    exporter: "recettes-douanieres",
  },
  {
    valeur: "administratives",
    libelle: "Recettes administratives",
    sousTitre: "SYSOP · dividendes versés à l'État par les sociétés publiques",
    // Donnée détenue par le portefeuille de l'État : même droit d'accès que la page Portefeuille.
    domaines: ["portefeuille"],
  },
];

export default function Recettes() {
  const { utilisateur } = useAuth();
  const [params, setParams] = useSearchParams();
  const vues = VUES.filter((v) => v.domaines.some((d) => utilisateur?.domaines.includes(d)));
  const demandee = vues.find((v) => v.valeur === params.get("vue"));
  const courante = demandee ?? vues[0];

  function changer(v: VueRecettes) {
    setParams(
      (avant) => {
        const suivant = new URLSearchParams(avant);
        suivant.set("vue", v);
        // Les dividendes (SYSOP) ont leurs propres exercices et situations.
        ["exercice", "date_situation"].forEach((k) => suivant.delete(k));
        return suivant;
      },
      { replace: true },
    );
  }

  if (!courante) return null;
  return (
    <>
      <TitrePage titre="Recettes" sousTitre={courante.sousTitre} exporter={courante.exporter}>
        <Segment<VueRecettes>
          libelle="Nature des recettes"
          valeur={courante.valeur}
          options={vues}
          onChange={changer}
        />
      </TitrePage>
      {courante.valeur === "fiscales" && <RecettesFiscales />}
      {courante.valeur === "douanieres" && <RecettesDouanieres />}
      {courante.valeur === "administratives" && <RecettesAdministratives />}
    </>
  );
}
