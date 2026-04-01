"use client";

import { useEffect, useState, useCallback } from "react";
import { getJobs, getJob } from "@/lib/api";
import type { Job } from "@/lib/types";

const STATUS_CONFIG: Record<string, { label: string; dot: string; text: string }> = {
  pending: { label: "Pendente", dot: "bg-text-muted", text: "text-text-muted" },
  running: { label: "Rodando", dot: "bg-info animate-pulse", text: "text-info" },
  done: { label: "Concluído", dot: "bg-accent", text: "text-accent" },
  failed: { label: "Falhou", dot: "bg-danger", text: "text-danger" },
};

const TYPE_LABELS: Record<string, string> = {
  scrape: "Scraping",
  enrich: "Enriquecimento",
  generate: "Geração de LPs",
  outreach: "Outreach",
};

const KEY_MAP: Record<string, string> = {
  scrape: "created",
  enrich: "enriched",
  generate: "generated",
  outreach: "messaged",
};

function getResultText(job: Job) {
  const s = job.result_summary;
  if (!s?.total) return job.error_message || "—";
  const count = s[KEY_MAP[job.type] ?? "success"] ?? 0;
  const errCount = (s.errors as string[] | undefined)?.length ?? 0;
  return errCount > 0
    ? `${count}/${s.total} ok, ${errCount} erros`
    : `${count}/${s.total} ok`;
}

function formatDuration(startedAt: string | null, finishedAt: string | null): string {
  if (!startedAt || !finishedAt) return "—";
  const ms = new Date(finishedAt).getTime() - new Date(startedAt).getTime();
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const m = Math.floor(ms / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  return `${m}m ${s}s`;
}

function LogLine({ index, text, isError }: { index: number; text: string; isError?: boolean }) {
  return (
    <p className="leading-relaxed flex gap-2">
      <span className="text-text-muted/40 select-none shrink-0 font-[family-name:var(--font-mono)] text-[11px]">
        {String(index).padStart(2, "0")}
      </span>
      <span className={isError ? "text-danger" : "text-text-secondary"}>{text}</span>
    </p>
  );
}

function JobDetailModal({ job, onClose }: { job: Job; onClose: () => void }) {
  const s = job.result_summary;
  const errors = (s?.errors as string[] | undefined) ?? [];
  const params = job.params as Record<string, unknown>;
  const config = STATUS_CONFIG[job.status] || STATUS_CONFIG.pending;

  const logLines: { text: string; isError?: boolean }[] = [];

  // Params block
  if (params) {
    const nichos = params.nichos as string[] | undefined;
    const cidades = params.cidades as string[] | undefined;
    const maxResults = params.max_results as number | undefined;
    const leadIds = params.lead_ids as number[] | undefined;

    if (nichos?.length) logLines.push({ text: `Nichos: ${nichos.join(", ")}` });
    if (cidades?.length) logLines.push({ text: `Cidades: ${cidades.join(", ")}` });
    if (maxResults) logLines.push({ text: `Máximo de resultados: ${maxResults}` });
    if (leadIds?.length) logLines.push({ text: `Lead IDs: ${leadIds.join(", ")}` });
  }

  logLines.push({ text: `Iniciado em: ${job.started_at ? new Date(job.started_at).toLocaleString("pt-BR") : "—"}` });
  logLines.push({ text: `Concluído em: ${job.finished_at ? new Date(job.finished_at).toLocaleString("pt-BR") : "—"}` });
  logLines.push({ text: `Duração: ${formatDuration(job.started_at, job.finished_at)}` });

  // Result summary
  if (s) {
    const countKey = KEY_MAP[job.type];
    if (countKey && s[countKey] !== undefined) {
      logLines.push({ text: `${countKey.charAt(0).toUpperCase() + countKey.slice(1)}: ${s[countKey]} / ${s.total ?? "?"}` });
    }
    if (s.disqualified !== undefined) {
      logLines.push({ text: `Desqualificados: ${s.disqualified}` });
    }
  }

  // Error message (job-level failure)
  if (job.error_message) {
    logLines.push({ text: `ERRO: ${job.error_message}`, isError: true });
  }

  // Per-item errors
  errors.forEach((e) => logLines.push({ text: e, isError: true }));

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.6)", backdropFilter: "blur(2px)" }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl rounded-xl border border-border bg-surface shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <div className="flex items-center gap-3">
            <span className="font-[family-name:var(--font-mono)] text-text-muted text-sm">
              #{job.id}
            </span>
            <span className="text-text font-medium">{TYPE_LABELS[job.type] || job.type}</span>
            <span className="inline-flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${config.dot}`} />
              <span className={`text-xs font-medium font-[family-name:var(--font-mono)] ${config.text}`}>
                {config.label}
              </span>
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text transition-colors p-1"
            aria-label="Fechar"
          >
            <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M2 2l12 12M14 2L2 14" />
            </svg>
          </button>
        </div>

        {/* Log output */}
        <div className="p-5 space-y-1 max-h-[60vh] overflow-y-auto bg-bg/50 text-xs font-[family-name:var(--font-mono)]">
          {logLines.length === 0 ? (
            <p className="text-text-muted">Nenhuma informação disponível.</p>
          ) : (
            logLines.map((line, i) => (
              <LogLine key={i} index={i + 1} text={line.text} isError={line.isError} />
            ))
          )}
        </div>

        {/* Footer summary */}
        {errors.length > 0 && (
          <div className="px-5 py-3 border-t border-border bg-danger/5">
            <p className="text-xs text-danger font-[family-name:var(--font-mono)]">
              {errors.length} erro{errors.length > 1 ? "s" : ""} encontrado{errors.length > 1 ? "s" : ""}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);

  useEffect(() => {
    getJobs().then((data) => {
      setJobs(data.items);
      setLoading(false);
    });
  }, []);

  const handleRowClick = useCallback(async (jobId: number) => {
    const job = await getJob(jobId);
    setSelectedJob(job);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-text-muted text-sm">
        <span className="w-4 h-4 border-2 border-text-muted border-t-accent rounded-full animate-spin" />
        Carregando...
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h2 className="text-2xl font-bold tracking-tight font-[family-name:var(--font-outfit)]">Jobs</h2>
        <p className="text-text-secondary text-sm mt-1">Histórico de execuções do pipeline</p>
      </div>

      <div className="rounded-xl border border-border bg-surface overflow-hidden">
        <table className="w-full text-[13px]">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left px-5 py-3 text-[10px] uppercase tracking-widest text-text-muted font-semibold font-[family-name:var(--font-mono)]">ID</th>
              <th className="text-left px-5 py-3 text-[10px] uppercase tracking-widest text-text-muted font-semibold font-[family-name:var(--font-mono)]">Tipo</th>
              <th className="text-left px-5 py-3 text-[10px] uppercase tracking-widest text-text-muted font-semibold font-[family-name:var(--font-mono)]">Status</th>
              <th className="text-left px-5 py-3 text-[10px] uppercase tracking-widest text-text-muted font-semibold font-[family-name:var(--font-mono)]">Resultado</th>
              <th className="text-left px-5 py-3 text-[10px] uppercase tracking-widest text-text-muted font-semibold font-[family-name:var(--font-mono)]">Data</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => {
              const config = STATUS_CONFIG[job.status] || STATUS_CONFIG.pending;
              return (
                <tr
                  key={job.id}
                  className="border-t border-border-subtle table-row-hover transition-default cursor-pointer"
                  onClick={() => handleRowClick(job.id)}
                >
                  <td className="px-5 py-3.5 font-[family-name:var(--font-mono)] text-text-muted">#{job.id}</td>
                  <td className="px-5 py-3.5 text-text">{TYPE_LABELS[job.type] || job.type}</td>
                  <td className="px-5 py-3.5">
                    <span className="inline-flex items-center gap-1.5">
                      <span className={`w-2 h-2 rounded-full ${config.dot}`} />
                      <span className={`text-xs font-medium font-[family-name:var(--font-mono)] ${config.text}`}>
                        {config.label}
                      </span>
                    </span>
                  </td>
                  <td className="px-5 py-3.5 text-text-secondary font-[family-name:var(--font-mono)] text-xs">
                    {getResultText(job)}
                  </td>
                  <td className="px-5 py-3.5 text-text-muted font-[family-name:var(--font-mono)] text-xs">
                    {new Date(job.created_at).toLocaleString("pt-BR")}
                  </td>
                </tr>
              );
            })}
            {jobs.length === 0 && (
              <tr>
                <td colSpan={5} className="px-5 py-16 text-center">
                  <div className="flex flex-col items-center">
                    <div className="w-12 h-12 rounded-full bg-surface-raised border border-border flex items-center justify-center mb-4">
                      <svg className="w-5 h-5 text-text-muted" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                        <circle cx="10" cy="10" r="8" />
                        <path d="M10 6v5l3 2" />
                      </svg>
                    </div>
                    <p className="text-text-secondary text-sm">Nenhum job executado ainda</p>
                    <p className="text-text-muted text-xs mt-1">Execute uma fase do pipeline no Kanban</p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {selectedJob && (
        <JobDetailModal job={selectedJob} onClose={() => setSelectedJob(null)} />
      )}
    </div>
  );
}
