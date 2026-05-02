"use client";

import { useEffect, useRef } from "react";
import { Icon } from "@/components/ui";
import { useFocusTrap } from "@/components/ui/use-focus-trap";
import type { Job } from "@/lib/types";

interface Props {
  job: Job | null;
  onClose: () => void;
}

const ACTION_LABEL: Record<string, string> = {
  enrich: "Enriquecimento",
  generate: "Geração de LP",
  outreach: "Geração de mensagens",
  classify: "Classificação",
  scrape: "Scraping",
};

interface ParsedSummary {
  successLabel: string;
  successCount: number;
  total: number;
  errors: string[];
}

function parseSummary(job: Job): ParsedSummary {
  const summary = (job.result_summary ?? {}) as Record<string, unknown>;
  const errorsRaw = Array.isArray(summary.errors) ? (summary.errors as unknown[]) : [];
  const errors = errorsRaw.map((e) => String(e));
  const total = typeof summary.total === "number" ? summary.total : 0;

  let successLabel = "Concluídos";
  let successCount = 0;
  if (typeof summary.enriched === "number") {
    successLabel = "Enriquecidos";
    successCount = summary.enriched;
  } else if (typeof summary.generated === "number") {
    successLabel = "LPs geradas";
    successCount = summary.generated;
  } else if (typeof summary.messaged === "number") {
    successLabel = "Mensagens geradas";
    successCount = summary.messaged;
  } else if (typeof summary.created === "number") {
    successLabel = "Criados";
    successCount = summary.created;
  }
  return { successLabel, successCount, total, errors };
}

function extractFailedIds(errors: string[]): number[] {
  const ids: number[] = [];
  for (const err of errors) {
    const match = err.match(/^Lead (\d+)/);
    if (match) ids.push(Number(match[1]));
  }
  return ids;
}

export function BulkResultModal({ job, onClose }: Props) {
  const dialogRef = useRef<HTMLDivElement>(null);
  useFocusTrap(dialogRef, job !== null);

  useEffect(() => {
    if (!job) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.stopImmediatePropagation();
        onClose();
      }
    }
    document.addEventListener("keydown", onKeyDown, true);
    return () => document.removeEventListener("keydown", onKeyDown, true);
  }, [job, onClose]);

  if (!job) return null;

  const parsed = parseSummary(job);
  const actionLabel = ACTION_LABEL[job.type] ?? job.type;
  const isFailure = job.status === "failed";
  const isPartial = job.status === "done_with_errors" || parsed.errors.length > 0;
  const failedIds = extractFailedIds(parsed.errors);

  const handleCopyFailedIds = async () => {
    if (failedIds.length === 0) return;
    try {
      await navigator.clipboard.writeText(failedIds.join(","));
    } catch {
      // best-effort
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="bulk-result-title"
        className="w-full max-w-md rounded-xl border border-border bg-surface shadow-2xl"
      >
        <div className="flex items-center justify-between border-b border-border-subtle px-5 py-4">
          <h3 id="bulk-result-title" className="text-lg font-semibold">
            {isFailure ? "Job falhou" : isPartial ? "Concluído com erros" : "Job concluído"}
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="text-text-muted hover:text-text"
            aria-label="Fechar"
          >
            <Icon name="x" className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4 px-5 py-4 text-sm text-text-secondary">
          <p>
            <strong className="text-text">{actionLabel}</strong> · job #{job.id}
          </p>

          <div className="rounded-lg bg-surface-raised p-3 font-mono text-[12px] tabular-nums space-y-1">
            <div>
              {parsed.successLabel}:{" "}
              <strong className={isFailure ? "text-danger" : "text-ok"}>{parsed.successCount}</strong>
              {parsed.total > 0 && <span className="text-text-muted"> / {parsed.total}</span>}
            </div>
            {parsed.errors.length > 0 && (
              <div>
                Erros: <strong className="text-danger">{parsed.errors.length}</strong>
              </div>
            )}
            {job.error_message && (
              <div className="text-danger">Erro fatal: {job.error_message}</div>
            )}
          </div>

          {parsed.errors.length > 0 && (
            <div className="space-y-1">
              <p className="t-eyebrow">Detalhes ({Math.min(parsed.errors.length, 10)} de {parsed.errors.length})</p>
              <ul className="max-h-48 overflow-y-auto space-y-1 rounded-md border border-border-subtle bg-surface-raised p-2 text-[12px] font-mono">
                {parsed.errors.slice(0, 10).map((err, i) => (
                  <li key={i} className="text-danger break-words">
                    {err}
                  </li>
                ))}
              </ul>
              {parsed.errors.length > 10 && (
                <p className="t-eyebrow text-text-muted">+ {parsed.errors.length - 10} erros adicionais</p>
              )}
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 border-t border-border-subtle px-5 py-3">
          {failedIds.length > 0 && (
            <button
              type="button"
              onClick={handleCopyFailedIds}
              className="rounded-md border border-border bg-surface-raised px-4 py-2 text-sm text-text-secondary hover:text-text hover:border-border-strong transition-default cursor-pointer"
            >
              Copiar {failedIds.length} IDs falhos
            </button>
          )}
          <button
            type="button"
            onClick={onClose}
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent/90 transition-default cursor-pointer"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
}
