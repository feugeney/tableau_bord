import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
  type VisibilityState,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ChevronsUpDown, Download, Search } from "lucide-react";
import { useState } from "react";

import { cn } from "@/lib/utils";

import { Bouton } from "./ui/primitives";

export type Colonne<T> = ColumnDef<T, unknown> & {
  meta?: { numerique?: boolean; exporter?: (l: T) => string };
};

const TAILLE_PAGE = 50;

/**
 * Tableau dense : en-têtes en capitales grises, zébrage léger, survol visible, tri (flèche dorée),
 * première colonne fixe sur mobile, pagination au-delà de 50 lignes, recherche et export CSV.
 */
export function DataTable<T>({
  donnees,
  colonnes,
  libelle,
  onLigne,
  ligneActive,
  recherche = true,
  nomExport,
  triInitial = [],
  vide = "Aucune ligne ne correspond.",
  visibilite,
}: {
  donnees: T[];
  colonnes: Colonne<T>[];
  libelle: string;
  onLigne?: (ligne: T) => void;
  ligneActive?: (ligne: T) => boolean;
  recherche?: boolean;
  nomExport?: string;
  triInitial?: SortingState;
  /** Message affiché quand le tableau est vide. */
  vide?: string;
  /** Colonnes masquées par l'utilisateur ({ id: false }) ; les autres restent affichées. */
  visibilite?: VisibilityState;
}) {
  const [tri, setTri] = useState<SortingState>(triInitial);
  const [filtre, setFiltre] = useState("");
  const pagine = donnees.length > TAILLE_PAGE;
  const table = useReactTable({
    data: donnees,
    columns: colonnes,
    state: { sorting: tri, globalFilter: filtre, columnVisibility: visibilite ?? {} },
    onSortingChange: setTri,
    onGlobalFilterChange: setFiltre,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    ...(pagine ? { getPaginationRowModel: getPaginationRowModel() } : {}),
    initialState: { pagination: { pageSize: TAILLE_PAGE } },
  });

  function exporter() {
    const cols = table.getVisibleLeafColumns();
    const entete = cols.map((c) => String(c.columnDef.header ?? c.id));
    const lignes = table.getSortedRowModel().rows.map((r) =>
      cols.map((c) => {
        const m = (c.columnDef as Colonne<T>).meta;
        return m?.exporter ? m.exporter(r.original) : String(r.getValue(c.id) ?? "");
      }),
    );
    const csv = [entete, ...lignes]
      .map((l) => l.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(";"))
      .join("\n");
    const url = URL.createObjectURL(new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `${nomExport ?? "export"}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const lignes = table.getRowModel().rows;
  return (
    <div className="min-w-0">
      {(recherche || nomExport) && (
        <div className="sans-impression mb-2 flex flex-wrap items-center justify-between gap-2">
          {recherche && (
            <label className="relative block w-full max-w-xs">
              <span className="sr-only">Rechercher dans le tableau</span>
              <Search className="absolute left-2 top-2 h-4 w-4 text-ink-3" aria-hidden />
              <input
                type="search"
                name="recherche"
                autoComplete="off"
                value={filtre}
                onChange={(e) => setFiltre(e.target.value)}
                placeholder="Rechercher…"
                className="min-h-8 w-full rounded-sm border border-border bg-surface py-1 pl-8 pr-2 text-base text-ink placeholder:text-ink-3"
              />
            </label>
          )}
          {nomExport && (
            <Bouton onClick={exporter}>
              <Download className="h-4 w-4" aria-hidden /> Exporter (CSV)
            </Bouton>
          )}
        </div>
      )}
      <div className="w-full overflow-x-auto rounded border border-border [overscroll-behavior-x:contain]">
        <table className="w-full border-collapse text-base">
          <caption className="sr-only">{libelle}</caption>
          <thead>
            {table.getHeaderGroups().map((g) => (
              <tr key={g.id} className="border-b border-border">
                {g.headers.map((h, i) => {
                  const numerique = (h.column.columnDef as Colonne<T>).meta?.numerique;
                  const sens = h.column.getIsSorted();
                  return (
                    <th
                      key={h.id}
                      scope="col"
                      aria-sort={sens === "asc" ? "ascending" : sens === "desc" ? "descending" : undefined}
                      className={cn(
                        "etiquette whitespace-nowrap bg-surface px-3 py-2",
                        numerique ? "text-right" : "text-left",
                        i === 0 && "sticky left-0 z-10 md:static",
                      )}
                    >
                      {h.column.getCanSort() ? (
                        <button
                          type="button"
                          onClick={h.column.getToggleSortingHandler()}
                          className={cn(
                            "etiquette inline-flex items-center gap-1 rounded-sm hover:text-ink",
                            numerique && "flex-row-reverse",
                          )}
                        >
                          {flexRender(h.column.columnDef.header, h.getContext())}
                          {sens === "asc" ? (
                            <ArrowUp className="h-3.5 w-3.5 text-gold" aria-hidden />
                          ) : sens === "desc" ? (
                            <ArrowDown className="h-3.5 w-3.5 text-gold" aria-hidden />
                          ) : (
                            <ChevronsUpDown className="h-3.5 w-3.5 text-ink-3" aria-hidden />
                          )}
                        </button>
                      ) : (
                        flexRender(h.column.columnDef.header, h.getContext())
                      )}
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {lignes.map((r, n) => {
              const active = ligneActive?.(r.original);
              const fond = active ? "bg-hover" : n % 2 ? "bg-zebra" : "bg-surface";
              return (
                <tr
                  key={r.id}
                  className={cn(
                    "group border-b border-border last:border-0",
                    fond,
                    onLigne && "cursor-pointer",
                  )}
                  onClick={onLigne ? () => onLigne(r.original) : undefined}
                >
                  {r.getVisibleCells().map((c, i) => {
                    const numerique = (c.column.columnDef as Colonne<T>).meta?.numerique;
                    const contenu = flexRender(c.column.columnDef.cell, c.getContext());
                    return (
                      <td
                        key={c.id}
                        className={cn(
                          "px-3 py-2 align-middle text-ink group-hover:bg-hover",
                          numerique && "chiffres text-right",
                          i === 0 && cn("sticky left-0 z-[1] md:static", fond),
                        )}
                      >
                        {i === 0 && onLigne ? (
                          // Ligne activable au clavier : le premier champ est un vrai bouton.
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              onLigne(r.original);
                            }}
                            className="rounded-sm text-left font-bold text-ink underline-offset-2 hover:underline"
                          >
                            {contenu}
                          </button>
                        ) : (
                          contenu
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
            {lignes.length === 0 && (
              <tr>
                <td
                  colSpan={table.getVisibleLeafColumns().length}
                  className="px-3 py-6 text-center text-ink-2"
                >
                  {vide}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {pagine && (
        <div className="sans-impression mt-2 flex items-center justify-end gap-2 text-sm text-ink-2">
          <span aria-live="polite">
            Page {table.getState().pagination.pageIndex + 1} sur {table.getPageCount()}
          </span>
          <Bouton onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}>
            Précédente
          </Bouton>
          <Bouton onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}>
            Suivante
          </Bouton>
        </div>
      )}
    </div>
  );
}
