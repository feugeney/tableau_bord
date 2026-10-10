import { useDonnees } from "@/api/hooks";
import type { Investissement, Projet } from "@/api/types";
import { HBarList } from "@/components/Barres";
import { DataTable, type Colonne } from "@/components/DataTable";
import { BandeauKpi, Jauge, KpiCard, StatusPill } from "@/components/Indicateurs";
import { Montant, Pourcentage } from "@/components/Montant";
import { Carte } from "@/components/ui/primitives";
import { enMds, pct } from "@/lib/format";

import { EtatPage, TitrePage, Zone } from "./commun";

const colonnes: Colonne<Projet>[] = [
  {
    header: "Projet",
    accessorKey: "projet",
    cell: ({ row }) => <span className="block min-w-[14rem] max-w-md">{row.original.projet}</span>,
  },
  { header: "Ministère", accessorKey: "ministere" },
  {
    header: "Crédits",
    accessorKey: "credit_actuel",
    cell: ({ getValue }) => <Montant gnf={getValue() as number} />,
    meta: { numerique: true, exporter: (p) => String(enMds(p.credit_actuel)) },
  },
  {
    header: "Engagé",
    accessorKey: "taux_engagement",
    cell: ({ row }) => (
      <span className="flex min-w-[8rem] flex-col gap-1">
        <span>
          <Montant gnf={row.original.credit_engage} /> · {pct(row.original.taux_engagement)}
        </span>
        <Jauge valeur={row.original.taux_engagement} libelle={`Taux d'engagement ${row.original.projet}`} />
      </span>
    ),
    meta: { numerique: true },
  },
  {
    header: "Payé",
    accessorKey: "montant_paye",
    cell: ({ getValue }) => <Montant gnf={getValue() as number} />,
    meta: { numerique: true, exporter: (p) => String(enMds(p.montant_paye)) },
  },
  {
    header: "Situation",
    id: "situation",
    accessorFn: (p) => (p.sans_engagement ? 0 : 1),
    cell: ({ row }) =>
      row.original.sans_engagement ? (
        <StatusPill etat="critique" libelle="Sans engagement" />
      ) : (row.original.taux_engagement ?? 0) < 0.5 ? (
        <StatusPill etat="vigilance" libelle="Faible engagement" />
      ) : (
        <StatusPill etat="bon" libelle="Engagé" />
      ),
    meta: { exporter: (p) => (p.sans_engagement ? "Sans engagement" : "") },
  },
  {
    header: "Avancement physique",
    id: "physique",
    cell: () => <span className="text-sm text-ink-2">SIGPIP non raccordé</span>,
    enableSorting: false,
  },
];

export default function Investissements() {
  const r = useDonnees<Investissement>("/investissement/");
  return (
    <>
      <TitrePage
        exporter="investissements"
        titre="Investissements"
        sousTitre="Volet financier : Chaîne Dépense (titre 5) · volet physique : SIGPIP"
      />
      <EtatPage requete={r} indicateurs={4}>
        {(d, env) => (
          <div className="flex flex-col gap-6">
            <Zone titre="Indicateurs clés">
              <BandeauKpi colonnes={4}>
                <KpiCard
                  libelle="Crédits d'investissement"
                  valeur={<Montant gnf={d.credit_actuel} />}
                  contexte={
                    <>
                      LFI <Montant gnf={d.credit_initial_lfi} />
                    </>
                  }
                  meta={env.meta}
                />
                <KpiCard
                  libelle="Engagé"
                  valeur={<Pourcentage ratio={d.taux_engagement} />}
                  contexte={
                    <>
                      <Montant gnf={d.credit_engage} /> engagés
                    </>
                  }
                  jauge={{ valeur: d.taux_engagement }}
                  meta={env.meta}
                />
                <KpiCard
                  libelle="Payé"
                  valeur={<Montant gnf={d.montant_paye} />}
                  contexte={`${pct(d.credit_actuel ? d.montant_paye / d.credit_actuel : null)} des crédits`}
                  meta={env.meta}
                />
                <KpiCard
                  libelle="Projets > 1 Md sans engagement"
                  valeur={
                    <span className="chiffres">
                      {d.nb_projets_sans_engagement}
                      <span className="text-sm font-normal text-ink-3"> sur {d.nb_projets}</span>
                    </span>
                  }
                  contexte={
                    <>
                      <Montant gnf={d.credits_projets_sans_engagement} /> de crédits non mobilisés
                    </>
                  }
                  etat={d.nb_projets_sans_engagement ? "critique" : undefined}
                  meta={env.meta}
                />
              </BandeauKpi>
            </Zone>
            <Zone titre="Analyses">
              <Carte
                id="ministeres"
                titre="Huit premiers ministères par crédits d'investissement"
                sousTitre="Barre : engagé · trait : crédits actuels · barre orangée sous 50 % d'engagement"
              >
                <HBarList
                  lignes={d.top_ministeres.map((m) => ({
                    cle: m.code,
                    libelle: m.libelle_court,
                    valeur: m.credit_engage,
                    objectif: m.credit_actuel,
                  }))}
                  seuil={0.5}
                  reference="des crédits engagés"
                  retard="faible engagement"
                />
              </Carte>
            </Zone>
            <Zone titre="Détail">
              <Carte
                id="projets"
                titre="Les 12 plus grands projets"
                sousTitre="Un projet correspond à une sous-section du titre 5"
              >
                <DataTable
                  donnees={d.grands_projets}
                  colonnes={colonnes}
                  libelle="Les 12 plus grands projets d'investissement"
                  nomExport="investissements-grands-projets"
                  triInitial={[{ id: "credit_actuel", desc: true }]}
                />
              </Carte>
            </Zone>
          </div>
        )}
      </EtatPage>
    </>
  );
}
