"use client";

import { Suspense, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { PipelineControls } from "@/components/pipeline-controls";
import { PipelineKanban } from "@/components/pipeline/pipeline-kanban";
import { PipelineTable } from "@/components/pipeline/pipeline-table";
import { PipelineToolbar } from "@/components/pipeline/pipeline-toolbar";
import { SelectAllBanner } from "@/components/pipeline/select-all-banner";
import { BulkActionBar } from "@/components/pipeline/bulk-action-bar";
import { useBulkSelection } from "@/components/pipeline/use-bulk-selection";

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

  const handleChanged = () => setRefreshKey((k) => k + 1);

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
