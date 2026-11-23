/** Fenêtre modale centrée (Radix Dialog), pour lire une fiche sans quitter la page.
 *
 * Avec `imprimable`, l'impression du navigateur (et « Enregistrer au format PDF ») ne sort que le contenu de
 * la fenêtre, en A4 portrait, avec l'en-tête officiel de l'application : voir `.modal-imprimable` dans
 * theme/print.css. */
import * as Dialog from "@radix-ui/react-dialog";
import { Printer, X } from "lucide-react";
import type { ReactNode } from "react";

import { useRetourFocus } from "@/hooks/useRetourFocus";
import { PLATEFORME } from "@/lib/identite";
import { dateFr } from "@/lib/format";
import { cn } from "@/lib/utils";

import { Armoiries, FiletTricolore } from "../cadre/Signature";

/** En-tête officiel d'une fiche imprimée : armoiries, ministère, plateforme, date, diffusion restreinte. */
function EnTeteImpressionFiche({ intitule }: { intitule: string }) {
  return (
    <div className="seulement-impression mb-3">
      <div className="flex items-end justify-between gap-4 pb-2">
        <div className="flex items-center gap-3">
          <Armoiries taille={44} />
          <div>
            <p className="etiquette">République de Guinée · {PLATEFORME.ministere}</p>
            <p className="font-titre text-lg font-semibold text-ink">
              {PLATEFORME.nom} — {intitule}
            </p>
          </div>
        </div>
        <p className="text-right text-sm font-bold text-ink">
          Document de travail – diffusion restreinte
          <span className="block font-normal text-ink-2">Imprimé le {dateFr(new Date().toISOString())}</span>
        </p>
      </div>
      <FiletTricolore />
    </div>
  );
}

export function Modal({
  ouvert,
  onChange,
  titre,
  description,
  imprimable,
  nomDocument,
  actions,
  largeur = "max-w-[980px]",
  children,
}: {
  ouvert: boolean;
  onChange: (ouvert: boolean) => void;
  /** Titre de la fenêtre ; aussi intitulé de l'en-tête imprimé. */
  titre: string;
  description?: ReactNode;
  /** Ajoute le bouton « Imprimer / PDF » et réserve l'impression au contenu de la fenêtre. */
  imprimable?: boolean;
  /** Titre du document pendant l'impression : nom proposé pour le fichier PDF. */
  nomDocument?: string;
  /** Boutons propres au contenu (ex. télécharger un PDF), placés dans l'en-tête avant la fermeture. */
  actions?: ReactNode;
  largeur?: string;
  children: ReactNode;
}) {
  const retourFocus = useRetourFocus();
  function imprimer() {
    const avant = document.title;
    if (nomDocument) document.title = nomDocument;
    window.print();
    document.title = avant;
  }
  return (
    <Dialog.Root open={ouvert} onOpenChange={onChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="modal-fond fixed inset-0 z-50 bg-[color-mix(in_srgb,var(--ink)_45%,transparent)]" />
        <Dialog.Content
          {...retourFocus}
          className={cn(
            "fixed left-1/2 top-1/2 z-50 flex max-h-[92vh] w-[calc(100vw-2rem)] -translate-x-1/2 -translate-y-1/2 flex-col rounded border border-border bg-surface text-ink shadow-lg",
            largeur,
            imprimable && "modal-imprimable",
          )}
        >
          <header className="sans-impression flex items-center justify-between gap-3 border-b border-border px-4 py-2.5">
            <div className="min-w-0">
              <Dialog.Title className="truncate text-md font-bold text-ink">{titre}</Dialog.Title>
              {description ? (
                <Dialog.Description className="truncate text-sm text-ink-2">{description}</Dialog.Description>
              ) : (
                <Dialog.Description className="sr-only">Fiche de détail</Dialog.Description>
              )}
            </div>
            <div className="flex shrink-0 items-center gap-1">
              {actions}
              {imprimable && (
                <button
                  type="button"
                  onClick={imprimer}
                  className="inline-flex items-center gap-1.5 rounded border border-border px-2.5 py-1 text-sm font-bold text-ink hover:bg-hover"
                >
                  <Printer className="h-4 w-4" aria-hidden />
                  Imprimer / PDF
                </button>
              )}
              <Dialog.Close
                className="rounded p-1 text-ink-2 hover:bg-hover hover:text-ink"
                aria-label="Fermer la fenêtre"
              >
                <X className="h-5 w-5" aria-hidden />
              </Dialog.Close>
            </div>
          </header>
          <div className="modal-corps min-h-0 flex-1 overflow-y-auto p-4">
            {imprimable && <EnTeteImpressionFiche intitule={titre} />}
            {children}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
