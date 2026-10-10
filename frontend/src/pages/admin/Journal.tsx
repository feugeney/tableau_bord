import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import type { EntreeJournal, Page } from "@/api/admin";
import { api } from "@/api/client";
import { DataTable } from "@/components/DataTable";
import { Bouton, Carte } from "@/components/ui/primitives";
import { Champ, Entree, Liste } from "@/components/ui/formulaire";
import { dateHeureFr, nombre } from "@/lib/format";

import { EtatBloc } from "./commun";

const ACTIONS: Record<string, string> = {
  connexion: "Connexion",
  echec_connexion: "Échec de connexion",
  consultation: "Consultation",
  export: "Export",
  import: "Import",
  parametre: "Administration",
  alerte: "Statut d'alerte",
};
const TAILLE = 50;

export default function Journal() {
  const [action, setAction] = useState("");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(0);
  const r = useQuery({
    queryKey: ["admin", "journal", action, q, page],
    queryFn: () =>
      api.get<Page<EntreeJournal>>("/journal/", {
        action: action || undefined,
        q: q || undefined,
        limit: TAILLE,
        offset: page * TAILLE,
      }),
  });
  return (
    <Carte
      id="journal"
      titre="Journal d'audit"
      sousTitre="Connexions, consultations, imports, exports et actions d'administration."
    >
      <div className="mb-3 grid max-w-2xl gap-3 sm:grid-cols-2">
        <Champ libelle="Action">
          {(id) => (
            <Liste
              id={id}
              value={action}
              onChange={(e) => {
                setAction(e.target.value);
                setPage(0);
              }}
            >
              <option value="">Toutes</option>
              {Object.entries(ACTIONS).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </Liste>
          )}
        </Champ>
        <Champ libelle="Utilisateur ou objet">
          {(id) => (
            <Entree
              id={id}
              type="search"
              autoComplete="off"
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setPage(0);
              }}
              placeholder="Rechercher…"
            />
          )}
        </Champ>
      </div>
      <EtatBloc requete={r}>
        {(p) => (
          <>
            <DataTable
              donnees={p.results}
              recherche={false}
              libelle="Journal d'audit"
              colonnes={[
                {
                  header: "Date",
                  accessorKey: "date",
                  cell: ({ getValue }) => dateHeureFr(getValue() as string),
                },
                { header: "Utilisateur", accessorKey: "identifiant" },
                {
                  header: "Action",
                  accessorKey: "action",
                  cell: ({ getValue }) => ACTIONS[getValue() as string] ?? getValue(),
                },
                {
                  header: "Objet",
                  accessorKey: "objet",
                  cell: ({ getValue }) => (
                    <span className="block max-w-sm break-words">{getValue() as string}</span>
                  ),
                },
                {
                  header: "Adresse IP",
                  accessorKey: "adresse_ip",
                  cell: ({ getValue }) => (getValue() as string) ?? "—",
                },
              ]}
            />
            <div className="mt-2 flex items-center justify-end gap-2 text-sm text-ink-2">
              <span aria-live="polite">
                {nombre(p.count)} entrées · page {page + 1} sur {Math.max(1, Math.ceil(p.count / TAILLE))}
              </span>
              <Bouton onClick={() => setPage((x) => x - 1)} disabled={page === 0}>
                Précédente
              </Bouton>
              <Bouton onClick={() => setPage((x) => x + 1)} disabled={(page + 1) * TAILLE >= p.count}>
                Suivante
              </Bouton>
            </div>
          </>
        )}
      </EtatBloc>
    </Carte>
  );
}
