import type { ComparaisonN1, IndicateursDepense } from "@/api/types";
import { BandeauKpi, KpiCard } from "@/components/Indicateurs";
import { Montant, Pourcentage } from "@/components/Montant";
import { dateFr, pct } from "@/lib/format";

import { EcartN1 } from "./analyses";

/**
 * Les six cadres de l'exécution de la dépense : crédits, puis chaque taux rapporté à l'étape précédente
 * (montants bruts), avec l'exercice précédent comme repère. Partagé par les pages Dépenses et Synthèse
 * pour que leurs architectures restent identiques.
 */
export function IndicateursExecution({
  i,
  n1,
}: {
  i: IndicateursDepense;
  n1: ComparaisonN1 | null | undefined;
}) {
  return (
    <BandeauKpi>
      <KpiCard
        libelle="Crédits actuels"
        valeur={<Montant gnf={i.credit_actuel} />}
        contexte={
          <>
            LFI <Montant gnf={i.credit_initial_lfi} /> ·{" "}
            {i.variation_lfi != null && i.variation_lfi >= 0 ? "+" : ""}
            {pct(i.variation_lfi)}
          </>
        }
      />
      <KpiCard
        libelle="Taux d'engagement"
        valeur={<Pourcentage ratio={i.taux_engagement} />}
        contexte={
          <>
            <Montant gnf={i.credit_engage} /> engagés sur les crédits
          </>
        }
        jauge={{ valeur: i.taux_engagement }}
        pied={
          <EcartN1
            taux={i.taux_engagement}
            reference={n1?.taux_engagement}
            libelle={`${n1?.exercice} au ${dateFr(n1?.date)}`}
          />
        }
        aide="Engagé / crédits actuels."
      />
      <KpiCard
        libelle="Taux de liquidation"
        valeur={<Pourcentage ratio={i.taux_liquidation} />}
        contexte={
          <>
            <Montant gnf={i.montant_liquide} /> liquidés sur l'engagé
          </>
        }
        jauge={{ valeur: i.taux_liquidation }}
        pied={
          <EcartN1
            taux={i.taux_liquidation}
            reference={n1?.cloture?.taux_liquidation}
            libelle={`Clôture ${n1?.exercice}`}
          />
        }
        aide={`Liquidé / engagé. Rapporté aux crédits : ${pct(i.taux_liquidation_sur_credits)}.`}
      />
      <KpiCard
        libelle="Taux d'ordonnancement"
        valeur={<Pourcentage ratio={i.taux_ordonnancement} />}
        contexte={
          <>
            <Montant gnf={i.montant_ordonnance} /> ordonnancés sur le liquidé
          </>
        }
        jauge={{ valeur: i.taux_ordonnancement }}
        pied={
          <EcartN1
            taux={i.taux_ordonnancement}
            reference={n1?.cloture?.taux_ordonnancement}
            libelle={`Clôture ${n1?.exercice}`}
          />
        }
        aide={`Ordonnancé / liquidé. Rapporté aux crédits : ${pct(i.taux_ordonnancement_sur_credits)}.`}
      />
      <KpiCard
        libelle="Taux de VBP"
        valeur={<Pourcentage ratio={i.taux_vbp} />}
        contexte={
          <>
            <Montant gnf={i.montant_vbp} /> vus bons à payer sur l'ordonnancé
          </>
        }
        jauge={{ valeur: i.taux_vbp }}
        pied={
          <EcartN1 taux={i.taux_vbp} reference={n1?.cloture?.taux_vbp} libelle={`Clôture ${n1?.exercice}`} />
        }
        aide="Vu bon à payer / ordonnancé. Ce ratio ne mesure pas un montant d'impayés."
      />
      <KpiCard
        libelle="Taux de paiement"
        valeur={<Pourcentage ratio={i.taux_paiement} />}
        contexte={
          <>
            <Montant gnf={i.montant_paye} /> payés sur l'ordonnancé
          </>
        }
        jauge={{ valeur: i.taux_paiement }}
        pied={
          <EcartN1
            taux={i.taux_paiement}
            reference={n1?.cloture?.taux_paiement}
            libelle={`Clôture ${n1?.exercice}`}
          />
        }
        aide={`Payé / ordonnancé, montants bruts (hors chaîne inclus). Rapporté aux crédits : ${pct(i.taux_paiement_sur_credits)}.`}
      />
    </BandeauKpi>
  );
}
