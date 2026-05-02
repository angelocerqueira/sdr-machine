"use client";

import { Suspense, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { PipelineControls } from "@/components/pipeline-controls";
import { PipelineKanban } from "@/components/pipeline/pipeline-kanban";
import { PipelineToolbar } from "@/components/pipeline/pipeline-toolbar";

type PipelineView = "kanban" | "table";

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

  return (
    <div className="space-y-6 p-5 md:p-6" style={{ maxWidth: "calc(100vw - 64px)" }}>
      <div>
        <h2 className="text-2xl font-bold tracking-tight font-[family-name:var(--font-heading)]">Pipeline</h2>
        <p className="text-text-secondary text-sm mt-1">Gerencie leads pelo pipeline</p>
      </div>
      <PipelineControls onJobDone={() => window.location.reload()} />
      <PipelineToolbar view={view} />
      {view === "table" ? (
        <div className="rounded-lg border border-border bg-surface p-8 text-center">
          <p className="t-eyebrow text-text-muted">Tabela em breve</p>
          <p className="text-text-secondary text-sm mt-2">A view de tabela está sendo construída na PR 2.D.</p>
        </div>
      ) : (
        <PipelineKanban />
      )}
    </div>
  );
}
