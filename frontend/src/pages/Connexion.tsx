import {
  ArrowLeft,
  Check,
  CircleAlert,
  Copy,
  Eye,
  EyeOff,
  Fingerprint,
  LoaderCircle,
  UserRound,
} from "lucide-react";
import { useEffect, useRef, useState, type FormEvent, type ReactNode, type RefObject } from "react";

import { api, ErreurApi } from "@/api/client";
import sceauMef from "@/assets/sceau-mef.png";
import { FiletTricolore } from "@/components/cadre/Signature";
import { useAuth } from "@/hooks/useAuth";
import { PLATEFORME } from "@/lib/identite";

import "@/theme/connexion.css";

// Graphique décoratif (aucune donnée) : courbe de tendance, aire et barres, dessinés au chargement.
const COURBE =
  "M0,250 C120,240 180,200 260,210 S400,170 480,182 S620,124 720,140 S860,98 960,112 S1100,62 1200,76 S1360,42 1440,34";
const BARRES = [
  262, 236, 250, 214, 226, 196, 204, 172, 186, 158, 166, 138, 150, 124, 132, 110, 118, 96, 104, 84, 92, 76,
  70, 62,
];

function GraphiqueDecoratif() {
  return (
    <svg
      className="auth-graphique"
      viewBox="0 0 1440 320"
      preserveAspectRatio="none"
      aria-hidden
      focusable="false"
    >
      {[80, 160, 240].map((y) => (
        <line key={y} className="auth-graphique-grille" x1="0" x2="1440" y1={y} y2={y} />
      ))}
      {BARRES.map((y, i) => (
        <rect
          key={i}
          className="auth-graphique-barre"
          x={i * 60 + 21}
          y={y}
          width="18"
          height={320 - y}
          style={{ animationDelay: `${0.4 + i * 0.04}s` }}
        />
      ))}
      <path className="auth-graphique-aire" d={`${COURBE} L1440,320 L0,320 Z`} />
      <path className="auth-graphique-courbe" d={COURBE} pathLength={1} vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

function EcranOfficiel({ children }: { children: ReactNode }) {
  return (
    <div className="auth-page">
      <FiletTricolore />
      <GraphiqueDecoratif />
      <span className="auth-graphique-point" aria-hidden />
      <header className="auth-entete-page">
        <p className="auth-republique">République de Guinée</p>
        <p className="auth-sous-titre">{PLATEFORME.ministere}</p>
        <h1 className="auth-produit">{PLATEFORME.nom}</h1>
      </header>
      <div className="auth-contenu">
        <main className="auth-carte" id="connexion">
          <div className="auth-identite">
            <img
              src={sceauMef}
              width={88}
              height={88}
              alt="Sceau du Ministère de l’Économie et des Finances"
              className="auth-sceau"
            />
          </div>
          {children}
        </main>
      </div>
      <footer className="auth-pied">
        © {new Date().getFullYear()} République de Guinée · Service de modernisation des systèmes
        d’information
      </footer>
    </div>
  );
}

function EnteteCarte({ titre, children }: { titre: string; children?: ReactNode }) {
  return (
    <header className="auth-entete">
      <h2>{titre}</h2>
      {children && <p>{children}</p>}
    </header>
  );
}

function ErreurConnexion({ message, reference }: { message: string; reference?: RefObject<HTMLDivElement> }) {
  return (
    <div ref={reference} id="erreur-connexion" role="alert" tabIndex={-1} className="auth-erreur">
      <CircleAlert size={18} aria-hidden />
      <p>{message}</p>
    </div>
  );
}

export function Connexion() {
  const { connecter } = useAuth();
  const [identifiant, setIdentifiant] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [visible, setVisible] = useState(false);
  const [majuscules, setMajuscules] = useState(false);
  const [codeOtp, setCodeOtp] = useState("");
  const [demandeOtp, setDemandeOtp] = useState(false);
  const [otpInvalide, setOtpInvalide] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [envoi, setEnvoi] = useState(false);
  const identifiantRef = useRef<HTMLInputElement>(null);
  const otpRef = useRef<HTMLInputElement>(null);
  const erreurRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (demandeOtp) otpRef.current?.focus();
  }, [demandeOtp]);
  useEffect(() => {
    if (erreur) {
      if (otpInvalide) otpRef.current?.focus();
      else erreurRef.current?.focus();
    }
  }, [erreur, otpInvalide]);

  function changerCompte() {
    setDemandeOtp(false);
    setCodeOtp("");
    setOtpInvalide(false);
    setMotDePasse("");
    setVisible(false);
    setErreur(null);
    requestAnimationFrame(() => identifiantRef.current?.focus());
  }

  async function soumettre(e: FormEvent) {
    e.preventDefault();
    if (envoi) return;
    setErreur(null);
    setEnvoi(true);
    setOtpInvalide(false);
    try {
      await connecter(identifiant.trim(), motDePasse, demandeOtp ? codeOtp : undefined);
    } catch (err) {
      if (err instanceof ErreurApi && err.code === "otp_requis") {
        setCodeOtp("");
        setDemandeOtp(true);
      } else if (err instanceof ErreurApi && err.code === "otp_invalide") {
        setCodeOtp("");
        setOtpInvalide(true);
        setErreur(
          "Ce code est incorrect ou a expiré. Saisissez le code actuel de votre application d’authentification.",
        );
      } else if (err instanceof ErreurApi && err.statut === 429) {
        setErreur("Trop de tentatives de connexion. Patientez quelques instants avant de réessayer.");
      } else if (err instanceof ErreurApi && err.statut === 401) {
        if (demandeOtp) setDemandeOtp(false);
        setErreur("Identifiant ou mot de passe incorrect. Vérifiez vos informations, puis réessayez.");
      } else {
        setErreur(
          "Connexion momentanément indisponible. Vérifiez votre accès au réseau du ministère, puis réessayez.",
        );
      }
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <EcranOfficiel>
      {demandeOtp && (
        <EnteteCarte titre="Vérification en deux étapes">
          Une dernière étape pour sécuriser votre accès.
        </EnteteCarte>
      )}
      <form
        onSubmit={soumettre}
        aria-label="Connexion à la plateforme"
        aria-busy={envoi}
        aria-describedby={erreur ? "erreur-connexion" : undefined}
      >
        <fieldset disabled={envoi} className="auth-fields">
          {demandeOtp ? (
            <>
              <div className="auth-compte">
                <span className="auth-compte-icon">
                  <UserRound size={20} aria-hidden />
                </span>
                <div>
                  <span>Compte à vérifier</span>
                  <strong>{identifiant.trim()}</strong>
                </div>
                <button type="button" onClick={changerCompte}>
                  Modifier
                </button>
              </div>
              <label htmlFor="code-otp" className="auth-label">
                Code de vérification
              </label>
              <p className="auth-field-help" id="aide-otp">
                Saisissez les 6 chiffres affichés par votre application d’authentification.
              </p>
              <div className="auth-input-wrap">
                <input
                  ref={otpRef}
                  id="code-otp"
                  name="one-time-code"
                  className="auth-input auth-input-otp"
                  value={codeOtp}
                  onChange={(e) => setCodeOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={6}
                  pattern="\d{6}"
                  aria-describedby={otpInvalide ? "aide-otp erreur-connexion" : "aide-otp"}
                  aria-invalid={otpInvalide || undefined}
                  spellCheck={false}
                  required
                />
              </div>
            </>
          ) : (
            <>
              <label htmlFor="identifiant" className="auth-label">
                Identifiant
              </label>
              <div className="auth-input-wrap">
                <input
                  ref={identifiantRef}
                  id="identifiant"
                  name="username"
                  className="auth-input"
                  value={identifiant}
                  onChange={(e) => setIdentifiant(e.target.value)}
                  autoComplete="username"
                  autoCapitalize="none"
                  spellCheck={false}
                  required
                />
              </div>
              <label htmlFor="mot-de-passe" className="auth-label auth-label-password">
                Mot de passe
              </label>
              <div className="auth-input-wrap">
                <input
                  id="mot-de-passe"
                  name="password"
                  type={visible ? "text" : "password"}
                  className="auth-input auth-input-password"
                  value={motDePasse}
                  onChange={(e) => setMotDePasse(e.target.value)}
                  autoComplete="current-password"
                  onKeyDown={(e) => setMajuscules(e.getModifierState("CapsLock"))}
                  onKeyUp={(e) => setMajuscules(e.getModifierState("CapsLock"))}
                  onBlur={() => setMajuscules(false)}
                  aria-describedby={majuscules ? "aide-majuscules" : undefined}
                  required
                />
                <button
                  className="auth-password-toggle"
                  type="button"
                  aria-label={visible ? "Masquer le mot de passe" : "Afficher le mot de passe"}
                  aria-pressed={visible}
                  aria-controls="mot-de-passe"
                  onClick={() => setVisible((v) => !v)}
                >
                  {visible ? <EyeOff size={19} aria-hidden /> : <Eye size={19} aria-hidden />}
                </button>
              </div>
              {majuscules && (
                <p id="aide-majuscules" className="auth-field-help" role="status">
                  Le verrouillage des majuscules est activé.
                </p>
              )}
            </>
          )}
          {erreur && <ErreurConnexion message={erreur} reference={erreurRef} />}
          <button className="auth-submit" type="submit" disabled={envoi}>
            {envoi && <LoaderCircle className="auth-spinner" size={18} aria-hidden />}
            <span>
              {envoi ? "Connexion en cours…" : demandeOtp ? "Vérifier et se connecter" : "Se connecter"}
            </span>
          </button>
        </fieldset>
      </form>
    </EcranOfficiel>
  );
}

export function Activer2FA() {
  const { appliquerConnexion, deconnecter } = useAuth();
  const [url, setUrl] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);
  const [envoi, setEnvoi] = useState(false);
  const [copie, setCopie] = useState(false);
  const codeRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (url) codeRef.current?.focus();
  }, [url]);

  async function demarrer() {
    setEnvoi(true);
    setErreur(null);
    try {
      const r = await api.post<{ otpauth_url: string }>("/auth/2fa/activer/");
      setUrl(r.otpauth_url);
    } catch {
      setErreur("L’activation n’a pas pu démarrer. Veuillez réessayer.");
    } finally {
      setEnvoi(false);
    }
  }
  async function confirmer(e: FormEvent) {
    e.preventDefault();
    if (envoi) return;
    setEnvoi(true);
    setErreur(null);
    try {
      appliquerConnexion(await api.post("/auth/2fa/confirmer/", { code_otp: code }));
    } catch {
      setErreur(
        "Code refusé. Vérifiez l’heure de votre téléphone et saisissez le code actuel de votre application.",
      );
    } finally {
      setEnvoi(false);
    }
  }
  const secret = url ? new URL(url).searchParams.get("secret") : null;

  async function copier() {
    if (!secret) return;
    try {
      await navigator.clipboard.writeText(secret);
      setCopie(true);
    } catch {
      setErreur("La copie automatique est indisponible. Sélectionnez la clé pour la copier manuellement.");
    }
  }

  return (
    <EcranOfficiel>
      <EnteteCarte titre="Protégez votre compte">
        Activez la vérification en deux étapes pour accéder aux données de votre périmètre.
      </EnteteCarte>
      <div className="auth-enrolment-intro">
        <Fingerprint size={26} strokeWidth={1.4} aria-hidden />
        <p>Un mot de passe et un code temporaire : une protection supplémentaire pour vos accès.</p>
      </div>
      {!url ? (
        <button type="button" className="auth-submit" onClick={demarrer} disabled={envoi}>
          {envoi && <LoaderCircle size={18} className="auth-spinner" aria-hidden />}
          <span>{envoi ? "Préparation…" : "Configurer la vérification"}</span>
        </button>
      ) : (
        <form onSubmit={confirmer} aria-busy={envoi}>
          <fieldset className="auth-fields" disabled={envoi}>
            <p className="auth-etape">01 · Associer votre application</p>
            <p className="auth-field-help">
              Ajoutez un compte basé sur le temps dans votre application d’authentification, puis renseignez
              cette clé.
            </p>
            <div className="auth-secret">
              <code translate="no">{secret}</code>
              <button type="button" onClick={copier} aria-label="Copier la clé de configuration">
                {copie ? <Check size={18} aria-hidden /> : <Copy size={18} aria-hidden />}
              </button>
            </div>
            {copie && (
              <p role="status" className="auth-field-help">
                Clé copiée.
              </p>
            )}
            <p className="auth-etape">02 · Confirmer l’association</p>
            <label htmlFor="code-2fa" className="auth-label">
              Code à 6 chiffres
            </label>
            <div className="auth-input-wrap">
              <input
                ref={codeRef}
                id="code-2fa"
                name="one-time-code"
                className="auth-input auth-input-otp"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="\d{6}"
                maxLength={6}
                required
              />
            </div>
            <button type="submit" className="auth-submit" disabled={envoi}>
              {envoi && <LoaderCircle size={18} className="auth-spinner" aria-hidden />}
              <span>{envoi ? "Vérification…" : "Activer et accéder à mon espace"}</span>
            </button>
          </fieldset>
        </form>
      )}
      {erreur && <ErreurConnexion message={erreur} />}
      <button type="button" className="auth-retour" onClick={deconnecter} disabled={envoi}>
        <ArrowLeft size={16} aria-hidden /> Retour à la connexion
      </button>
    </EcranOfficiel>
  );
}
