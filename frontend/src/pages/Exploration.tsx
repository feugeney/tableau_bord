import { useQuery } from "@tanstack/react-query";
import { FileSpreadsheet, FileText, Play, Plus, X } from "lucide-react";
import { useMemo, useState } from "react";

import { api, telecharger } from "@/api/client";
import type { Enveloppe, Meta } from "@/api/types";
import { DataTable, type Colonne } from "@/components/DataTable";
import { SourceBadge } from "@/components/Source";
import { Case, Champ, Entree, Liste, Retour } from "@/components/ui/formulaire";
import { Bouton, Carte, Squelette } from "@/components/ui/primitives";
import { dateFr, nombre } from "@/lib/format";

import { TitrePage } from "./commun";

interface Axe {
  code: string;
  libelle: string;
  type: "date" | "periode" | "booleen" | "reference" | "liste" | "texte" | "nombre";
}
interface Mesure {
  code: string;
  libelle: string;
  agregat_defaut: string;
}
interface Jeu {
  code: string;
  libelle: string;
  domaine: string;
  domaine_libelle: string;
  source: string;
  statut_source: Meta["statut_source"];
  axes: Axe[];
  mesures: Mesure[];
  situations: { exercice: number; date_situation: string }[];
}
interface Catalogue {
  jeux: Jeu[];
  agregats: string[];
  operateurs: string[];
  limites: { axes: number; mesures: number; filtres: number; lignes: number };
}
interface Filtre {
  champ: string;
  operateur: string;
  valeur: string;
}
interface Requete {
  jeu: string;
  axes: string[];
  mesures: { champ: string; agregat: string }[];
  filtres: Filtre[];
  exercice?: number;
  date_situation?: string;
}
interface ColonneResultat {
  code: string;
  libelle: string;
  type: Axe["type"] | "mesure";
  agregat?: string;
}
type Ligne = Record<string, string | number | boolean | null>;
interface Resultat {
  jeu: { code: string; libelle: string };
  colonnes: ColonneResultat[];
  lignes: Ligne[];
  totaux: Record<string, number | null>;
  nb_groupes: number;
  tronque: boolean;
}

const LIBELLES_AGREGATS: Record<string, string> = {
  somme: "Somme",
  moyenne: "Moyenne",
  minimum: "Minimum",
  maximum: "Maximum",
};
const LIBELLES_OPERATEURS: Record<string, string> = {
  egal: "est égal à",
  different: "est différent de",
  contient: "contient",
  superieur: "au moins",
  inferieur: "au plus",
  parmi: "parmi (séparer par « ; »)",
};

/** Valeur d'une mesure : les montants sont en GNF, non arrondis à l'export. */
function valeurMesure(v: unknown, c: ColonneResultat) {
  if (typeof v !== "number") return "—";
  if (c.agregat === "nombre") return nombre(v);
  if (c.agregat === "moyenne") return nombre(v, 2);
  return nombre(v, Number.isInteger(v) || Math.abs(v) >= 1000 ? 0 : 2);
}

/** Barres horizontales : première mesure selon le premier axe (dix premières lignes). */
function Barres({ resultat }: { resultat: Resultat }) {
  const axe = resultat.colonnes.find((c) => c.type !== "mesure");
  const mesure = resultat.colonnes.find((c) => c.type === "mesure");
  if (!axe || !mesure || resultat.lignes.length < 2) return null;
  const lignes = resultat.lignes.slice(0, 10);
  const max = Math.max(1, ...lignes.map((l) => Math.abs(Number(l[mesure.code]) || 0)));
  return (
    <figure className="mb-4">
      <figcaption className="etiquette mb-2">
        {mesure.libelle} selon {axe.libelle.toLowerCase()}
        {resultat.lignes.length > 10 ? " · dix premières lignes" : ""}
      </figcaption>
      <ul className="flex flex-col gap-2">
        {lignes.map((l, i) => {
          const v = Number(l[mesure.code]) || 0;
          return (
            <li key={i}>
              <span className="flex items-baseline justify-between gap-3 text-base">
                <span className="min-w-0 truncate text-ink" title={String(l[`${axe.code}__libelle`])}>
                  {String(l[`${axe.code}__libelle`])}
                </span>
                <span className="chiffres shrink-0 text-ink">{valeurMesure(v, mesure)}</span>
              </span>
              <span className="relative mt-1 block h-2 w-full rounded-full bg-grid" aria-hidden>
                <span
                  className="jauge-remplie block h-2 rounded-full"
                  style={{ width: `${(Math.abs(v) / max) * 100}%`, background: "var(--serie-1)" }}
                />
              </span>
            </li>
          );
        })}
      </ul>
    </figure>
  );
}

function Resultats({ requete }: { requete: Requete }) {
  const q = JSON.stringify(requete);
  const r = useQuery({
    queryKey: ["exploration", q],
    queryFn: () => api.get<Enveloppe<Resultat>>("/exploration/requete/", { q }),
  });
  const [echecExport, setEchecExport] = useState(false);
  const colonnes = useMemo<Colonne<Ligne>[]>(
    () =>
      (r.data?.data?.colonnes ?? []).map((c) =>
        c.type === "mesure"
          ? {
              header: c.libelle,
              id: c.code,
              accessorFn: (l: Ligne) => l[c.code],
              cell: ({ getValue }) => valeurMesure(getValue(), c),
              meta: { numerique: true },
            }
          : { header: c.libelle, id: c.code, accessorFn: (l: Ligne) => l[`${c.code}__libelle`] },
      ),
    [r.data],
  );
  if (r.isPending) return <Squelette className="h-96 w-full" />;
  if (r.isError || !r.data.data)
    return <Retour ok={false}>La requête n'a pas abouti. Vérifiez les filtres saisis, puis relancez.</Retour>;
  const d = r.data.data;
  const mesures = d.colonnes.filter((c) => c.type === "mesure");
  return (
    <Carte
      id="resultat"
      titre={d.jeu.libelle}
      sousTitre={
        r.data.meta.date_situation
          ? `Exercice ${r.data.meta.exercice} · situation au ${dateFr(r.data.meta.date_situation)} · montants en GNF`
          : "Aucune situation chargée pour ce jeu de données"
      }
      actions={
        <span className="flex flex-wrap items-center gap-2">
          <SourceBadge meta={r.data.meta} />
          <Bouton
            onClick={() => {
              setEchecExport(false);
              telecharger("/exploration/export.xlsx", { q }).catch(() => setEchecExport(true));
            }}
          >
            <FileSpreadsheet className="h-4 w-4" aria-hidden /> Exporter (Excel)
          </Bouton>
          <Bouton
            onClick={() => {
              setEchecExport(false);
              telecharger("/exploration/export.pdf", { q }).catch(() => setEchecExport(true));
            }}
          >
            <FileText className="h-4 w-4" aria-hidden /> Exporter (PDF)
          </Bouton>
        </span>
      }
    >
      {echecExport && <Retour ok={false}>Export impossible. Réessayez.</Retour>}
      <p className="mb-3 text-base text-ink" aria-live="polite">
        {nombre(d.lignes.length)} ligne{d.lignes.length > 1 ? "s" : ""}
        {d.tronque ? ` affichées sur ${nombre(d.nb_groupes)} (l'export en contient davantage)` : ""}
        {mesures.map((c) => (
          <span key={c.code}>
            {" · "}
            {c.libelle} : <span className="chiffres font-bold">{valeurMesure(d.totaux[c.code], c)}</span>
          </span>
        ))}
      </p>
      <Barres resultat={d} />
      <DataTable
        donnees={d.lignes}
        colonnes={colonnes}
        libelle={`Résultat : ${d.jeu.libelle}`}
        vide="Aucune ligne."
      />
    </Carte>
  );
}

export default function Exploration() {
  const catalogue = useQuery({
    queryKey: ["exploration", "jeux"],
    queryFn: () => api.get<Catalogue>("/exploration/jeux/"),
  });
  const [code, setCode] = useState("");
  const [situation, setSituation] = useState("");
  const [axes, setAxes] = useState<string[]>([]);
  const [mesures, setMesures] = useState<Record<string, string>>({});
  const [filtres, setFiltres] = useState<Filtre[]>([]);
  const [lancee, setLancee] = useState<Requete | null>(null);

  if (catalogue.isPending) return <Squelette className="h-96 w-full" />;
  if (catalogue.isError)
    return <Retour ok={false}>Le catalogue des jeux de données n'a pas pu être chargé.</Retour>;
  const { jeux, limites, agregats, operateurs } = catalogue.data;
  const jeu = jeux.find((j) => j.code === code) ?? null;
  const domaines = [...new Set(jeux.map((j) => j.domaine_libelle))];
  const champs = jeu
    ? [
        ...jeu.axes.filter((a) => a.type !== "periode").map((a) => ({ code: a.code, libelle: a.libelle })),
        ...jeu.mesures.map((m) => ({ code: m.code, libelle: m.libelle })),
      ]
    : [];

  function choisirJeu(c: string) {
    setCode(c);
    setSituation("");
    setAxes([]);
    setMesures({});
    setFiltres([]);
    setLancee(null);
  }
  function lancer() {
    if (!jeu) return;
    const [exercice, date_situation] = situation ? situation.split("|") : [];
    setLancee({
      jeu: jeu.code,
      axes,
      mesures: Object.entries(mesures).map(([champ, agregat]) => ({ champ, agregat })),
      filtres: filtres.filter((f) => f.champ && f.valeur.trim() !== ""),
      ...(exercice ? { exercice: Number(exercice), date_situation } : {}),
    });
  }

  return (
    <>
      <TitrePage
        titre="Exploration des données"
        sousTitre="Requêtes libres sur l'entrepôt, dans la limite de vos domaines. Les exports sont inscrits au journal d'audit."
      />
      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">
        <Carte id="requete" titre="Requête">
          <form
            className="flex flex-col gap-4"
            onSubmit={(e) => {
              e.preventDefault();
              lancer();
            }}
          >
            <Champ libelle="Jeu de données">
              {(id) => (
                <Liste id={id} value={code} onChange={(e) => choisirJeu(e.target.value)}>
                  <option value="">Choisir…</option>
                  {domaines.map((d) => (
                    <optgroup key={d} label={d}>
                      {jeux
                        .filter((j) => j.domaine_libelle === d)
                        .map((j) => (
                          <option key={j.code} value={j.code}>
                            {j.libelle}
                          </option>
                        ))}
                    </optgroup>
                  ))}
                </Liste>
              )}
            </Champ>
            {jeu && (
              <>
                <Champ
                  libelle="Situation"
                  aide={
                    jeu.situations.length ? undefined : "Aucune situation chargée pour ce jeu de données."
                  }
                >
                  {(id, d) => (
                    <Liste
                      id={id}
                      aria-describedby={d}
                      value={situation}
                      onChange={(e) => setSituation(e.target.value)}
                      disabled={!jeu.situations.length}
                    >
                      <option value="">Dernière situation chargée</option>
                      {jeu.situations.map((s) => (
                        <option
                          key={`${s.exercice}|${s.date_situation}`}
                          value={`${s.exercice}|${s.date_situation}`}
                        >
                          Exercice {s.exercice} · {dateFr(s.date_situation)}
                        </option>
                      ))}
                    </Liste>
                  )}
                </Champ>
                <fieldset>
                  <legend className="text-sm font-bold text-ink">
                    Regrouper par <span className="font-normal text-ink-2">({limites.axes} au plus)</span>
                  </legend>
                  <div className="mt-1 flex max-h-56 flex-col overflow-y-auto rounded-sm border border-border px-2 py-1">
                    {jeu.axes.map((a) => (
                      <Case
                        key={a.code}
                        libelle={a.libelle}
                        checked={axes.includes(a.code)}
                        disabled={!axes.includes(a.code) && axes.length >= limites.axes}
                        onChange={(e) =>
                          setAxes(e.target.checked ? [...axes, a.code] : axes.filter((x) => x !== a.code))
                        }
                      />
                    ))}
                  </div>
                </fieldset>
                <fieldset>
                  <legend className="text-sm font-bold text-ink">
                    Mesures{" "}
                    <span className="font-normal text-ink-2">(le nombre de lignes est toujours compté)</span>
                  </legend>
                  <div className="mt-1 flex max-h-56 flex-col gap-1 overflow-y-auto rounded-sm border border-border px-2 py-1">
                    {jeu.mesures.length === 0 && (
                      <p className="text-sm text-ink-2">Aucune mesure numérique.</p>
                    )}
                    {jeu.mesures.map((m) => (
                      <div key={m.code} className="flex items-center justify-between gap-2">
                        <Case
                          libelle={m.libelle}
                          checked={m.code in mesures}
                          disabled={!(m.code in mesures) && Object.keys(mesures).length >= limites.mesures}
                          onChange={(e) => {
                            const suite = { ...mesures };
                            if (e.target.checked) suite[m.code] = m.agregat_defaut;
                            else delete suite[m.code];
                            setMesures(suite);
                          }}
                        />
                        {m.code in mesures && (
                          <Liste
                            aria-label={`Agrégat de ${m.libelle}`}
                            className="!mt-0 !w-auto shrink-0"
                            value={mesures[m.code]}
                            onChange={(e) => setMesures({ ...mesures, [m.code]: e.target.value })}
                          >
                            {agregats.map((a) => (
                              <option key={a} value={a}>
                                {LIBELLES_AGREGATS[a] ?? a}
                              </option>
                            ))}
                          </Liste>
                        )}
                      </div>
                    ))}
                  </div>
                </fieldset>
                <fieldset>
                  <legend className="text-sm font-bold text-ink">Filtres</legend>
                  <div className="mt-1 flex flex-col gap-3">
                    {filtres.map((f, i) => {
                      const modifier = (suite: Partial<Filtre>) =>
                        setFiltres(filtres.map((x, j) => (j === i ? { ...x, ...suite } : x)));
                      return (
                        <div key={i} className="rounded-sm border border-border p-2">
                          <div className="flex items-start gap-2">
                            <Liste
                              aria-label={`Champ du filtre ${i + 1}`}
                              className="!mt-0"
                              value={f.champ}
                              onChange={(e) => modifier({ champ: e.target.value })}
                            >
                              <option value="">Champ…</option>
                              {champs.map((c) => (
                                <option key={c.code} value={c.code}>
                                  {c.libelle}
                                </option>
                              ))}
                            </Liste>
                            <Bouton
                              variante="discret"
                              aria-label={`Retirer le filtre ${i + 1}`}
                              onClick={() => setFiltres(filtres.filter((_, j) => j !== i))}
                            >
                              <X className="h-4 w-4" aria-hidden />
                            </Bouton>
                          </div>
                          <Liste
                            aria-label={`Opérateur du filtre ${i + 1}`}
                            value={f.operateur}
                            onChange={(e) => modifier({ operateur: e.target.value })}
                          >
                            {operateurs.map((o) => (
                              <option key={o} value={o}>
                                {LIBELLES_OPERATEURS[o] ?? o}
                              </option>
                            ))}
                          </Liste>
                          <Entree
                            aria-label={`Valeur du filtre ${i + 1}`}
                            placeholder="Valeur (code, texte, nombre ou AAAA-MM-JJ)"
                            autoComplete="off"
                            value={f.valeur}
                            onChange={(e) => modifier({ valeur: e.target.value })}
                          />
                        </div>
                      );
                    })}
                    <Bouton
                      className="self-start"
                      disabled={filtres.length >= limites.filtres}
                      onClick={() => setFiltres([...filtres, { champ: "", operateur: "egal", valeur: "" }])}
                    >
                      <Plus className="h-4 w-4" aria-hidden /> Ajouter un filtre
                    </Bouton>
                  </div>
                </fieldset>
                <Bouton type="submit" variante="primaire" className="min-h-10">
                  <Play className="h-4 w-4" aria-hidden /> Lancer la requête
                </Bouton>
              </>
            )}
          </form>
        </Carte>
        {lancee ? (
          <Resultats requete={lancee} />
        ) : (
          <Carte id="resultat" titre="Résultat">
            <p className="text-base text-ink-2">
              Choisissez un jeu de données, les axes de regroupement et les mesures, puis lancez la requête.
              Sans axe, la requête renvoie les totaux du jeu de données.
            </p>
          </Carte>
        )}
      </div>
    </>
  );
}
