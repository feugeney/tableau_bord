import { useDonnees } from "@/api/hooks";
import { HBarList, Legende, StackedProgress } from "@/components/Barres";
import { DataTable } from "@/components/DataTable";
import { GroupedBarChart } from "@/components/GroupedBarChart";
import { BandeauKpi, KpiCard, Note, StatusPill, type Etat } from "@/components/Indicateurs";
import { Montant, Pourcentage } from "@/components/Montant";
import { SourceBadge } from "@/components/Source";
import { Carte } from "@/components/ui/primitives";
import { enMds, nombre, pct } from "@/lib/format";

import { EtatPage, TitrePage, Zone } from "../commun";
import { ContenuBloc, ContenuPrevu, libelleMois, type Bloc } from "./commun";

interface Repartition {
  code: string;
  libelle: string;
  nombre: number;
  montant: number;
  part: number | null;
}

interface Exemple {
  numero: string;
  autorite_contractante: string;
  objet: string;
  montant_ttc: number;
  ecart?: number;
}

interface Controle {
  nombre: number;
  montant: number;
  exemples?: Exemple[];
}

interface Donnees {
  indicateurs: {
    nb_marches: number;
    montant_ttc: number;
    montant_ht: number;
    part_entente_directe: number | null;
    entente_directe_excessive: boolean;
    seuil_entente_directe: number;
    montant_reserve: number;
    nb_reservations: number;
    delai_reservation_immatriculation: number | null;
    delai_immatriculation_paiement: number | null;
    seuil_delai: number;
    montant_paye: number;
    taux_paiement: number | null;
    montant_avenants: number;
    part_avenants: number | null;
    nb_en_execution: number;
    nb_recours: number;
  };
  controles: {
    marches_sans_reservation: Controle;
    marches_depassant_reservation: Controle;
    paiements_superieurs: Controle;
    paiements_sans_marche: Controle;
    reservations_inutilisees: Controle & { jours: number };
  };
  par_mode: Repartition[];
  par_type: Repartition[];
  mensuel: { mois: number; nombre: number; montant: number }[];
  par_autorite: { libelle: string; nombre: number; montant: number }[];
  titulaires: {
    titulaire_nif: string;
    libelle: string;
    nombre: number;
    montant: number;
    part: number | null;
  }[];
  engagements_chaine_depense: Bloc<{
    procedures: { libelle: string; nb_engagements: number; montant_engage: number; montant_paye: number }[];
    montant_engage: number;
    montant_ordonnance: number;
    montant_paye: number;
    nb_engagements: number;
  }>;
}

// Modes de passation : rampe bleue neutre (ce ne sont pas des états).
const COULEURS_MODES: Record<string, string> = {
  aoo: "var(--phase-6)",
  aor: "var(--phase-4)",
  cotation: "var(--phase-3)",
  drp: "var(--phase-2)",
  entente_directe: "var(--serie-2)",
};

/** Contrôles de rapprochement, dans l'ordre de la chaîne F3 → F4 → F5.
 *  Sérieux : ce qui déclenche l'alerte « Anomalies de rapprochement des marchés ». */
function lignesControles(c: Donnees["controles"]) {
  return [
    {
      cle: "sans_reservation",
      libelle: "Marchés immatriculés sans réservation de crédit",
      flux: "F3 ↔ F4",
      etat: "serieux" as Etat,
      mesure: "Montant TTC",
      ...c.marches_sans_reservation,
    },
    {
      cle: "depasse_reservation",
      libelle: "Marchés supérieurs au crédit réservé",
      flux: "F3 ↔ F4",
      etat: "vigilance" as Etat,
      mesure: "Dépassement",
      ...c.marches_depassant_reservation,
    },
    {
      cle: "sur_payes",
      libelle: "Paiements au-delà du montant du marché",
      flux: "F4 ↔ F5",
      etat: "serieux" as Etat,
      mesure: "Trop payé",
      ...c.paiements_superieurs,
    },
    {
      cle: "orphelins",
      libelle: "Paiements sans marché immatriculé",
      flux: "F4 ↔ F5",
      etat: "serieux" as Etat,
      mesure: "Montant payé",
      ...c.paiements_sans_marche,
    },
    {
      cle: "inutilisees",
      libelle: `Réservations visées non utilisées depuis plus de ${c.reservations_inutilisees.jours} jours`,
      flux: "F3 ↔ F4",
      etat: "vigilance" as Etat,
      mesure: "Crédit immobilisé",
      ...c.reservations_inutilisees,
    },
  ];
}

function anomalies(c: Donnees["controles"]) {
  const avec = (libelle: string, x: Controle) => (x.exemples ?? []).map((e) => ({ anomalie: libelle, ...e }));
  return [
    ...avec("Paiement au-delà du marché", c.paiements_superieurs),
    ...avec("Sans réservation de crédit", c.marches_sans_reservation),
    ...avec("Supérieur au crédit réservé", c.marches_depassant_reservation),
  ];
}

function Jours({ valeur }: { valeur: number | null }) {
  return (
    <span className="chiffres">
      {nombre(valeur)} <span className="text-sm font-normal text-ink-3">jours</span>
    </span>
  );
}

export default function MarchesPublics() {
  const r = useDonnees<Donnees>("/marches-publics/");
  return (
    <>
      <TitrePage
        titre="Marchés publics"
        sousTitre="Telemo · réservations de crédit, marchés immatriculés et paiements"
        exporter="marches-publics"
      />
      <EtatPage
        requete={r}
        vide={<ContenuPrevu cle="marches-publics" />}
        indicateurs={4}
        precisionDemo="Les engagements passés en procédure « marché public » viennent de la Chaîne Dépense (réel)."
      >
        {(d, env) => {
          const i = d.indicateurs;
          const controles = lignesControles(d.controles);
          const aExaminer = anomalies(d.controles);
          const delaiLong =
            i.delai_reservation_immatriculation !== null &&
            i.delai_reservation_immatriculation > i.seuil_delai;
          return (
            <div className="flex flex-col gap-6">
              <Zone titre="Indicateurs clés">
                <BandeauKpi colonnes={4}>
                  <KpiCard
                    libelle="Marchés immatriculés"
                    valeur={<Montant gnf={i.montant_ttc} />}
                    contexte={
                      <>
                        {nombre(i.nb_marches)} marchés, montant TTC · <Montant gnf={i.montant_ht} /> HT
                      </>
                    }
                    aide="Marchés immatriculés dans Telemo et transmis à la Chaîne de dépenses (flux F4)."
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle="Part de l'entente directe"
                    valeur={<Pourcentage ratio={i.part_entente_directe} />}
                    contexte={`En montant · seuil ${pct(i.seuil_entente_directe)}`}
                    jauge={{
                      valeur: i.part_entente_directe,
                      repere: i.seuil_entente_directe,
                      etat: i.entente_directe_excessive ? "serieux" : undefined,
                    }}
                    etat={i.entente_directe_excessive ? "serieux" : undefined}
                    aide="Marchés passés de gré à gré, sans mise en concurrence, rapportés au montant de l'ensemble des marchés immatriculés."
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle="De la réservation à l'immatriculation"
                    valeur={<Jours valeur={i.delai_reservation_immatriculation} />}
                    contexte={
                      <>
                        Délai moyen depuis le visa du contrôleur financier · puis{" "}
                        {nombre(i.delai_immatriculation_paiement)} jours jusqu'au premier paiement
                      </>
                    }
                    etat={delaiLong ? "vigilance" : undefined}
                    aide={`Du visa de la réservation de crédit (F3) à l'immatriculation du marché (F4). Seuil : ${nombre(i.seuil_delai)} jours.`}
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle="Exécution financière"
                    valeur={<Pourcentage ratio={i.taux_paiement} />}
                    contexte={
                      <>
                        <Montant gnf={i.montant_paye} /> payés par la BCRG · {nombre(i.nb_en_execution)}{" "}
                        marchés en exécution
                      </>
                    }
                    jauge={{ valeur: i.taux_paiement }}
                    aide="Paiements effectifs (flux F5) rapportés au montant TTC des marchés immatriculés."
                    meta={env.meta}
                  />
                </BandeauKpi>
              </Zone>

              <Zone titre="Points d'attention">
                <Carte
                  id="controles"
                  titre="Contrôles de cohérence Telemo ↔ Chaîne de dépenses"
                  sousTitre="Rapprochement des réservations (F3), des marchés (F4) et des paiements (F5)"
                >
                  <DataTable
                    donnees={controles}
                    recherche={false}
                    libelle="Contrôles de cohérence des flux Telemo"
                    colonnes={[
                      {
                        header: "Contrôle",
                        id: "libelle",
                        accessorFn: (c) => c.libelle,
                        cell: ({ row }) =>
                          row.original.nombre ? (
                            <StatusPill etat={row.original.etat} libelle={row.original.libelle} />
                          ) : (
                            row.original.libelle
                          ),
                      },
                      { header: "Flux", accessorKey: "flux" },
                      {
                        header: "Nombre",
                        accessorKey: "nombre",
                        cell: ({ getValue }) => nombre(getValue() as number),
                        meta: { numerique: true },
                      },
                      {
                        header: "Montant",
                        accessorKey: "montant",
                        cell: ({ row }) => (
                          <span title={row.original.mesure}>
                            <Montant gnf={row.original.montant} />
                          </span>
                        ),
                        meta: { numerique: true },
                      },
                    ]}
                  />
                  <Note>
                    Rapprochement sur le numéro de réservation (F3 ↔ F4) et le numéro d'immatriculation (F4 ↔
                    F5). Montant : TTC du marché, dépassement, trop payé ou crédit immobilisé selon le
                    contrôle.
                  </Note>
                </Carte>
                <div className="grid gap-4 lg:grid-cols-2">
                  <Carte
                    id="modes"
                    titre="Modes de passation"
                    sousTitre="Part en montant des marchés immatriculés"
                  >
                    <StackedProgress
                      libelle="Répartition des marchés immatriculés par mode de passation"
                      segments={d.par_mode.map((m) => ({
                        code: m.code,
                        libelle: m.libelle,
                        valeur: m.montant,
                        couleur: COULEURS_MODES[m.code] ?? "var(--phase-3)",
                      }))}
                    />
                    <div className="mt-3">
                      <Legende
                        elements={d.par_mode.map((m) => ({
                          libelle: m.libelle,
                          couleur: COULEURS_MODES[m.code] ?? "var(--phase-3)",
                        }))}
                      />
                    </div>
                    <DataTable
                      donnees={d.par_mode}
                      recherche={false}
                      libelle="Marchés immatriculés par mode de passation"
                      colonnes={[
                        {
                          header: "Mode",
                          accessorKey: "libelle",
                          cell: ({ row }) =>
                            row.original.code === "entente_directe" && i.entente_directe_excessive ? (
                              <StatusPill etat="serieux" libelle={row.original.libelle} />
                            ) : (
                              row.original.libelle
                            ),
                        },
                        { header: "Marchés", accessorKey: "nombre", meta: { numerique: true } },
                        {
                          header: "Montant",
                          accessorKey: "montant",
                          cell: ({ getValue }) => <Montant gnf={getValue() as number} />,
                          meta: { numerique: true },
                        },
                        {
                          header: "Part",
                          accessorKey: "part",
                          cell: ({ getValue }) => pct(getValue() as number),
                          meta: { numerique: true },
                        },
                      ]}
                    />
                  </Carte>
                  <Carte
                    id="chaine"
                    titre="Du crédit réservé au paiement"
                    sousTitre="Montants cumulés de chaque flux sur l'exercice"
                  >
                    <HBarList
                      lignes={[
                        {
                          libelle: "Crédits réservés et visés (F3)",
                          valeur: i.montant_reserve,
                          complement: `${nombre(i.nb_reservations)} réservations`,
                        },
                        {
                          libelle: "Marchés immatriculés (F4)",
                          valeur: i.montant_ttc,
                          complement: `${nombre(i.nb_marches)} marchés, montant TTC`,
                        },
                        {
                          libelle: "Paiements effectifs BCRG (F5)",
                          valeur: i.montant_paye,
                          complement: `${pct(i.taux_paiement)} du montant des marchés`,
                        },
                      ]}
                    />
                    <p className="mt-3 text-sm text-ink-2">
                      {nombre(i.nb_recours)} recours · avenants : <Montant gnf={i.montant_avenants} /> (
                      {pct(i.part_avenants)} du montant immatriculé)
                    </p>
                  </Carte>
                </div>
              </Zone>

              <Zone titre="Analyses">
                <div className="grid gap-4 lg:grid-cols-2">
                  <Carte id="mensuel" titre="Marchés immatriculés par mois" sousTitre="En milliards de GNF">
                    <GroupedBarChart
                      libelle="Montant des marchés immatriculés par mois"
                      donnees={d.mensuel.map((m) => ({
                        libelle: libelleMois(env.meta.exercice, m.mois),
                        montant: enMds(m.montant),
                      }))}
                      categorie="libelle"
                      series={[{ cle: "montant", libelle: "Montant immatriculé", couleur: "var(--phase-4)" }]}
                    />
                  </Carte>
                  <Carte id="types" titre="Par type de marché">
                    <HBarList
                      lignes={d.par_type.map((t) => ({
                        libelle: t.libelle,
                        valeur: t.montant,
                        complement: `${nombre(t.nombre)} marchés · ${pct(t.part)} du montant immatriculé`,
                      }))}
                    />
                  </Carte>
                  <Carte
                    id="execution-budgetaire"
                    titre="Engagements en procédure « marché public »"
                    sousTitre="Chaîne Dépense : procédures MP de l'exercice"
                    actions={<SourceBadge meta={d.engagements_chaine_depense.meta} />}
                  >
                    <ContenuBloc bloc={d.engagements_chaine_depense}>
                      {(e) => (
                        <>
                          <p className="text-base text-ink">
                            <Montant gnf={e.montant_engage} className="font-bold" /> engagés (
                            {nombre(e.nb_engagements)} engagements), dont <Montant gnf={e.montant_paye} />{" "}
                            payés.
                          </p>
                          <HBarList
                            lignes={e.procedures.map((p) => ({
                              libelle: p.libelle,
                              valeur: p.montant_paye,
                              objectif: p.montant_engage,
                            }))}
                            reference="de l'engagé payé"
                            retard="paiement lent"
                            seuil={0.5}
                          />
                        </>
                      )}
                    </ContenuBloc>
                  </Carte>
                  <Carte
                    id="autorites"
                    titre="Principales autorités contractantes"
                    sousTitre="Montant TTC des marchés immatriculés"
                  >
                    <HBarList
                      lignes={d.par_autorite.map((a) => ({
                        libelle: a.libelle,
                        valeur: a.montant,
                        complement: `${nombre(a.nombre)} marchés`,
                      }))}
                    />
                  </Carte>
                </div>
              </Zone>

              <Zone titre="Détail">
                <Carte
                  id="titulaires"
                  titre="Dix premiers titulaires"
                  sousTitre="Regroupés par NIF · part du montant immatriculé"
                >
                  <DataTable
                    donnees={d.titulaires}
                    recherche={false}
                    libelle="Principaux titulaires de marchés"
                    colonnes={[
                      { header: "Titulaire", accessorKey: "libelle" },
                      { header: "NIF", accessorKey: "titulaire_nif" },
                      { header: "Marchés", accessorKey: "nombre", meta: { numerique: true } },
                      {
                        header: "Montant",
                        accessorKey: "montant",
                        cell: ({ getValue }) => <Montant gnf={getValue() as number} />,
                        meta: { numerique: true },
                      },
                      {
                        header: "Part",
                        accessorKey: "part",
                        cell: ({ getValue }) => pct(getValue() as number),
                        meta: { numerique: true },
                      },
                    ]}
                  />
                </Carte>
                <Carte
                  id="anomalies"
                  titre="Marchés à examiner"
                  sousTitre="Principaux écarts relevés par les contrôles de cohérence"
                >
                  <DataTable
                    donnees={aExaminer}
                    libelle="Marchés présentant une anomalie de rapprochement"
                    vide="Aucune anomalie de rapprochement."
                    colonnes={[
                      { header: "Anomalie", accessorKey: "anomalie" },
                      { header: "Numéro", accessorKey: "numero" },
                      { header: "Autorité contractante", accessorKey: "autorite_contractante" },
                      { header: "Objet", accessorKey: "objet" },
                      {
                        header: "Montant TTC",
                        accessorKey: "montant_ttc",
                        cell: ({ getValue }) => <Montant gnf={getValue() as number} />,
                        meta: { numerique: true },
                      },
                      {
                        header: "Écart",
                        accessorKey: "ecart",
                        cell: ({ getValue }) =>
                          getValue() === undefined ? "—" : <Montant gnf={getValue() as number} />,
                        meta: { numerique: true },
                      },
                    ]}
                  />
                </Carte>
              </Zone>
            </div>
          );
        }}
      </EtatPage>
    </>
  );
}
