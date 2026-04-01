"use client";

import { useState, useEffect, useCallback } from "react";
import { runScrape, runEnrich, runGenerate, runOutreach, getPipelineStatus } from "@/lib/api";
import { JobProgress } from "./job-progress";
import { ConfirmModal } from "./confirm-modal";
import { ScrapeModal } from "./scrape-modal";
import type { Job } from "@/lib/types";

const PHASES = [
  { key: "scrape", label: "Scraping", description: "Google Maps", run: runScrape, defaultParams: {} },
  { key: "enrich", label: "Enriquecer", description: "Análise de gaps", run: runEnrich, defaultParams: {} },
  { key: "generate", label: "Gerar LPs", description: "Landing pages", run: runGenerate, defaultParams: {} },
  { key: "outreach", label: "Outreach", description: "WhatsApp msgs", run: runOutreach, defaultParams: {} },
] as const;

const PHASE_DESCRIPTIONS: Record<string, string> = {
  scrape: "Buscar negócios no Google Maps por nicho e cidade.",
  enrich: "Analisar o site de cada lead (SSL, responsividade, PageSpeed).",
  generate: "Gerar uma landing page personalizada com IA para cada lead. Custo estimado: ~$0.01/lead.",
  outreach: "Gerar 3 mensagens de WhatsApp (inicial + 2 follow-ups) para cada lead.",
};

interface PipelineControlsProps {
  onJobDone?: () => void;
}

export function PipelineControls({ onJobDone }: PipelineControlsProps) {
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [eligibleCounts, setEligibleCounts] = useState<Record<string, number>>({});
  const [runningJobs, setRunningJobs] = useState<string[]>([]);
  const [pendingPhase, setPendingPhase] = useState<typeof PHASES[number] | null>(null);

  useEffect(() => {
    getPipelineStatus()
      .then((data) => {
        setEligibleCounts(data.eligible_counts);
        setRunningJobs(data.running_jobs);
      })
      .catch(() => {});
  }, [activeJob]);

  const handleRun = useCallback(async (phase: typeof PHASES[number], params?: Record<string, unknown>) => {
    setError(null);
    try {
      const job = await phase.run(params ?? phase.defaultParams);
      setActiveJob(job);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao iniciar job");
    }
  }, []);

  const handleConfirm = useCallback(() => {
    if (pendingPhase) {
      handleRun(pendingPhase);
      setPendingPhase(null);
    }
  }, [pendingPhase, handleRun]);

  const handleScrapeConfirm = useCallback((params: { nichos: string[]; cidades: string[]; max_results: number }) => {
    const scrapePhase = PHASES[0];
    handleRun(scrapePhase, params);
    setPendingPhase(null);
  }, [handleRun]);

  const handleDone = useCallback(() => {
    setActiveJob(null);
    onJobDone?.();
  }, [onJobDone]);

  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <div className="flex items-center gap-3 mb-4">
        <h3 className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider font-[family-name:var(--font-mono)]">
          Pipeline
        </h3>
        {activeJob && (
          <span className="flex items-center gap-1.5 text-[10px] text-info font-[family-name:var(--font-mono)]">
            <span className="w-1.5 h-1.5 rounded-full bg-info animate-pulse" />
            Em execução
          </span>
        )}
      </div>

      <div className="flex gap-2 flex-wrap">
        {PHASES.map((phase, i) => {
          const count = eligibleCounts[phase.key] ?? 0;
          const isRunning = runningJobs.includes(phase.key);
          const disabled = activeJob !== null || isRunning;
          return (
            <button
              key={phase.key}
              onClick={() => setPendingPhase(phase)}
              disabled={disabled}
              className="group flex items-center gap-3 px-4 py-2.5 bg-surface-raised hover:bg-surface-overlay disabled:opacity-30 disabled:cursor-not-allowed border border-border hover:border-text-muted/30 rounded-lg transition-default"
            >
              <span className="flex items-center justify-center w-5 h-5 rounded-md bg-surface-overlay text-[10px] font-bold text-text-muted font-[family-name:var(--font-mono)] group-hover:text-accent group-hover:bg-accent-subtle transition-default">
                {i + 1}
              </span>
              <div className="text-left">
                <p className="text-[13px] font-medium text-text group-hover:text-text transition-default">
                  {phase.label}
                  {phase.key !== "scrape" && count > 0 && (
                    <span className="ml-1.5 text-[10px] text-accent font-[family-name:var(--font-mono)]">
                      ({count})
                    </span>
                  )}
                </p>
                <p className="text-[10px] text-text-muted">{phase.description}</p>
              </div>
            </button>
          );
        })}
      </div>

      {error && (
        <div className="mt-3 px-3 py-2 rounded-lg border border-danger/20 bg-danger/5">
          <p className="text-danger text-xs font-[family-name:var(--font-mono)]">{error}</p>
        </div>
      )}
      {activeJob && <JobProgress jobId={activeJob.id} onDone={handleDone} />}

      <ScrapeModal
        open={pendingPhase?.key === "scrape"}
        onConfirm={handleScrapeConfirm}
        onCancel={() => setPendingPhase(null)}
      />

      <ConfirmModal
        open={pendingPhase !== null && pendingPhase.key !== "scrape"}
        title={`Executar ${pendingPhase?.label ?? ""}?`}
        confirmLabel="Executar"
        onConfirm={handleConfirm}
        onCancel={() => setPendingPhase(null)}
      >
        <p>{pendingPhase ? PHASE_DESCRIPTIONS[pendingPhase.key] : ""}</p>
        {pendingPhase && pendingPhase.key !== "scrape" && (
          <p className="mt-2 text-accent font-[family-name:var(--font-mono)] text-[13px]">
            {eligibleCounts[pendingPhase.key] ?? 0} leads elegíveis
          </p>
        )}
      </ConfirmModal>
    </div>
  );
}
