import { RefreshCw } from "lucide-react";
import { useState, type FormEvent } from "react";

import { messageErreur, useAdmin, useMutationAdmin, type RegleAlerte } from "@/api/admin";
import { api } from "@/api/client";
import { DataTable } from "@/components/DataTable";
import { StatusPill } from "@/components/Indicateurs";
import { Bouton, Carte } from "@/components/ui/primitives";
import { Sheet } from "@/components/ui/sheet";
import { Case, Champ, Entree, Liste, Retour, ZoneTexte } from "@/components/ui/formulaire";
import { DOMAINES_LIBELLES } from "@/lib/sources";

import { EtatBloc } from "./commun";

export default function Regles() {
  const r = useAdmin<RegleAlerte[]>("regles-alerte/");
  const [edite, setEdite] = useState<RegleAlerte | null>(null);
  const evaluer = useMutationAdmin(() =>
    api.post<{ alertes_creees: number }>("/admin/regles-alerte/evaluer/"),
  );
  const basculer = useMutationAdmin((x: RegleAlerte) =>
    api.patch(`/admin/regles-alerte/${x.id}/`, { actif: !x.actif }),
  );
  return (
    <Carte
      id="regles"
      titre="Règles d'alerte"
      sousTitre="Activer ou désactiver une règle, ajuster sa sévérité, ses seuils et ses messages. Les variables entre accolades ({nombre}, {montant}…) sont remplacées à l'évaluation."
      actions={
        <Bouton onClick={() => evaluer.mutate(undefined)} disabled={evaluer.isPending}>
          <RefreshCw className="h-4 w-4" aria-hidden />{" "}
          {evaluer.isPending ? "Évaluation…" : "Réévaluer les alertes"}
        </Bouton>
      }
    >
      {evaluer.data && (
        <div className="mb-3">
          <Retour ok>{evaluer.data.alertes_creees} alertes produites.</Retour>
        </div>
      )}
      <EtatBloc requete={r}>
        {(regles) => (
          <DataTable
            donnees={regles}
            libelle="Règles d'alerte"
            onLigne={setEdite}
            colonnes={[
              { header: "Règle", accessorKey: "titre_modele" },
              {
                header: "Domaine",
                accessorKey: "domaine",
                cell: ({ getValue }) => DOMAINES_LIBELLES[getValue() as string] ?? getValue(),
              },
              {
                header: "Sévérité",
                accessorKey: "severite",
                cell: ({ row }) => <StatusPill etat={row.original.severite} />,
              },
              { header: "Ouvertes", accessorKey: "nb_alertes_ouvertes", meta: { numerique: true } },
              {
                header: "Active",
                accessorKey: "actif",
                cell: ({ row }) => (
                  <Bouton
                    variante="discret"
                    onClick={(e) => {
                      e.stopPropagation();
                      basculer.mutate(row.original);
                    }}
                    aria-pressed={row.original.actif}
                  >
                    {row.original.actif ? "Oui (désactiver)" : "Non (activer)"}
                  </Bouton>
                ),
              },
            ]}
          />
        )}
      </EtatBloc>
      {edite && <EditionRegle regle={edite} onFermer={() => setEdite(null)} />}
    </Carte>
  );
}

function EditionRegle({ regle, onFermer }: { regle: RegleAlerte; onFermer: () => void }) {
  const [f, setF] = useState({ ...regle, seuils: JSON.stringify(regle.seuils ?? {}, null, 2) });
  const [erreur, setErreur] = useState<string | null>(null);
  const enregistrer = useMutationAdmin((corps: object) =>
    api.patch(`/admin/regles-alerte/${regle.id}/`, corps),
  );

  function soumettre(e: FormEvent) {
    e.preventDefault();
    let seuils;
    try {
      seuils = JSON.parse(f.seuils || "{}");
    } catch {
      setErreur("JSON invalide.");
      return;
    }
    setErreur(null);
    enregistrer.mutate({
      severite: f.severite,
      seuils,
      titre_modele: f.titre_modele,
      message_modele: f.message_modele,
      action_recommandee: f.action_recommandee,
      lien: f.lien,
      actif: f.actif,
    });
  }

  return (
    <Sheet
      ouvert
      onChange={(o) => !o && onFermer()}
      titre="Règle d'alerte"
      description={`${regle.code} · ${regle.classe.split(".").pop()}`}
    >
      <form onSubmit={soumettre} className="flex flex-col gap-4">
        <Champ libelle="Sévérité">
          {(id) => (
            <Liste
              id={id}
              value={f.severite}
              onChange={(e) => setF({ ...f, severite: e.target.value as RegleAlerte["severite"] })}
            >
              <option value="critique">Critique</option>
              <option value="serieux">Sérieux</option>
              <option value="vigilance">Vigilance</option>
            </Liste>
          )}
        </Champ>
        <Champ libelle="Titre (modèle)">
          {(id) => (
            <Entree
              id={id}
              value={f.titre_modele}
              onChange={(e) => setF({ ...f, titre_modele: e.target.value })}
            />
          )}
        </Champ>
        <Champ libelle="Message (modèle)">
          {(id) => (
            <ZoneTexte
              id={id}
              rows={3}
              className="font-sans"
              value={f.message_modele}
              onChange={(e) => setF({ ...f, message_modele: e.target.value })}
            />
          )}
        </Champ>
        <Champ libelle="Action recommandée">
          {(id) => (
            <ZoneTexte
              id={id}
              rows={2}
              className="font-sans"
              value={f.action_recommandee}
              onChange={(e) => setF({ ...f, action_recommandee: e.target.value })}
            />
          )}
        </Champ>
        <Champ
          libelle="Seuils propres à la règle (JSON)"
          aide="Les seuils généraux se règlent dans « Paramètres et seuils »."
          erreur={erreur}
        >
          {(id, d) => (
            <ZoneTexte
              id={id}
              rows={3}
              aria-describedby={d}
              spellCheck={false}
              value={f.seuils}
              onChange={(e) => setF({ ...f, seuils: e.target.value })}
            />
          )}
        </Champ>
        <Champ libelle="Page liée">
          {(id) => <Entree id={id} value={f.lien} onChange={(e) => setF({ ...f, lien: e.target.value })} />}
        </Champ>
        <Case
          libelle="Règle active"
          checked={f.actif}
          onChange={(e) => setF({ ...f, actif: e.target.checked })}
        />
        {enregistrer.isError && <Retour ok={false}>{messageErreur(enregistrer.error)}</Retour>}
        {enregistrer.isSuccess && (
          <Retour ok>Règle enregistrée. Réévaluez les alertes pour l'appliquer.</Retour>
        )}
        <div>
          <Bouton type="submit" variante="primaire" disabled={enregistrer.isPending}>
            Enregistrer
          </Bouton>
        </div>
      </form>
    </Sheet>
  );
}
