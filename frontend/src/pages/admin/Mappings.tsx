import { Plus, Trash2 } from "lucide-react";
import { useState, type FormEvent } from "react";

import {
  messageErreur,
  useAdmin,
  useListesAdmin,
  useMutationAdmin,
  type Mapping,
  type TableCible,
} from "@/api/admin";
import { api } from "@/api/client";
import { DataTable } from "@/components/DataTable";
import { Bouton, Carte } from "@/components/ui/primitives";
import { Case, Champ, Confirmation, Entree, Liste, Retour } from "@/components/ui/formulaire";
import { nomSource } from "@/lib/sources";

import { EtatBloc } from "./commun";

const SOURCES = ["safig", "sydonia", "scie", "dette", "sigpip", "fugas", "sicom", "sysop"];

export default function Mappings() {
  const [source, setSource] = useState("safig");
  const mappings = useAdmin<Mapping[]>("mappings/", { source });
  const tables = useAdmin<TableCible[]>("tables-cibles/");
  const listes = useListesAdmin();
  const vide = {
    table_cible: "",
    colonne_source: "",
    champ_cible: "",
    type_donnee: "texte",
    onglet: "",
    obligatoire: false,
  };
  const [f, setF] = useState(vide);
  const [aSupprimer, setASupprimer] = useState<Mapping | null>(null);
  const ajouter = useMutationAdmin((corps: object) => api.post<Mapping>("/admin/mappings/", corps));
  const supprimer = useMutationAdmin((id: number) => api.supprimer(`/admin/mappings/${id}/`));
  const table = tables.data?.find((t) => t.table === f.table_cible);

  function soumettre(e: FormEvent) {
    e.preventDefault();
    ajouter.mutate({ ...f, source }, { onSuccess: () => setF({ ...vide, table_cible: f.table_cible }) });
  }

  return (
    <Carte
      id="mappings"
      titre="Mappings de colonnes"
      sousTitre="Correspondance entre les colonnes d'une extraction (Excel, CSV, requête) et les champs de l'entrepôt : brancher une nouvelle extraction sans modifier le code."
    >
      <div className="mb-4 max-w-xs">
        <Champ libelle="Source">
          {(id) => (
            <Liste id={id} value={source} onChange={(e) => setSource(e.target.value)}>
              {SOURCES.map((s) => (
                <option key={s} value={s}>
                  {nomSource(s)}
                </option>
              ))}
            </Liste>
          )}
        </Champ>
      </div>
      <EtatBloc requete={mappings}>
        {(m) => (
          <DataTable
            donnees={m}
            recherche={false}
            libelle={`Mappings de ${nomSource(source)}`}
            colonnes={[
              { header: "Table cible", accessorKey: "table_cible" },
              { header: "Colonne source", accessorKey: "colonne_source" },
              { header: "Champ cible", accessorKey: "champ_cible" },
              { header: "Type", accessorKey: "type_donnee" },
              {
                header: "Obligatoire",
                accessorKey: "obligatoire",
                cell: ({ getValue }) => (getValue() ? "Oui" : "Non"),
              },
              {
                header: "",
                id: "actions",
                enableSorting: false,
                cell: ({ row }) => (
                  <Bouton
                    variante="discret"
                    onClick={() => setASupprimer(row.original)}
                    aria-label={`Supprimer le mapping ${row.original.colonne_source}`}
                  >
                    <Trash2 className="h-4 w-4" aria-hidden />
                  </Bouton>
                ),
              },
            ]}
          />
        )}
      </EtatBloc>

      <form onSubmit={soumettre} className="mt-6 flex flex-col gap-4 border-t border-border pt-4">
        <h3 className="text-md font-bold text-ink">Ajouter une correspondance</h3>
        <div className="grid gap-4 md:grid-cols-3">
          <Champ libelle="Table cible">
            {(id) => (
              <Liste
                id={id}
                required
                value={f.table_cible}
                onChange={(e) => setF({ ...f, table_cible: e.target.value, champ_cible: "" })}
              >
                <option value="">Choisir…</option>
                {tables.data?.map((t) => (
                  <option key={t.table} value={t.table}>
                    {t.table}
                  </option>
                ))}
              </Liste>
            )}
          </Champ>
          <Champ libelle="Champ cible">
            {(id) => (
              <Liste
                id={id}
                required
                value={f.champ_cible}
                onChange={(e) => {
                  const champ = table?.champs.find((c) => c.nom === e.target.value);
                  setF({
                    ...f,
                    champ_cible: e.target.value,
                    type_donnee: champ?.type === "reference" ? "code" : (champ?.type ?? "texte"),
                    obligatoire: champ?.obligatoire ?? false,
                  });
                }}
              >
                <option value="">Choisir…</option>
                {table?.champs.map((c) => (
                  <option key={c.nom} value={c.nom}>
                    {c.nom} ({c.type})
                  </option>
                ))}
              </Liste>
            )}
          </Champ>
          <Champ libelle="Colonne dans l'extraction" aide="Comparée sans accents ni majuscules.">
            {(id, d) => (
              <Entree
                id={id}
                required
                autoComplete="off"
                aria-describedby={d}
                value={f.colonne_source}
                onChange={(e) => setF({ ...f, colonne_source: e.target.value })}
                placeholder="Code ministère…"
              />
            )}
          </Champ>
          <Champ libelle="Type de donnée">
            {(id) => (
              <Liste
                id={id}
                value={f.type_donnee}
                onChange={(e) => setF({ ...f, type_donnee: e.target.value })}
              >
                {listes.data?.types_donnee.map((t) => (
                  <option key={t.code} value={t.code}>
                    {t.libelle}
                  </option>
                ))}
              </Liste>
            )}
          </Champ>
          <Champ libelle="Onglet (facultatif)">
            {(id) => (
              <Entree
                id={id}
                autoComplete="off"
                value={f.onglet}
                onChange={(e) => setF({ ...f, onglet: e.target.value })}
              />
            )}
          </Champ>
          <div className="flex items-end">
            <Case
              libelle="Colonne obligatoire"
              checked={f.obligatoire}
              onChange={(e) => setF({ ...f, obligatoire: e.target.checked })}
            />
          </div>
        </div>
        {ajouter.isError && <Retour ok={false}>{messageErreur(ajouter.error)}</Retour>}
        <div>
          <Bouton type="submit" variante="primaire" disabled={ajouter.isPending}>
            <Plus className="h-4 w-4" aria-hidden /> Ajouter la correspondance
          </Bouton>
        </div>
      </form>

      <Confirmation
        ouvert={Boolean(aSupprimer)}
        onChange={(o) => !o && setASupprimer(null)}
        titre="Supprimer cette correspondance ?"
        message={`La colonne « ${aSupprimer?.colonne_source} » ne sera plus chargée dans ${aSupprimer?.table_cible}.${aSupprimer?.champ_cible}.`}
        libelleAction="Supprimer"
        enCours={supprimer.isPending}
        onConfirmer={() =>
          aSupprimer && supprimer.mutate(aSupprimer.id, { onSuccess: () => setASupprimer(null) })
        }
      />
    </Carte>
  );
}
