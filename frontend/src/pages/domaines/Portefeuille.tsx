import { useDonnees } from "@/api/hooks";
import { HBarList } from "@/components/Barres";
import { DataTable } from "@/components/DataTable";
import { BandeauKpi, KpiCard, StatusPill, type Etat } from "@/components/Indicateurs";
import { Montant, Pourcentage } from "@/components/Montant";
import { Carte } from "@/components/ui/primitives";
import { nombre } from "@/lib/format";

import { EtatPage, TitrePage, Zone } from "../commun";
import { ContenuPrevu, type Bloc } from "./commun";

interface Donnees {
  indicateurs: {
    epa: number;
    societes: number;
    subventions_prevues: number;
    subventions_payees: number;
    dividendes_votes: number;
    dividendes_encaisses: number;
    taux_dividendes: number | null;
    taux_transmission: number | null;
  };
  transferts: Bloc<{ credit_actuel: number; montant_ordonnance: number; montant_paye: number }>;
  subventions: { libelle: string; prevu: number; paye: number }[];
  dividendes: { libelle: string; vote: number; encaisse: number }[];
  sante: { statut: string; libelle: string; nombre: number }[];
  gouvernance: {
    etats_non_transmis: number;
    mandats_expires: number;
    organismes_mandats_expires: { libelle: string; mandats_expires: number }[];
  };
}

const ETAT_SANTE: Record<string, Etat | undefined> = {
  excedentaire: "bon",
  equilibre: undefined,
  deficitaire: "serieux",
  non_transmis: "vigilance",
};

export default function Portefeuille() {
  const r = useDonnees<Donnees>("/portefeuille/");
  return (
    <>
      <TitrePage
        exporter="portefeuille"
        titre="Portefeuille de l'État"
        sousTitre="SYSOP · EPA et sociétés publiques · DGPEIP"
      />
      <EtatPage
        requete={r}
        vide={<ContenuPrevu cle="portefeuille" />}
        indicateurs={4}
        precisionDemo="Les transferts de l'État viennent de la Chaîne Dépense (réel)."
      >
        {(d, env) => {
          const i = d.indicateurs;
          return (
            <div className="flex flex-col gap-6">
              <Zone titre="Indicateurs clés">
                <BandeauKpi colonnes={4}>
                  <KpiCard
                    libelle="Organismes suivis"
                    valeur={<span className="chiffres">{nombre(i.epa + i.societes)}</span>}
                    contexte={`${nombre(i.epa)} EPA et ${nombre(i.societes)} sociétés publiques`}
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle="Transferts de l'État"
                    valeur={<Montant gnf={d.transferts.donnees?.montant_ordonnance} />}
                    contexte={
                      <>
                        Ordonnancés sur <Montant gnf={d.transferts.donnees?.credit_actuel} /> de crédits
                        (titre 4)
                      </>
                    }
                    meta={d.transferts.meta}
                  />
                  <KpiCard
                    libelle="Dividendes encaissés"
                    valeur={<Montant gnf={i.dividendes_encaisses} />}
                    contexte={
                      <>
                        <Pourcentage ratio={i.taux_dividendes} /> des <Montant gnf={i.dividendes_votes} />{" "}
                        votés
                      </>
                    }
                    jauge={{ valeur: i.taux_dividendes }}
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle="États financiers transmis"
                    valeur={<Pourcentage ratio={i.taux_transmission} />}
                    contexte={`${nombre(d.gouvernance.etats_non_transmis)} organismes n'ont pas transmis`}
                    jauge={{ valeur: i.taux_transmission }}
                    meta={env.meta}
                  />
                </BandeauKpi>
              </Zone>

              <Zone titre="Points d'attention">
                <div className="grid gap-4 lg:grid-cols-2">
                  <Carte id="sante" titre="Santé financière des organismes">
                    <ul className="flex flex-col gap-2">
                      {d.sante.map((s) => (
                        <li key={s.statut} className="flex items-center justify-between gap-3 text-base">
                          {ETAT_SANTE[s.statut] ? (
                            <StatusPill etat={ETAT_SANTE[s.statut]!} libelle={s.libelle} />
                          ) : (
                            <span className="text-ink">{s.libelle}</span>
                          )}
                          <span className="chiffres font-bold text-ink">{nombre(s.nombre)}</span>
                        </li>
                      ))}
                    </ul>
                  </Carte>
                  <Carte
                    id="gouvernance"
                    titre="Gouvernance"
                    sousTitre={`${nombre(d.gouvernance.mandats_expires)} mandats d'administrateurs expirés`}
                  >
                    <DataTable
                      donnees={d.gouvernance.organismes_mandats_expires}
                      recherche={false}
                      libelle="Organismes aux mandats d'administrateurs expirés"
                      colonnes={[
                        { header: "Organisme", accessorKey: "libelle" },
                        {
                          header: "Mandats expirés",
                          accessorKey: "mandats_expires",
                          meta: { numerique: true },
                        },
                      ]}
                    />
                  </Carte>
                </div>
              </Zone>

              <Zone titre="Analyses">
                <div className="grid gap-4 lg:grid-cols-2">
                  <Carte
                    id="subventions"
                    titre="Subventions aux EPA"
                    sousTitre="Dix premières · barre : payé · trait : prévu"
                  >
                    <HBarList
                      lignes={d.subventions.map((s) => ({
                        libelle: s.libelle,
                        valeur: s.paye,
                        objectif: s.prevu,
                      }))}
                      reference="du prévu"
                      retard="paiement en retard"
                      seuil={0.5}
                    />
                  </Carte>
                  <Carte
                    id="dividendes"
                    titre="Dividendes"
                    sousTitre="Dix premiers · barre : encaissé · trait : voté"
                  >
                    <HBarList
                      lignes={d.dividendes.map((x) => ({
                        libelle: x.libelle,
                        valeur: x.encaisse,
                        objectif: x.vote,
                      }))}
                      reference="du voté"
                      retard="non versé"
                      seuil={0.99}
                    />
                  </Carte>
                </div>
              </Zone>
            </div>
          );
        }}
      </EtatPage>
    </>
  );
}
