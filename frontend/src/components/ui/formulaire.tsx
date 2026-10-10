/** Champs de formulaire (administration) : libellé visible, aide, erreur au plus près du champ. */
import * as Dialog from "@radix-ui/react-dialog";
import {
  useId,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";

import { useRetourFocus } from "@/hooks/useRetourFocus";
import { cn } from "@/lib/utils";

import { Bouton } from "./primitives";

const CONTROLE =
  "mt-1 min-h-9 w-full rounded-sm border border-border bg-surface px-2 text-base text-ink placeholder:text-ink-3 disabled:opacity-60";

export function Champ({
  libelle,
  aide,
  erreur,
  children,
}: {
  libelle: string;
  aide?: ReactNode;
  erreur?: string | null;
  children: (id: string, decrit?: string) => ReactNode;
}) {
  const id = useId();
  const idAide = aide || erreur ? `${id}-aide` : undefined;
  return (
    <div className="flex flex-col">
      <label htmlFor={id} className="text-sm font-bold text-ink">
        {libelle}
      </label>
      {children(id, idAide)}
      {(aide || erreur) && (
        <p
          id={idAide}
          className={cn("mt-1 text-sm", erreur ? "font-bold text-ink" : "text-ink-2")}
          role={erreur ? "alert" : undefined}
        >
          {erreur ?? aide}
        </p>
      )}
    </div>
  );
}

export function Entree(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cn(CONTROLE, props.className)} />;
}

export function Liste(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={cn(CONTROLE, props.className)} />;
}

export function ZoneTexte(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={cn(CONTROLE, "py-1 font-mono text-sm", props.className)} />;
}

export function Case({ libelle, ...props }: InputHTMLAttributes<HTMLInputElement> & { libelle: ReactNode }) {
  return (
    <label className="inline-flex min-h-8 cursor-pointer items-center gap-2 text-base text-ink">
      <input type="checkbox" className="h-4 w-4 accent-[var(--navy)]" {...props} />
      {libelle}
    </label>
  );
}

/** Cases à cocher pour une liste de valeurs (domaines…). */
export function CasesMultiples({
  legende,
  options,
  valeur,
  onChange,
}: {
  legende: string;
  options: { code: string; libelle: string }[];
  valeur: string[];
  onChange: (v: string[]) => void;
}) {
  return (
    <fieldset>
      <legend className="text-sm font-bold text-ink">{legende}</legend>
      <div className="mt-1 grid grid-cols-1 gap-x-4 sm:grid-cols-2">
        {options.map((o) => (
          <Case
            key={o.code}
            libelle={o.libelle}
            checked={valeur.includes(o.code)}
            onChange={(e) =>
              onChange(e.target.checked ? [...valeur, o.code] : valeur.filter((x) => x !== o.code))
            }
          />
        ))}
      </div>
    </fieldset>
  );
}

/** Confirmation explicite avant une action destructrice ou irréversible. */
export function Confirmation({
  ouvert,
  onChange,
  titre,
  message,
  libelleAction,
  onConfirmer,
  enCours,
}: {
  ouvert: boolean;
  onChange: (o: boolean) => void;
  titre: string;
  message: ReactNode;
  libelleAction: string;
  onConfirmer: () => void;
  enCours?: boolean;
}) {
  const retourFocus = useRetourFocus();
  return (
    <Dialog.Root open={ouvert} onOpenChange={onChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-[color-mix(in_srgb,var(--ink)_35%,transparent)]" />
        <Dialog.Content
          {...retourFocus}
          className="carte fixed left-1/2 top-1/2 z-50 w-[calc(100%-32px)] max-w-md -translate-x-1/2 -translate-y-1/2 p-6"
        >
          <Dialog.Title className="text-md font-bold text-ink">{titre}</Dialog.Title>
          <Dialog.Description className="mt-2 text-base text-ink-2">{message}</Dialog.Description>
          <div className="mt-6 flex justify-end gap-2">
            <Dialog.Close asChild>
              <Bouton>Annuler</Bouton>
            </Dialog.Close>
            <Bouton variante="primaire" onClick={onConfirmer} disabled={enCours}>
              {enCours ? "En cours…" : libelleAction}
            </Bouton>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

/** Retour d'une action (succès ou erreur), annoncé aux lecteurs d'écran. */
export function Retour({ ok, children }: { ok: boolean; children: ReactNode }) {
  return (
    <p
      role="status"
      aria-live="polite"
      className={cn(
        "rounded-sm border px-3 py-2 text-base",
        ok
          ? "border-border bg-zebra text-ink"
          : "border-[var(--etat-critique)] bg-surface font-bold text-ink",
      )}
    >
      {children}
    </p>
  );
}
