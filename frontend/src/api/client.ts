/**
 * Client HTTP de l'API /api/v1.
 * Jeton d'accès en mémoire ; jeton de rafraîchissement en sessionStorage (effacé à la fermeture de l'onglet).
 */

const BASE = "/api/v1";
const CLE_REFRESH = "tdb.refresh";

let acces: string | null = null;
let rafraichissementEnCours: Promise<boolean> | null = null;
let surDeconnexion: () => void = () => {};

export class ErreurApi extends Error {
  constructor(
    public statut: number,
    public corps: Record<string, unknown> = {},
  ) {
    super(String(corps.detail ?? `Erreur ${statut}`));
  }
  get code(): string | undefined {
    return this.corps.code as string | undefined;
  }
}

function lireRefresh(): string | null {
  try {
    return sessionStorage.getItem(CLE_REFRESH);
  } catch {
    return null;
  }
}

export function definirJetons(jetons: { access: string; refresh: string } | null) {
  acces = jetons?.access ?? null;
  try {
    if (jetons) sessionStorage.setItem(CLE_REFRESH, jetons.refresh);
    else sessionStorage.removeItem(CLE_REFRESH);
  } catch {
    /* stockage indisponible : la session reste en mémoire */
  }
}

export function aUneSession(): boolean {
  return Boolean(acces || lireRefresh());
}

export function surSessionExpiree(fn: () => void) {
  surDeconnexion = fn;
}

async function rafraichir(): Promise<boolean> {
  const refresh = lireRefresh();
  if (!refresh) return false;
  rafraichissementEnCours ??= fetch(`${BASE}/auth/rafraichir/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  })
    .then(async (r) => {
      if (!r.ok) return false;
      const j = await r.json();
      definirJetons({ access: j.access, refresh: j.refresh ?? refresh });
      return true;
    })
    .catch(() => false)
    .finally(() => {
      rafraichissementEnCours = null;
    });
  return rafraichissementEnCours;
}

export function construireUrl(chemin: string, params?: Record<string, string | number | undefined | null>) {
  const q = new URLSearchParams();
  Object.entries(params ?? {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") q.set(k, String(v));
  });
  const s = q.toString();
  return `${BASE}${chemin}${s ? `?${s}` : ""}`;
}

export async function requete<T>(url: string, init: RequestInit = {}, reessai = true): Promise<T> {
  if (!acces && lireRefresh()) await rafraichir();
  const headers = new Headers(init.headers);
  if (acces) headers.set("Authorization", `Bearer ${acces}`);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const r = await fetch(url, { ...init, headers });
  if (r.status === 401 && reessai && !url.includes("/auth/connexion/")) {
    if (await rafraichir()) return requete<T>(url, init, false);
    definirJetons(null);
    surDeconnexion();
  }
  const texte = await r.text();
  const corps = texte ? JSON.parse(texte) : {};
  if (!r.ok) throw new ErreurApi(r.status, corps);
  return corps as T;
}

export const api = {
  get: <T>(chemin: string, params?: Record<string, string | number | undefined | null>) =>
    requete<T>(construireUrl(chemin, params)),
  post: <T>(chemin: string, corps?: unknown) =>
    requete<T>(construireUrl(chemin), {
      method: "POST",
      body: corps instanceof FormData ? corps : JSON.stringify(corps ?? {}),
    }),
  patch: <T>(chemin: string, corps: unknown) =>
    requete<T>(construireUrl(chemin), { method: "PATCH", body: JSON.stringify(corps) }),
  supprimer: (chemin: string) => requete<void>(construireUrl(chemin), { method: "DELETE" }),
};

/** Télécharge un fichier protégé (en-tête d'authentification) sous le nom donné par le serveur. */
export async function telecharger(
  chemin: string,
  params?: Record<string, string | number | undefined | null>,
) {
  if (!acces && lireRefresh()) await rafraichir();
  const r = await fetch(construireUrl(chemin, params), {
    headers: acces ? { Authorization: `Bearer ${acces}` } : {},
  });
  if (!r.ok) throw new ErreurApi(r.status, await r.json().catch(() => ({})));
  const disposition = r.headers.get("Content-Disposition") ?? "";
  const encode = /filename\*=utf-8''([^;]+)/i.exec(disposition)?.[1];
  const nom = encode
    ? decodeURIComponent(encode)
    : (/filename="([^"]+)"/.exec(disposition)?.[1] ?? "export.xlsx");
  const url = URL.createObjectURL(await r.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = nom;
  a.click();
  URL.revokeObjectURL(url);
}
