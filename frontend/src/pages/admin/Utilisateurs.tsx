import { KeyRound, UserPlus } from "lucide-react";
import { useState, type FormEvent } from "react";

import {
  messageErreur,
  useAdmin,
  useListesAdmin,
  useMutationAdmin,
  type UtilisateurAdmin,
} from "@/api/admin";
import { api } from "@/api/client";
import { DataTable } from "@/components/DataTable";
import { StatusPill } from "@/components/Indicateurs";
import { Bouton, Carte } from "@/components/ui/primitives";
import { Sheet } from "@/components/ui/sheet";
import { Case, CasesMultiples, Champ, Confirmation, Entree, Liste, Retour } from "@/components/ui/formulaire";
import { dateHeureFr } from "@/lib/format";

import { EtatBloc } from "./commun";

const VIDE = {
  username: "",
  first_name: "",
  last_name: "",
  email: "",
  role: "lecteur",
  domaines: [] as string[],
  structure: "",
  is_active: true,
  mot_de_passe: "",
};

export default function Utilisateurs() {
  const r = useAdmin<UtilisateurAdmin[]>("utilisateurs/");
  const listes = useListesAdmin();
  const [edite, setEdite] = useState<UtilisateurAdmin | "nouveau" | null>(null);
  const libelleRole = (c: string) => listes.data?.roles.find((x) => x.code === c)?.libelle ?? c;
  return (
    <Carte
      id="utilisateurs"
      titre="Utilisateurs et accès"
      sousTitre="Rôle et domaines visibles de chaque compte. Les profils cabinet et administrateur doivent activer la double authentification."
      actions={
        <Bouton variante="primaire" onClick={() => setEdite("nouveau")}>
          <UserPlus className="h-4 w-4" aria-hidden /> Nouvel utilisateur
        </Bouton>
      }
    >
      <EtatBloc requete={r}>
        {(u) => (
          <DataTable
            donnees={u}
            libelle="Utilisateurs"
            onLigne={setEdite}
            colonnes={[
              { header: "Identifiant", accessorKey: "username" },
              { header: "Nom", id: "nom", accessorFn: (x) => `${x.first_name} ${x.last_name}`.trim() || "—" },
              {
                header: "Rôle",
                accessorKey: "role",
                cell: ({ getValue }) => libelleRole(getValue() as string),
              },
              { header: "Structure", accessorKey: "structure" },
              {
                header: "Domaines",
                id: "domaines",
                accessorFn: (x) =>
                  ["ministre_cabinet", "dnsi_admin"].includes(x.role) ? "Tous" : `${x.domaines.length}`,
              },
              { header: "2FA", accessorKey: "a_2fa", cell: ({ getValue }) => (getValue() ? "Activée" : "—") },
              {
                header: "Dernière connexion",
                accessorKey: "last_login",
                cell: ({ getValue }) => dateHeureFr(getValue() as string),
              },
              {
                header: "État",
                accessorKey: "is_active",
                cell: ({ getValue }) =>
                  getValue() ? (
                    <StatusPill etat="bon" libelle="Actif" />
                  ) : (
                    <StatusPill etat="vigilance" libelle="Désactivé" />
                  ),
              },
            ]}
          />
        )}
      </EtatBloc>
      {edite && (
        <FormulaireUtilisateur
          utilisateur={edite === "nouveau" ? null : edite}
          onFermer={() => setEdite(null)}
        />
      )}
    </Carte>
  );
}

function FormulaireUtilisateur({
  utilisateur,
  onFermer,
}: {
  utilisateur: UtilisateurAdmin | null;
  onFermer: () => void;
}) {
  const listes = useListesAdmin();
  const [f, setF] = useState(utilisateur ? { ...VIDE, ...utilisateur, mot_de_passe: "" } : VIDE);
  const [reinit, setReinit] = useState(false);
  const enregistrer = useMutationAdmin((corps: object) =>
    utilisateur
      ? api.patch<UtilisateurAdmin>(`/admin/utilisateurs/${utilisateur.id}/`, corps)
      : api.post<UtilisateurAdmin>("/admin/utilisateurs/", corps),
  );
  const reinit2fa = useMutationAdmin(() =>
    api.post<{ detail: string }>(`/admin/utilisateurs/${utilisateur!.id}/reinitialiser-2fa/`),
  );
  const tousDomaines = ["ministre_cabinet", "dnsi_admin"].includes(f.role);

  function soumettre(e: FormEvent) {
    e.preventDefault();
    const { mot_de_passe, ...reste } = f;
    enregistrer.mutate(mot_de_passe ? { ...reste, mot_de_passe } : reste);
  }

  return (
    <Sheet
      ouvert
      onChange={(o) => !o && onFermer()}
      titre={utilisateur ? `Compte ${utilisateur.username}` : "Nouvel utilisateur"}
    >
      <form onSubmit={soumettre} className="flex flex-col gap-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Champ libelle="Identifiant">
            {(id) => (
              <Entree
                id={id}
                name="username"
                required
                autoComplete="off"
                spellCheck={false}
                disabled={Boolean(utilisateur)}
                value={f.username}
                onChange={(e) => setF({ ...f, username: e.target.value })}
              />
            )}
          </Champ>
          <Champ libelle="Adresse électronique">
            {(id) => (
              <Entree
                id={id}
                name="email"
                type="email"
                autoComplete="off"
                spellCheck={false}
                value={f.email}
                onChange={(e) => setF({ ...f, email: e.target.value })}
              />
            )}
          </Champ>
          <Champ libelle="Prénom">
            {(id) => (
              <Entree
                id={id}
                name="first_name"
                autoComplete="off"
                value={f.first_name}
                onChange={(e) => setF({ ...f, first_name: e.target.value })}
              />
            )}
          </Champ>
          <Champ libelle="Nom">
            {(id) => (
              <Entree
                id={id}
                name="last_name"
                autoComplete="off"
                value={f.last_name}
                onChange={(e) => setF({ ...f, last_name: e.target.value })}
              />
            )}
          </Champ>
          <Champ libelle="Rôle">
            {(id) => (
              <Liste id={id} value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}>
                {listes.data?.roles.map((r) => (
                  <option key={r.code} value={r.code}>
                    {r.libelle}
                  </option>
                ))}
              </Liste>
            )}
          </Champ>
          <Champ libelle="Structure" aide="DGI, DGD, Trésor, DGB, DGPEIP…">
            {(id, d) => (
              <Entree
                id={id}
                autoComplete="off"
                aria-describedby={d}
                value={f.structure}
                onChange={(e) => setF({ ...f, structure: e.target.value })}
              />
            )}
          </Champ>
        </div>
        {tousDomaines ? (
          <p className="text-base text-ink-2">Ce rôle voit tous les domaines.</p>
        ) : (
          <CasesMultiples
            legende="Domaines visibles"
            options={(listes.data?.domaines ?? []).filter((d) => d.code !== "synthese")}
            valeur={f.domaines}
            onChange={(v) => setF({ ...f, domaines: v })}
          />
        )}
        <Champ
          libelle={utilisateur ? "Nouveau mot de passe (facultatif)" : "Mot de passe (facultatif)"}
          aide="12 caractères au moins, avec minuscule, majuscule, chiffre et caractère spécial. Vide à la création : un mot de passe est généré et affiché une fois."
        >
          {(id, d) => (
            <Entree
              id={id}
              name="new-password"
              type="password"
              autoComplete="new-password"
              aria-describedby={d}
              value={f.mot_de_passe}
              onChange={(e) => setF({ ...f, mot_de_passe: e.target.value })}
            />
          )}
        </Champ>
        {utilisateur && (
          <Case
            libelle="Compte actif"
            checked={f.is_active}
            onChange={(e) => setF({ ...f, is_active: e.target.checked })}
          />
        )}
        {enregistrer.isError && <Retour ok={false}>{messageErreur(enregistrer.error)}</Retour>}
        {enregistrer.data?.mot_de_passe_initial && (
          <Retour ok>
            Compte créé. Mot de passe initial, à transmettre de façon sûre (il ne sera plus affiché) :{" "}
            <code translate="no" className="break-all font-bold">
              {enregistrer.data.mot_de_passe_initial}
            </code>
          </Retour>
        )}
        {enregistrer.isSuccess && !enregistrer.data?.mot_de_passe_initial && (
          <Retour ok>Compte enregistré.</Retour>
        )}
        <div className="flex flex-wrap gap-2">
          <Bouton type="submit" variante="primaire" disabled={enregistrer.isPending}>
            {enregistrer.isPending ? "Enregistrement…" : utilisateur ? "Enregistrer" : "Créer le compte"}
          </Bouton>
          {utilisateur?.a_2fa && (
            <Bouton onClick={() => setReinit(true)}>
              <KeyRound className="h-4 w-4" aria-hidden /> Réinitialiser la double authentification
            </Bouton>
          )}
        </div>
        {reinit2fa.data && <Retour ok>{reinit2fa.data.detail}</Retour>}
      </form>
      <Confirmation
        ouvert={reinit}
        onChange={setReinit}
        titre="Réinitialiser la double authentification ?"
        message="L'utilisateur devra enregistrer une nouvelle application d'authentification à sa prochaine connexion."
        libelleAction="Réinitialiser"
        enCours={reinit2fa.isPending}
        onConfirmer={() => reinit2fa.mutate(undefined, { onSuccess: () => setReinit(false) })}
      />
    </Sheet>
  );
}
