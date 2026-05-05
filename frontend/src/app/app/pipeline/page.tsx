"use client";

import "@/components/pipeline/pipeline.css";
import { Suspense, useCallback, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { PipelineKanban } from "@/components/pipeline/pipeline-kanban";
import { PipelineTable } from "@/components/pipeline/pipeline-table";
import { PipelineToolbar } from "@/components/pipeline/pipeline-toolbar";
import { SelectAllBanner } from "@/components/pipeline/select-all-banner";
import { BulkActionBar } from "@/components/pipeline/bulk-action-bar";
import { useBulkSelection } from "@/components/pipeline/use-bulk-selection";
import { FiltrosAtivosBanner } from "@/components/pipeline/filtros-ativos-banner";
import { PipelineFunnel } from "@/components/pipeline/pipeline-funnel";
import { PipelinePageHeader } from "@/components/pipeline/pipeline-page-header";
import { usePipelineCounts } from "@/components/pipeline/use-pipeline-counts";
import { usePipelineDensity } from "@/components/pipeline/use-pipeline-density";
import { ScrapeModal } from "@/components/scrape-modal";
import { CsvImportModal } from "@/components/csv-import-modal";
import { ClassifyModal } from "@/components/pipeline/classify-modal";
import { JobProgress } from "@/components/job-progress";
import { getLeads, runScrape, importCSV } from "@/lib/api";
import type { Job } from "@/lib/types";
import { exportLeadsCSV } from "@/lib/csv-export";
import { useToast } from "@/components/ui/toast";

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

const PROGRESS_STATUSES = [
  "scraped",
  "enriched",
  "lp_generated",
  "outreach_ready",
  "outreach_sent",
  "responded",
  "in_call",
  "closed",
  "delivered",
];

const EXPORT_PER_PAGE = 500;

function isPipelineView(value: string | null): value is PipelineView {
  return value === "kanban" || value === "table";
}

function readStoredView(): PipelineView | null {
  if (typeof window === "undefined") return null;
  try {
    const stored = window.localStorage.getItem("sdr-pipeline-view");
    return isPipelineView(stored) ? stored : null;
  } catch {
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
  const router = useRouter();
  const { toast } = useToast();
  const qsView = sp.get("view");

  const [storedView] = useState<PipelineView | null>(readStoredView);

  const view: PipelineView = useMemo(() => {
    if (isPipelineView(qsView)) return qsView;
    if (storedView) return storedView;
    return "kanban";
  }, [qsView, storedView]);

  const sel = useBulkSelection();
  const { density, toggle: toggleDensity } = usePipelineDensity();
  const [visibleIds, setVisibleIds] = useState<number[]>([]);
  const [pageTotal, setPageTotal] = useState(0);
  const [refreshKey, setRefreshKey] = useState(0);
  const [scrapeOpen, setScrapeOpen] = useState(false);
  const [csvOpen, setCsvOpen] = useState(false);
  const [classifyOpen, setClassifyOpen] = useState(false);
  const [activeJob, setActiveJob] = useState<Job | null>(null);

  const filters = useMemo(() => {
    const out: Record<string, string> = {};
    for (const key of FILTER_KEYS) {
      const v = sp.get(key);
      if (v) out[key] = v;
    }
    return out;
  }, [sp]);

  const advancedOpen = sp.get("adv") === "1";

  const { counts, staleDelta, dismissStale, refresh: refreshCounts } = usePipelineCounts(filters);

  const conversionRate = useMemo(() => {
    const everEntered = PROGRESS_STATUSES.reduce(
      (sum, s) => sum + (counts[s] ?? 0),
      0,
    );
    const responded = counts.responded ?? 0;
    return everEntered > 0 ? (responded / everEntered) * 100 : 0;
  }, [counts]);

  const handleChanged = () => setRefreshKey((k) => k + 1);

  const handleRefresh = useCallback(async () => {
    await refreshCounts();
    setRefreshKey((k) => k + 1);
  }, [refreshCounts]);

  const handleExport = useCallback(async () => {
    try {
      const data = await getLeads({
        ...filters,
        page: "1",
        per_page: String(EXPORT_PER_PAGE),
      });
      if (!data.items.length) {
        toast("Nada pra exportar nos filtros atuais.", { variant: "warning" });
        return;
      }
      const stamp = new Date().toISOString().slice(0, 10);
      exportLeadsCSV(data.items, `leads-${stamp}.csv`);
      const truncated = data.total > data.items.length;
      toast(
        `Exportado: ${data.items.length} leads.${
          truncated ? ` (${data.total - data.items.length} além do limite ficaram de fora — refine os filtros)` : ""
        }`,
        { variant: truncated ? "warning" : "success" },
      );
    } catch (err) {
      toast(
        `Erro ao exportar: ${err instanceof Error ? err.message : "desconhecido"}`,
        { variant: "error" },
      );
    }
  }, [filters, toast]);

  const handleToggleAdvanced = useCallback(() => {
    const next = new URLSearchParams(sp.toString());
    if (advancedOpen) {
      next.delete("adv");
    } else {
      next.set("adv", "1");
    }
    router.replace(`?${next.toString()}`, { scroll: false });
  }, [sp, router, advancedOpen]);

  const handleEnrichScraped = useCallback(() => {
    const scrapedCount = counts.scraped ?? 0;
    if (scrapedCount === 0) return;
    sel.selectAllFilter({ ...filters, status: "scraped" }, scrapedCount);
    toast(
      `${scrapedCount} leads selecionados — confirme em "Re-enriquecer" abaixo.`,
      { variant: "default", duration: 6000 },
    );
  }, [counts.scraped, filters, sel, toast]);

  const handleGenerateLPs = useCallback(() => {
    const count = counts.enriched ?? 0;
    if (count === 0) return;
    sel.selectAllFilter({ ...filters, status: "enriched" }, count);
    toast(
      `${count} leads selecionados — confirme em "Gerar LPs" abaixo.`,
      { variant: "default", duration: 6000 },
    );
  }, [counts.enriched, filters, sel, toast]);

  const handleOutreachReady = useCallback(() => {
    const count = counts.lp_generated ?? 0;
    if (count === 0) return;
    sel.selectAllFilter({ ...filters, status: "lp_generated" }, count);
    toast(
      `${count} leads selecionados — confirme em "Outreach" abaixo.`,
      { variant: "default", duration: 6000 },
    );
  }, [counts.lp_generated, filters, sel, toast]);

  const handleScrapeConfirm = useCallback(
    async (params: { nichos: string[]; cidades: string[]; max_results: number; fontes: string[] }) => {
      setScrapeOpen(false);
      try {
        const job = await runScrape(params);
        setActiveJob(job);
      } catch (err) {
        toast(`Erro ao iniciar scrape: ${err instanceof Error ? err.message : "desconhecido"}`, {
          variant: "error",
        });
      }
    },
    [toast],
  );

  const handleCsvImport = useCallback(
    async (file: File, nicho: string, cidade: string) => {
      setCsvOpen(false);
      try {
        const job = await importCSV(file, nicho, cidade);
        setActiveJob(job);
      } catch (err) {
        toast(`Erro ao importar CSV: ${err instanceof Error ? err.message : "desconhecido"}`, {
          variant: "error",
        });
      }
    },
    [toast],
  );

  const handleClassifyStarted = useCallback((jobId: number) => {
    setClassifyOpen(false);
    setActiveJob({ id: jobId } as Job);
  }, []);

  const handleJobDone = useCallback(() => {
    setActiveJob(null);
    window.location.reload();
  }, []);

  return (
    <div
      className={`pl-page p-5 md:p-6 pb-24${density === "compact" ? " pl-density-compact" : ""}`}
      style={{ maxWidth: "calc(100vw - 64px)" }}
    >
      <PipelinePageHeader
        counts={counts}
        conversionRate={conversionRate}
        onExport={handleExport}
        onToggleAdvancedFilters={handleToggleAdvanced}
        advancedOpen={advancedOpen}
        onScrape={() => setScrapeOpen(true)}
        onCsvImport={() => setCsvOpen(true)}
        onEnrichScraped={handleEnrichScraped}
        onGenerateLPs={handleGenerateLPs}
        onOutreachReady={handleOutreachReady}
        onClassify={() => setClassifyOpen(true)}
      />
      {activeJob && <JobProgress jobId={activeJob.id} onDone={handleJobDone} />}
      <PipelineToolbar view={view} density={density} onToggleDensity={toggleDensity} />
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
            density={density}
            onVisibleIdsChange={setVisibleIds}
            onTotalChange={setPageTotal}
            refreshKey={refreshKey}
          />
        </>
      ) : (
        <PipelineKanban />
      )}
      <BulkActionBar sel={sel} onChanged={handleChanged} />

      <ScrapeModal
        open={scrapeOpen}
        onConfirm={handleScrapeConfirm}
        onCancel={() => setScrapeOpen(false)}
      />
      <CsvImportModal
        open={csvOpen}
        onConfirm={handleCsvImport}
        onCancel={() => setCsvOpen(false)}
      />
      <ClassifyModal
        open={classifyOpen}
        onStarted={handleClassifyStarted}
        onCancel={() => setClassifyOpen(false)}
      />
    </div>
  );
}
