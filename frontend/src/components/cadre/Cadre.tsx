import {
  CalendarDays,
  ListTree,
  Telescope,
  LogOut,
  Maximize2,
  Minimize2,
  Moon,
  Printer,
  Settings,
  Sun,
  UserRound,
} from "lucide-react";
import { Suspense, useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

import { Squelette } from "@/components/ui/primitives";
import { Sheet } from "@/components/ui/sheet";
import { consommerConnexionRecente, useAuth } from "@/hooks/useAuth";
import { useFiltres } from "@/hooks/useFiltres";
import { usePresentation } from "@/hooks/usePresentation";
import { useSituation } from "@/hooks/useSituation";
import { dateFr } from "@/lib/format";
import { PLATEFORME } from "@/lib/identite";
import { ONGLETS, ongletCourant } from "@/lib/onglets";
import { cn } from "@/lib/utils";
import { useTheme } from "@/theme/ThemeProvider";

import { Armoiries, CREDIT_ARMOIRIES, FiletTricolore, MiniDrapeau } from "./Signature";

const SELECT = "h-7 cursor-pointer rounded-full border-0 px-1.5 text-sm font-bold text-on-navy";

function Separateur() {
  return <span aria-hidden className="hidden h-5 w-px bg-on-navy-2 opacity-40 sm:block" />;
}

/** Période affichée : exercice, date de situation et unité, regroupés dans une seule pastille. */
function Periode() {
  const { definir } = useFiltres();
  const { exercices, exercice, dates, dateSituation } = useSituation();
  return (
    <div
      role="group"
      aria-label="Période affichée"
      className="flex flex-wrap items-center gap-x-2 gap-y-1 rounded border border-champ-navy bg-champ-navy px-3 py-1 lg:h-10 lg:flex-nowrap lg:rounded-full lg:py-0 lg:pl-3.5 lg:pr-2"
    >
      <CalendarDays className="h-4 w-4 shrink-0 text-gold" aria-hidden />
      <label className="flex items-center gap-1">
        <span className="text-xs text-on-navy-2">Exercice</span>
        <select
          className={SELECT}
          style={{ backgroundColor: "var(--champ-navy)", color: "var(--on-navy)" }}
          value={exercice ?? ""}
          onChange={(e) => definir({ exercice: e.target.value })}
          disabled={!exercices.length}
        >
          {!exercices.length && <option value="">—</option>}
          {exercices.map((e) => (
            <option key={e.exercice} value={e.exercice}>
              {e.exercice}
            </option>
          ))}
        </select>
      </label>
      <Separateur />
      <label className="flex items-center gap-1">
        <span className="whitespace-nowrap text-xs text-on-navy-2">Situation au</span>
        <select
          className={SELECT}
          style={{ backgroundColor: "var(--champ-navy)", color: "var(--on-navy)" }}
          value={dateSituation ?? ""}
          onChange={(e) => definir({ date_situation: e.target.value })}
          disabled={!dates.length}
        >
          {!dates.length && <option value="">—</option>}
          {dates.map((d) => (
            <option key={d} value={d}>
              {dateFr(d)}
            </option>
          ))}
        </select>
      </label>
      <Separateur />
      <span className="whitespace-nowrap text-xs text-on-navy-2">Montants en Mds GNF</span>
    </div>
  );
}

function initiales(nom?: string) {
  return (nom ?? "")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((m) => m[0].toUpperCase())
    .join("");
}

function Profil() {
  const { utilisateur, deconnecter } = useAuth();
  const sigle = initiales(utilisateur?.nom);
  return (
    <details className="group relative">
      <summary
        className="flex cursor-pointer list-none items-center gap-2 rounded-full p-1 text-sm text-on-navy hover:bg-champ-navy 2xl:pr-3 [&::-webkit-details-marker]:hidden"
        aria-label={`Profil : ${utilisateur?.nom}`}
      >
        <span
          aria-hidden
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-on-navy text-xs font-bold text-navy ring-2 ring-gold"
        >
          {sigle || <UserRound className="h-4 w-4" />}
        </span>
        <span className="hidden min-w-0 flex-col text-left leading-tight 2xl:flex">
          <span className="max-w-[10rem] truncate font-bold">{utilisateur?.nom}</span>
          <span className="max-w-[10rem] truncate text-xs text-on-navy-2">{utilisateur?.role_libelle}</span>
        </span>
      </summary>
      <div className="carte absolute right-0 z-50 mt-2 w-64 p-3 text-ink">
        <p className="font-bold">{utilisateur?.nom}</p>
        <p className="text-sm text-ink-2">{utilisateur?.role_libelle}</p>
        {utilisateur?.structure && <p className="text-sm text-ink-2">{utilisateur.structure}</p>}
        {utilisateur?.peut_explorer && (
          <Link
            to="/exploration"
            onClick={(e) => e.currentTarget.closest("details")?.removeAttribute("open")}
            className="mt-3 flex items-center gap-2 rounded-sm px-2 py-1 text-sm font-bold text-ink hover:bg-hover"
          >
            <Telescope className="h-4 w-4" aria-hidden /> Exploration des données
          </Link>
        )}
        {utilisateur?.est_admin && (
          <Link
            to="/administration"
            onClick={(e) => e.currentTarget.closest("details")?.removeAttribute("open")}
            className="mt-1 flex items-center gap-2 rounded-sm px-2 py-1 text-sm font-bold text-ink hover:bg-hover"
          >
            <Settings className="h-4 w-4" aria-hidden /> Administration de l'entrepôt
          </Link>
        )}
        <button
          type="button"
          onClick={deconnecter}
          className="mt-1 flex w-full items-center gap-2 rounded-sm px-2 py-1 text-sm font-bold text-ink hover:bg-hover"
        >
          <LogOut className="h-4 w-4" aria-hidden /> Se déconnecter
        </button>
      </div>
    </details>
  );
}

/** Armoiries, République de Guinée, ministère et nom de la plateforme. */
function Identite({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex min-w-0 items-center gap-3 lg:gap-4">
      <Armoiries taille={compact ? 40 : 52} />
      <div className="min-w-0">
        <p className="flex min-w-0 items-center gap-2 text-xs text-on-navy-2">
          <span className="whitespace-nowrap font-bold uppercase tracking-etiquette text-on-navy">
            République de Guinée
          </span>
          <MiniDrapeau className="shrink-0" />
          <span className="hidden truncate xl:inline">{PLATEFORME.ministere}</span>
        </p>
        <p
          className={cn(
            "mt-0.5 font-titre font-semibold text-on-navy",
            compact ? "text-md leading-tight" : "truncate text-lg",
          )}
        >
          {compact ? PLATEFORME.nomCourt : PLATEFORME.nom}
        </p>
      </div>
    </div>
  );
}

function BoutonTheme() {
  const { theme, basculer } = useTheme();
  return (
    <button
      type="button"
      onClick={basculer}
      className="flex h-9 w-9 items-center justify-center rounded-full text-on-navy hover:bg-champ-navy"
      aria-label={theme === "clair" ? "Passer au thème sombre" : "Passer au thème clair"}
    >
      {theme === "clair" ? <Moon className="h-4 w-4" aria-hidden /> : <Sun className="h-4 w-4" aria-hidden />}
    </button>
  );
}

function EnTete() {
  return (
    <header className="sans-impression bg-navy text-on-navy">
      {/* Ordinateur et tablette : une seule ligne, 80 px + filet 4 px. */}
      <div className="mx-auto hidden h-20 max-w-page items-center justify-between gap-6 px-6 lg:flex">
        <Identite />
        <div className="flex shrink-0 items-center gap-2">
          <Periode />
          <BoutonTheme />
          <Profil />
        </div>
      </div>
      {/* Mobile et petite tablette : identité et profil, puis période. */}
      <div className="flex flex-col gap-3 px-4 py-3 lg:hidden">
        <div className="flex items-center justify-between gap-3">
          <Identite compact />
          <div className="flex shrink-0 items-center gap-1">
            <BoutonTheme />
            <Profil />
          </div>
        </div>
        <Periode />
      </div>
      <FiletTricolore />
    </header>
  );
}

function Navigation({ onSommaire }: { onSommaire: () => void }) {
  const { utilisateur } = useAuth();
  const { global } = useFiltres();
  const { actif, basculer } = usePresentation();
  const onglets = ONGLETS.filter((o) => utilisateur?.domaines.includes(o.domaine));
  const { pathname } = useLocation();
  const liste = useRef<HTMLUListElement>(null);
  useEffect(() => {
    // Sur mobile, l'onglet actif est ramené dans la zone visible de la barre défilante.
    liste.current
      ?.querySelector<HTMLElement>('[aria-current="page"]')
      ?.scrollIntoView?.({ block: "nearest", inline: "center" });
  }, [pathname]);
  const bouton =
    "relative inline-flex h-11 w-10 shrink-0 items-center justify-center text-ink-2 hover:bg-hover hover:text-ink 2xl:w-auto 2xl:gap-1.5 2xl:px-2 2xl:text-sm 2xl:font-bold";
  const indicateur = (visible: boolean) => (
    <span
      aria-hidden
      className={cn(
        "absolute inset-x-2 bottom-0 h-[3px] rounded-t-full",
        visible ? "bg-gold" : "bg-transparent",
      )}
    />
  );
  return (
    <nav
      aria-label="Pages du tableau de bord"
      className="sans-impression sans-presentation sticky top-0 z-40 border-b border-border bg-surface shadow-sm"
    >
      <div className="mx-auto flex max-w-page items-stretch px-2 md:px-4">
        <button
          type="button"
          onClick={onSommaire}
          className={cn(bouton, "hidden md:inline-flex")}
          title="Sommaire"
        >
          <ListTree className="h-[18px] w-[18px]" aria-hidden />
          <span className="hidden 2xl:inline">Sommaire</span>
          <span className="sr-only 2xl:hidden">Sommaire de la page</span>
        </button>
        <span aria-hidden className="my-2.5 hidden w-px shrink-0 bg-border md:block" />
        <ul
          ref={liste}
          className="defilement-fondu flex min-w-0 flex-1 overflow-x-auto [scrollbar-width:none]"
        >
          {onglets.map((o) => {
            return (
              <li key={o.chemin} className="shrink-0">
                <NavLink
                  to={`${o.chemin}${global}`}
                  className={({ isActive }) =>
                    cn(
                      "relative flex h-11 items-center whitespace-nowrap px-1.5 text-base 2xl:px-2.5",
                      isActive
                        ? "bg-gold-tint font-bold text-navy dark:text-ink"
                        : "text-ink-2 hover:bg-hover hover:text-ink",
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      {o.libelle}
                      {indicateur(isActive)}
                    </>
                  )}
                </NavLink>
              </li>
            );
          })}
        </ul>
        <span aria-hidden className="my-2.5 w-px shrink-0 bg-border" />
        {utilisateur?.peut_explorer && (
          <NavLink to="/exploration" className={bouton} title="Exploration des données">
            {({ isActive }) => (
              <>
                <Telescope className={cn("h-[18px] w-[18px]", isActive && "text-gold")} aria-hidden />
                <span className="hidden 2xl:inline">Exploration</span>
                <span className="sr-only 2xl:hidden">Exploration des données</span>
                {indicateur(isActive)}
              </>
            )}
          </NavLink>
        )}
        {utilisateur?.est_admin && (
          <NavLink to="/administration" className={bouton} title="Administration de l'entrepôt">
            {({ isActive }) => (
              <>
                <Settings className={cn("h-[18px] w-[18px]", isActive && "text-gold")} aria-hidden />
                <span className="hidden 2xl:inline">Administration</span>
                <span className="sr-only 2xl:hidden">Administration de l'entrepôt</span>
                {indicateur(isActive)}
              </>
            )}
          </NavLink>
        )}
        <button
          type="button"
          onClick={basculer}
          className={bouton}
          aria-pressed={actif}
          title="Mode présentation"
        >
          {actif ? (
            <Minimize2 className="h-[18px] w-[18px]" aria-hidden />
          ) : (
            <Maximize2 className="h-[18px] w-[18px]" aria-hidden />
          )}
          <span className="hidden 2xl:inline">Présentation</span>
          <span className="sr-only 2xl:hidden">Mode présentation</span>
        </button>
        <button type="button" onClick={() => window.print()} className={bouton} title="Imprimer la page">
          <Printer className="h-[18px] w-[18px]" aria-hidden />
          <span className="hidden 2xl:inline">Imprimer</span>
          <span className="sr-only 2xl:hidden">Imprimer la page</span>
        </button>
      </div>
    </nav>
  );
}

/** Sommaire latéral : liste des sections (titres h2 dotés d'un id) de la page courante. */
function Sommaire({ ouvert, onChange }: { ouvert: boolean; onChange: (o: boolean) => void }) {
  const [sections, setSections] = useState<{ id: string; titre: string }[]>([]);
  useEffect(() => {
    if (!ouvert) return;
    const titres = Array.from(document.querySelectorAll<HTMLElement>("main section[id] h2"));
    setSections(
      titres
        .map((h) => ({ id: h.closest("section")!.id, titre: h.textContent ?? "" }))
        .filter((s) => s.titre),
    );
  }, [ouvert]);
  return (
    <Sheet
      ouvert={ouvert}
      onChange={onChange}
      titre="Sommaire de la page"
      cote="gauche"
      largeur="max-w-[320px]"
    >
      <ol className="flex flex-col">
        {sections.map((s) => (
          <li key={s.id}>
            <a
              href={`#${s.id}`}
              onClick={() => onChange(false)}
              className="block rounded-sm px-2 py-2 text-base text-ink hover:bg-hover"
            >
              {s.titre}
            </a>
          </li>
        ))}
      </ol>
    </Sheet>
  );
}

function PiedDePage() {
  return (
    <footer className="sans-impression sans-presentation mt-8">
      <FiletTricolore fin />
      <div className="mx-auto flex max-w-page flex-wrap items-baseline justify-between gap-x-6 gap-y-1 px-4 py-4 text-sm text-ink-2 md:px-6">
        <p>{PLATEFORME.ministere} · Direction nationale des systèmes d'information</p>
        {CREDIT_ARMOIRIES && <p className="text-xs text-ink-3">{CREDIT_ARMOIRIES}</p>}
      </div>
    </footer>
  );
}

/** En-tête officiel, visible uniquement à l'impression. */
function EnTeteImpression() {
  const { exercice, dateSituation } = useSituation();
  const page = ongletCourant(useLocation().pathname);
  return (
    <div className="seulement-impression mb-3">
      <div className="flex items-end justify-between gap-4 pb-2">
        <div className="flex items-center gap-3">
          <Armoiries taille={48} />
          <div>
            <p className="etiquette">République de Guinée · {PLATEFORME.ministere}</p>
            <p className="font-titre text-lg font-semibold text-ink">
              {PLATEFORME.nom} — {page?.libelle}
            </p>
            <p className="text-sm text-ink-2">
              Exercice {exercice} · situation au {dateFr(dateSituation)} · montants en milliards de GNF
            </p>
          </div>
        </div>
        <p className="text-right text-sm font-bold text-ink">
          Document de travail – diffusion restreinte
          <span className="block font-normal text-ink-2">Imprimé le {dateFr(new Date().toISOString())}</span>
        </p>
      </div>
      <FiletTricolore />
    </div>
  );
}

export function Cadre() {
  const location = useLocation();
  const [sommaire, setSommaire] = useState(false);
  const { actif, basculer } = usePresentation();

  const [annonce, setAnnonce] = useState("");
  const pagePrecedente = useRef<string | null>(null);
  useEffect(() => {
    const titre = ongletCourant(location.pathname)?.libelle;
    document.title = `${titre ? `${titre} — ` : ""}${PLATEFORME.nomCourt}`;
    setAnnonce(titre ? `Page ${titre}` : "");
    // Au chargement initial, le navigateur garde la main (premier Tab : « Aller au contenu »).
    // Après une connexion ou un vrai changement de page, si l'élément actif a disparu,
    // le focus va au contenu principal (comparaison avec la page précédente : robuste au double
    // passage des effets du mode strict de React).
    const changement = pagePrecedente.current !== null && pagePrecedente.current !== location.pathname;
    pagePrecedente.current = location.pathname;
    const actif = document.activeElement;
    const perdu = !actif || actif === document.body || !actif.isConnected;
    if ((changement || consommerConnexionRecente()) && perdu) {
      document.getElementById("contenu")?.focus({ preventScroll: true });
    } else if (perdu) {
      // Chargement initial : le squelette d'attente a disparu ; le parcours au clavier repart du haut de page.
      const debut = document.getElementById("debut-page");
      debut?.focus({ preventScroll: true });
      debut?.blur();
    }
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen flex-col">
      <span id="debut-page" tabIndex={-1} aria-hidden className="sr-only" />
      <a
        href="#contenu"
        className="sans-impression sr-only z-50 bg-surface px-3 py-2 text-ink focus:not-sr-only focus:fixed focus:left-2 focus:top-2"
      >
        Aller au contenu
      </a>
      <div className="sans-presentation">
        <EnTete />
      </div>
      <Navigation onSommaire={() => setSommaire(true)} />
      <Sommaire ouvert={sommaire} onChange={setSommaire} />
      {actif && (
        <button
          type="button"
          onClick={basculer}
          className="sans-impression fixed right-4 top-4 z-50 inline-flex items-center gap-2 rounded-sm border border-border bg-surface px-3 py-2 text-sm font-bold text-ink"
        >
          <Minimize2 className="h-4 w-4" aria-hidden /> Quitter la présentation
        </button>
      )}
      <p aria-live="polite" className="sr-only">
        {annonce}
      </p>
      <main id="contenu" tabIndex={-1} className="mx-auto w-full max-w-page flex-1 px-4 py-6 md:px-6">
        <EnTeteImpression />
        <Suspense fallback={<Squelette className="h-64 w-full" />}>
          <Outlet />
        </Suspense>
      </main>
      <PiedDePage />
    </div>
  );
}
