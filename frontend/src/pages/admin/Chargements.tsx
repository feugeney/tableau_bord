import { Download } from "lucide-react";
import { useState } from "react";

import { useAdmin, type ChargementAdmin, type Page } from "@/api/admin";
import { telecharger } from "@/api/client";
import { DataTable } from "@/components/DataTable";
import { StatusPill, type Etat } from "@/components/Indicateurs";
import { Bouton, Carte } from "@/components/ui/primitives";
import { Sheet } from "@/components/ui/sheet";
import { Champ, Liste, Retour } from "@/components/ui/formulaire";
import { dateFr, dateHeureFr, nombre } from "@/lib/format";
import { nomSource } from "@/lib/sources";

import { EtatBloc } from "./commun";

const STATUTS: Record<ChargementAdmin["statut"], { etat: Etat; libelle: string }> = {
  succes: { etat: "bon", libelle: "Succès" },
  echec: { etat: "critique", libelle: "Échec" },
  apercu: { etat: "vigilance", libelle: "Aperçu" },
  en_cours: { etat: "vigilance", libelle: "En cours" },
};
const TAILLE = 50;

export default function Chargements() {
  const [source, setSource] = useState("");
  const [statut, setStatut] = useState("");
  const [page, setPage] = useState(0);
  const r = useAdmin<Page<ChargementAdmin>>("chargements/", {
    source: source || undefined,
    statut: statut || undefined,
    limit: TAILLE,
    offset: page * TAILLE,
  });
  const [choisi, setChoisi] = useState<ChargementAdmin | null>(null);
  const [echecFichier, setEchecFichier] = useState(false);
  function ouvrir(c: ChargementAdmin | null) {
    setEchecFichier(false);
    setChoisi(c);
  }
  return (
    <Carte
      id="chargements"
      titre="Imports et chargements"
      sousTitre="Historique de tous les chargements, avec leurs contrôles de qualité. Les imports se lancent depuis « Sources et connecteurs »."
    >
      <div className="mb-3 grid max-w-xl gap-3 sm:grid-cols-2">
        <Champ libelle="Source">
          {(id) => (
            <Liste
              id={id}
              value={source}
              onChange={(e) => {
                setSource(e.target.value);
                setPage(0);
              }}
            >
              <option value="">Toutes</option>
              {[
                "chaine_depense",
                "safig",
                "sydonia",
                "scie",
                "dette",
                "sigpip",
                "fugas",
                "sicom",
                "sysop",
                "telemo",
              ].map((s) => (
                <option key={s} value={s}>
                  {nomSource(s)}
                </option>
              ))}
            </Liste>
          )}
        </Champ>
        <Champ libelle="Statut">
          {(id) => (
            <Liste
              id={id}
              value={statut}
              onChange={(e) => {
                setStatut(e.target.value);
                setPage(0);
              }}
            >
              <option value="">Tous</option>
              {Object.entries(STATUTS).map(([k, v]) => (
                <option key={k} value={k}>
                  {v.libelle}
                </option>
              ))}
            </Liste>
          )}
        </Champ>
      </div>
      <EtatBloc requete={r}>
        {(p) => (
          <>
            <DataTable
              donnees={p.results}
              recherche={false}
              libelle="Chargements"
              onLigne={ouvrir}
              colonnes={[
                {
                  header: "Début",
                  accessorKey: "debut",
                  cell: ({ getValue }) => dateHeureFr(getValue() as string),
                },
                {
                  header: "Source",
                  accessorKey: "source",
                  cell: ({ getValue }) => nomSource(getValue() as string),
                },
                {
                  header: "Fichier",
                  accessorKey: "fichier",
                  cell: ({ row }) => (
                    <span className="block max-w-xs truncate" title={row.original.fichier}>
                      {row.original.demo ? "Données d'illustration" : row.original.fichier}
                    </span>
                  ),
                },
                {
                  header: "Situation",
                  accessorKey: "date_situation",
                  cell: ({ getValue }) => dateFr(getValue() as string),
                },
                {
                  header: "Chargées",
                  accessorKey: "lignes_chargees",
                  cell: ({ getValue }) => nombre(getValue() as number),
                  meta: { numerique: true },
                },
                {
                  header: "Rejetées",
                  accessorKey: "lignes_rejetees",
                  cell: ({ getValue }) => nombre(getValue() as number),
                  meta: { numerique: true },
                },
                {
                  header: "Statut",
                  accessorKey: "statut",
                  cell: ({ row }) => (
                    <StatusPill
                      etat={STATUTS[row.original.statut].etat}
                      libelle={STATUTS[row.original.statut].libelle}
                    />
                  ),
                },
                {
                  header: "Par",
                  accessorKey: "utilisateur",
                  cell: ({ row }) =>
                    row.original.utilisateur ??
                    (row.original.detail?.origine === "depot" ? "Dépôt SFTP" : "Automatique"),
                },
              ]}
            />
            <div className="mt-2 flex items-center justify-end gap-2 text-sm text-ink-2">
              <span aria-live="polite">
                {nombre(p.count)} chargements · page {page + 1} sur {Math.max(1, Math.ceil(p.count / TAILLE))}
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
      {choisi && (
        <Sheet
          ouvert
          onChange={(o) => !o && ouvrir(null)}
          titre={`Chargement n° ${choisi.id}`}
          description={`${nomSource(choisi.source)} · ${dateHeureFr(choisi.debut)}`}
        >
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-base">
            <dt className="text-ink-2">Fichier</dt>
            <dd className="break-words">{choisi.fichier}</dd>
            <dt className="text-ink-2">Exercice</dt>
            <dd>{choisi.exercice ?? "—"}</dd>
            <dt className="text-ink-2">Situation</dt>
            <dd>{dateFr(choisi.date_situation)}</dd>
            <dt className="text-ink-2">Lignes</dt>
            <dd>
              {nombre(choisi.lignes_lues)} lues · {nombre(choisi.lignes_chargees)} chargées ·{" "}
              {nombre(choisi.lignes_rejetees)} rejetées
            </dd>
            <dt className="text-ink-2">Durée</dt>
            <dd>{nombre(choisi.duree_secondes, 1)} s</dd>
            <dt className="text-ink-2">Identifiant du flux</dt>
            <dd className="chiffres break-all text-sm">{choisi.uuid}</dd>
            {choisi.empreinte_sha256 && (
              <>
                <dt className="text-ink-2">Empreinte SHA-256</dt>
                <dd className="chiffres break-all text-sm">{choisi.empreinte_sha256}</dd>
              </>
            )}
          </dl>
          {choisi.detail?.deja_charge && (
            <p className="mt-4 text-base text-ink">
              <StatusPill etat="vigilance" libelle="Contenu déjà chargé" /> Ce fichier est identique à celui
              du chargement n° {choisi.detail.deja_charge}.
            </p>
          )}
          {choisi.fichier_archive && (
            <div className="mt-4 flex flex-col gap-2">
              <Bouton
                onClick={() =>
                  telecharger(`/admin/chargements/${choisi.id}/fichier/`).catch(() => setEchecFichier(true))
                }
              >
                <Download className="h-4 w-4" aria-hidden /> Télécharger le fichier reçu
              </Bouton>
              <p className="text-sm text-ink-2">
                Copie conservée telle que reçue. Le téléchargement est inscrit au journal d'audit.
              </p>
              {echecFichier && (
                <Retour ok={false}>Le fichier n'est plus disponible dans la zone brute.</Retour>
              )}
            </div>
          )}
          {choisi.message_erreur && (
            <p className="mt-4 text-base font-bold text-ink">Erreur : {choisi.message_erreur}</p>
          )}
          {choisi.detail?.controles?.length ? (
            <>
              <h3 className="etiquette mb-2 mt-6">Contrôles de qualité</h3>
              <ul className="divide-y divide-border text-sm">
                {choisi.detail.controles.map((c) => (
                  <li key={c.code} className="flex items-center justify-between gap-3 py-1.5">
                    <span className="flex items-center gap-2">
                      <StatusPill
                        etat={c.reussi ? "bon" : c.niveau === "bloquant" ? "critique" : "vigilance"}
                        libelle={c.reussi ? "Conforme" : c.niveau === "bloquant" ? "Bloquant" : "À vérifier"}
                      />
                      {c.libelle}
                    </span>
                    <span className="chiffres text-ink-2">{c.nombre != null ? nombre(c.nombre) : ""}</span>
                  </li>
                ))}
              </ul>
            </>
          ) : null}
        </Sheet>
      )}
    </Carte>
  );
}
