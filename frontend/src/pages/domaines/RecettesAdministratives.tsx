import { useDonnees } from "@/api/hooks";
import { DataTable, type Colonne } from "@/components/DataTable";
import { BandeauKpi, KpiCard, StatusPill } from "@/components/Indicateurs";
import { Montant } from "@/components/Montant";
import { Carte } from "@/components/ui/primitives";
import { dateFr, enMds, mds, nombre, pct } from "@/lib/format";

import { EtatPage, Zone } from "../commun";
import { ContenuPrevu } from "./commun";

type Statut = "verse" | "partiel" | "non_verse" | "sans_vote";

interface Societe {
  libelle: string;
  sigle: string;
  tutelle: string;
  vote: number;
  encaisse: number;
  reste: number;
  taux: number | null;
  statut: Statut;
}

interface Donnees {
  indicateurs: {
    dividendes_votes: number;
    dividendes_encaisses: number;
    taux_recouvrement: number | null;
    reste_a_encaisser: number;
    nb_societes: number;
    nb_non_verses: number;
  };
  societes: Societe[];
  perimetre: string;
}

const STATUTS: Record<Statut, { libelle: string; etat: "bon" | "vigilance" | "serieux" }> = {
  verse: { libelle: "Versé", etat: "bon" },
  partiel: { libelle: "Versement partiel", etat: "vigilance" },
  non_verse: { libelle: "Non versé", etat: "serieux" },
  sans_vote: { libelle: "Versé sans vote renseigné", etat: "vigilance" },
};

/** Recettes administratives : dividendes versés à l'État par les sociétés publiques (SYSOP). */
export default function RecettesAdministratives() {
  const r = useDonnees<Donnees>("/recettes-administratives/");
  return (
    <EtatPage requete={r} vide={<ContenuPrevu cle="recettes-administratives" />} indicateurs={4}>
      {(d, env) => {
        const i = d.indicateurs;
        return (
          <div className="flex flex-col gap-6">
            <p className="text-sm text-ink-2">
              Exercice {env.meta.exercice} · situation SYSOP du {dateFr(env.meta.date_situation)} · montants
              en milliards de GNF.
            </p>
            <Zone titre="Dividendes des sociétés publiques">
              <BandeauKpi colonnes={4}>
                <KpiCard
                  libelle="Dividendes votés"
                  valeur={<Montant gnf={i.dividendes_votes} />}
                  contexte={`${nombre(i.nb_societes)} société(s) avec un dividende renseigné`}
                  aide="Dividende attendu, arrêté par l'organe délibérant de la société."
                  meta={env.meta}
                />
                <KpiCard
                  libelle="Dividendes encaissés"
                  valeur={<Montant gnf={i.dividendes_encaisses} />}
                  contexte="Versés à l'État"
                  meta={env.meta}
                />
                <KpiCard
                  libelle="Taux de recouvrement"
                  valeur={pct(i.taux_recouvrement)}
                  contexte="Encaissé / voté"
                  jauge={{ valeur: i.taux_recouvrement, repere: 1 }}
                  meta={env.meta}
                />
                <KpiCard
                  libelle="Reste à encaisser"
                  valeur={<Montant gnf={i.reste_a_encaisser} />}
                  contexte={`${nombre(i.nb_non_verses)} société(s) n'ont pas tout versé`}
                  etat={i.nb_non_verses ? "vigilance" : undefined}
                  meta={env.meta}
                />
              </BandeauKpi>
            </Zone>
            <Carte
              id="dividendes-societes"
              titre="Dividendes par société"
              sousTitre="Une société sans dividende renseigné n'est pas comptée comme débitrice"
            >
              <DataTable
                donnees={d.societes}
                colonnes={COLONNES}
                libelle="Dividendes par société publique"
                nomExport={`dividendes-${env.meta.exercice}`}
                triInitial={[{ id: "vote", desc: true }]}
                vide="Aucun dividende renseigné dans SYSOP pour cet exercice."
              />
              <p className="mt-3 text-sm text-ink-2">{d.perimetre}</p>
            </Carte>
            <Carte id="recettes-administratives-prevu" titre="À raccorder ensuite">
              <ContenuPrevu cle="recettes-administratives" />
            </Carte>
          </div>
        );
      }}
    </EtatPage>
  );
}

const COLONNES: Colonne<Societe>[] = [
  {
    header: "Société",
    id: "libelle",
    accessorFn: (s) => s.libelle,
    cell: ({ row }) => (
      <span className="block min-w-[14rem]">
        {row.original.libelle}
        {row.original.sigle && <span className="text-ink-2"> · {row.original.sigle}</span>}
      </span>
    ),
  },
  {
    header: "Voté",
    accessorKey: "vote",
    cell: ({ getValue }) => <Montant gnf={getValue() as number} />,
    meta: { numerique: true, exporter: (s) => String(enMds(s.vote)) },
  },
  {
    header: "Encaissé",
    accessorKey: "encaisse",
    cell: ({ getValue }) => <Montant gnf={getValue() as number} />,
    meta: { numerique: true, exporter: (s) => String(enMds(s.encaisse)) },
  },
  {
    header: "Recouvrement",
    accessorKey: "taux",
    cell: ({ row }) => pct(row.original.taux),
    meta: { numerique: true, exporter: (s) => String(s.taux ?? "") },
  },
  {
    header: "Reste",
    accessorKey: "reste",
    cell: ({ row }) => mds(row.original.reste),
    meta: { numerique: true, exporter: (s) => String(enMds(s.reste)) },
  },
  {
    header: "Statut",
    id: "statut",
    accessorFn: (s) => STATUTS[s.statut].libelle,
    cell: ({ row }) => (
      <StatusPill etat={STATUTS[row.original.statut].etat} libelle={STATUTS[row.original.statut].libelle} />
    ),
  },
];
