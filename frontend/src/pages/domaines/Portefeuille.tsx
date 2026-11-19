import { useDonnees } from "@/api/hooks";
import { HBarList } from "@/components/Barres";
import { DataTable } from "@/components/DataTable";
import { BandeauKpi, KpiCard, StatusPill, type Etat } from "@/components/Indicateurs";
import { Montant, Pourcentage } from "@/components/Montant";
import { SourceBadge } from "@/components/Source";
import { Carte } from "@/components/ui/primitives";
import { nombre } from "@/lib/format";

import { EtatPage, TitrePage, Zone } from "../commun";
import type { Bloc } from "./commun";

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
  couverture?: {
    epa_avec_subvention: number;
    societes_avec_dividende: number;
    resultats_exploitables: number;
    organismes_validation_etablie: number;
    organismes_recenses: number;
    obligations_dividendes_connues: boolean;
  };
  perimetre_transferts?: string;
  avertissement_periode?: string | null;
  subventions: { libelle: string; prevu: number; paye: number }[];
  dividendes: { libelle: string; vote: number; encaisse: number }[];
  sante: { statut: string; libelle: string; nombre: number }[];
  precision_sante?: string | null;
  precision_transmission?: string | null;
  gouvernance: {
    etats_non_transmis: number;
    mandats_expires: number | null;
    mandats_disponibles?: boolean;
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
        indicateurs={4}
        precisionDemo="Le contexte budgétaire du titre 4 est présenté séparément, avec sa propre source."
      >
        {(d, env) => {
          const i = d.indicateurs;
          return (
            <div className="flex flex-col gap-6">
              <Zone titre="Indicateurs clés">
                <BandeauKpi colonnes={4}>
                  <KpiCard
                    libelle="Organismes recensés"
                    valeur={<span className="chiffres">{nombre(i.epa + i.societes)}</span>}
                    contexte={`${nombre(i.epa)} EPA et ${nombre(i.societes)} sociétés publiques`}
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle="Subventions versées aux EPA renseignés"
                    valeur={<Montant gnf={i.subventions_payees} />}
                    contexte={
                      <>
                        Prévision LFR renseignée : <Montant gnf={i.subventions_prevues} />
                        {d.couverture && (
                          <>
                            {" "}
                            · {nombre(d.couverture.epa_avec_subvention)} EPA avec une ligne sur{" "}
                            {nombre(i.epa)} recensés
                          </>
                        )}
                      </>
                    }
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle="Dividendes encaissés"
                    valeur={<Montant gnf={i.dividendes_encaisses} />}
                    contexte={
                      <>
                        <Pourcentage ratio={i.taux_dividendes} /> des <Montant gnf={i.dividendes_votes} />{" "}
                        attendus renseignés
                        {d.couverture && (
                          <> · {nombre(d.couverture.societes_avec_dividende)} société(s) renseignée(s)</>
                        )}
                      </>
                    }
                    jauge={{ valeur: i.taux_dividendes }}
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle={
                      d.precision_transmission ? "Validation des états SYSOP" : "États financiers transmis"
                    }
                    valeur={<Pourcentage ratio={i.taux_transmission} />}
                    contexte={
                      d.couverture
                        ? `${nombre(d.couverture.organismes_validation_etablie)} sur ${nombre(d.couverture.organismes_recenses)} selon les critères actuels`
                        : `${nombre(d.gouvernance.etats_non_transmis)} sans validation établie`
                    }
                    jauge={{ valeur: i.taux_transmission }}
                    meta={env.meta}
                  />
                </BandeauKpi>
                {d.precision_transmission && (
                  <p className="mt-3 text-sm text-ink-2">{d.precision_transmission}</p>
                )}
                {d.couverture && (
                  <p className="mt-2 text-sm text-ink-2">
                    Le référentiel recensé ne représente pas des dossiers financiers complets pour chaque
                    organisme. Le taux de dividendes couvre uniquement les montants renseignés ; le nombre de
                    sociétés redevables et les échéances ne sont pas établis.
                  </p>
                )}
              </Zone>

              <Zone titre="Points d'attention">
                <div className="grid gap-4 lg:grid-cols-2">
                  <Carte
                    id="sante"
                    titre="Couverture des résultats financiers"
                    sousTitre={d.precision_sante ?? undefined}
                  >
                    {d.couverture && (
                      <p className="mb-3 text-sm text-ink-2">
                        {nombre(d.couverture.resultats_exploitables)} résultat(s) exploitable(s) sur{" "}
                        {nombre(d.couverture.organismes_recenses)} organismes recensés.{" "}
                        {d.couverture.resultats_exploitables === 0 &&
                          "Aucun diagnostic de santé financière ne peut être établi sur cet import."}
                      </p>
                    )}
                    <ul className="flex flex-col gap-2">
                      {d.sante
                        .filter(
                          (s) =>
                            !d.couverture ||
                            d.couverture.resultats_exploitables > 0 ||
                            (s.nombre > 0 &&
                              !["excedentaire", "equilibre", "deficitaire"].includes(s.statut)),
                        )
                        .map((s) => (
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
                    sousTitre={
                      d.gouvernance.mandats_disponibles === false
                        ? "Mandats d'administrateurs : données non raccordées"
                        : `${nombre(d.gouvernance.mandats_expires)} mandats d'administrateurs expirés`
                    }
                  >
                    {d.gouvernance.mandats_disponibles === false ? (
                      <p className="text-sm text-ink-2">
                        Les dates de fin de mandat ne sont pas encore disponibles dans ce raccordement SYSOP.
                      </p>
                    ) : (
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
                    )}
                  </Carte>
                </div>
              </Zone>

              <Zone titre="Analyses">
                <div className="grid gap-4 lg:grid-cols-2">
                  <Carte
                    id="subventions"
                    titre="Subventions aux EPA"
                    sousTitre="Dix premières · barre : versé · trait : prévision LFR renseignée ; aucune échéance n'est évaluée"
                  >
                    <HBarList
                      lignes={d.subventions.map((s) => ({
                        libelle: s.libelle,
                        valeur: s.paye,
                        objectif: s.prevu,
                      }))}
                      reference="du prévu"
                      seuil={null}
                    />
                  </Carte>
                  <Carte
                    id="dividendes"
                    titre="Dividendes"
                    sousTitre="Sociétés renseignées · barre : encaissé · trait : attendu ; une échéance est nécessaire pour établir un retard"
                  >
                    <HBarList
                      lignes={d.dividendes.map((x) => ({
                        libelle: x.libelle,
                        valeur: x.encaisse,
                        objectif: x.vote,
                      }))}
                      reference="de l'attendu renseigné"
                      seuil={null}
                    />
                  </Carte>
                </div>
              </Zone>
              <Zone titre="Contexte budgétaire global">
                <Carte
                  titre="Transferts budgétaires de l'État · ensemble du titre 4"
                  sousTitre={
                    d.perimetre_transferts ??
                    "Périmètre plus large que le portefeuille SYSOP ; ne pas additionner aux subventions ci-dessus."
                  }
                >
                  <p className="text-base text-ink">
                    Ordonnancé : <Montant gnf={d.transferts.donnees?.montant_ordonnance} /> · Crédits :{" "}
                    <Montant gnf={d.transferts.donnees?.credit_actuel} />.
                  </p>
                  {d.avertissement_periode && (
                    <p className="mt-2 text-sm text-ink-2">{d.avertissement_periode}</p>
                  )}
                  <div className="mt-2">
                    <SourceBadge meta={d.transferts.meta} />
                  </div>
                </Carte>
              </Zone>
            </div>
          );
        }}
      </EtatPage>
    </>
  );
}
