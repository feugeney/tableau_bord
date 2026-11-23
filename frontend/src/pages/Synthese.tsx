import { useMemo } from "react";
import { useNavigate } from "react-router-dom";

import { useDonnees } from "@/api/hooks";
import type { ComparaisonN1, KpiSynthese, Synthese as TSynthese } from "@/api/types";
import { ListeAlertes } from "@/components/Alertes";
import { GroupedBarChart } from "@/components/GroupedBarChart";
import { BandeauKpi, KpiCard, Note, StatusPill } from "@/components/Indicateurs";
import { Montant, Pourcentage } from "@/components/Montant";
import { SourceBadge } from "@/components/Source";
import { Carte, Segment } from "@/components/ui/primitives";
import { useAuth } from "@/hooks/useAuth";
import { useFiltres } from "@/hooks/useFiltres";
import { dateFr, enMds, moisCourt, nombre, pct } from "@/lib/format";
import { nomSource } from "@/lib/sources";

import { EtatPage, TitrePage, Zone } from "./commun";
import { CourbeExecution, EcartN1 } from "./depenses/analyses";
import { IndicateursExecution } from "./depenses/IndicateursExecution";
import { BlocProjectionDepenses } from "./depenses/Projection";

/**
 * Synthèse (révisée le 19/11/2026) : bandes Trésorerie → Recettes → Exécution → Dette, sources et dates
 * dans un bandeau unique, blocs sans donnée regroupés sur une ligne, tendance et « où agir ».
 */

const AIDES: Record<string, string> = {
  recettes: "Recettes fiscales (SAFIG) et douanières (SYDONIA) recouvrées, rapportées à l'objectif.",
  recettes_fiscales: "Recettes fiscales recouvrées (SAFIG), rapportées à l'objectif.",
  recettes_douanieres: "Recettes douanières recouvrées (SYDONIA), rapportées à l'objectif.",
  recettes_administratives:
    "Dividendes versés à l'État par les sociétés publiques (SYSOP), rapportés aux dividendes votés.",
  depenses_engagees: "Crédits engagés rapportés aux crédits actuels (Chaîne Dépense).",
  reste_a_payer:
    "Ordonnancé non payé, hors procédures payées hors chaîne (salaires en procédure Solde, dette en débit d'office).",
  tresorerie: "Solde de fin de période exprimé en jours de décaissements moyens (SCIE).",
  dette: "Encours total rapporté au PIB, comparé au seuil de convergence CEDEAO de 70 %.",
  personnel_ordonnance: "Dépenses de personnel (titre 2) ordonnancées dans la Chaîne Dépense.",
};

const LIBELLES: Record<string, string> = {
  tresorerie: "Trésorerie",
  recettes: "Total fiscal et douanier",
  recettes_fiscales: "Recettes fiscales",
  recettes_douanieres: "Recettes douanières",
  recettes_administratives: "Recettes administratives (dividendes)",
  depenses_engagees: "Engagement des crédits",
  reste_a_payer: "Reste à payer",
  personnel_ordonnance: "Personnel ordonnancé",
  dette: "Dette",
};

const SERIES = [
  { cle: "recettes", libelle: "Recettes (SAFIG + SYDONIA)", couleur: "var(--serie-2)" },
  { cle: "depenses", libelle: "Dépenses engagées", couleur: "var(--serie-1)" },
];

function Kpi({ k, n1 }: { k: KpiSynthese; n1?: ComparaisonN1 | null }) {
  if (k.masque) {
    return <KpiCard libelle={k.libelle} valeur="—" contexte="Hors de votre périmètre" />;
  }
  if (k.code === "depenses_engagees") {
    return (
      <KpiCard
        libelle="Engagement des crédits"
        valeur={<Pourcentage ratio={k.taux} />}
        contexte={
          <>
            <Montant gnf={k.valeur} /> sur <Montant gnf={k.reference} /> de crédits
          </>
        }
        jauge={{ valeur: k.taux }}
        pied={
          n1?.disponible ? (
            <EcartN1
              taux={k.taux}
              reference={n1.taux_engagement}
              libelle={`${n1.exercice} au ${dateFr(n1.date)}`}
            />
          ) : undefined
        }
        aide={AIDES[k.code]}
      />
    );
  }
  if (k.code === "recettes" || k.code === "recettes_fiscales" || k.code === "recettes_douanieres") {
    return (
      <KpiCard
        libelle={LIBELLES[k.code]}
        valeur={<Montant gnf={k.valeur} />}
        contexte={
          <>
            <Pourcentage ratio={k.taux} /> de l'objectif (<Montant gnf={k.reference} />)
          </>
        }
        jauge={{ valeur: k.taux, repere: 0.8 }}
        etat={k.taux != null && k.taux < 0.8 ? "serieux" : undefined}
        aide={AIDES[k.code]}
      />
    );
  }
  if (k.code === "recettes_administratives") {
    return (
      <KpiCard
        libelle={LIBELLES[k.code]}
        valeur={<Montant gnf={k.valeur} />}
        contexte={
          <>
            <Pourcentage ratio={k.taux} /> des dividendes votés (<Montant gnf={k.reference} />) ·{" "}
            {nombre(k.nombre)} société(s)
          </>
        }
        jauge={{ valeur: k.taux, repere: 1 }}
        aide={AIDES[k.code]}
      />
    );
  }
  if (k.code === "tresorerie") {
    return (
      <KpiCard
        libelle="Trésorerie fin de période"
        valeur={<Montant gnf={k.valeur} />}
        contexte={`${nombre(k.jours)} jours de décaissements`}
        jauge={{ valeur: (k.jours ?? 0) / 60, repere: 0.5 }}
        etat={k.sous_seuil ? "critique" : undefined}
        aide={AIDES[k.code]}
      />
    );
  }
  if (k.code === "dette") {
    return (
      <KpiCard
        libelle="Encours de la dette"
        valeur={<Montant gnf={k.valeur} />}
        contexte={
          <>
            <Pourcentage ratio={k.taux} /> du PIB · seuil CEDEAO {pct(k.reference)}
          </>
        }
        jauge={{ valeur: k.taux, repere: k.reference ?? undefined }}
        etat={k.depasse ? "critique" : undefined}
        aide={AIDES[k.code]}
      />
    );
  }
  if (k.code === "reste_a_payer") {
    return (
      <KpiCard
        libelle="Reste à payer"
        valeur={<Montant gnf={k.valeur} />}
        contexte={
          <>
            Payé / ordonnancé : <Pourcentage ratio={k.taux} /> · ordonnancé non payé, à rapprocher avec le
            Trésor
          </>
        }
        aide={AIDES[k.code]}
      />
    );
  }
  return (
    <KpiCard
      libelle="Personnel ordonnancé"
      valeur={<Montant gnf={k.valeur} />}
      contexte={
        k.taux != null ? (
          <>
            <Pourcentage ratio={k.taux} /> des crédits de personnel
          </>
        ) : undefined
      }
      jauge={k.taux != null ? { valeur: k.taux } : undefined}
      aide={AIDES[k.code]}
    />
  );
}

const BANDES: { cle: NonNullable<KpiSynthese["bande"]>; titre: string }[] = [
  { cle: "tresorerie", titre: "Trésorerie" },
  { cle: "recettes", titre: "Recettes" },
  { cle: "execution", titre: "Exécution de la dépense" },
  { cle: "dette", titre: "Dette" },
];

// Bande de lecture : fournie par l'API, sinon déduite du code de l'indicateur.
const BANDE_CODE: Record<string, NonNullable<KpiSynthese["bande"]>> = {
  tresorerie: "tresorerie",
  recettes: "recettes",
  recettes_fiscales: "recettes",
  recettes_douanieres: "recettes",
  recettes_administratives: "recettes",
  depenses_engagees: "execution",
  reste_a_payer: "execution",
  personnel_ordonnance: "execution",
  dette: "dette",
};
const bandeDe = (k: KpiSynthese) => k.bande ?? BANDE_CODE[k.code];

const disponible = (k: KpiSynthese) => k.masque || (k.valeur !== null && k.valeur !== undefined);

export default function Synthese() {
  const requete = useDonnees<TSynthese>("/synthese/");
  const { filtres, definir } = useFiltres();
  return (
    <>
      <TitrePage exporter="synthese" titre="Synthèse">
        <Segment<"decision" | "demonstration">
          libelle="Données de la synthèse"
          valeur={filtres.mode_synthese ?? "decision"}
          options={[
            { valeur: "decision", libelle: "Données réelles" },
            { valeur: "demonstration", libelle: "Démonstration" },
          ]}
          onChange={(mode_synthese) => definir({ mode_synthese })}
        />
      </TitrePage>
      <EtatPage requete={requete}>{(d) => <Contenu d={d} />}</EtatPage>
    </>
  );
}

function Contenu({ d }: { d: TSynthese }) {
  const { utilisateur } = useAuth();
  const navigate = useNavigate();
  const voitDepenses = utilisateur?.domaines.includes("depense") ?? false;
  const serie = useMemo(() => {
    const parMois = new Map<string, { mois: string; recettes: number; depenses: number }>();
    for (const l of d.serie_mensuelle) {
      const m = parMois.get(l.mois) ?? { mois: l.mois, recettes: 0, depenses: 0 };
      if (l.indicateur === "depense_engagee") m.depenses += enMds(l.realise);
      else m.recettes += enMds(l.realise);
      parMois.set(l.mois, m);
    }
    return [...parMois.values()]
      .sort((a, b) => a.mois.localeCompare(b.mois))
      .map((m) => ({ ...m, libelle: moisCourt(m.mois, true) }));
  }, [d.serie_mensuelle]);
  const aDesRecettes = d.serie_mensuelle.some((l) => l.indicateur !== "depense_engagee");
  // Blocs sans donnée : regroupés sur une ligne plutôt qu'affichés en grands cadres vides (S6).
  // Le total fiscal et douanier n'est listé que s'il est seul (sinon ses composantes le sont déjà).
  const detailRecettes = d.indicateurs.some(
    (k) => k.code === "recettes_fiscales" || k.code === "recettes_douanieres",
  );
  const enAttente = d.indicateurs.filter((k) => !disponible(k) && !(k.code === "recettes" && detailRecettes));
  const n1 = d.execution?.comparaison_n1;
  const compte = d.alertes_compte ?? {};

  return (
    <div className="flex flex-col gap-6">
      <p role="note" className="rounded border border-border bg-surface p-3 text-sm text-ink-2">
        {d.mode_synthese === "demonstration"
          ? "Mode démonstration : cette vue peut inclure des chiffres fictifs, identifiés dans le bandeau des sources."
          : "Vue décisionnelle : seules les données réelles sont présentées."}
      </p>
      <BandeauSources indicateurs={d.indicateurs} avertissements={d.avertissements} />
      {enAttente.length > 0 && (
        <p className="text-sm text-ink-2">
          <strong className="text-ink">
            {d.mode_synthese === "demonstration"
              ? "Sans donnée pour cette période"
              : "En attente de données réelles"}{" "}
            :
          </strong>{" "}
          {enAttente.map((k) => `${LIBELLES[k.code] ?? k.libelle} (${nomSource(k.meta.source)})`).join(" · ")}
          .
        </p>
      )}

      <Zone titre="Points d'attention">
        <section id="alertes" aria-labelledby="alertes-titre" className="carte p-4">
          <p className="mb-2 flex flex-wrap gap-2" aria-label="Alertes ouvertes par gravité">
            {(["critique", "serieux", "vigilance"] as const).map((g) => (
              <StatusPill key={g} etat={g} libelle={`${nombre(compte[g] ?? 0)} ${LIBELLES_GRAVITE[g]}`} />
            ))}
          </p>
          <ListeAlertes
            alertes={d.alertes}
            compact
            limite={3}
            titre="Priorités à examiner"
            titreId="alertes-titre"
          />
        </section>
      </Zone>

      {BANDES.map((b) => {
        const kpis = d.indicateurs.filter((k) => bandeDe(k) === b.cle && disponible(k));
        if (!kpis.length && !(b.cle === "execution" && d.execution)) return null;
        return (
          <Zone key={b.cle} titre={b.titre}>
            {b.cle === "execution" && d.execution ? (
              // Mêmes cadres que la page Dépenses (architecture harmonisée).
              <IndicateursExecution i={d.execution.indicateurs} n1={n1} />
            ) : (
              kpis.length > 0 && (
                <BandeauKpi colonnes={kpis.length >= 4 ? 4 : 3}>
                  {kpis.map((k) => (
                    <Kpi key={k.code} k={k} n1={n1} />
                  ))}
                </BandeauKpi>
              )
            )}
            {b.cle === "execution" && d.plan_engagement && (
              <Note etat={d.plan_engagement.nb_depassements ? "vigilance" : undefined}>
                Plan d'engagement {d.plan_engagement.exercice} · {d.plan_engagement.periode} (
                {d.plan_engagement.etat}) : plafond <Montant gnf={d.plan_engagement.plafond} />
                {d.plan_engagement.taux != null && (
                  <>
                    , consommé à <Pourcentage ratio={d.plan_engagement.taux} />
                  </>
                )}
                {d.plan_engagement.nb_depassements > 0 &&
                  ` · ${nombre(d.plan_engagement.nb_depassements)} ministère(s) en dépassement`}
                .
              </Note>
            )}
          </Zone>
        );
      })}

      {voitDepenses && (
        <Zone titre="Tendance et où agir">
          <CourbeExecution
            parMois={
              serie.length ? (
                <GroupedBarChart
                  donnees={serie}
                  categorie="libelle"
                  series={SERIES.slice(1)}
                  libelle="Engagements par mois de création"
                  hauteur={240}
                />
              ) : (
                <p className="text-base text-ink-2">Aucune série disponible.</p>
              )
            }
          />
          <div className={aDesRecettes ? "grid gap-4 lg:grid-cols-2" : ""}>
            <BlocProjectionDepenses onSection={(code) => navigate(`/depenses?ministere=${code}`)} />
            {aDesRecettes && (
              <Carte
                id="encaissements"
                titre="Encaissements fiscaux et douaniers par mois"
                sousTitre="Suivi séparé des engagements ; aucun solde n'est déduit de ce graphique."
              >
                <GroupedBarChart
                  donnees={serie}
                  categorie="libelle"
                  series={SERIES.slice(0, 1)}
                  libelle="Encaissements fiscaux et douaniers"
                  hauteur={240}
                />
              </Carte>
            )}
          </div>
        </Zone>
      )}
    </div>
  );
}

const LIBELLES_GRAVITE = { critique: "critique(s)", serieux: "sérieuse(s)", vigilance: "en vigilance" };

/** Une ligne par source utilisée : application, statut (réel / illustration) et date de situation (S7). */
function BandeauSources({
  indicateurs,
  avertissements,
}: {
  indicateurs: KpiSynthese[];
  avertissements?: string[];
}) {
  const sources = new Map<string, KpiSynthese["meta"]>();
  for (const k of indicateurs)
    if (!k.masque && !sources.has(k.meta.source)) sources.set(k.meta.source, k.meta);
  return (
    <section aria-label="Sources et dates de situation" className="flex flex-col gap-1">
      <ul className="flex flex-wrap gap-2">
        {[...sources.values()].map((m) => (
          <li key={m.source}>
            <SourceBadge meta={m} />
          </li>
        ))}
      </ul>
      {avertissements?.map((a) => (
        <p key={a} role="note" className="text-sm text-ink-2">
          {a}
        </p>
      ))}
    </section>
  );
}
