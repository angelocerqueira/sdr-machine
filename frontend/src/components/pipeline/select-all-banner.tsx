"use client";

import { useCallback, useState } from "react";
import { getLeadIds } from "@/lib/api";
import type { useBulkSelection } from "./use-bulk-selection";

interface Props {
  sel: ReturnType<typeof useBulkSelection>;
  visibleIds: number[];
  /** total leads matching current filter */
  pageTotal: number;
  filters: Record<string, string>;
}

export function SelectAllBanner({ sel, visibleIds, pageTotal, filters }: Props) {
  const [busy, setBusy] = useState(false);
  const [truncatedWarning, setTruncatedWarning] = useState(false);

  const pageAllSelected =
    visibleIds.length > 0 && visibleIds.every((id) => sel.has(id));
  const showOfferAllFilter =
    pageAllSelected && pageTotal > visibleIds.length && !sel.isAllFilterMode;

  const handleSelectAllFilter = useCallback(async () => {
    if (busy) return;
    setBusy(true);
    setTruncatedWarning(false);
    try {
      const res = await getLeadIds(filters);
      if (res.truncated) {
        // Backend cap reached. Don't enter all_filter mode — every dispatch would
        // throw BULK_LIMIT_EXCEEDED and look like a silent failure. Warn instead.
        setTruncatedWarning(true);
        return;
      }
      sel.selectAllFilter(filters, res.total);
    } catch {
      // best-effort; selection stays as page-only
    } finally {
      setBusy(false);
    }
  }, [busy, filters, sel]);

  if (sel.isAllFilterMode) {
    return (
      <div className="flex items-center justify-between rounded-lg border border-accent/30 bg-accent-soft px-4 py-2 text-sm">
        <span className="text-accent">
          ✓ Todos os {sel.totalInFilter} leads do filtro selecionados.
        </span>
        <button
          type="button"
          onClick={() => sel.clear()}
          className="t-eyebrow text-text-secondary hover:text-text transition-default cursor-pointer"
        >
          Limpar seleção
        </button>
      </div>
    );
  }

  if (truncatedWarning) {
    return (
      <div className="flex items-center justify-between rounded-lg border border-warn/30 bg-warn/10 px-4 py-2 text-sm">
        <span className="text-warn">
          ⚠ Filtro tem mais de 5000 leads. Refine os filtros para selecionar todos.
        </span>
        <button
          type="button"
          onClick={() => setTruncatedWarning(false)}
          className="t-eyebrow text-text-secondary hover:text-text transition-default cursor-pointer"
        >
          Dispensar
        </button>
      </div>
    );
  }

  if (!showOfferAllFilter) return null;

  return (
    <div className="flex items-center justify-between rounded-lg border border-accent/20 bg-accent-soft/50 px-4 py-2 text-sm">
      <span className="text-text-secondary">
        Os {visibleIds.length} desta página estão selecionados.
      </span>
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={handleSelectAllFilter}
          disabled={busy}
          className="t-eyebrow text-accent hover:underline disabled:opacity-50 cursor-pointer"
        >
          {busy
            ? "Carregando..."
            : `Selecionar todos os ${pageTotal} leads do filtro →`}
        </button>
        <button
          type="button"
          onClick={() => sel.clear()}
          className="t-eyebrow text-text-secondary hover:text-text transition-default cursor-pointer"
        >
          Limpar seleção
        </button>
      </div>
    </div>
  );
}
