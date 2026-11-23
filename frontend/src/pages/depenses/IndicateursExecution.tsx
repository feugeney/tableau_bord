import type { ComparaisonN1, IndicateursDepense } from "@/api/types";
import { KpiCard } from "@/components/Indicateurs";
import { Montant } from "@/components/Montant";
import { dateFr, pct } from "@/lib/format";

import { EcartN1 } from "./analyses";

/** Chaque taux suit la chaîne : crédits → engagé → liquidé → ordonnancé → vu bon à payer → payé. */
export function IndicateursExecution({
  i,
  n1,
}: {
  i: IndicateursDepense;
  n1: ComparaisonN1 | null | undefined;
}) {
  const etapes = [
    {
      libelle: "Engagé",
      montant: i.credit_engage,
      taux: i.taux_engagement,
      base: "des crédits actuels",
      formule: "Engagé / crédits actuels",
    },
    {
      libelle: "Liquidé",
      montant: i.montant_liquide,
      taux: i.taux_liquidation,
      base: "de l’engagé",
      formule: "Liquidé / engagé",
    },
    {
      libelle: "Ordonnancé",
      montant: i.montant_ordonnance,
      taux: i.taux_ordonnancement,
      base: "du liquidé",
      formule: "Ordonnancé / liquidé",
    },
    {
      libelle: "Vu bon à payer",
      montant: i.montant_vbp,
      taux: i.taux_vbp,
      base: "de l’ordonnancé",
      formule: "Vu bon à payer / ordonnancé",
    },
    {
      libelle: "Payé enregistré",
      montant: i.montant_paye,
      taux: i.taux_paiement,
      base: "de l’ordonnancé",
      formule: "Payé enregistré / ordonnancé",
    },
  ];
  const passages: { libelle: string; taux: number | null }[] = [
    { libelle: "Liquidé / engagé", taux: i.taux_liquidation },
    { libelle: "Ordonnancé / liquidé", taux: i.taux_ordonnancement },
    { libelle: "Vu bon à payer / ordonnancé", taux: i.taux_vbp },
    { libelle: "Payé enregistré / ordonnancé", taux: i.taux_paiement },
  ];
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-ink-2">
        Montants en milliards de GNF · engagé sur crédits actuels, liquidé sur engagé, ordonnancé sur liquidé
        et vu bon à payer et payé sur ordonnancé.
      </p>
      <div className="grid grid-cols-1 gap-px overflow-hidden rounded border border-border bg-border sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 print:grid-cols-6">
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
        {etapes.map((e) => (
          <KpiCard
            key={e.libelle}
            libelle={e.libelle}
            valeur={<Montant gnf={e.montant} />}
            contexte={`${pct(e.taux, 1)} ${e.base}`}
            jauge={e.taux == null ? undefined : { valeur: e.taux }}
            aide={
              e.libelle === "Payé enregistré"
                ? `${e.formule} × 100. Paiements bruts enregistrés dans la Chaîne Dépense. Les paiements hors chaîne peuvent être incomplets ; ce montant ne certifie pas le total payé par le Trésor.`
                : `${e.formule} × 100.`
            }
            pied={
              e.libelle === "Engagé" && n1?.disponible ? (
                <EcartN1
                  taux={e.taux}
                  reference={n1.taux_engagement}
                  libelle={`${n1.exercice} au ${dateFr(n1.date)}`}
                />
              ) : undefined
            }
          />
        ))}
      </div>
      <details className="rounded border border-border bg-surface p-3">
        <summary className="cursor-pointer text-sm font-bold text-ink">
          Comprendre le passage entre les étapes
        </summary>
        <dl className="mt-3 grid gap-4 text-sm sm:grid-cols-2 xl:grid-cols-4">
          {passages.map((p) => (
            <div key={p.libelle}>
              <dt className="text-ink-2">{p.libelle}</dt>
              <dd className="chiffres mt-1 text-lg font-bold text-ink">{pct(p.taux, 1)}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-3 text-sm text-ink-2">
          Ratios calculés sur les montants bruts enregistrés. Vu bon à payer : <Montant gnf={i.montant_vbp} />
          . Les soldes ajustés sont présentés dans l’analyse des restes à payer.
        </p>
      </details>
    </div>
  );
}
