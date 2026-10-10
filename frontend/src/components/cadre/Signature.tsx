/** Signature République de Guinée : armoiries, mini-drapeau, filet tricolore (voir theme/signature.css). */
import { cn } from "@/lib/utils";

// Armoiries officielles déposées par le ministère dans src/assets (aucune armoirie dessinée ici).
const fichiers = import.meta.glob<string>("../../assets/armoiries.{svg,png}", {
  eager: true,
  query: "?url",
  import: "default",
});
const ARMOIRIES: string | undefined = Object.values(fichiers)[0];

/** Mention obligatoire tant que le fichier provisoire (Wikimedia Commons, CC BY-SA 3.0) est en place.
 *  À vider lorsque le fichier officiel fourni par le ministère le remplace (voir src/assets/LISEZMOI.md). */
export const CREDIT_ARMOIRIES =
  "Armoiries : version Wikimedia Commons (Turn685, d'après Ttzavaras), licence CC BY-SA 3.0";

export function Armoiries({ taille = 56, className }: { taille?: number; className?: string }) {
  if (ARMOIRIES) {
    return (
      <img
        src={ARMOIRIES}
        width={taille}
        height={taille}
        style={{ width: taille, height: taille }}
        alt="Armoiries de la République de Guinée"
        className={cn("shrink-0 object-contain", className)}
      />
    );
  }
  return (
    <span
      role="img"
      aria-label="Emplacement des armoiries officielles (fichier à fournir)"
      title="Déposer src/assets/armoiries.svg"
      style={{ width: taille, height: taille }}
      className={cn("block shrink-0 rounded-sm border border-dashed border-on-navy-2 opacity-60", className)}
    />
  );
}

export function MiniDrapeau({ className }: { className?: string }) {
  return <span aria-hidden className={cn("mini-drapeau", className)} />;
}

export function FiletTricolore({ fin = false, className }: { fin?: boolean; className?: string }) {
  return <div aria-hidden className={cn("filet-tricolore", fin && "filet-tricolore-fin", className)} />;
}
