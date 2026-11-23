import { Building2, CalendarDays, ClipboardList, FileText } from "lucide-react";
import type { ReactNode } from "react";

import type { Alerte } from "@/api/types";
import { dateFr, dateHeureFr, nombre } from "@/lib/format";

import { StatusPill } from "./Indicateurs";

const STATUTS = { nouvelle: "Nouvelle", vue: "Vue", traitee: "Traitée" };

function ChampDossier({ libelle, children }: { libelle: string; children: ReactNode }) {
  const absent = children == null || children === "";
  return (
    <div className="min-w-0">
      <dt className="text-xs text-ink-2">{libelle}</dt>
      <dd className={`whitespace-pre-wrap text-sm ${absent ? "text-ink-2" : "font-semibold text-ink"}`}>
        {absent ? "Non renseigné" : children}
      </dd>
    </div>
  );
}

/** Fiche de suivi, en version resserrée : en-tête sur une ligne, chiffres clés, action proposée, objet,
 * puis situation, rattachement et dates côte à côte. Mêmes rubriques et mêmes intitulés qu'auparavant. */
export function FicheDossier({ a, titreId }: { a: Alerte; titreId: string }) {
  const d = a.donnees ?? {};
  const texte = (cle: string) => (d[cle] == null || String(d[cle]).trim() === "" ? null : String(d[cle]));
  const jours = texte("jours") == null ? null : Number(d.jours);
  const anciennete =
    jours != null && Number.isFinite(jours) && jours >= 0
      ? `${nombre(jours)} jour${jours === 1 ? "" : "s"}`
      : "Non renseignée";
  const rubrique = "flex items-center gap-1.5 text-sm font-bold text-ink";
  return (
    <div className="[overflow-wrap:anywhere]">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-border bg-zebra px-3 py-2">
        <div className="flex min-w-0 flex-wrap items-baseline gap-x-2">
          <span className="text-xs text-ink-2">Fiche de suivi</span>
          <h4 id={titreId} className="text-base font-bold text-navy dark:text-ink">
            Dossier n° {texte("numero")}
          </h4>
          {texte("libelle_titre") && <span className="text-sm text-ink-2">· {texte("libelle_titre")}</span>}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusPill etat={a.severite} />
          <span className="rounded border border-border bg-surface px-1.5 py-0.5 text-xs font-semibold text-ink">
            {STATUTS[a.statut]}
          </span>
        </div>
      </header>

      <div className="flex flex-col gap-3 p-3">
        <dl className="flex flex-wrap gap-x-8 gap-y-2">
          <div className="min-w-0">
            <dt className="text-xs text-ink-2">Montant engagé</dt>
            <dd className="chiffres text-md font-bold text-ink">{a.valeur || "Non renseigné"}</dd>
          </div>
          <div className="min-w-0">
            <dt className="text-xs text-ink-2">En attente depuis</dt>
            <dd className="chiffres text-md font-bold text-ink">{anciennete}</dd>
            <dd className="text-xs text-ink-2">
              À la situation du {a.date_situation ? dateFr(a.date_situation) : "—"}
            </dd>
          </div>
        </dl>

        <section
          aria-labelledby={`${titreId}-action`}
          className="rounded border border-l-4 border-border border-l-navy bg-zebra px-3 py-2"
        >
          <h5 id={`${titreId}-action`} className={rubrique}>
            <ClipboardList className="h-4 w-4 shrink-0" aria-hidden />
            Action proposée
          </h5>
          <p className="mt-1 whitespace-pre-wrap text-sm text-ink">
            {a.action_recommandee ||
              "Faire qualifier le motif de l’attente et confirmer la décision attendue auprès du service concerné."}
          </p>
        </section>

        <section aria-labelledby={`${titreId}-objet`}>
          <h5 id={`${titreId}-objet`} className={rubrique}>
            <FileText className="h-4 w-4 shrink-0 text-ink-2" aria-hidden />
            Objet du dossier
          </h5>
          <p className="mt-1 whitespace-pre-wrap text-sm text-ink">
            {texte("objet") || "Objet non renseigné"}
          </p>
          <dl className="mt-2">
            <ChampDossier libelle="Bénéficiaire">{texte("beneficiaire")}</ChampDossier>
          </dl>
        </section>

        <div className="grid gap-x-6 gap-y-3 border-t border-border pt-3 md:grid-cols-3">
          <section aria-labelledby={`${titreId}-traitement`}>
            <h5 id={`${titreId}-traitement`} className={rubrique}>
              Situation et traitement
            </h5>
            <dl className="mt-2 flex flex-col gap-2">
              <ChampDossier libelle="Étape en attente">{texte("etape")}</ChampDossier>
              <ChampDossier libelle="Acteur concerné">{texte("acteur")}</ChampDossier>
              <ChampDossier libelle="État du dossier">{texte("etat")}</ChampDossier>
              <ChampDossier libelle="Procédure">{texte("procedure")}</ChampDossier>
            </dl>
          </section>

          <section aria-labelledby={`${titreId}-identification`}>
            <h5 id={`${titreId}-identification`} className={rubrique}>
              <Building2 className="h-4 w-4 shrink-0 text-ink-2" aria-hidden />
              Rattachement administratif
            </h5>
            <dl className="mt-2 flex flex-col gap-2">
              <ChampDossier libelle="Ministère / institution">{texte("ministere")}</ChampDossier>
              <ChampDossier libelle="Service">{texte("service")}</ChampDossier>
              <ChampDossier libelle="Imputation budgétaire">{texte("imputation")}</ChampDossier>
            </dl>
          </section>

          <section aria-labelledby={`${titreId}-suivi`}>
            <h5 id={`${titreId}-suivi`} className={rubrique}>
              <CalendarDays className="h-4 w-4 shrink-0 text-ink-2" aria-hidden />
              Dates et notifications
            </h5>
            <dl className="mt-2 flex flex-col gap-2">
              <ChampDossier libelle="Création du dossier">
                {texte("date_creation") && dateFr(texte("date_creation"))}
              </ChampDossier>
              <ChampDossier libelle="Notification par courriel">
                {a.notifiee_le ? dateHeureFr(a.notifiee_le) : "Envoi non renseigné"}
              </ChampDossier>
              <ChampDossier libelle="Relance par courriel">
                {a.relancee_le ? dateHeureFr(a.relancee_le) : "Relance non renseignée"}
              </ChampDossier>
            </dl>
          </section>
        </div>
      </div>
    </div>
  );
}
