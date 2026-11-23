import { RefreshCw, Send } from "lucide-react";
import { useState, type FormEvent } from "react";

import { messageErreur, useAdmin, useMutationAdmin, type Page } from "@/api/admin";
import { api } from "@/api/client";
import { DataTable } from "@/components/DataTable";
import { Champ, Entree, Liste, Retour } from "@/components/ui/formulaire";
import { Bouton, Carte } from "@/components/ui/primitives";
import { dateHeureFr } from "@/lib/format";

import { EtatBloc } from "./commun";

interface Notification {
  id: number;
  date: string;
  type: string;
  statut: string;
  sujet: string;
  reference: string;
  destinataires: string[];
  regle: string | null;
  utilisateur: string | null;
  erreur: string;
}

interface Configuration {
  smtp: boolean;
  hote: string;
  port: number;
  tls: boolean;
  ssl: boolean;
  expediteur: string;
  authentification_configuree: boolean;
  url_application: string;
  planificateur_actif: boolean;
  verification_active: boolean;
  derniere_verification: string | null;
  compteurs: Record<string, number>;
}

interface ModeleMail {
  code: string;
  titre: string;
}

interface ApercuMail {
  sujet: string;
  texte: string;
  html: string;
}

const STATUTS: Record<string, string> = {
  en_cours: "En cours",
  envoye: "Accepté par la messagerie",
  echec: "Échec",
  simulation: "Simulation",
};

export default function Notifications() {
  const [destinataire, setDestinataire] = useState("");
  const [statut, setStatut] = useState("");
  const [page, setPage] = useState(1);
  const [modele, setModele] = useState("depense_arbitrage_ministre");
  const [categorie, setCategorie] = useState("alerte");
  const [format, setFormat] = useState("html");
  const modeles = useAdmin<ModeleMail[]>("notifications/modeles/");
  const apercu = useAdmin<ApercuMail>("notifications/apercu/", { modele, categorie });
  const configuration = useAdmin<Configuration>("notifications/configuration/");
  const historique = useAdmin<Page<Notification>>("notifications/", {
    statut,
    limit: 25,
    offset: (page - 1) * 25,
  });
  const test = useMutationAdmin((corps: { destinataire: string; modele: string; categorie: string }) =>
    api.post<Notification>("/admin/notifications/tester/", corps),
  );

  function soumettre(e: FormEvent) {
    e.preventDefault();
    test.mutate({ destinataire: destinataire.trim(), modele, categorie });
  }

  return (
    <div className="grid gap-6">
      <Carte
        id="notifications"
        titre="Notifications et mails"
        sousTitre="Configuration de la messagerie et surveillance des envois."
        actions={
          <Bouton
            onClick={() => {
              void configuration.refetch();
              void historique.refetch();
            }}
          >
            <RefreshCw className="h-4 w-4" aria-hidden /> Actualiser
          </Bouton>
        }
      >
        <EtatBloc requete={configuration}>
          {(c) => (
            <>
              <dl className="grid gap-4 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-ink-2">Mode d’envoi</dt>
                  <dd className="font-bold">{c.smtp ? "SMTP" : "Simulation ou autre service"}</dd>
                </div>
                <div>
                  <dt className="text-ink-2">Serveur</dt>
                  <dd>
                    {c.hote || "Non renseigné"} · port {c.port} ·{" "}
                    {c.tls ? "TLS" : c.ssl ? "SSL" : "Sans chiffrement"}
                  </dd>
                </div>
                <div>
                  <dt className="text-ink-2">Expéditeur</dt>
                  <dd className="break-words">{c.expediteur}</dd>
                </div>
                <div>
                  <dt className="text-ink-2">Authentification</dt>
                  <dd>
                    {c.authentification_configuree ? "Identifiants renseignés" : "Identifiants absents"}
                  </dd>
                </div>
                <div>
                  <dt className="text-ink-2">Planificateur local</dt>
                  <dd>
                    {c.planificateur_actif ? "Actif" : "Arrêté"} · vérification{" "}
                    {c.verification_active ? "activée" : "désactivée"}
                  </dd>
                </div>
                <div>
                  <dt className="text-ink-2">Dernière vérification</dt>
                  <dd>{c.derniere_verification ? dateHeureFr(c.derniere_verification) : "Aucune"}</dd>
                </div>
                <div>
                  <dt className="text-ink-2">Adresse de l’application dans les mails</dt>
                  <dd className="break-all">{c.url_application}</dd>
                </div>
              </dl>
              <div className="mt-4 flex flex-wrap gap-4 border-t border-border pt-3 text-sm">
                {Object.entries(STATUTS).map(([s, nom]) => (
                  <span key={s}>
                    {nom} : <strong>{c.compteurs[s] ?? 0}</strong>
                  </span>
                ))}
              </div>
            </>
          )}
        </EtatBloc>
      </Carte>
      <Carte
        id="modeles-mails"
        titre="Modèles institutionnels"
        sousTitre="Notification principale : retard de traitement des dossiers. Prévisualisez les notifications et leurs relances avec des données fictives."
      >
        <EtatBloc requete={modeles}>
          {(liste) => (
            <div className="mb-4 grid gap-3 sm:grid-cols-2">
              <Champ libelle="Modèle de notification">
                {(id) => (
                  <Liste
                    id={id}
                    value={modele}
                    disabled={test.isPending}
                    onChange={(e) => {
                      setModele(e.target.value);
                      test.reset();
                    }}
                  >
                    {liste.map((m) => (
                      <option key={m.code} value={m.code}>
                        {m.titre}
                      </option>
                    ))}
                  </Liste>
                )}
              </Champ>
              {modele !== "test" && (
                <Champ libelle="Nature du message">
                  {(id) => (
                    <Liste
                      id={id}
                      value={categorie}
                      disabled={test.isPending}
                      onChange={(e) => {
                        setCategorie(e.target.value);
                        test.reset();
                      }}
                    >
                      <option value="alerte">Notification initiale</option>
                      <option value="relance">Relance</option>
                    </Liste>
                  )}
                </Champ>
              )}
            </div>
          )}
        </EtatBloc>
        <EtatBloc requete={apercu}>
          {(a) => (
            <div className="grid gap-3">
              <p className="text-sm">
                <strong>Objet :</strong> {a.sujet}
              </p>
              <Champ libelle="Format de prévisualisation">
                {(id) => (
                  <Liste id={id} value={format} onChange={(e) => setFormat(e.target.value)}>
                    <option value="html">Présentation institutionnelle</option>
                    <option value="texte">Version texte</option>
                  </Liste>
                )}
              </Champ>
              {format === "html" ? (
                <iframe
                  title="Aperçu du mail institutionnel"
                  sandbox=""
                  srcDoc={a.html}
                  className="h-[680px] w-full rounded-sm border border-border bg-surface"
                />
              ) : (
                <pre className="max-h-[680px] overflow-auto whitespace-pre-wrap rounded-sm border border-border bg-surface p-4 font-sans text-sm">
                  {a.texte}
                </pre>
              )}
            </div>
          )}
        </EtatBloc>
      </Carte>
      <Carte
        id="test-mail"
        titre="Tester l’envoi d’un mail"
        sousTitre="Le modèle sélectionné sera envoyé uniquement à l’adresse saisie. Les exemples métier portent la mention TEST et ne modifient aucune alerte."
      >
        <form onSubmit={soumettre} className="grid max-w-xl gap-3">
          <Champ libelle="Adresse destinataire">
            {(id) => (
              <Entree
                id={id}
                type="email"
                required
                maxLength={254}
                value={destinataire}
                onChange={(e) => {
                  setDestinataire(e.target.value);
                  test.reset();
                }}
                placeholder="nom@exemple.gn"
              />
            )}
          </Champ>
          <div>
            <Bouton
              type="submit"
              variante="primaire"
              disabled={test.isPending || !destinataire.trim() || !apercu.data || apercu.isError}
            >
              <Send className="h-4 w-4" aria-hidden />
              {test.isPending ? "Envoi en cours…" : "Envoyer le mail de test"}
            </Bouton>
          </div>
          {test.isError && <Retour ok={false}>{messageErreur(test.error)}</Retour>}
          {test.data && (
            <Retour ok={test.data.statut === "envoye"}>
              {test.data.statut === "envoye"
                ? "Message accepté par la messagerie. Vérifiez la boîte de réception et les courriers indésirables."
                : test.data.statut === "simulation"
                  ? "Simulation enregistrée : aucun mail réel envoyé."
                  : test.data.erreur || "Envoi non terminé."}
            </Retour>
          )}
        </form>
      </Carte>
      <Carte
        id="historique-mails"
        titre="Historique des envois"
        sousTitre="Tests, alertes et relances. L’acceptation SMTP ne confirme pas la réception ou la lecture du mail."
        actions={
          <Liste
            aria-label="Filtrer par statut"
            value={statut}
            onChange={(e) => {
              setStatut(e.target.value);
              setPage(1);
            }}
          >
            <option value="">Tous les statuts</option>
            {Object.entries(STATUTS).map(([s, nom]) => (
              <option key={s} value={s}>
                {nom}
              </option>
            ))}
          </Liste>
        }
      >
        <EtatBloc requete={historique}>
          {(h) => (
            <>
              <DataTable
                donnees={h.results}
                libelle="Historique des mails"
                colonnes={[
                  { header: "Date", accessorKey: "date", cell: ({ row }) => dateHeureFr(row.original.date) },
                  {
                    header: "Type",
                    accessorKey: "type",
                    cell: ({ row }) =>
                      ({ test: "Test", alerte: "Alerte", relance: "Relance" })[row.original.type] ??
                      row.original.type,
                  },
                  {
                    header: "Destinataires",
                    accessorKey: "destinataires",
                    cell: ({ row }) => row.original.destinataires.join(", "),
                  },
                  {
                    header: "Statut",
                    accessorKey: "statut",
                    cell: ({ row }) => STATUTS[row.original.statut] ?? row.original.statut,
                  },
                  { header: "Sujet", accessorKey: "sujet" },
                  { header: "Référence", accessorKey: "reference" },
                  {
                    header: "Demandé par / règle",
                    id: "origine",
                    cell: ({ row }) => row.original.utilisateur ?? row.original.regle ?? "Automatique",
                  },
                  { header: "Détail de l’échec", accessorKey: "erreur" },
                ]}
              />
              <div className="mt-3 flex items-center justify-between gap-2 text-sm">
                <span>
                  {h.count} tentative(s) · page {page}
                </span>
                <div className="flex gap-2">
                  <Bouton disabled={page === 1} onClick={() => setPage(page - 1)}>
                    Précédente
                  </Bouton>
                  <Bouton disabled={page * 25 >= h.count} onClick={() => setPage(page + 1)}>
                    Suivante
                  </Bouton>
                </div>
              </div>
            </>
          )}
        </EtatBloc>
      </Carte>
    </div>
  );
}
