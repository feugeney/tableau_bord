import { FileJson, PlugZap, Save, Upload } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { messageErreur, useAdmin, useListesAdmin, useMutationAdmin, type SourceAdmin } from "@/api/admin";
import { api, telecharger } from "@/api/client";
import { DataTable } from "@/components/DataTable";
import { StatusPill } from "@/components/Indicateurs";
import { SourceBadge } from "@/components/Source";
import { Bouton, Carte } from "@/components/ui/primitives";
import { Sheet } from "@/components/ui/sheet";
import { Case, Champ, Entree, Liste, Retour, ZoneTexte } from "@/components/ui/formulaire";
import { nombre } from "@/lib/format";

import { EtatBloc } from "./commun";

interface ResultatImport {
  statut: string;
  lignes_lues: number;
  lignes_chargees: number;
  lignes_rejetees: number;
  message_erreur: string;
  detail: {
    controles?: { code: string; libelle: string; niveau: string; reussi: boolean; nombre: number | null }[];
  };
}

const AUTOMATIQUES = ["oracle_chaine_depense", "postgres", "api"];

export default function Sources() {
  const r = useAdmin<SourceAdmin[]>("sources/");
  const listes = useListesAdmin();
  const libelleConnecteur = (c: string) => listes.data?.connecteurs.find((x) => x.code === c)?.libelle ?? c;
  const [choisie, setChoisie] = useState<SourceAdmin | null>(null);
  return (
    <Carte
      id="sources"
      titre="Connexions aux sources"
      sousTitre="Configurer et tester les accès aux systèmes d'origine. Les identifiants restent dans les variables d'environnement. Les traitements SYSOP et Chaîne Dépense se règlent dans Flux ETL."
    >
      <EtatBloc requete={r}>
        {(sources) => (
          <DataTable
            donnees={sources}
            libelle="Connexions aux sources de données"
            onLigne={setChoisie}
            colonnes={[
              { header: "Application", accessorKey: "application" },
              { header: "Structure", accessorKey: "structure" },
              {
                header: "Connecteur",
                accessorKey: "connecteur",
                cell: ({ getValue }) => libelleConnecteur(getValue() as string),
              },
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
              {
                header: "Connexion",
                id: "connexion",
                accessorFn: (s) => String(s.connexion_configuree),
                cell: ({ row }) =>
                  row.original.connexion_configuree === null ? (
                    <span className="text-ink-2">Import de fichier</span>
                  ) : row.original.connexion_configuree ? (
                    <StatusPill etat="bon" libelle="Configurée" />
                  ) : (
                    <StatusPill
                      etat="vigilance"
                      libelle={`${row.original.variable_connexion} à renseigner`}
                    />
                  ),
              },
              {
                header: "Planification",
                accessorKey: "planification_cron",
                cell: ({ row }) =>
                  ["sysop", "chaine_depense"].includes(row.original.code) ? (
                    <span className="text-ink-2">Dans Flux ETL</span>
                  ) : AUTOMATIQUES.includes(row.original.connecteur) ? (
                    <code translate="no">{row.original.planification_cron || "—"}</code>
                  ) : (
                    <span className="text-ink-2">Import manuel</span>
                  ),
              },
              { header: "Chargements", accessorKey: "nb_chargements", meta: { numerique: true } },
            ]}
          />
        )}
      </EtatBloc>
      {choisie && <PanneauSource source={choisie} onFermer={() => setChoisie(null)} />}
    </Carte>
  );
}

function PanneauSource({ source, onFermer }: { source: SourceAdmin; onFermer: () => void }) {
  const listes = useListesAdmin();
  const [f, setF] = useState({
    connecteur: source.connecteur,
    statut: source.statut,
    planification_cron: source.planification_cron,
    remarque: source.remarque,
    configuration: JSON.stringify(source.configuration ?? {}, null, 2),
  });
  const [erreurJson, setErreurJson] = useState<string | null>(null);
  const enregistrer = useMutationAdmin((corps: object) =>
    api.patch<SourceAdmin>(`/admin/sources/${source.code}/`, corps),
  );
  const tester = useMutationAdmin(() =>
    api.post<{ ok: boolean; message: string }>(`/admin/sources/${source.code}/tester/`),
  );

  useEffect(() => setErreurJson(null), [f.configuration]);

  function soumettre(e: FormEvent) {
    e.preventDefault();
    let configuration: unknown;
    try {
      configuration = JSON.parse(f.configuration || "{}");
    } catch {
      setErreurJson("JSON invalide : vérifiez les guillemets et les virgules.");
      return;
    }
    enregistrer.mutate({ ...f, configuration });
  }

  return (
    <Sheet
      ouvert
      onChange={(o) => !o && onFermer()}
      titre={source.application}
      description={`${source.structure} · code ${source.code}`}
    >
      <form onSubmit={soumettre} className="flex flex-col gap-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Champ libelle="Type de connecteur">
            {(id) => (
              <Liste
                id={id}
                name="connecteur"
                value={f.connecteur}
                onChange={(e) => setF({ ...f, connecteur: e.target.value })}
              >
                {listes.data?.connecteurs.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.libelle}
                  </option>
                ))}
              </Liste>
            )}
          </Champ>
          <Champ
            libelle="Statut affiché"
            aide="« réel » est positionné automatiquement au premier chargement réussi."
          >
            {(id, d) => (
              <Liste
                id={id}
                name="statut"
                aria-describedby={d}
                value={f.statut}
                onChange={(e) => setF({ ...f, statut: e.target.value as SourceAdmin["statut"] })}
              >
                {listes.data?.statuts.map((s) => (
                  <option key={s.code} value={s.code}>
                    {s.libelle}
                  </option>
                ))}
              </Liste>
            )}
          </Champ>
        </div>
        {["sysop", "chaine_depense"].includes(source.code) ? (
          <p className="text-sm text-ink-2">
            L'exercice, l'activation et la programmation sont définis dans{" "}
            <Link className="underline" to="/administration/flux-etl">
              Flux ETL
            </Link>
            .
          </p>
        ) : (
          <Champ
            libelle="Planification (cron)"
            aide="Ex. « 0 2 * * * » : chaque nuit à 2 h. Vide : chargement manuel uniquement."
          >
            {(id, d) => (
              <Entree
                id={id}
                name="planification_cron"
                autoComplete="off"
                spellCheck={false}
                aria-describedby={d}
                value={f.planification_cron}
                onChange={(e) => setF({ ...f, planification_cron: e.target.value })}
                placeholder="0 2 * * *…"
              />
            )}
          </Champ>
        )}
        <Champ
          libelle="Configuration du connecteur (JSON)"
          aide={
            source.variable_connexion
              ? `Connexion lue dans la variable ${source.variable_connexion} (${source.connexion_configuree ? "renseignée" : "non renseignée"}). Clés usuelles : table_cible, requete (SELECT uniquement), onglet.`
              : "Clés usuelles : table_cible, onglet (import générique), url (API)."
          }
          erreur={erreurJson}
        >
          {(id, d) => (
            <ZoneTexte
              id={id}
              name="configuration"
              rows={8}
              spellCheck={false}
              aria-describedby={d}
              value={f.configuration}
              onChange={(e) => setF({ ...f, configuration: e.target.value })}
            />
          )}
        </Champ>
        <Champ libelle="Remarque">
          {(id) => (
            <Entree
              id={id}
              name="remarque"
              autoComplete="off"
              value={f.remarque}
              onChange={(e) => setF({ ...f, remarque: e.target.value })}
            />
          )}
        </Champ>
        {enregistrer.isError && <Retour ok={false}>{messageErreur(enregistrer.error)}</Retour>}
        {enregistrer.isSuccess && <Retour ok>Configuration enregistrée.</Retour>}
        {tester.data && <Retour ok={tester.data.ok}>{tester.data.message}</Retour>}
        <div className="flex flex-wrap gap-2">
          <Bouton type="submit" variante="primaire" disabled={enregistrer.isPending}>
            <Save className="h-4 w-4" aria-hidden />{" "}
            {enregistrer.isPending ? "Enregistrement…" : "Enregistrer"}
          </Bouton>
          <Bouton onClick={() => tester.mutate(undefined)} disabled={tester.isPending}>
            <PlugZap className="h-4 w-4" aria-hidden />{" "}
            {tester.isPending ? "Test en cours…" : "Tester la connexion"}
          </Bouton>
          <Bouton
            onClick={() => void telecharger(`/admin/sources/${source.code}/schemas/`).catch(() => undefined)}
            title="Contrat d'échange à remettre au partenaire : clés attendues, types, champs obligatoires"
          >
            <FileJson className="h-4 w-4" aria-hidden /> Schémas JSON des flux
          </Bouton>
        </div>
      </form>
      <hr className="my-6 border-border" />
      <ImportFichier source={source} />
    </Sheet>
  );
}

function ImportFichier({ source }: { source: SourceAdmin }) {
  const [fichier, setFichier] = useState<File | null>(null);
  const [dateSituation, setDateSituation] = useState("");
  const [exercice, setExercice] = useState("");
  const [tableCible, setTableCible] = useState(String(source.configuration?.table_cible ?? ""));
  const [apercu, setApercu] = useState(true);
  const envoyer = useMutationAdmin(() => {
    const fd = new FormData();
    fd.append("fichier", fichier!);
    if (dateSituation) fd.append("date_situation", dateSituation);
    if (exercice) fd.append("exercice", exercice);
    if (tableCible && source.code !== "chaine_depense") fd.append("table_cible", tableCible);
    fd.append("apercu", String(apercu));
    return api.post<ResultatImport>(`/sources/${source.code}/import/`, fd);
  });
  const res = envoyer.data;
  return (
    <section aria-labelledby="import-titre" className="flex flex-col gap-4">
      <h3 id="import-titre" className="text-md font-bold text-ink">
        Importer un fichier
      </h3>
      <p className="text-sm text-ink-2">
        Excel (.xlsx) ou CSV. L'aperçu valide sans rien écrire ; décochez-le pour charger. Pour la Chaîne
        Dépense, le contrôle de concordance entre onglets est bloquant.
      </p>
      <Champ libelle="Fichier">
        {(id) => (
          <Entree
            id={id}
            name="fichier"
            type="file"
            accept=".xlsx,.csv,.xml,.json"
            onChange={(e) => setFichier(e.target.files?.[0] ?? null)}
          />
        )}
      </Champ>
      <div className="grid gap-4 sm:grid-cols-3">
        <Champ libelle="Date de situation" aide="Sinon : nom du fichier.">
          {(id, d) => (
            <Entree
              id={id}
              name="date_situation"
              type="date"
              aria-describedby={d}
              value={dateSituation}
              onChange={(e) => setDateSituation(e.target.value)}
            />
          )}
        </Champ>
        <Champ libelle="Exercice" aide="Sinon : fichier.">
          {(id, d) => (
            <Entree
              id={id}
              name="exercice"
              inputMode="numeric"
              autoComplete="off"
              aria-describedby={d}
              value={exercice}
              onChange={(e) => setExercice(e.target.value)}
            />
          )}
        </Champ>
        {source.code !== "chaine_depense" && (
          <Champ
            libelle="Table cible"
            aide="ex. fait_paie ; vide : tous les onglets mappés du classeur (ex. Telemo F3, F4, F5)"
          >
            {(id, d) => (
              <Entree
                id={id}
                name="table_cible"
                autoComplete="off"
                spellCheck={false}
                aria-describedby={d}
                value={tableCible}
                onChange={(e) => setTableCible(e.target.value)}
              />
            )}
          </Champ>
        )}
      </div>
      <Case
        libelle="Aperçu seulement (valider sans charger)"
        checked={apercu}
        onChange={(e) => setApercu(e.target.checked)}
      />
      <div>
        <Bouton
          variante="primaire"
          disabled={!fichier || envoyer.isPending}
          onClick={() => envoyer.mutate(undefined)}
        >
          <Upload className="h-4 w-4" aria-hidden />{" "}
          {envoyer.isPending ? "Import en cours…" : apercu ? "Valider le fichier" : "Charger le fichier"}
        </Bouton>
      </div>
      {envoyer.isError && <Retour ok={false}>{messageErreur(envoyer.error)}</Retour>}
      {res && (
        <Retour ok={res.statut !== "echec"}>
          {res.statut === "echec"
            ? `Échec : ${res.message_erreur}`
            : res.statut === "apercu"
              ? "Fichier valide (aperçu, rien n'a été chargé)."
              : "Chargement réussi."}{" "}
          {nombre(res.lignes_lues)} lignes lues, {nombre(res.lignes_chargees)} chargées,{" "}
          {nombre(res.lignes_rejetees)} rejetées.
        </Retour>
      )}
      {res?.detail?.controles && (
        <ul className="divide-y divide-border text-sm">
          {res.detail.controles.map((c) => (
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
      )}
    </section>
  );
}
