import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

/** Mode présentation (réunion de cabinet) : plein écran, navigation masquée, indicateurs agrandis. */
const Contexte = createContext<{ actif: boolean; basculer: () => void }>({
  actif: false,
  basculer: () => {},
});

export function PresentationProvider({ children }: { children: ReactNode }) {
  const [actif, setActif] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle("presentation", actif);
  }, [actif]);

  useEffect(() => {
    // Quitter le plein écran (Échap) quitte aussi le mode présentation.
    const surChangement = () => {
      if (!document.fullscreenElement) setActif(false);
    };
    document.addEventListener("fullscreenchange", surChangement);
    return () => document.removeEventListener("fullscreenchange", surChangement);
  }, []);

  const basculer = useCallback(() => {
    setActif((a) => {
      const suivant = !a;
      if (suivant) document.documentElement.requestFullscreen?.().catch(() => {});
      else if (document.fullscreenElement) document.exitFullscreen?.().catch(() => {});
      return suivant;
    });
  }, []);

  return <Contexte.Provider value={{ actif, basculer }}>{children}</Contexte.Provider>;
}

export const usePresentation = () => useContext(Contexte);
