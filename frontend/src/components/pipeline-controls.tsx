"use client";

import { useState, useCallback } from "react";
import { runScrape, runEnrich, runGenerate, runOutreach } from "@/lib/api";
import { JobProgress } from "./job-progress";
import type { Job } from "@/lib/types";

const PHASES = [
  { key: "scrape", label: "Scraping", icon: "📍", run: runScrape, defaultParams: {} },
  { key: "enrich", label: "Enriquecer", icon: "🔬", run: runEnrich, defaultParams: {} },
  { key: "generate", label: "Gerar LPs", icon: "🎨", run: runGenerate, defaultParams: {} },
  { key: "outreach", label: "Gerar Msgs", icon: "📨", run: runOutreach, defaultParams: {} },
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
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wide mb-4">Pipeline</h3>
      <div className="flex gap-3 flex-wrap">
        {PHASES.map((phase) => (
          <button
            key={phase.key}
            onClick={() => handleRun(phase)}
            disabled={activeJob !== null}
            className="flex items-center gap-2 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-40 disabled:cursor-not-allowed border border-zinc-700 rounded-lg text-sm transition-colors"
          >
            <span>{phase.icon}</span>
            {phase.label}
          </button>
        ))}
      </div>
      {error && <p className="text-red-400 text-sm mt-3">{error}</p>}
      {activeJob && <JobProgress jobId={activeJob.id} onDone={handleDone} />}
    </div>
  );
}
