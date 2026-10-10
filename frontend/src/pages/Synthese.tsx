import { useMemo } from "react";

import { useDonnees } from "@/api/hooks";
import type { KpiSynthese, Source, Synthese as TSynthese } from "@/api/types";
import { ListeAlertes } from "@/components/Alertes";
import { DataTable, type Colonne } from "@/components/DataTable";
import { GroupedBarChart } from "@/components/GroupedBarChart";
import { BandeauKpi, KpiCard, StatusPill } from "@/components/Indicateurs";
import { Montant, Pourcentage } from "@/components/Montant";
import { SourceBadge } from "@/components/Source";
import { Carte } from "@/components/ui/primitives";
import { dateFr, dateHeureFr, enMds, moisCourt, nombre, pct } from "@/lib/format";

import { EtatPage, TitrePage } from "./commun";

const AIDES: Record<string, string> = {
  recettes: "Recettes fiscales (SAFIG) et douanières (SYDONIA) recouvrées, rapportées à l'objectif.",
  depenses_engagees: "Crédits engagés rapportés aux crédits actuels (Chaîne Dépense).",
  reste_a_payer:
    "Ordonnancé non payé, hors procédures payées hors chaîne (salaires en procédure Solde, dette en débit d'office).",
  tresorerie: "Solde de fin de période exprimé en jours de décaissements moyens (SCIE).",
  dette: "Encours total rapporté au PIB, comparé au seuil de convergence CEDEAO de 70 %.",
  personnel_ordonnance: "Dépenses de personnel (titre 2) ordonnancées dans la Chaîne Dépense.",
};

function Kpi({ k }: { k: KpiSynthese }) {
  if (k.masque) {
    return <KpiCard libelle={k.libelle} valeur="—" contexte="Hors de votre périmètre" meta={k.meta} />;
  }
  if (k.valeur === null || k.valeur === undefined) {
    return (
      <KpiCard
        libelle={k.libelle}
        valeur={<span className="text-ink-3">—</span>}
        contexte={k.meta.statut_source === "non_raccorde" ? "Source non raccordée" : "Aucune donnée"}
        meta={k.meta}
        aide={AIDES[k.code]}
      />
    );
  }
  if (k.code === "depenses_engagees") {
    return (
      <KpiCard
        libelle="Dépenses engagées"
        valeur={<Pourcentage ratio={k.taux} />}
        contexte={
          <>
            <Montant gnf={k.valeur} /> sur <Montant gnf={k.reference} /> de crédits
          </>
        }
        jauge={{ valeur: k.taux }}
        meta={k.meta}
        aide={AIDES[k.code]}
      />
    );
  }
  if (k.code === "recettes") {
    return (
      <KpiCard
        libelle="Recettes fiscales et douanières"
        valeur={<Montant gnf={k.valeur} />}
        contexte={
          <>
            <Pourcentage ratio={k.taux} /> de l'objectif (<Montant gnf={k.reference} />)
          </>
        }
        jauge={{ valeur: k.taux, repere: 0.8 }}
        etat={k.taux != null && k.taux < 0.8 ? "serieux" : undefined}
        meta={k.meta}
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
        meta={k.meta}
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
        meta={k.meta}
        aide={AIDES[k.code]}
      />
    );
  }
  if (k.code === "reste_a_payer") {
    return (
      <KpiCard
        libelle="Reste à payer ajusté"
        valeur={<Montant gnf={k.valeur} />}
        contexte={
          <>
            Payé / ordonnancé : <Pourcentage ratio={k.taux} />
          </>
        }
        meta={k.meta}
        aide={AIDES[k.code]}
      />
    );
  }
  return (
    <KpiCard
      libelle={k.code === "personnel_ordonnance" ? "Personnel ordonnancé" : k.libelle}
      valeur={<Montant gnf={k.valeur} />}
      contexte={
        k.taux != null ? (
          <>
            <Pourcentage ratio={k.taux} />{" "}
            {k.code === "personnel_ordonnance" ? "des crédits de personnel" : ""}
          </>
        ) : undefined
      }
      jauge={k.taux != null ? { valeur: k.taux } : undefined}
      meta={k.meta}
      aide={AIDES[k.code]}
    />
  );
}

const colonnesSources: Colonne<Source>[] = [
  { header: "Domaine", accessorKey: "domaine_libelle" },
  { header: "Application", accessorKey: "application" },
  { header: "Structure", accessorKey: "structure" },
  {
    header: "Dernier chargement",
    id: "dernier",
    accessorFn: (s) => s.dernier_chargement?.date ?? "",
    cell: ({ row }) => {
      const c = row.original.dernier_chargement;
      if (!c) return <span className="text-ink-2">Aucun</span>;
      return (
        <span className="flex flex-col gap-1">
          <span className="chiffres">{dateHeureFr(c.date)}</span>
          {c.statut === "echec" && <StatusPill etat="critique" libelle="Échec du chargement" />}
          {row.original.derniere_date_situation && (
            <span className="text-sm text-ink-2">
              situation au {dateFr(row.original.derniere_date_situation)}
            </span>
          )}
        </span>
      );
    },
  },
  {
    header: "Statut",
    accessorKey: "statut",
    cell: ({ row }) => {
      const s = row.original;
      return (
        <span className="flex flex-col items-start gap-1">
          <SourceBadge
            meta={{ source: s.code, statut_source: s.statut, date_situation: s.derniere_date_situation }}
          />
          {s.remarque && <span className="text-sm text-ink-2">{s.remarque}</span>}
        </span>
      );
    },
  },
];

const SERIES = [
  { cle: "recettes", libelle: "Recettes (SAFIG + SYDONIA)", couleur: "var(--serie-2)" },
  { cle: "depenses", libelle: "Dépenses engagées", couleur: "var(--serie-1)" },
];

export default function Synthese() {
  const requete = useDonnees<TSynthese>("/synthese/");
  return (
    <>
      <TitrePage exporter="synthese" titre="Synthèse" />
      <EtatPage requete={requete}>{(d) => <Contenu d={d} />}</EtatPage>
    </>
  );
}

function Contenu({ d }: { d: TSynthese }) {
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

  return (
    <div className="flex flex-col gap-4">
      <section id="indicateurs" aria-labelledby="indicateurs-titre">
        <h2 id="indicateurs-titre" className="sr-only">
          Indicateurs clés
        </h2>
        <BandeauKpi>
          {d.indicateurs.map((k) => (
            <Kpi key={k.code} k={k} />
          ))}
        </BandeauKpi>
      </section>

      <div className="grid gap-4 lg:grid-cols-12">
        <section id="alertes" aria-labelledby="alertes-titre" className="carte p-4 lg:col-span-7">
          <ListeAlertes
            alertes={d.alertes}
            compact
            limite={3}
            titre="Points d'attention"
            titreId="alertes-titre"
          />
        </section>
        <Carte
          id="mensuel"
          titre="Recettes et dépenses engagées par mois"
          sousTitre={
            aDesRecettes
              ? "En milliards de GNF"
              : "En milliards de GNF · recettes : SAFIG et SYDONIA non raccordés"
          }
          className="lg:col-span-5"
        >
          {serie.length ? (
            <GroupedBarChart
              donnees={serie}
              categorie="libelle"
              series={aDesRecettes ? SERIES : SERIES.slice(1)}
              libelle="Recettes et dépenses engagées par mois"
              hauteur={200}
            />
          ) : (
            <p className="text-base text-ink-2">Aucune série disponible.</p>
          )}
        </Carte>
      </div>

      <Carte
        id="sources"
        titre="État des sources"
        sousTitre="Dernier chargement et statut de chaque application"
      >
        <DataTable
          donnees={d.sources}
          colonnes={colonnesSources}
          libelle="État des sources"
          recherche={false}
        />
      </Carte>
    </div>
  );
}
