import { Database, FolderInput, RefreshCw, TestTube2, Trash2 } from "lucide-react";
import { useState } from "react";

import { messageErreur, useAdmin, useMutationAdmin, type Entrepot as TEntrepot } from "@/api/admin";
import { api } from "@/api/client";
import { DataTable } from "@/components/DataTable";
import { SourceBadge } from "@/components/Source";
import { Bouton, Carte } from "@/components/ui/primitives";
import { Confirmation, Retour } from "@/components/ui/formulaire";
import { nombre } from "@/lib/format";
import { nomSource } from "@/lib/sources";

import { EtatBloc } from "./commun";

type Action = "rafraichir" | "demo" | "demo_supprimer" | "relever";

export default function Entrepot({ tests = false }: { tests?: boolean }) {
  const r = useAdmin<TEntrepot>("entrepot/");
  const action = useMutationAdmin((a: Action) =>
    api.post<{ detail: string; sources?: Record<string, string> }>("/admin/entrepot/", { action: a }),
  );
  const [confirmer, setConfirmer] = useState<Action | null>(null);
  return (
    <div className="flex flex-col gap-4">
      <Carte
        id="actions"
        titre={tests ? "Données de test et d'illustration" : "Base centrale du tableau de bord"}
        sousTitre={
          tests
            ? "Les données d'illustration remplissent les onglets des sources non raccordées, avec des organismes fictifs. Une source réelle n'est jamais écrasée."
            : "Données enregistrées par les flux ETL, fichiers reçus et vues utilisées par les indicateurs."
        }
      >
        <div className="flex flex-wrap gap-2">
          {!tests && (
            <Bouton onClick={() => action.mutate("rafraichir")} disabled={action.isPending}>
              <RefreshCw className="h-4 w-4" aria-hidden /> Rafraîchir les vues et le cache
            </Bouton>
          )}
          {tests && (
            <>
              <Bouton variante="primaire" onClick={() => setConfirmer("demo")} disabled={action.isPending}>
                <TestTube2 className="h-4 w-4" aria-hidden /> Générer les données d'illustration
              </Bouton>
              <Bouton onClick={() => setConfirmer("demo_supprimer")} disabled={action.isPending}>
                <Trash2 className="h-4 w-4" aria-hidden /> Retirer les données d'illustration
              </Bouton>
            </>
          )}
        </div>
        {action.isPending && (
          <p className="mt-3 text-base text-ink-2" role="status">
            Traitement en cours…
          </p>
        )}
        {action.isError && (
          <div className="mt-3">
            <Retour ok={false}>{messageErreur(action.error)}</Retour>
          </div>
        )}
        {action.data && (
          <div className="mt-3">
            <Retour ok>
              {action.data.detail}
              {action.data.sources &&
                ` ${Object.entries(action.data.sources)
                  .map(([k, v]) => `${k} : ${v}`)
                  .join(" · ")}`}
            </Retour>
          </div>
        )}
      </Carte>
      {!tests && (
        <EtatBloc requete={r} hauteur="h-96">
          {(e) => (
            <>
              <Carte
                id="depot"
                titre="Dépôt de fichiers des partenaires (SFTP)"
                sousTitre={`Un dossier par source, relevé toutes les ${nombre(e.depot.releve_minutes)} minutes. Chaque fichier relevé est chargé, conservé en zone brute, puis retiré du dépôt.`}
                actions={
                  <Bouton onClick={() => action.mutate("relever")} disabled={action.isPending}>
                    <FolderInput className="h-4 w-4" aria-hidden /> Relever maintenant
                  </Bouton>
                }
              >
                <DataTable
                  donnees={e.depot.en_attente}
                  recherche={false}
                  libelle="Fichiers en attente dans le dépôt"
                  vide="Aucun fichier en attente."
                  colonnes={[
                    {
                      header: "Source",
                      accessorKey: "source",
                      cell: ({ getValue }) => nomSource(getValue() as string),
                    },
                    { header: "Fichier", accessorKey: "fichier" },
                    {
                      header: "Taille (Ko)",
                      accessorKey: "octets",
                      cell: ({ getValue }) => nombre((getValue() as number) / 1000, 0),
                      meta: { numerique: true },
                    },
                  ]}
                />
                <p className="mt-3 text-sm text-ink-2">
                  Dossier : <span className="chiffres break-all">{e.depot.dossier}</span> · événements AMQP
                  (RabbitMQ) :{" "}
                  {e.evenements_amqp ? "publiés à chaque chargement" : "messagerie non configurée"}
                </p>
              </Carte>
              <Carte
                id="sources-etat"
                titre="Sources"
                sousTitre={`Taille de la base : ${e.taille_base} · zone brute : ${nombre(e.zone_brute.fichiers)} fichier${e.zone_brute.fichiers > 1 ? "s" : ""} conservé${e.zone_brute.fichiers > 1 ? "s" : ""} (${nombre(e.zone_brute.octets / 1e6, 1)} Mo) · version du cache : ${e.version_cache}`}
              >
                <DataTable
                  donnees={e.sources}
                  recherche={false}
                  libelle="État des sources"
                  colonnes={[
                    { header: "Application", accessorKey: "application" },
                    {
                      header: "Statut",
                      accessorKey: "statut",
                      cell: ({ row }) => (
                        <SourceBadge
                          meta={{
                            source: row.original.code,
                            statut_source: row.original.statut,
                            date_situation: null,
                          }}
                        />
                      ),
                    },
                    { header: "Chargements", accessorKey: "chargements", meta: { numerique: true } },
                  ]}
                />
              </Carte>
              <div className="grid gap-4 lg:grid-cols-2">
                <Carte
                  id="tables"
                  titre="Tables (schémas ref et dw)"
                  sousTitre="Nombre de lignes estimé par PostgreSQL"
                >
                  <DataTable
                    donnees={e.tables}
                    libelle="Tables de la base centrale"
                    colonnes={[
                      { header: "Schéma", accessorKey: "schema" },
                      {
                        header: "Table",
                        accessorKey: "table",
                        cell: ({ getValue }) => <code translate="no">{getValue() as string}</code>,
                      },
                      {
                        header: "Lignes",
                        accessorKey: "lignes",
                        cell: ({ getValue }) => nombre(getValue() as number),
                        meta: { numerique: true },
                      },
                    ]}
                    triInitial={[{ id: "lignes", desc: true }]}
                  />
                </Carte>
                <Carte
                  id="vues"
                  titre="Vues de restitution (mart)"
                  actions={<Database className="h-4 w-4 text-ink-2" aria-hidden />}
                >
                  <DataTable
                    donnees={e.vues}
                    recherche={false}
                    libelle="Vues matérialisées"
                    colonnes={[
                      {
                        header: "Vue",
                        accessorKey: "vue",
                        cell: ({ getValue }) => <code translate="no">{getValue() as string}</code>,
                      },
                      {
                        header: "Lignes",
                        accessorKey: "lignes",
                        cell: ({ getValue }) => nombre(getValue() as number),
                        meta: { numerique: true },
                      },
                    ]}
                  />
                </Carte>
              </div>
            </>
          )}
        </EtatBloc>
      )}
      <Confirmation
        ouvert={Boolean(confirmer)}
        onChange={(o) => !o && setConfirmer(null)}
        titre={
          confirmer === "demo"
            ? "Générer les données d'illustration ?"
            : "Retirer les données d'illustration ?"
        }
        message={
          confirmer === "demo"
            ? "Les onglets des sources non raccordées afficheront des chiffres fictifs, signalés « illustration » sur chaque indicateur. Les données réelles ne sont pas modifiées."
            : "Les onglets concernés afficheront de nouveau « Source non raccordée ». Les données réelles ne sont pas modifiées."
        }
        libelleAction={confirmer === "demo" ? "Générer" : "Retirer"}
        enCours={action.isPending}
        onConfirmer={() => confirmer && action.mutate(confirmer, { onSettled: () => setConfirmer(null) })}
      />
    </div>
  );
}
