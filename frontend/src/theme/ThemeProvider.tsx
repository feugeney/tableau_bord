import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

type Theme = "clair" | "sombre";
const CLE = "tdb.theme";

const Contexte = createContext<{ theme: Theme; basculer: () => void }>({
  theme: "clair",
  basculer: () => {},
});

function initial(): Theme {
  try {
    const t = localStorage.getItem(CLE);
    if (t === "clair" || t === "sombre") return t;
  } catch {
    /* stockage indisponible */
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "sombre" : "clair";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(initial);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "sombre");
    // La barre du navigateur mobile prend la couleur de l'en-tête (jeton --navy du thème actif).
    const navy = getComputedStyle(document.documentElement).getPropertyValue("--navy").trim();
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", navy);
    try {
      localStorage.setItem(CLE, theme);
    } catch {
      /* préférence non mémorisée */
    }
  }, [theme]);

  const basculer = useCallback(() => setTheme((t) => (t === "clair" ? "sombre" : "clair")), []);
  return <Contexte.Provider value={{ theme, basculer }}>{children}</Contexte.Provider>;
}

export const useTheme = () => useContext(Contexte);
