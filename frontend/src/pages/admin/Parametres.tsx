import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { messageErreur, useMutationAdmin, type Parametre } from "@/api/admin";
import { api } from "@/api/client";
import { Bouton, Carte } from "@/components/ui/primitives";
import { Entree, Retour } from "@/components/ui/formulaire";
import { dateHeureFr } from "@/lib/format";

import { EtatBloc } from "./commun";

/** Seuils des règles de gestion (core_parametre) ; toute modification est journalisée. */
export default function Parametres() {
  const r = useQuery({
    queryKey: ["admin", "parametres"],
    queryFn: () => api.get<Parametre[]>("/parametres/"),
  });
  return (
    <Carte
      id="parametres"
      titre="Paramètres et seuils"
      sousTitre="Seuils des règles de gestion (statut des ministères, trésorerie, recouvrement, dette…). Les montants sont en GNF, les taux entre 0 et 1."
    >
      <EtatBloc requete={r}>
        {(params) => (
          <ul className="divide-y divide-border">
            {params.map((p) => (
              <LigneParametre key={p.code} p={p} />
            ))}
          </ul>
        )}
      </EtatBloc>
    </Carte>
  );
}

function LigneParametre({ p }: { p: Parametre }) {
  const [valeur, setValeur] = useState(String(p.valeur));
  const enregistrer = useMutationAdmin((v: unknown) =>
    api.patch<Parametre>(`/parametres/${p.code}/`, { valeur: v }),
  );
  const modifie = valeur !== String(p.valeur);
  const id = `param-${p.code}`;

  function valider() {
    const nombre = Number(valeur.replace(",", ".").replace(/\s/g, ""));
    enregistrer.mutate(valeur.trim() !== "" && !Number.isNaN(nombre) ? nombre : valeur);
  }

  return (
    <li className="grid gap-2 py-3 md:grid-cols-[minmax(0,1fr)_220px_auto] md:items-center">
      <label htmlFor={id} className="min-w-0">
        <span className="block text-base text-ink">{p.libelle}</span>
        <span className="block text-sm text-ink-2">
          <code translate="no">{p.code}</code>
          {p.unite && ` · ${p.unite}`} · modifié le {dateHeureFr(p.modifie_le)}
        </span>
      </label>
      <Entree
        id={id}
        autoComplete="off"
        spellCheck={false}
        className="chiffres mt-0"
        value={valeur}
        onChange={(e) => setValeur(e.target.value)}
      />
      <Bouton onClick={valider} disabled={!modifie || enregistrer.isPending}>
        Enregistrer
      </Bouton>
      {enregistrer.isError && (
        <div className="md:col-span-3">
          <Retour ok={false}>{messageErreur(enregistrer.error)}</Retour>
        </div>
      )}
      {enregistrer.isSuccess && !modifie && (
        <div className="md:col-span-3">
          <Retour ok>Valeur enregistrée ; les indicateurs sont recalculés.</Retour>
        </div>
      )}
    </li>
  );
}
