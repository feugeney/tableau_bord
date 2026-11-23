import { Bell, X } from "lucide-react";
import { useEffect, useState } from "react";

import { useAlertes } from "@/api/hooks";
import type { Alerte } from "@/api/types";

import { ListeAlertes } from "./Alertes";
import { ETATS } from "./Indicateurs";
import { Sheet } from "./ui/sheet";

const DUREE_ANNONCE_MS = 9000;

function lireDejaAnnonce(cle: string): boolean {
  try {
    return sessionStorage.getItem(cle) === "1";
  } catch {
    return false;
  }
}

function noterAnnonce(cle: string) {
  try {
    sessionStorage.setItem(cle, "1");
  } catch {
    /* stockage indisponible : l'annonce pourra réapparaître */
  }
}

/** Gravité la plus haute des alertes ouvertes (couleur de la pastille et de l'annonce). */
function pire(alertes: Alerte[]) {
  return [...alertes].sort((a, b) => ETATS[a.severite].rang - ETATS[b.severite].rang)[0]?.severite;
}

/**
 * Points d'attention en notification : une cloche dans l'en-tête de la page porte le nombre d'alertes
 * ouvertes (couleur de la plus grave) et ouvre la liste dans un panneau latéral. À l'arrivée sur la page,
 * une annonce brève signale les alertes critiques ou sérieuses, une seule fois par session.
 */
export function NotificationAlertes({ domaine, libelle }: { domaine: string; libelle: string }) {
  const r = useAlertes({ domaine, statut: "nouvelle,vue" });
  const alertes = r.data ?? [];
  const [ouvert, setOuvert] = useState(false);
  const cle = `tdb.annonce-alertes.${domaine}`;
  const graves = alertes.filter((a) => a.severite === "critique" || a.severite === "serieux");
  const [annonce, setAnnonce] = useState(false);

  useEffect(() => {
    if (!graves.length || lireDejaAnnonce(cle)) return;
    noterAnnonce(cle);
    setAnnonce(true);
    const t = window.setTimeout(() => setAnnonce(false), DUREE_ANNONCE_MS);
    return () => window.clearTimeout(t);
  }, [graves.length, cle]);

  const gravite = pire(alertes);
  const critiques = alertes.filter((a) => a.severite === "critique").length;
  const resume = r.isError
    ? "alertes indisponibles"
    : r.isLoading
      ? "chargement des alertes"
      : alertes.length === 0
        ? "aucune alerte ouverte"
        : `${alertes.length} alerte(s) ouverte(s)${critiques ? `, dont ${critiques} critique(s)` : ""}`;

  function ouvrir() {
    setAnnonce(false);
    setOuvert(true);
  }

  return (
    <>
      <button
        type="button"
        onClick={ouvrir}
        aria-haspopup="dialog"
        aria-label={`Points d'attention : ${resume}`}
        title={`Points d'attention : ${resume}`}
        // Cloche seule ; le nom accessible et l'infobulle disent « Points d'attention » et le décompte.
        className="relative inline-flex h-9 w-9 items-center justify-center rounded-full border border-border bg-surface text-ink hover:bg-hover"
      >
        <Bell className="h-5 w-5" aria-hidden />
        {alertes.length > 0 && (
          <span
            aria-hidden
            className="chiffres absolute -right-1.5 -top-1.5 min-w-[1.25rem] rounded-full border-2 border-surface px-1 text-center text-xs font-bold leading-4 text-sur-etat"
            style={{ background: gravite ? ETATS[gravite].couleur : undefined }}
          >
            {alertes.length > 99 ? "99+" : alertes.length}
          </span>
        )}
      </button>

      {annonce && (
        <div
          role="status"
          className="sans-impression fixed bottom-4 right-4 z-40 flex max-w-sm items-start gap-3 rounded border border-l-4 border-border bg-surface p-3 shadow-lg"
          style={{ borderLeftColor: gravite ? ETATS[gravite].couleur : undefined }}
        >
          <Bell className="mt-0.5 h-4 w-4 shrink-0 text-ink" aria-hidden />
          <div className="min-w-0 text-sm text-ink">
            <p className="font-bold">
              {libelle} : {graves.length} alerte(s) {critiques ? "critique(s) ou sérieuse(s)" : "sérieuse(s)"}
            </p>
            <p className="truncate text-ink-2">
              {[...graves].sort((a, b) => ETATS[a.severite].rang - ETATS[b.severite].rang)[0]?.titre}
            </p>
            <button type="button" onClick={ouvrir} className="mt-1 font-bold underline underline-offset-2">
              Voir les points d'attention
            </button>
          </div>
          <button
            type="button"
            onClick={() => setAnnonce(false)}
            aria-label="Fermer l'annonce"
            className="rounded-sm p-0.5 text-ink-2 hover:bg-hover hover:text-ink"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>
      )}

      <Sheet
        ouvert={ouvert}
        onChange={setOuvert}
        titre="Points d'attention"
        largeur="max-w-[800px]"
        description={`${libelle} · ${resume}`}
      >
        <p className="mb-3 text-sm text-ink-2">
          Périmètre global des alertes du domaine · indépendant des filtres de consultation.
        </p>
        {r.isError ? (
          <div role="alert">
            <p className="text-sm text-ink">
              Les alertes n’ont pas pu être chargées. Leur absence ne peut pas être confirmée.
            </p>
            <button type="button" className="mt-2 text-sm font-bold underline" onClick={() => r.refetch()}>
              Réessayer
            </button>
          </div>
        ) : alertes.length ? (
          <ListeAlertes alertes={alertes} filtres onNavigation={() => setOuvert(false)} />
        ) : (
          <p className="text-base text-ink-2">{r.isLoading ? "Chargement…" : "Aucune alerte ouverte."}</p>
        )}
      </Sheet>
    </>
  );
}
