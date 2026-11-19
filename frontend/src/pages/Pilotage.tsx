import { useSearchParams } from "react-router-dom";

import { Segment } from "@/components/ui/primitives";

import { TitrePage } from "./commun";
import PlanEngagement from "./domaines/PlanEngagement";
import Tofe from "./domaines/Tofe";
import { ContenuPrevu } from "./domaines/commun";

type VuePilotage = "tresor" | "plan" | "tofe";

const VUES_PILOTAGE: { valeur: VuePilotage; libelle: string; sousTitre: string }[] = [
  {
    valeur: "tresor",
    libelle: "Tableau du Trésor public",
    sousTitre: "Trésor public · position et flux de trésorerie de l'État",
  },
  {
    valeur: "plan",
    libelle: "Plan d'engagement",
    sousTitre: "Chaîne Dépense · plafonds trimestriels d'engagement par ministère et par titre",
  },
  {
    valeur: "tofe",
    libelle: "TOFE",
    sousTitre: "Tableau des opérations financières de l'État · cadre guinéen",
  },
];

/** Vue demandée dans l'URL (?vue=…), TOFE par défaut. */
function vuePilotage(params: URLSearchParams): VuePilotage {
  const v = params.get("vue");
  return VUES_PILOTAGE.some((o) => o.valeur === v) ? (v as VuePilotage) : "tofe";
}

export default function Pilotage() {
  const [params, setParams] = useSearchParams();
  const vue = vuePilotage(params);
  const courante = VUES_PILOTAGE.find((o) => o.valeur === vue)!;

  function changer(v: VuePilotage) {
    setParams(
      (avant) => {
        const suivant = new URLSearchParams(avant);
        suivant.set("vue", v);
        // Chaque vue a sa propre source : l'exercice et la situation d'une autre vue ne s'appliquent pas.
        ["exercice", "date_situation", "periode"].forEach((k) => suivant.delete(k));
        return suivant;
      },
      { replace: true },
    );
  }

  return (
    <>
      <TitrePage
        titre="Pilotage"
        sousTitre={courante.sousTitre}
        exporter={vue === "tofe" ? "tofe" : undefined}
      >
        <Segment<VuePilotage>
          libelle="Tableau de pilotage"
          valeur={vue}
          options={VUES_PILOTAGE}
          onChange={changer}
        />
      </TitrePage>
      {vue === "tresor" && <TableauTresor />}
      {vue === "plan" && <PlanEngagement />}
      {vue === "tofe" && <Tofe />}
    </>
  );
}

function TableauTresor() {
  return (
    <section className="carte p-4" aria-labelledby="tresor-public-titre">
      <h2 id="tresor-public-titre" className="text-base font-bold text-ink">
        Tableau du Trésor public
      </h2>
      <p className="mt-1 text-sm text-ink-2">
        Contenu à définir avec le Trésor public. Aucun chiffre n'est affiché tant que la source n'est pas
        raccordée.
      </p>
      <div className="mt-4">
        <ContenuPrevu cle="tresor-public" />
      </div>
    </section>
  );
}
