import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { aUneSession, api, definirJetons, surSessionExpiree } from "@/api/client";
import type { Utilisateur } from "@/api/types";

interface ReponseConnexion {
  access: string;
  refresh: string;
  utilisateur: Utilisateur;
}

interface ContexteAuth {
  utilisateur: Utilisateur | null;
  chargement: boolean;
  connecter: (identifiant: string, motDePasse: string, codeOtp?: string) => Promise<void>;
  deconnecter: () => void;
  appliquerConnexion: (r: ReponseConnexion) => void;
}

const Contexte = createContext<ContexteAuth | null>(null);

// Vrai juste après une connexion : le cadre place alors le focus sur le contenu principal.
let connexionRecente = false;
export function consommerConnexionRecente(): boolean {
  const v = connexionRecente;
  connexionRecente = false;
  return v;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [utilisateur, setUtilisateur] = useState<Utilisateur | null>(null);
  const [chargement, setChargement] = useState(aUneSession());
  const client = useQueryClient();

  const deconnecter = useCallback(() => {
    definirJetons(null);
    setUtilisateur(null);
    client.clear();
  }, [client]);

  useEffect(() => {
    surSessionExpiree(() => setUtilisateur(null));
    if (!aUneSession()) return;
    api
      .get<Utilisateur>("/auth/moi/")
      .then(setUtilisateur)
      .catch(() => definirJetons(null))
      .finally(() => setChargement(false));
  }, []);

  const appliquerConnexion = useCallback((r: ReponseConnexion) => {
    connexionRecente = true;
    definirJetons({ access: r.access, refresh: r.refresh });
    setUtilisateur(r.utilisateur);
  }, []);

  const connecter = useCallback(
    async (identifiant: string, motDePasse: string, codeOtp?: string) => {
      const r = await api.post<ReponseConnexion>("/auth/connexion/", {
        identifiant,
        mot_de_passe: motDePasse,
        code_otp: codeOtp,
      });
      appliquerConnexion(r);
    },
    [appliquerConnexion],
  );

  const valeur = useMemo(
    () => ({ utilisateur, chargement, connecter, deconnecter, appliquerConnexion }),
    [utilisateur, chargement, connecter, deconnecter, appliquerConnexion],
  );
  return <Contexte.Provider value={valeur}>{children}</Contexte.Provider>;
}

export function useAuth(): ContexteAuth {
  const c = useContext(Contexte);
  if (!c) throw new Error("useAuth hors de AuthProvider");
  return c;
}
