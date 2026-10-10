/** Panneau latéral (modèle « Sheet » de shadcn/ui, sur Radix Dialog). */
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ReactNode } from "react";

import { useRetourFocus } from "@/hooks/useRetourFocus";
import { cn } from "@/lib/utils";

export function Sheet({
  ouvert,
  onChange,
  titre,
  description,
  cote = "droite",
  largeur = "max-w-[640px]",
  children,
}: {
  ouvert: boolean;
  onChange: (ouvert: boolean) => void;
  titre: ReactNode;
  description?: ReactNode;
  cote?: "gauche" | "droite";
  largeur?: string;
  children: ReactNode;
}) {
  const retourFocus = useRetourFocus();
  return (
    <Dialog.Root open={ouvert} onOpenChange={onChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-[color-mix(in_srgb,var(--ink)_35%,transparent)]" />
        <Dialog.Content
          {...retourFocus}
          className={cn(
            "fixed inset-y-0 z-50 flex w-full flex-col border-border bg-surface text-ink [overscroll-behavior:contain]",
            cote === "droite" ? "right-0 border-l" : "left-0 border-r",
            largeur,
          )}
        >
          <header className="flex items-start justify-between gap-3 border-b border-border px-6 py-4">
            <div className="min-w-0">
              <Dialog.Title className="text-md font-bold text-ink">{titre}</Dialog.Title>
              {description ? (
                <Dialog.Description className="text-sm text-ink-2">{description}</Dialog.Description>
              ) : (
                <Dialog.Description className="sr-only">Panneau de détail</Dialog.Description>
              )}
            </div>
            <Dialog.Close
              className="rounded p-1 text-ink-2 hover:bg-hover hover:text-ink"
              aria-label="Fermer le panneau"
            >
              <X className="h-5 w-5" aria-hidden />
            </Dialog.Close>
          </header>
          <div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
