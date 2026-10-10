import type { Config } from "tailwindcss";

/** Toutes les couleurs pointent vers les jetons de src/theme/tokens.css (aucune valeur en dur). */
const jeton = (nom: string) => `var(--${nom})`;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    // Échelle typographique fixe : 12 / 13 / 14 / 16 / 20 / 28 px.
    fontSize: {
      xs: ["12px", { lineHeight: "16px" }],
      sm: ["13px", { lineHeight: "18px" }],
      base: ["14px", { lineHeight: "20px" }],
      md: ["16px", { lineHeight: "22px" }],
      lg: ["20px", { lineHeight: "26px" }],
      xl: ["28px", { lineHeight: "34px" }],
    },
    // Espacements : échelle Tailwind par défaut (pas de 4 px) ; la grille de page utilise 8 / 12 / 16 / 24 / 32 px.
    borderRadius: { none: "0", sm: "3px", DEFAULT: "var(--radius)", full: "9999px" },
    extend: {
      fontFamily: {
        sans: ["Arial", '"Helvetica Neue"', "Helvetica", "sans-serif"],
        titre: ['"Source Serif 4"', "Arial", "sans-serif"],
      },
      colors: {
        navy: jeton("navy"),
        gold: jeton("gold"),
        "gold-tint": jeton("gold-tint"),
        bg: jeton("bg"),
        surface: jeton("surface"),
        ink: jeton("ink"),
        "ink-2": jeton("ink-2"),
        "ink-3": jeton("ink-3"),
        border: jeton("border"),
        grid: jeton("grid"),
        zebra: jeton("zebra"),
        hover: jeton("hover"),
        "on-navy": jeton("on-navy"),
        "on-navy-2": jeton("on-navy-2"),
        "champ-navy": jeton("champ-navy"),
        etat: {
          bon: jeton("etat-bon"),
          vigilance: jeton("etat-vigilance"),
          serieux: jeton("etat-serieux"),
          critique: jeton("etat-critique"),
        },
        "sur-etat": jeton("sur-etat"),
        // Thème shadcn/ui
        background: jeton("background"),
        foreground: jeton("foreground"),
        primary: { DEFAULT: jeton("primary"), foreground: jeton("primary-foreground") },
        muted: { DEFAULT: jeton("muted"), foreground: jeton("muted-foreground") },
        accent: { DEFAULT: jeton("accent"), foreground: jeton("accent-foreground") },
        ring: jeton("ring"),
        input: jeton("input"),
      },
      maxWidth: { page: "1280px" },
      letterSpacing: { etiquette: "0.06em" },
    },
  },
  plugins: [],
} satisfies Config;
