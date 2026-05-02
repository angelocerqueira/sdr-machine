"use client";

import { Suspense, useCallback, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { PipelineControls } from "@/components/pipeline-controls";
import { PipelineKanban } from "@/components/pipeline/pipeline-kanban";
import { PipelineTable } from "@/components/pipeline/pipeline-table";
import { PipelineToolbar } from "@/components/pipeline/pipeline-toolbar";
import { SelectAllBanner } from "@/components/pipeline/select-all-banner";
import { BulkActionBar } from "@/components/pipeline/bulk-action-bar";
import { useBulkSelection } from "@/components/pipeline/use-bulk-selection";
import { FiltrosAtivosBanner } from "@/components/pipeline/filtros-ativos-banner";
import { PipelineFunnel } from "@/components/pipeline/pipeline-funnel";
import { usePipelineCounts } from "@/components/pipeline/use-pipeline-counts";

type PipelineView = "kanban" | "table";

const FILTER_KEYS = [
  "status",
  "nicho",
  "cidade",
  "score_min",
  "score_max",
  "has_telefone",
  "has_email",
  "search",
  "perfil_lead",
  "nicho_canonico",
  "order_by",
] as const;

function isPipelineView(value: string | null): value is PipelineView {
  return value === "kanban" || value === "table";
}

function readStoredView(): PipelineView | null {
  if (typeof window === "undefined") return null;
  try {
    const stored = window.localStorage.getItem("sdr-pipeline-view");
    return isPipelineView(stored) ? stored : null;
  } catch {
    // localStorage unavailable; stay with default
    return null;
  }
}

export default function PipelinePage() {
  return (
    <Suspense fallback={<div className="text-text-muted text-sm py-8 text-center">Carregando...</div>}>
      <PipelineInner />
    </Suspense>
  );
}

function PipelineInner() {
  const sp = useSearchParams();
  const qsView = sp.get("view");

  // Read localStorage once on mount as fallback when query string is absent.
  // Lazy initializer avoids the read on every render and avoids setState-in-effect.
  const [storedView] = useState<PipelineView | null>(readStoredView);

  // Resolve view: query string > localStorage > default kanban
  const view: PipelineView = useMemo(() => {
    if (isPipelineView(qsView)) return qsView;
    if (storedView) return storedView;
    return "kanban";
  }, [qsView, storedView]);

  const sel = useBulkSelection();
  const [visibleIds, setVisibleIds] = useState<number[]>([]);
  const [pageTotal, setPageTotal] = useState(0);
  const [refreshKey, setRefreshKey] = useState(0);

  const filters = useMemo(() => {
    const out: Record<string, string> = {};
    for (const key of FILTER_KEYS) {
      const v = sp.get(key);
      if (v) out[key] = v;
    }
    return out;
  }, [sp]);

  const { counts, staleDelta, dismissStale, refresh: refreshCounts } = usePipelineCounts(filters);

  const handleChanged = () => setRefreshKey((k) => k + 1);

  const handleRefresh = useCallback(async () => {
    await refreshCounts();
    setRefreshKey((k) => k + 1);
  }, [refreshCounts]);

  return (
    <div
      className="space-y-6 p-5 md:p-6 pb-24"
      style={{ maxWidth: "calc(100vw - 64px)" }}
    >
      <div>
        <h2 className="text-2xl font-bold tracking-tight font-[family-name:var(--font-heading)]">
          Pipeline
        </h2>
        <p className="text-text-secondary text-sm mt-1">
          Gerencie leads pelo pipeline
        </p>
      </div>
      <PipelineControls onJobDone={() => window.location.reload()} />
      <PipelineToolbar view={view} />
      <FiltrosAtivosBanner />
      <PipelineFunnel counts={counts} />
      {staleDelta != null && (
        <div className="flex items-center justify-between rounded-md border border-accent/30 bg-accent-soft px-3 py-2 text-[13px]">
          <span>{Math.abs(staleDelta)} {staleDelta > 0 ? "novos" : "atualizados"} desde a última carga.</span>
          <div className="flex gap-3">
            <button onClick={handleRefresh} className="t-eyebrow text-accent hover:underline">Atualizar</button>
            <button onClick={dismissStale} className="t-eyebrow text-text-muted hover:text-text">Dispensar</button>
          </div>
        </div>
      )}
      {view === "table" ? (
        <>
          <SelectAllBanner
            sel={sel}
            visibleIds={visibleIds}
            pageTotal={pageTotal}
            filters={filters}
          />
          <PipelineTable
            sel={sel}
            onVisibleIdsChange={setVisibleIds}
            onTotalChange={setPageTotal}
            refreshKey={refreshKey}
          />
        </>
      ) : (
        <PipelineKanban />
      )}
      {view === "table" && <BulkActionBar sel={sel} onChanged={handleChanged} />}
    </div>
  );
}
