"use client";

import { useEffect, useState } from "react";
import { getJobs } from "@/lib/api";
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

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getJobs().then((data) => {
      setJobs(data.items);
      setLoading(false);
    });
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
                <tr key={job.id} className="border-t border-border-subtle table-row-hover transition-default">
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
                    {job.result_summary?.total
                      ? `${job.result_summary.success}/${job.result_summary.total} ok`
                      : job.error_message || "—"}
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
    </div>
  );
}
