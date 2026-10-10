import { useRef } from "react";

/**
 * Rend le focus à l'élément qui avait le focus à l'ouverture d'une boîte de dialogue Radix.
 * Nécessaire quand l'ouverture ne passe pas par un <Dialog.Trigger> (ligne de tableau, bouton ordinaire).
 */
export function useRetourFocus() {
  const precedent = useRef<HTMLElement | null>(null);
  return {
    onOpenAutoFocus: () => {
      precedent.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    },
    onCloseAutoFocus: (e: Event) => {
      const el = precedent.current;
      if (el?.isConnected) {
        e.preventDefault();
        el.focus();
      }
    },
  };
}
