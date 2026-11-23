import { Check, ChevronRight, FileDown } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";

import { telecharger } from "@/api/client";
import { useSources, useStatutAlerte } from "@/api/hooks";
import type { Alerte, Severite } from "@/api/types";
import { dateFr, dateHeureFr } from "@/lib/format";
import { DOMAINES_LIBELLES } from "@/lib/sources";

import { FicheDossier } from "./FicheDossier";
import { ETATS, PastilleEtat } from "./Indicateurs";
import { SourceBadge } from "./Source";
import { Modal } from "./ui/modal";
import { Bouton, Segment } from "./ui/primitives";

type FiltreGravite = "toutes" | Severite;

const STATUTS: Record<Alerte["statut"], string> = { nouvelle: "Nouvelle", vue: "Vue", traitee: "Traitée" };

function Champ({ libelle, children }: { libelle: string; children: ReactNode }) {
  if (children === null || children === undefined || children === "") return null;
  return (
    <div className="flex flex-col">
      <dt className="text-xs text-ink-2">{libelle}</dt>
      <dd className="text-sm text-ink">{children}</dd>
    </div>
  );
}

/** Fiche de l'alerte : détail du dossier pour les alertes par dossier (arbitrages), sinon message et source. */
export function DetailAlerte({
  a,
  id,
  onNavigation,
  ouvrirLien,
}: {
  a: Alerte;
  id: string;
  onNavigation?: () => void;
  /** Remplace le lien par une action sur place (ex. ouvrir la fiche du titre sans quitter les filtres). */
  ouvrirLien?: () => void;
}) {
  const d = a.donnees ?? {};
  const texte = (cle: string) => (d[cle] == null || d[cle] === "" ? null : String(d[cle]));
  const dossier = Boolean(texte("numero"));
  return (
    <div
      id={id}
      role={dossier ? "region" : undefined}
      aria-labelledby={dossier ? `${id}-titre` : undefined}
      className={
        dossier
          ? "mt-2 overflow-hidden rounded border border-border bg-surface"
          : "mt-2 rounded-sm border border-border bg-hover p-3"
      }
    >
      {dossier ? (
        <FicheDossier a={a} titreId={`${id}-titre`} />
      ) : (
        <dl className="grid gap-x-4 gap-y-2 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <Champ libelle="Constat">{a.message}</Champ>
          </div>
          <Champ libelle="Action recommandée">{a.action_recommandee}</Champ>
          <Champ libelle="Valeur">{a.valeur}</Champ>
          <Champ libelle="Source">{a.source}</Champ>
          <Champ libelle="Situation des données">{a.date_situation && dateFr(a.date_situation)}</Champ>
          <Champ libelle="Levée le">{dateHeureFr(a.date)}</Champ>
          <Champ libelle="Statut de l'alerte">{STATUTS[a.statut]}</Champ>
        </dl>
      )}
      {ouvrirLien ? (
        <button
          type="button"
          onClick={ouvrirLien}
          className={
            dossier
              ? "sans-impression mx-3 mb-3 inline-flex items-center justify-center rounded border border-border bg-zebra px-3 py-1 text-sm font-bold text-navy hover:bg-hover dark:text-ink"
              : "mt-3 inline-block text-sm font-bold text-ink underline underline-offset-2"
          }
        >
          {dossier ? `Ouvrir le détail du ${texte("libelle_titre") ?? "titre"}` : "Ouvrir la page concernée"}
        </button>
      ) : (
        a.lien && (
          <Link
            to={a.lien}
            onClick={onNavigation}
            className={
              dossier
                ? "sans-impression mx-3 mb-3 inline-flex items-center justify-center rounded border border-border bg-zebra px-3 py-1 text-sm font-bold text-navy hover:bg-hover dark:text-ink"
                : "mt-3 inline-block text-sm font-bold text-ink underline underline-offset-2"
            }
          >
            {dossier
              ? `Ouvrir le détail du ${texte("libelle_titre") ?? "titre"}`
              : "Ouvrir la page concernée"}
          </Link>
        )
      )}
    </div>
  );
}

/** Vrai pour une alerte par dossier (arbitrage) : sa fiche s'ouvre dans une fenêtre imprimable. */
function estDossier(a: Alerte) {
  const n = a.donnees?.numero;
  return n != null && String(n).trim() !== "";
}

/** Télécharge la fiche de suivi en PDF structuré (A4, charte des rapports), produite par le serveur. */
function BoutonFichePdf({ a }: { a: Alerte }) {
  const [etat, setEtat] = useState<"pret" | "encours" | "erreur">("pret");
  async function telechargerFiche() {
    setEtat("encours");
    try {
      await telecharger(`/alertes/${a.id}/fiche-pdf/`);
      setEtat("pret");
    } catch {
      setEtat("erreur");
    }
  }
  return (
    <>
      {etat === "erreur" && (
        <span role="alert" className="text-sm text-ink">
          PDF indisponible
        </span>
      )}
      <button
        type="button"
        onClick={telechargerFiche}
        disabled={etat === "encours"}
        className="inline-flex items-center gap-1.5 rounded border border-border bg-navy px-2.5 py-1 text-sm font-bold text-on-navy hover:opacity-90 disabled:opacity-60"
      >
        <FileDown className="h-4 w-4" aria-hidden />
        {etat === "encours" ? "Préparation…" : "Télécharger la fiche PDF"}
      </button>
    </>
  );
}

/** Fiche de suivi d'un dossier dans une fenêtre modale ; le PDF structuré se télécharge depuis l'en-tête. */
export function FenetreDossier({
  a,
  ouvert,
  onChange,
  onNavigation,
  ouvrirLien,
}: {
  a: Alerte;
  ouvert: boolean;
  onChange: (ouvert: boolean) => void;
  onNavigation?: () => void;
  ouvrirLien?: () => void;
}) {
  const d = a.donnees ?? {};
  const numero = String(d.numero ?? "");
  const contexte = [d.libelle_titre, d.ministere].filter(Boolean).join(" · ");
  return (
    <Modal
      ouvert={ouvert}
      onChange={onChange}
      titre={`Fiche de suivi · dossier n° ${numero}`}
      description={contexte || undefined}
      actions={<BoutonFichePdf a={a} />}
    >
      <DetailAlerte
        a={a}
        id={`fenetre-dossier-${a.id}`}
        onNavigation={() => {
          onChange(false);
          onNavigation?.();
        }}
        ouvrirLien={
          ouvrirLien
            ? () => {
                onChange(false);
                ouvrirLien();
              }
            : undefined
        }
      />
    </Modal>
  );
}

function LigneAlerte({
  a,
  compact,
  onNavigation,
}: {
  a: Alerte;
  compact: boolean;
  onNavigation?: () => void;
}) {
  const statut = useStatutAlerte();
  const sources = useSources();
  const [ouvert, setOuvert] = useState(false);
  const statutSource = sources.data?.find((s) => s.code === a.source_code)?.statut ?? "reel";
  const { couleur, libelle } = ETATS[a.severite];
  const idDetail = `alerte-${a.id}-detail`;
  // Dossier : la fiche s'ouvre en fenêtre ; autre alerte : son détail se déplie sous la ligne.
  const dossier = estDossier(a);
  return (
    <li className="flex gap-3 border-l-4 bg-surface py-2 pl-3 pr-1" style={{ borderLeftColor: couleur }}>
      <PastilleEtat etat={a.severite} />
      <div className="min-w-0 flex-1">
        {/* Un clic n'importe où sur l'alerte (titre, action, message) déplie sa fiche ; le bouton du titre
            porte l'état pour le clavier et les lecteurs d'écran, son clic remonte jusqu'ici. */}
        <div className="cursor-pointer" onClick={() => setOuvert((o) => !o)}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <h3 className="min-w-0 text-base font-bold text-ink">
              <span className="sr-only">{libelle} : </span>
              <button
                type="button"
                aria-expanded={dossier ? undefined : ouvert}
                aria-controls={dossier ? undefined : idDetail}
                aria-haspopup={dossier ? "dialog" : undefined}
                className="group inline-flex items-start gap-1 text-left hover:underline"
              >
                <ChevronRight
                  aria-hidden
                  className={`mt-1 h-4 w-4 shrink-0 text-ink-2 transition-transform ${ouvert && !dossier ? "rotate-90" : ""}`}
                />
                {a.titre}
              </button>
            </h3>
            {a.valeur && (
              <span className="chiffres shrink-0 whitespace-nowrap text-md font-bold text-ink">
                {a.valeur}
              </span>
            )}
          </div>
          {a.action_recommandee && (
            <p className="text-sm font-bold text-ink">Action recommandée : {a.action_recommandee}</p>
          )}
          {!compact && <p className="text-sm text-ink-2">{a.message}</p>}
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
          {a.source_code && (
            <SourceBadge
              meta={{ source: a.source_code, statut_source: statutSource, date_situation: a.date_situation }}
            />
          )}
          {a.statut !== "traitee" && (
            <button
              type="button"
              className="sans-presentation sans-impression inline-flex items-center gap-1 rounded-sm px-1 text-xs text-ink-2 hover:bg-hover hover:text-ink"
              onClick={() => statut.mutate({ id: a.id, statut: "traitee" })}
              disabled={statut.isPending}
            >
              <Check className="h-3 w-3" aria-hidden /> Marquer comme traitée
            </button>
          )}
        </div>
        {dossier ? (
          <FenetreDossier a={a} ouvert={ouvert} onChange={setOuvert} onNavigation={onNavigation} />
        ) : (
          ouvert && <DetailAlerte a={a} id={idDetail} onNavigation={onNavigation} />
        )}
      </div>
    </li>
  );
}

/** Alertes classées par gravité, filtrables par gravité et par domaine. */
export function ListeAlertes({
  alertes,
  compact = false,
  limite,
  filtres = true,
  titre,
  titreId,
  onNavigation,
}: {
  alertes: Alerte[];
  compact?: boolean;
  limite?: number;
  filtres?: boolean;
  titre?: string;
  titreId?: string;
  /** Appelé quand on suit le lien d'une alerte (ex. fermer le panneau qui contient la liste). */
  onNavigation?: () => void;
}) {
  const [gravite, setGravite] = useState<FiltreGravite>("toutes");
  const [domaine, setDomaine] = useState("");
  const [tout, setTout] = useState(false);

  const domaines = useMemo(() => [...new Set(alertes.map((a) => a.domaine))], [alertes]);
  const filtrees = alertes
    .filter((a) => (gravite === "toutes" || a.severite === gravite) && (!domaine || a.domaine === domaine))
    .sort((x, y) => ETATS[x.severite].rang - ETATS[y.severite].rang);
  const visibles = limite && !tout ? filtrees.slice(0, limite) : filtrees;

  return (
    <div className="flex flex-col gap-2">
      {(titre || (filtres && alertes.length > 0)) && (
        <div className="flex flex-wrap items-center gap-2">
          {titre && (
            <h2 id={titreId} className="mr-auto text-md font-bold text-ink">
              {titre}{" "}
              <span className="chiffres text-sm font-normal text-ink-2" aria-live="polite">
                ({filtrees.length})
              </span>
            </h2>
          )}
          {filtres && alertes.length > 0 && (
            <div className="sans-impression sans-presentation flex flex-wrap items-center gap-2">
              <Segment<FiltreGravite>
                libelle="Filtrer par gravité"
                valeur={gravite}
                onChange={setGravite}
                options={[
                  { valeur: "toutes", libelle: "Toutes" },
                  { valeur: "critique", libelle: "Critiques" },
                  { valeur: "serieux", libelle: "Sérieuses" },
                  { valeur: "vigilance", libelle: "Vigilance" },
                ]}
              />
              {domaines.length > 1 && (
                <label className="flex items-center gap-1.5 text-sm text-ink-2">
                  <span className="sr-only">Filtrer par domaine</span>
                  <select
                    value={domaine}
                    onChange={(e) => setDomaine(e.target.value)}
                    className="min-h-8 rounded-sm border border-border px-2 text-sm"
                  >
                    <option value="">Tous les domaines</option>
                    {domaines.map((d) => (
                      <option key={d} value={d}>
                        {DOMAINES_LIBELLES[d] ?? d}
                      </option>
                    ))}
                  </select>
                </label>
              )}
            </div>
          )}
        </div>
      )}
      {visibles.length ? (
        <ul className="flex flex-col divide-y divide-border">
          {visibles.map((a) => (
            <LigneAlerte key={a.id} a={a} compact={compact} onNavigation={onNavigation} />
          ))}
        </ul>
      ) : (
        <p className="py-2 text-base text-ink-2">Aucune alerte pour ces critères.</p>
      )}
      {limite && filtrees.length > limite && (
        <Bouton
          variante="discret"
          className="sans-impression self-start"
          onClick={() => setTout((t) => !t)}
          aria-expanded={tout}
        >
          {tout
            ? "Afficher moins"
            : filtrees.length - limite === 1
              ? "Voir l'autre alerte"
              : `Voir les ${filtrees.length - limite} autres alertes`}
        </Bouton>
      )}
    </div>
  );
}
