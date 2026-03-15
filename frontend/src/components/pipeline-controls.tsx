"use client";

import { useState, useCallback } from "react";
import { runScrape, runEnrich, runGenerate, runOutreach } from "@/lib/api";
import { JobProgress } from "./job-progress";
import type { Job } from "@/lib/types";

const PHASES = [
  { key: "scrape", label: "Scraping", description: "Google Maps", run: runScrape, defaultParams: {} },
  { key: "enrich", label: "Enriquecer", description: "Análise de gaps", run: runEnrich, defaultParams: {} },
  { key: "generate", label: "Gerar LPs", description: "Landing pages", run: runGenerate, defaultParams: {} },
  { key: "outreach", label: "Outreach", description: "WhatsApp msgs", run: runOutreach, defaultParams: {} },
] as const;

interface PipelineControlsProps {
  onJobDone?: () => void;
}

export function PipelineControls({ onJobDone }: PipelineControlsProps) {
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRun = useCallback(async (phase: typeof PHASES[number]) => {
    setError(null);
    try {
      const job = await phase.run(phase.defaultParams);
      setActiveJob(job);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao iniciar job");
    }
  }, []);

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
        {PHASES.map((phase, i) => (
          <button
            key={phase.key}
            onClick={() => handleRun(phase)}
            disabled={activeJob !== null}
            className="group flex items-center gap-3 px-4 py-2.5 bg-surface-raised hover:bg-surface-overlay disabled:opacity-30 disabled:cursor-not-allowed border border-border hover:border-text-muted/30 rounded-lg transition-default"
          >
            <span className="flex items-center justify-center w-5 h-5 rounded-md bg-surface-overlay text-[10px] font-bold text-text-muted font-[family-name:var(--font-mono)] group-hover:text-accent group-hover:bg-accent-subtle transition-default">
              {i + 1}
            </span>
            <div className="text-left">
              <p className="text-[13px] font-medium text-text group-hover:text-text transition-default">{phase.label}</p>
              <p className="text-[10px] text-text-muted">{phase.description}</p>
            </div>
          </button>
        ))}
      </div>

      {error && (
        <div className="mt-3 px-3 py-2 rounded-lg border border-danger/20 bg-danger/5">
          <p className="text-danger text-xs font-[family-name:var(--font-mono)]">{error}</p>
        </div>
      )}
      {activeJob && <JobProgress jobId={activeJob.id} onDone={handleDone} />}
    </div>
  );
}
