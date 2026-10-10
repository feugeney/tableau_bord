import { Copy, Plus, Trash2 } from "lucide-react";
import { useState, type FormEvent } from "react";

import { messageErreur, useAdmin, useListesAdmin, useMutationAdmin, type Jeton } from "@/api/admin";
import { api } from "@/api/client";
import { DataTable } from "@/components/DataTable";
import { StatusPill } from "@/components/Indicateurs";
import { Bouton, Carte } from "@/components/ui/primitives";
import { Sheet } from "@/components/ui/sheet";
import { CasesMultiples, Champ, Confirmation, Entree, Retour } from "@/components/ui/formulaire";
import { dateFr, dateHeureFr } from "@/lib/format";

import { EtatBloc } from "./commun";

export default function Partages() {
  const r = useAdmin<Jeton[]>("partages/");
  const listes = useListesAdmin();
  const [creation, setCreation] = useState(false);
  const [aRevoquer, setARevoquer] = useState<Jeton | null>(null);
  const basculer = useMutationAdmin((j: Jeton) => api.patch(`/admin/partages/${j.id}/`, { actif: !j.actif }));
  const revoquer = useMutationAdmin((id: number) => api.supprimer(`/admin/partages/${id}/`));
  const libelle = (c: string) => listes.data?.domaines.find((d) => d.code === c)?.libelle ?? c;
  return (
    <Carte
      id="partages"
      titre="Partage de données (API)"
      sousTitre="Jetons d'accès en lecture seule pour les systèmes tiers, limités aux domaines choisis. Chaque appel met à jour la date de dernière utilisation."
      actions={
        <Bouton variante="primaire" onClick={() => setCreation(true)}>
          <Plus className="h-4 w-4" aria-hidden /> Nouveau jeton
        </Bouton>
      }
    >
      <EtatBloc requete={r}>
        {(jetons) => (
          <DataTable
            donnees={jetons}
            recherche={false}
            libelle="Jetons de partage"
            vide="Aucun jeton de partage. Créez-en un pour ouvrir un accès en lecture seule à un système tiers."
            colonnes={[
              { header: "Nom", accessorKey: "nom" },
              { header: "Destinataire", accessorKey: "destinataire" },
              {
                header: "Préfixe",
                accessorKey: "prefixe",
                cell: ({ getValue }) => <code translate="no">{getValue() as string}…</code>,
              },
              { header: "Domaines", id: "domaines", accessorFn: (j) => j.domaines.map(libelle).join(", ") },
              {
                header: "Expire le",
                accessorKey: "expire_le",
                cell: ({ getValue }) => dateFr(getValue() as string),
              },
              {
                header: "Dernier appel",
                accessorKey: "derniere_utilisation",
                cell: ({ getValue }) => dateHeureFr(getValue() as string),
              },
              {
                header: "État",
                accessorKey: "actif",
                cell: ({ getValue }) =>
                  getValue() ? (
                    <StatusPill etat="bon" libelle="Actif" />
                  ) : (
                    <StatusPill etat="vigilance" libelle="Suspendu" />
                  ),
              },
              {
                header: "",
                id: "actions",
                enableSorting: false,
                cell: ({ row }) => (
                  <span className="flex gap-1">
                    <Bouton variante="discret" onClick={() => basculer.mutate(row.original)}>
                      {row.original.actif ? "Suspendre" : "Réactiver"}
                    </Bouton>
                    <Bouton
                      variante="discret"
                      onClick={() => setARevoquer(row.original)}
                      aria-label={`Révoquer le jeton ${row.original.nom}`}
                    >
                      <Trash2 className="h-4 w-4" aria-hidden />
                    </Bouton>
                  </span>
                ),
              },
            ]}
          />
        )}
      </EtatBloc>
      {creation && <CreationJeton onFermer={() => setCreation(false)} />}
      <Confirmation
        ouvert={Boolean(aRevoquer)}
        onChange={(o) => !o && setARevoquer(null)}
        titre="Révoquer ce jeton ?"
        message={`« ${aRevoquer?.nom} » (${aRevoquer?.destinataire}) perdra immédiatement et définitivement l'accès. Pour une coupure temporaire, préférez « Suspendre ».`}
        libelleAction="Révoquer définitivement"
        enCours={revoquer.isPending}
        onConfirmer={() =>
          aRevoquer && revoquer.mutate(aRevoquer.id, { onSuccess: () => setARevoquer(null) })
        }
      />
    </Carte>
  );
}

function CreationJeton({ onFermer }: { onFermer: () => void }) {
  const listes = useListesAdmin();
  const [f, setF] = useState({ nom: "", destinataire: "", domaines: [] as string[], expire_le: "" });
  const [copie, setCopie] = useState(false);
  const creer = useMutationAdmin((corps: object) => api.post<Jeton>("/admin/partages/", corps));
  const cle = creer.data?.cle;

  function soumettre(e: FormEvent) {
    e.preventDefault();
    creer.mutate({ ...f, expire_le: f.expire_le || null });
  }

  return (
    <Sheet ouvert onChange={(o) => !o && onFermer()} titre="Nouveau jeton de partage">
      {cle ? (
        <div className="flex flex-col gap-4">
          <Retour ok>Jeton créé. Copiez la clé maintenant : elle ne sera plus jamais affichée.</Retour>
          <code translate="no" className="break-all rounded-sm border border-border bg-zebra p-3 text-sm">
            {cle}
          </code>
          <div>
            <Bouton onClick={() => navigator.clipboard.writeText(cle).then(() => setCopie(true))}>
              <Copy className="h-4 w-4" aria-hidden /> {copie ? "Clé copiée" : "Copier la clé"}
            </Bouton>
          </div>
          <h3 className="etiquette mt-2">Utilisation</h3>
          <pre
            translate="no"
            className="overflow-x-auto rounded-sm border border-border bg-zebra p-3 text-xs"
          >
            {`curl -H "Authorization: Jeton ${cle.slice(0, 12)}…" \\
  https://<serveur>/api/v1/depense/indicateurs/`}
          </pre>
          <p className="text-sm text-ink-2">
            Accès en lecture seule, limité aux domaines choisis. Les réponses portent la source et la date de
            situation de chaque chiffre (<code>meta</code>).
          </p>
        </div>
      ) : (
        <form onSubmit={soumettre} className="flex flex-col gap-4">
          <Champ libelle="Nom du jeton" aide="ex. « Tableau de suivi de la Primature »">
            {(id, d) => (
              <Entree
                id={id}
                required
                autoComplete="off"
                aria-describedby={d}
                value={f.nom}
                onChange={(e) => setF({ ...f, nom: e.target.value })}
              />
            )}
          </Champ>
          <Champ libelle="Structure ou système destinataire">
            {(id) => (
              <Entree
                id={id}
                required
                autoComplete="off"
                value={f.destinataire}
                onChange={(e) => setF({ ...f, destinataire: e.target.value })}
              />
            )}
          </Champ>
          <CasesMultiples
            legende="Domaines partagés"
            options={(listes.data?.domaines ?? []).filter((d) => d.code !== "preparation")}
            valeur={f.domaines}
            onChange={(v) => setF({ ...f, domaines: v })}
          />
          <Champ
            libelle="Date d'expiration (facultative)"
            aide="Recommandée : une échéance limite l'exposition en cas de fuite."
          >
            {(id, d) => (
              <Entree
                id={id}
                type="date"
                aria-describedby={d}
                value={f.expire_le}
                onChange={(e) => setF({ ...f, expire_le: e.target.value })}
              />
            )}
          </Champ>
          {creer.isError && <Retour ok={false}>{messageErreur(creer.error)}</Retour>}
          <div>
            <Bouton type="submit" variante="primaire" disabled={creer.isPending || !f.domaines.length}>
              {creer.isPending ? "Création…" : "Créer le jeton"}
            </Bouton>
          </div>
        </form>
      )}
    </Sheet>
  );
}
