import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useAdmin, useMutationAdmin, messageErreur } from "@/api/admin";
import { api } from "@/api/client";
import { DataTable } from "@/components/DataTable";
import { Bouton, Carte } from "@/components/ui/primitives";
import { Retour } from "@/components/ui/formulaire";
import { dateHeureFr } from "@/lib/format";
import { EtatBloc } from "./commun";
import {
  ecrireProgrammation,
  FREQUENCES,
  JOURS,
  lireProgrammation,
  type Frequence,
  type Programmation,
} from "./programmation";

interface Flux {
  id: number;
  code: string;
  nom: string;
  source: string;
  profil: string;
  exercice: number;
  actif: boolean;
  planification_cron: string;
  requetes: { table: string; sql: string; champs: string[] }[];
  derniere_execution: { id: number; statut: string; lignes_chargees: number; message_erreur: string } | null;
  derniere_execution_planifiee: {
    id: number;
    statut: string;
    debut: string;
    lignes_chargees: number;
    message_erreur: string;
  } | null;
  prochaine_execution: string | null;
}
interface Execution {
  id: number;
  statut: string;
  lignes_lues: number;
  lignes_chargees: number;
  message: string;
  detail: { controles?: { code: string; libelle: string; niveau: string; reussi: boolean }[] };
}
const CHAMP = "mt-1 min-h-10 w-full rounded border border-border bg-surface px-3 text-ink";

function Fiche({ flux, planificateurActif }: { flux: Flux; planificateurActif: boolean | undefined }) {
  const oracle = flux.profil === "oracle_chaine_depense";
  const [exceptionHoraire, setExceptionHoraire] = useState(false);
  const [exercice, setExercice] = useState(flux.exercice);
  const [actif, setActif] = useState(flux.actif);
  const [prog, setProg] = useState(() => lireProgrammation(flux.planification_cron));
  const cron = ecrireProgrammation(prog);
  const changer = (p: Partial<Programmation>) => setProg((avant) => ({ ...avant, ...p }));
  const enregistrer = useMutationAdmin(() =>
    api.patch<Flux>(`/admin/flux-etl/${flux.id}/`, { exercice, actif, planification_cron: cron }),
  );
  const lancer = useMutationAdmin((apercu: boolean) =>
    api.post<Execution>(`/admin/flux-etl/${flux.id}/lancer/`, {
      apercu,
      exception_horaire_ponctuelle: oracle && exceptionHoraire,
    }),
  );
  const modifie = exercice !== flux.exercice || actif !== flux.actif || cron !== flux.planification_cron;
  const occupe = enregistrer.isPending || lancer.isPending;
  function sauver(e: FormEvent) {
    e.preventDefault();
    enregistrer.mutate(undefined, { onSuccess: (f) => setProg(lireProgrammation(f.planification_cron)) });
  }
  function executer(apercu: boolean) {
    lancer.mutate(apercu, { onSettled: () => setExceptionHoraire(false) });
  }
  return (
    <Carte
      id={`flux-${flux.code}`}
      titre={flux.nom}
      sousTitre={`Connexion : ${oracle ? "Oracle Chaîne Dépense" : "SYSOP"} · ${oracle ? "lignes budgétaires et engagements" : "portefeuille de l'État"}`}
    >
      <p className="text-sm text-ink-2">
        {oracle
          ? "LBUDG → situation budgétaire ; ENGAGEMENT → détail des engagements. Les requêtes et les correspondances existantes sont utilisées, avec un filtre explicite sur l'exercice et un rapprochement sur chaque clé budgétaire. "
          : "Organismes → subventions et dividendes → validation et santé financière. "}
        Les données sont conservées par exercice et situation ; seule la dernière exécution réussie de la même
        situation alimente les indicateurs.
      </p>
      <form onSubmit={sauver} className="my-4 flex flex-col gap-3">
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="text-sm font-bold text-ink">
            Exercice à récupérer
            <input
              type="number"
              min={2000}
              max={new Date().getFullYear()}
              required
              className={CHAMP}
              value={exercice}
              onChange={(e) => setExercice(Number(e.target.value))}
              disabled={occupe}
            />
          </label>
          <label className="text-sm font-bold text-ink">
            Chargement automatique
            <select
              className={CHAMP}
              value={prog.frequence}
              onChange={(e) => changer({ frequence: e.target.value as Frequence })}
              disabled={occupe}
            >
              {FREQUENCES.map(([valeur, libelle]) => (
                <option key={valeur} value={valeur}>
                  {libelle}
                </option>
              ))}
            </select>
          </label>
          {prog.frequence === "hebdomadaire" && (
            <label className="text-sm font-bold text-ink">
              Jour
              <select
                className={CHAMP}
                value={prog.jour}
                onChange={(e) => changer({ jour: e.target.value })}
                disabled={occupe}
              >
                {JOURS.map(([valeur, libelle]) => (
                  <option key={valeur} value={valeur}>
                    {libelle}
                  </option>
                ))}
              </select>
            </label>
          )}
          {["quotidien", "ouvres", "hebdomadaire"].includes(prog.frequence) && (
            <label className="text-sm font-bold text-ink">
              Heure (Conakry)
              <input
                type="time"
                required
                className={CHAMP}
                value={prog.heure}
                onChange={(e) => changer({ heure: e.target.value })}
                disabled={occupe}
              />
            </label>
          )}
          {prog.frequence === "avance" && (
            <label className="text-sm font-bold text-ink">
              Expression cron · minute heure jour mois jour-de-semaine
              <input
                className={CHAMP}
                value={prog.avance}
                onChange={(e) => changer({ avance: e.target.value })}
                placeholder="Ex. : 0 2 * * *"
                required
                disabled={occupe}
              />
            </label>
          )}
        </div>
        {oracle && prog.frequence !== "manuel" && (
          <p className="text-sm text-ink-2">
            La Chaîne Dépense n'est pas interrogée en semaine entre 7 h 30 et 18 h 30 : choisir un horaire de
            nuit (2 h par exemple) ou le week-end.
          </p>
        )}
        <label className="flex items-center gap-2 text-base text-ink">
          <input
            type="checkbox"
            checked={actif}
            onChange={(e) => setActif(e.target.checked)}
            disabled={occupe}
          />{" "}
          Autoriser l'alimentation réelle par ce flux
        </label>
        <p className="text-xs text-ink-2">
          Les chargements automatiques sont lancés par le planificateur, démarré avec l'application
          (Lancer.cmd). Une échéance manquée, poste éteint, n'est pas rattrapée. En cas d'échec, une alerte
          est publiée.
        </p>
        <div>
          <Bouton type="submit" disabled={!modifie || occupe}>
            Enregistrer la configuration
          </Bouton>
        </div>
      </form>
      {oracle && (
        <>
          <details className="mb-4 rounded border border-border p-3 text-sm text-ink">
            <summary className="cursor-pointer font-bold">
              Requêtes et correspondances Oracle utilisées
            </summary>
            {flux.requetes.length ? (
              flux.requetes.map((r) => (
                <div key={r.table} className="mt-3 min-w-0">
                  <h3 className="font-bold">
                    {r.table} · {r.champs.length} champs
                  </h3>
                  <p className="my-2 text-ink-2">{r.champs.join(" · ")}</p>
                  <pre className="max-w-full overflow-x-auto rounded bg-bg p-3 text-xs">
                    <code>{r.sql}</code>
                  </pre>
                </div>
              ))
            ) : (
              <p className="mt-2">Requêtes à renseigner dans la connexion Chaîne Dépense.</p>
            )}
          </details>
          <label className="mb-3 flex items-start gap-2 text-sm text-ink">
            <input
              type="checkbox"
              checked={exceptionHoraire}
              onChange={(e) => setExceptionHoraire(e.target.checked)}
              disabled={occupe}
              className="mt-1"
            />
            Autoriser ce lancement Oracle ponctuel en heures ouvrées. Cette exception est journalisée ; la
            programmation conserve ses restrictions horaires.
          </label>
        </>
      )}
      {enregistrer.isError && <Retour ok={false}>{messageErreur(enregistrer.error)}</Retour>}
      <div className="flex flex-wrap gap-2">
        <Bouton onClick={() => executer(true)} disabled={occupe || modifie}>
          Vérifier un aperçu
        </Bouton>
        <Bouton
          variante="primaire"
          onClick={() => executer(false)}
          disabled={occupe || modifie || !flux.actif}
        >
          Actualiser les données · {flux.exercice}
        </Bouton>
        <Link to="/administration/chargements" className="self-center text-sm underline">
          Consulter les exécutions
        </Link>
        <Link
          to={`/${oracle ? "depenses" : "portefeuille"}?exercice=${flux.exercice}`}
          className="self-center text-sm underline"
        >
          Voir {oracle ? "les dépenses" : "le portefeuille"} · {flux.exercice}
        </Link>
      </div>
      {modifie && (
        <p className="mt-2 text-sm text-ink-2">Enregistrez les modifications avant de lancer le flux.</p>
      )}
      {lancer.isPending && (
        <p className="mt-3 text-base text-ink" role="status">
          Extraction et contrôles en cours…
        </p>
      )}
      {lancer.isError && <Retour ok={false}>{messageErreur(lancer.error)}</Retour>}
      {lancer.data && (
        <div className="mt-3 flex flex-col gap-3">
          <Retour ok={lancer.data.statut !== "echec"}>
            Exécution n° {lancer.data.id} · {lancer.data.statut} · {lancer.data.lignes_lues} lignes lues ·{" "}
            {lancer.data.lignes_chargees} lignes enregistrées. {lancer.data.message}
            {lancer.data.statut === "apercu" && " Aperçu uniquement : aucune donnée métier enregistrée."}
          </Retour>
          <DataTable
            donnees={lancer.data.detail.controles ?? []}
            recherche={false}
            libelle="Contrôles de l'exécution ETL"
            colonnes={[
              { header: "Contrôle", accessorKey: "libelle" },
              { header: "Niveau", accessorKey: "niveau" },
              {
                header: "Résultat",
                accessorKey: "reussi",
                cell: ({ getValue }) => (getValue() ? "Réussi" : "À vérifier"),
              },
            ]}
          />
        </div>
      )}
      <div className="mt-3 flex flex-col gap-1 text-sm text-ink-2">
        {flux.prochaine_execution && (
          <p>
            Prochain chargement automatique :{" "}
            <strong className="text-ink">{dateHeureFr(flux.prochaine_execution)}</strong>
          </p>
        )}
        {flux.prochaine_execution && planificateurActif === false && (
          <Retour ok={false}>
            Le planificateur n'est pas démarré : ce chargement ne partira pas. Lancer l'application avec
            Lancer.cmd, ou exécuter « python manage.py planificateur » dans le dossier backend.
          </Retour>
        )}
        {flux.derniere_execution_planifiee && (
          <p>
            Dernier chargement automatique : {dateHeureFr(flux.derniere_execution_planifiee.debut)} · n°{" "}
            {flux.derniere_execution_planifiee.id} · {flux.derniere_execution_planifiee.statut} ·{" "}
            {flux.derniere_execution_planifiee.lignes_chargees} lignes.
            {flux.derniere_execution_planifiee.statut === "echec" &&
              ` ${flux.derniere_execution_planifiee.message_erreur}`}
          </p>
        )}
        {flux.derniere_execution && (
          <p>
            Dernière tentative : n° {flux.derniere_execution.id} · {flux.derniere_execution.statut} ·{" "}
            {flux.derniere_execution.lignes_chargees} lignes.
          </p>
        )}
      </div>
    </Carte>
  );
}
export default function FluxETL() {
  const r = useAdmin<Flux[]>("flux-etl/");
  const planificateur = useAdmin<{ actif: boolean }>("flux-etl/planificateur/");
  return (
    <div className="flex flex-col gap-4">
      <Carte titre="Flux ETL" sousTitre="Définir le traitement indépendamment de la connexion à la source">
        <p className="text-base text-ink-2">
          Les profils SYSOP et Chaîne Dépense Oracle utilisent les connexions existantes en lecture seule. Les
          autres besoins figurent dans la cartographie et seront raccordés avec leurs propres règles validées.
        </p>
      </Carte>
      <EtatBloc requete={r}>
        {(flux) =>
          flux.length ? (
            flux.map((f) => <Fiche key={f.id} flux={f} planificateurActif={planificateur.data?.actif} />)
          ) : (
            <p>Aucun flux configuré.</p>
          )
        }
      </EtatBloc>
    </div>
  );
}
