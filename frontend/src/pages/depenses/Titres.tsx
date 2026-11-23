import { Bell, ChevronRight } from "lucide-react";
import { useState } from "react";

import { useAlertes, useDonnees, useStatutAlerte } from "@/api/hooks";
import type { Alerte, FicheTitre as TFicheTitre, Voyant } from "@/api/types";
import { FenetreDossier } from "@/components/Alertes";
import { ETATS, Jauge, StatusPill } from "@/components/Indicateurs";
import { Montant } from "@/components/Montant";
import { Bouton } from "@/components/ui/primitives";
import { Sheet } from "@/components/ui/sheet";
import { dateFr, nombre, pct } from "@/lib/format";

import { EtatBloc } from "../commun";

export const REGLE_ARBITRAGE = "depense_arbitrage_ministre";

const LIBELLES_VOYANT: Record<Voyant, string> = {
  bon: "au rythme de l'exercice",
  vigilance: "en retard sur l'exercice",
  critique: "très en retard sur l'exercice",
};

interface VueTitres {
  titres: {
    titre: string;
    libelle_titre: string;
    credit_actuel: number;
    credit_engage: number;
    montant_paye: number;
    taux_engagement: number | null;
    taux_paiement: number | null;
    paiement_suivi: boolean;
    voyant: Voyant | null;
  }[];
}

/** Comparer l'exécution avant d'explorer les répartitions. La nature reste un filtre du détail. */
export function TableauTitres({ onOuvrir }: { onOuvrir: (titre: string) => void }) {
  const r = useDonnees<VueTitres>("/depense/titres/", { nature: undefined, titres: undefined });
  return (
    <section className="carte overflow-hidden" aria-labelledby="titres-execution">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-border px-3 py-2">
        <h3 id="titres-execution" className="text-base font-bold text-ink">
          Exécution par titre
        </h3>
        <p className="text-sm text-ink-2">Mds GNF · taux sur crédits actuels</p>
      </div>
      <EtatBloc requete={r} hauteur="h-56">
        {(d) =>
          d.titres.length ? (
            <>
              <div
                className="overflow-x-auto"
                tabIndex={0}
                role="region"
                aria-label="Comparaison des titres, tableau défilant horizontalement sur petit écran"
              >
                <table className="w-full text-sm">
                  <caption className="sr-only">
                    Crédits, engagement et paiement des titres budgétaires
                  </caption>
                  <thead className="bg-zebra text-ink-2">
                    <tr>
                      <th scope="col" className="px-3 py-2 text-left">
                        Titre budgétaire
                      </th>
                      <th scope="col" className="px-3 py-2 text-right">
                        Crédits actuels
                      </th>
                      <th scope="col" className="px-3 py-2 text-right">
                        Engagé / crédits
                      </th>
                      <th scope="col" className="px-3 py-2 text-right">
                        Payé / crédits
                      </th>
                      <th scope="col" className="px-3 py-2 text-left">
                        Rythme d’engagement
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {d.titres.map((t) => (
                      <tr key={t.titre} className="border-t border-border hover:bg-hover">
                        <th scope="row" className="px-3 py-2 text-left font-bold">
                          <button
                            type="button"
                            onClick={() => onOuvrir(t.titre)}
                            className="text-left text-navy underline decoration-border underline-offset-4 hover:decoration-current dark:text-ink"
                            aria-label={`Voir le détail de ${t.libelle_titre}`}
                          >
                            {t.libelle_titre}
                          </button>
                        </th>
                        <td className="chiffres px-3 py-2 text-right font-bold">
                          <Montant gnf={t.credit_actuel} />
                        </td>
                        <td className="min-w-[150px] px-3 py-2 text-right">
                          <div className="flex items-baseline justify-end gap-2 whitespace-nowrap">
                            <span className="chiffres font-bold">{pct(t.taux_engagement, 1)}</span>
                            <span className="text-ink-2">
                              <Montant gnf={t.credit_engage} />
                            </span>
                          </div>
                          <div className="mt-1">
                            <Jauge
                              valeur={t.taux_engagement}
                              libelle={`Engagé / crédits · ${t.libelle_titre}`}
                            />
                          </div>
                        </td>
                        <td className="min-w-[150px] px-3 py-2 text-right">
                          {t.paiement_suivi ? (
                            <>
                              <div className="flex items-baseline justify-end gap-2 whitespace-nowrap">
                                <span className="chiffres font-bold">{pct(t.taux_paiement, 1)}</span>
                                <span className="text-ink-2">
                                  <Montant gnf={t.montant_paye} />
                                </span>
                              </div>
                              <div className="mt-1">
                                <Jauge
                                  valeur={t.taux_paiement}
                                  libelle={`Payé / crédits · ${t.libelle_titre}`}
                                />
                              </div>
                            </>
                          ) : (
                            <span className="text-ink-2">Non suivi dans la chaîne</span>
                          )}
                        </td>
                        <td className="px-3 py-2">
                          {t.voyant ? (
                            <StatusPill etat={t.voyant} libelle={LIBELLES_VOYANT[t.voyant]} />
                          ) : (
                            <span className="text-ink-2">Non évalué</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <details className="border-t border-border px-3 py-2 text-sm text-ink-2">
                <summary className="cursor-pointer">Clés de lecture</summary>
                <p className="mt-2">
                  Engagé et payé sont rapportés aux crédits actuels. Le rythme est un repère calendaire
                  indicatif, sans prise en compte de la saisonnalité. Les autres filtres de consultation sont
                  conservés. Cliquer sur un titre ouvre sa chaîne, ses ministères et ses acteurs.
                </p>
              </details>
            </>
          ) : (
            <p className="p-4 text-sm text-ink-2">Aucun titre disponible pour ce périmètre.</p>
          )
        }
      </EtatBloc>
    </section>
  );
}

/** Pastille de couleur, toujours doublée d'un libellé accessible (la couleur seule ne porte pas l'information). */
export function Pastille({ voyant, libelle }: { voyant: Voyant | null; libelle?: string }) {
  const texte = libelle ?? (voyant ? LIBELLES_VOYANT[voyant] : "non évalué");
  return (
    <span
      className="inline-block h-4 w-4 shrink-0 rounded-full"
      style={{ background: voyant ? ETATS[voyant].couleur : "var(--ink-3)" }}
      title={texte}
      role="img"
      aria-label={texte}
    />
  );
}

/** Un dossier de l'encadré : un clic n'importe où sur la ligne déplie la fiche du dossier. */
function LigneArbitrage({
  a,
  couleur,
  onOuvrir,
  traiter,
  occupe,
}: {
  a: Alerte;
  couleur: string;
  onOuvrir: (titre: string) => void;
  traiter: () => void;
  occupe: boolean;
}) {
  const [ouvert, setOuvert] = useState(false);
  const d = a.donnees ?? {};
  return (
    <li className="py-2">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        {/* Le clic du bouton remonte jusqu'à ce bloc : texte et bouton ouvrent la fiche en fenêtre. */}
        <div className="min-w-0 flex-1 cursor-pointer text-sm" onClick={() => setOuvert((o) => !o)}>
          <button
            type="button"
            aria-haspopup="dialog"
            className="inline-flex items-start gap-1 text-left font-bold text-ink underline-offset-2 hover:underline"
          >
            <ChevronRight aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-ink-2" />
            {d.libelle_titre ?? a.titre}
          </button>
          <span className="text-ink-2">
            {" · "}
            {d.ministere} · {d.acteur} · <b className="chiffres text-ink">{a.valeur}</b> · en attente depuis{" "}
            <b className="chiffres" style={{ color: couleur }}>
              {nombre(Number(d.jours))} jours
            </b>
          </span>
          <p className="pl-5 text-ink-2">
            Dossier n° {d.numero}
            {d.beneficiaire ? ` · ${d.beneficiaire}` : ""}
            {d.etat ? ` · ${d.etat}` : ""}
            {a.relancee_le ? " · relance envoyée" : a.notifiee_le ? " · notifié" : ""}
          </p>
          <p className="mt-2 pl-5 text-sm text-ink">
            <b>Action proposée :</b>{" "}
            {a.action_recommandee ||
              "Faire qualifier le motif de l’attente et confirmer la décision attendue auprès du service concerné."}
          </p>
          <p className="mt-1 pl-5 text-sm text-ink-2">
            Situation au {dateFr(a.date_situation)} · compétence d’arbitrage à confirmer.
          </p>
        </div>
        <Bouton variante="discret" className="sans-impression" disabled={occupe} onClick={traiter}>
          Clore l’alerte
        </Bouton>
      </div>
      {/* Fiche de suivi en fenêtre : lecture confortable et impression PDF au thème de l'application. */}
      <FenetreDossier
        a={a}
        ouvert={ouvert}
        onChange={setOuvert}
        ouvrirLien={d.titre ? () => onOuvrir(String(d.titre)) : undefined}
      />
    </li>
  );
}

/** Dossiers bloqués qui relèvent de la Ministre (alertes par dossier, notifiées par courriel). */
export function EncadreArbitrages({ onOuvrir }: { onOuvrir: (titre: string) => void }) {
  const r = useAlertes({ domaine: "depense", regle: REGLE_ARBITRAGE, statut: "nouvelle,vue" });
  const statut = useStatutAlerte();
  const [tout, setTout] = useState(false);
  const alertes = r.data ?? [];
  const visibles = tout ? alertes : alertes.slice(0, 5);
  const couleur = ETATS.critique.couleur;
  if (r.isError)
    return (
      <div role="alert" className="carte p-4">
        <p className="font-bold text-ink">Arbitrages indisponibles</p>
        <p className="mt-1 text-sm text-ink-2">
          La liste n’a pas pu être chargée. L’absence d’alerte ne peut pas être confirmée.
        </p>
        <Bouton variante="discret" onClick={() => r.refetch()}>
          Réessayer
        </Bouton>
      </div>
    );
  return (
    <section
      aria-labelledby="arbitrages-titre"
      className="flex flex-col gap-3 rounded border-2 bg-surface p-4"
      style={{ borderColor: alertes.length ? couleur : "var(--border)" }}
    >
      <div className="flex items-start gap-3">
        <span
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sur-etat"
          style={{ background: alertes.length ? couleur : "var(--ink-3)" }}
        >
          <Bell className="h-5 w-5" aria-hidden />
        </span>
        <div className="min-w-0">
          <h3
            id="arbitrages-titre"
            className="text-base font-bold"
            style={{ color: alertes.length ? couleur : undefined }}
          >
            Dossiers à examiner pour arbitrage
            {alertes.length ? ` : ${nombre(alertes.length)} dossier(s)` : ""}
          </h3>
          <p className="text-sm text-ink-2">
            {r.isLoading
              ? "Chargement…"
              : alertes.length
                ? "Dossiers dépassant les seuils de montant et d’ancienneté. Le motif de l’attente et la compétence ministérielle doivent être confirmés."
                : "Aucun dossier remonté par la règle d’alerte."}
          </p>
          <p className="mt-1 text-sm text-ink-2">
            Périmètre global des alertes Dépenses · indépendant des filtres de consultation. Les dates de
            situation sont précisées sur chaque dossier.
          </p>
        </div>
      </div>
      {statut.isError && (
        <p role="alert" className="text-sm text-ink">
          La clôture a échoué. Réessayez ; le statut de l’alerte n’a pas été confirmé.
        </p>
      )}
      {alertes.length > 0 && (
        <ul className="flex flex-col divide-y divide-border">
          {visibles.map((a) => (
            <LigneArbitrage
              key={a.id}
              a={a}
              couleur={couleur}
              onOuvrir={onOuvrir}
              traiter={() => statut.mutate({ id: a.id, statut: "traitee" })}
              occupe={statut.isPending}
            />
          ))}
        </ul>
      )}
      {alertes.length > 5 && (
        <Bouton variante="discret" className="sans-impression self-start" onClick={() => setTout((t) => !t)}>
          {tout ? "Afficher moins" : `Afficher les ${nombre(alertes.length)} dossiers`}
        </Bouton>
      )}
    </section>
  );
}

/** Vue 2 : chaîne complète, ministères, acteurs et alertes d'un titre. */
export function FicheTitre({
  titre,
  onFermer,
  onFiltrer,
}: {
  titre: string | null;
  onFermer: () => void;
  onFiltrer: (titre: string) => void;
}) {
  const r = useDonnees<TFicheTitre>(
    `/depense/titres/${titre}/`,
    { nature: undefined, titres: undefined },
    { actif: Boolean(titre) },
  );
  const d = r.data?.data;
  return (
    <Sheet
      ouvert={Boolean(titre)}
      onChange={(o) => !o && onFermer()}
      titre={d?.libelle_titre ?? "Détail du titre"}
      description="Chaîne complète, ministères, acteurs et alertes du titre"
      largeur="max-w-[1040px]"
    >
      <EtatBloc requete={r} hauteur="h-96">
        {(d) => (
          <div className="flex flex-col gap-6">
            <p className="text-sm text-ink-2">
              Situation au {dateFr(r.data?.meta.date_situation)} · montants en Mds GNF · chaque taux est
              rapporté aux crédits actuels du titre.
            </p>
            <ol className="grid gap-2 sm:grid-cols-5" aria-label="Chaîne de la dépense">
              {d.chaine.map((e, i) => (
                <li key={e.code} className="flex flex-col rounded border border-border p-3">
                  <span className="text-sm text-ink-2">
                    {i > 0 && <span aria-hidden>› </span>}
                    {e.libelle}
                  </span>
                  {e.montant == null ? (
                    <span className="text-base text-ink-2">non suivi</span>
                  ) : (
                    <span className="flex flex-wrap items-baseline gap-x-2">
                      <Montant gnf={e.montant} decimales={0} className="text-lg font-bold text-ink" />
                      {i > 0 && <span className="chiffres text-sm text-ink-2">{pct(e.taux, 1)}</span>}
                    </span>
                  )}
                </li>
              ))}
            </ol>

            <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
              <section>
                <h3 className="etiquette mb-2">
                  Par ministère (
                  {d.ministeres.length < d.nb_ministeres
                    ? `${d.ministeres.length} plus gros crédits sur ${d.nb_ministeres}`
                    : "tous"}
                  )
                </h3>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-ink-2">
                      <th scope="col" className="py-1.5 pr-2 font-bold">
                        Ministère
                      </th>
                      <th scope="col" className="py-1.5 pr-2 text-right font-bold">
                        Crédits
                      </th>
                      <th scope="col" className="py-1.5 pr-2 text-right font-bold">
                        Engagé
                      </th>
                      <th scope="col" className="py-1.5 text-right font-bold">
                        Payé
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {d.ministeres.map((m) => (
                      <tr key={m.code} className="border-b border-border">
                        <td className="py-1.5 pr-2 text-ink">{m.libelle}</td>
                        <td className="py-1.5 pr-2 text-right">
                          <Montant gnf={m.credit_actuel} decimales={0} />
                        </td>
                        <td className="chiffres py-1.5 pr-2 text-right">{pct(m.taux_engagement, 1)}</td>
                        <td className="chiffres py-1.5 text-right">
                          {d.paiement_suivi ? pct(m.taux_paiement, 1) : "non suivi"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="mt-1 text-xs text-ink-2">Engagé et payé rapportés aux crédits du ministère.</p>
              </section>

              <section>
                <h3 className="etiquette mb-2">Par acteur</h3>
                <ul className="flex flex-col gap-2">
                  {d.acteurs.map((a) => (
                    <li key={a.code} className="flex items-start gap-3 rounded border border-border p-3">
                      <Pastille
                        voyant={a.voyant}
                        libelle={
                          a.voyant
                            ? ETATS[a.voyant].libelle
                            : a.raccorde === false
                              ? "non raccordé"
                              : "information"
                        }
                      />
                      <span className="text-sm">
                        <b className="text-ink">{a.acteur}</b>
                        <span className="ml-2 text-ink-2">
                          {a.voyant
                            ? ETATS[a.voyant].libelle
                            : a.raccorde === false
                              ? "Non raccordé"
                              : "Information"}
                        </span>
                        <span className="mt-1 block text-ink-2">{a.texte}</span>
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            </div>

            <section
              className="rounded border-2 p-3 text-sm"
              style={{ borderColor: d.alertes.length ? ETATS.critique.couleur : "var(--border)" }}
            >
              <h3
                className="font-bold"
                style={{ color: d.alertes.length ? ETATS.critique.couleur : undefined }}
              >
                Alertes du titre {d.titre}
              </h3>
              {d.alertes.length ? (
                <ul className="mt-1 list-inside list-disc text-ink">
                  {d.alertes.map((a) => (
                    <li key={a.texte}>{a.texte}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-ink-2">Aucune alerte pour ce titre.</p>
              )}
            </section>

            <Bouton variante="discret" className="self-start" onClick={() => onFiltrer(d.titre)}>
              Filtrer toute la page sur ce titre
            </Bouton>
          </div>
        )}
      </EtatBloc>
    </Sheet>
  );
}
