import { useDonnees } from "@/api/hooks";
import { HBarList, Legende, StackedProgress } from "@/components/Barres";
import { DataTable } from "@/components/DataTable";
import { BandeauKpi, KpiCard, StatusPill } from "@/components/Indicateurs";
import { Montant, Pourcentage } from "@/components/Montant";
import { Carte } from "@/components/ui/primitives";
import { nombre } from "@/lib/format";

import { EtatPage, TitrePage, Zone } from "../commun";
import { ContenuPrevu } from "./commun";

interface Donnees {
  indicateurs: {
    valeur_nette: number;
    valeur_brute: number;
    taux_amortissement: number | null;
    nombre_biens: number;
    biens_immatricules: number;
    taux_immatriculation: number | null;
    vehicules: number;
    taux_en_service: number | null;
    institutions_actives: number | null;
    institutions_prevues: number | null;
  };
  par_categorie: { libelle: string; valeur_nette: number; valeur_brute: number; nombre_biens: number }[];
  par_ministere: { libelle: string; valeur_nette: number; valeur_brute: number }[];
  parc: { etat: string; libelle: string; nombre: number; part: number | null }[];
  controles: { controle: string; libelle: string; nombre: number; montant: number }[];
}

const COULEURS_PARC: Record<string, string> = {
  en_service: "var(--phase-6)",
  en_panne: "var(--phase-4)",
  hors_usage: "var(--phase-2)",
};

export default function Patrimoine() {
  const r = useDonnees<Donnees>("/patrimoine/");
  return (
    <>
      <TitrePage
        exporter="patrimoine"
        titre="Patrimoine de l'État"
        sousTitre="SICOM · comptabilité matière · DNSI / DNCM"
      />
      <EtatPage requete={r} vide={<ContenuPrevu cle="patrimoine" />}>
        {(d, env) => {
          const i = d.indicateurs;
          return (
            <div className="flex flex-col gap-6">
              <Zone titre="Indicateurs clés">
                <BandeauKpi>
                  <KpiCard
                    libelle="Valeur nette"
                    valeur={<Montant gnf={i.valeur_nette} />}
                    contexte={
                      <>
                        Valeur brute <Montant gnf={i.valeur_brute} />
                      </>
                    }
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle="Taux d'amortissement"
                    valeur={<Pourcentage ratio={i.taux_amortissement} />}
                    jauge={{ valeur: i.taux_amortissement }}
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle="Biens immatriculés"
                    valeur={<Pourcentage ratio={i.taux_immatriculation} />}
                    contexte={`${nombre(i.biens_immatricules)} sur ${nombre(i.nombre_biens)} biens`}
                    jauge={{ valeur: i.taux_immatriculation }}
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle="Véhicules et engins"
                    valeur={<span className="chiffres">{nombre(i.vehicules)}</span>}
                    contexte={
                      <>
                        <Pourcentage ratio={i.taux_en_service} /> en service
                      </>
                    }
                    jauge={{ valeur: i.taux_en_service }}
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle="Institutions déployées"
                    valeur={
                      <span className="chiffres">
                        {nombre(i.institutions_actives)}
                        <span className="text-sm font-normal text-ink-3">
                          {" "}
                          sur {nombre(i.institutions_prevues)}
                        </span>
                      </span>
                    }
                    jauge={{
                      valeur: i.institutions_prevues
                        ? (i.institutions_actives ?? 0) / i.institutions_prevues
                        : null,
                    }}
                    contexte="Institutions utilisant SICOM"
                    meta={env.meta}
                  />
                  <KpiCard
                    libelle="Biens recensés"
                    valeur={<span className="chiffres">{nombre(i.nombre_biens)}</span>}
                    contexte="Toutes catégories"
                    meta={env.meta}
                  />
                </BandeauKpi>
              </Zone>

              <Zone titre="Points d'attention">
                <Carte id="controles" titre="Contrôles de la comptabilité matière">
                  <DataTable
                    donnees={d.controles}
                    recherche={false}
                    libelle="Contrôles du patrimoine"
                    colonnes={[
                      {
                        header: "Contrôle",
                        id: "libelle",
                        accessorFn: (c) => c.libelle,
                        cell: ({ row }) =>
                          row.original.nombre || row.original.montant ? (
                            <StatusPill etat="vigilance" libelle={row.original.libelle} />
                          ) : (
                            row.original.libelle
                          ),
                      },
                      {
                        header: "Nombre",
                        accessorKey: "nombre",
                        cell: ({ getValue }) => nombre(getValue() as number),
                        meta: { numerique: true },
                      },
                      {
                        header: "Valeur",
                        accessorKey: "montant",
                        cell: ({ getValue }) => <Montant gnf={getValue() as number} />,
                        meta: { numerique: true },
                      },
                    ]}
                  />
                </Carte>
              </Zone>

              <Zone titre="Analyses">
                <div className="grid gap-4 lg:grid-cols-2">
                  <Carte id="categories" titre="Valeur nette par catégorie">
                    <HBarList
                      lignes={d.par_categorie.map((c) => ({
                        libelle: c.libelle,
                        valeur: c.valeur_nette,
                        complement: `${nombre(c.nombre_biens)} biens · valeur brute ${nombre(c.valeur_brute / 1e9, 1)} Mds`,
                      }))}
                    />
                  </Carte>
                  <Carte
                    id="ministeres"
                    titre="Valeur nette par ministère"
                    sousTitre="Ministères fictifs tant que SICOM n'est pas raccordé"
                  >
                    <HBarList
                      lignes={d.par_ministere.map((m) => ({ libelle: m.libelle, valeur: m.valeur_nette }))}
                    />
                  </Carte>
                  <Carte id="parc" titre="Parc automobile par état" className="lg:col-span-2">
                    <StackedProgress
                      libelle="Parc automobile par état"
                      segments={d.parc.map((p) => ({
                        code: p.etat,
                        libelle: p.libelle,
                        valeur: p.nombre,
                        couleur: COULEURS_PARC[p.etat],
                      }))}
                    />
                    <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                      <Legende
                        elements={d.parc.map((p) => ({ libelle: p.libelle, couleur: COULEURS_PARC[p.etat] }))}
                      />
                      <p className="text-sm text-ink-2">
                        {d.parc.map((p) => `${p.libelle} : ${nombre(p.nombre)}`).join(" · ")}
                      </p>
                    </div>
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
