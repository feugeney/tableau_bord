import { useState, type FormEvent, type ReactNode } from "react";

import { api, ErreurApi } from "@/api/client";
import { Armoiries, MiniDrapeau } from "@/components/cadre/Signature";
import { Bouton } from "@/components/ui/primitives";
import { useAuth } from "@/hooks/useAuth";
import { PLATEFORME } from "@/lib/identite";

const CHAMP =
  "mt-1 min-h-11 w-full rounded-sm border border-border bg-surface px-3 text-md text-ink placeholder:text-ink-3";

/** Écran officiel : colonne bleu marine (armoiries, devise, filet tricolore vertical), formulaire à droite. */
function EcranOfficiel({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-bg md:flex-row">
      <aside className="relative flex bg-navy text-on-navy md:w-[42%] md:max-w-[520px]">
        <div className="flex flex-1 flex-col justify-between gap-8 px-8 py-8 md:px-12 md:py-12">
          <div className="flex items-center gap-4 md:flex-col md:items-start">
            <Armoiries taille={72} />
            <div>
              <p className="flex items-center gap-2 text-sm font-bold uppercase tracking-etiquette">
                République de Guinée <MiniDrapeau />
              </p>
              <p className="text-sm text-on-navy-2">{PLATEFORME.devise}</p>
            </div>
          </div>
          <div>
            <p className="text-sm text-on-navy-2">{PLATEFORME.ministere}</p>
            <h1 className="mt-2 font-titre text-xl font-semibold leading-tight">{PLATEFORME.nom}</h1>
          </div>
          <p className="hidden text-sm text-on-navy-2 md:block">
            Direction nationale des systèmes d'information
          </p>
        </div>
        <div aria-hidden className="filet-tricolore-vertical hidden md:block" />
      </aside>
      <div aria-hidden className="filet-tricolore md:hidden" />
      <main className="flex flex-1 items-center justify-center px-4 py-10">{children}</main>
    </div>
  );
}

export function Connexion() {
  const { connecter } = useAuth();
  const [identifiant, setIdentifiant] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [codeOtp, setCodeOtp] = useState("");
  const [demandeOtp, setDemandeOtp] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [envoi, setEnvoi] = useState(false);

  async function soumettre(e: FormEvent) {
    e.preventDefault();
    setErreur(null);
    setEnvoi(true);
    try {
      await connecter(identifiant, motDePasse, demandeOtp ? codeOtp : undefined);
    } catch (err) {
      if (err instanceof ErreurApi && err.code === "otp_requis") setDemandeOtp(true);
      else if (err instanceof ErreurApi && err.statut === 401)
        setErreur("Identifiant ou mot de passe incorrect. Vérifiez la saisie, puis réessayez.");
      else setErreur("Connexion impossible pour le moment. Vérifiez votre accès au réseau du ministère.");
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <EcranOfficiel>
      <form
        onSubmit={soumettre}
        className="w-full max-w-sm"
        aria-describedby={erreur ? "erreur-connexion" : undefined}
      >
        <h2 className="text-lg font-bold text-ink">Connexion</h2>
        <p className="mb-6 text-base text-ink-2">Accès réservé aux agents habilités.</p>
        <label htmlFor="identifiant" className="block text-base font-bold text-ink">
          Identifiant
        </label>
        <input
          id="identifiant"
          name="username"
          className={CHAMP}
          value={identifiant}
          onChange={(e) => setIdentifiant(e.target.value)}
          autoComplete="username"
          spellCheck={false}
          required
        />
        <label htmlFor="mot-de-passe" className="mt-4 block text-base font-bold text-ink">
          Mot de passe
        </label>
        <input
          id="mot-de-passe"
          name="password"
          type="password"
          className={CHAMP}
          value={motDePasse}
          onChange={(e) => setMotDePasse(e.target.value)}
          autoComplete="current-password"
          required
        />
        {demandeOtp && (
          <>
            <label htmlFor="code-otp" className="mt-4 block text-base font-bold text-ink">
              Code de vérification
            </label>
            <p className="text-sm text-ink-2">
              6 chiffres affichés par votre application d'authentification.
            </p>
            <input
              id="code-otp"
              name="one-time-code"
              className={CHAMP}
              value={codeOtp}
              onChange={(e) => setCodeOtp(e.target.value)}
              inputMode="numeric"
              autoComplete="one-time-code"
              spellCheck={false}
              pattern="\d{6}"
              placeholder="123456…"
              required
            />
          </>
        )}
        {erreur && (
          <p id="erreur-connexion" role="alert" className="mt-4 text-base font-bold text-ink">
            {erreur}
          </p>
        )}
        <Bouton type="submit" variante="primaire" className="mt-6 min-h-11 w-full text-md" disabled={envoi}>
          {envoi ? "Connexion…" : "Se connecter"}
        </Bouton>
        <p className="mt-6 text-sm text-ink-2">
          Accès depuis le réseau du ministère ou par VPN. Les connexions sont journalisées.
        </p>
      </form>
    </EcranOfficiel>
  );
}

/** Enrôlement obligatoire de la double authentification (profils cabinet et administrateur). */
export function Activer2FA() {
  const { appliquerConnexion, deconnecter } = useAuth();
  const [url, setUrl] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);

  async function demarrer() {
    const r = await api.post<{ otpauth_url: string }>("/auth/2fa/activer/");
    setUrl(r.otpauth_url);
  }
  async function confirmer(e: FormEvent) {
    e.preventDefault();
    try {
      appliquerConnexion(await api.post("/auth/2fa/confirmer/", { code_otp: code }));
    } catch {
      setErreur("Code refusé. Vérifiez l'heure du téléphone, attendez le code suivant, puis réessayez.");
    }
  }
  const secret = url ? new URL(url).searchParams.get("secret") : null;

  return (
    <EcranOfficiel>
      <div className="w-full max-w-md">
        <h2 className="text-lg font-bold text-ink">Activer la double authentification</h2>
        <p className="mb-6 text-base text-ink-2">
          Votre profil donne accès à des données sensibles. Associez une application d'authentification
          (FreeOTP, Google Authenticator, Microsoft Authenticator…) avant de continuer.
        </p>
        {!url ? (
          <Bouton variante="primaire" onClick={demarrer} className="min-h-11">
            Commencer l'activation
          </Bouton>
        ) : (
          <form onSubmit={confirmer} className="flex flex-col gap-3">
            <p className="text-base text-ink">
              Dans l'application, ajoutez un compte « basé sur le temps » avec cette clé :
            </p>
            <code
              translate="no"
              className="break-all rounded-sm border border-border bg-surface p-2 text-base"
            >
              {secret}
            </code>
            <label htmlFor="code-2fa" className="text-base font-bold text-ink">
              Code à 6 chiffres affiché
            </label>
            <input
              id="code-2fa"
              name="one-time-code"
              className={CHAMP}
              value={code}
              onChange={(e) => setCode(e.target.value)}
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="\d{6}"
              required
            />
            {erreur && (
              <p role="alert" className="text-base font-bold text-ink">
                {erreur}
              </p>
            )}
            <Bouton type="submit" variante="primaire" className="min-h-11">
              Activer la double authentification
            </Bouton>
          </form>
        )}
        <Bouton variante="discret" className="mt-6" onClick={deconnecter}>
          Se déconnecter
        </Bouton>
      </div>
    </EcranOfficiel>
  );
}
