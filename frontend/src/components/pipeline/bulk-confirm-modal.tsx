"use client";

import { useEffect, useState, type ReactNode } from "react";
import { Icon } from "@/components/ui";
import type { PipelinePreviewResponse } from "@/lib/types";

export type ConfirmVariant = "soft" | "hard";

interface Props {
  open: boolean;
  onClose: () => void;
  onConfirm: (options?: { force?: boolean }) => void;
  variant: ConfirmVariant;
  title: string;
  description?: ReactNode;
  confirmLabel: string;
  /** Required for variant="hard". Typed-input must match exactly. */
  hardConfirmKeyword?: string;
  /** Optional preview from /api/pipeline/preview */
  preview?: PipelinePreviewResponse | null;
  /** Show the "force re-process" checkbox for enrich. */
  showForceToggle?: boolean;
  busy?: boolean;
}

export function BulkConfirmModal(props: Props) {
  const {
    open,
    onClose,
    onConfirm,
    variant,
    title,
    description,
    confirmLabel,
    hardConfirmKeyword,
    preview,
    showForceToggle,
    busy,
  } = props;

  const [typed, setTyped] = useState("");
  const [force, setForce] = useState(false);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  const hardOk = variant === "hard" ? typed === hardConfirmKeyword : true;
  const canConfirm = hardOk && !busy;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="bulk-confirm-title"
        className="w-full max-w-md rounded-xl border border-border bg-surface shadow-2xl"
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h3
            id="bulk-confirm-title"
            className="text-lg font-semibold text-text"
          >
            {title}
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="text-text-muted hover:text-text transition-default"
            aria-label="Fechar"
          >
            <Icon name="x" size={16} />
          </button>
        </div>

        <div className="space-y-4 px-5 py-4 text-sm text-text-secondary">
          {description}

          {preview && (
            <div className="rounded-lg bg-surface-raised p-3 font-mono text-[12px] tabular-nums space-y-1">
              <div>
                Total:{" "}
                <strong className="text-text">{preview.total_leads}</strong>
              </div>
              <div>
                Elegíveis:{" "}
                <strong className="text-text">{preview.eligible}</strong>
              </div>
              {preview.skipped > 0 && (
                <div>
                  Ignorados:{" "}
                  <strong className="text-warn">{preview.skipped}</strong>{" "}
                  (
                  {Object.entries(preview.skipped_reasons)
                    .map(([k, v]) => `${k}=${v}`)
                    .join(", ")}
                  )
                </div>
              )}
              {preview.warnings.map((w, i) => (
                <div key={i} className="text-warn">
                  ⚠ {w}
                </div>
              ))}
            </div>
          )}

          {showForceToggle && preview && (
            <div className="space-y-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={force}
                  onChange={(e) => setForce(e.target.checked)}
                  className="cursor-pointer"
                />
                <span>Forçar reprocessamento de leads já processados</span>
              </label>
            </div>
          )}

          {variant === "hard" && (
            <div className="space-y-2">
              <p className="text-danger">Esta ação não pode ser desfeita.</p>
              <label className="block">
                <span className="t-eyebrow text-text-muted">
                  Digite{" "}
                  <strong className="text-text">{hardConfirmKeyword}</strong>{" "}
                  para confirmar:
                </span>
                <input
                  type="text"
                  value={typed}
                  onChange={(e) => setTyped(e.target.value)}
                  className="mt-1 w-full rounded-md border border-border bg-surface-raised px-3 py-2 font-mono text-[13px] text-text focus:border-danger focus:outline-none"
                  autoFocus
                />
              </label>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 border-t border-border px-5 py-3">
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            className="rounded-md px-4 py-2 text-sm text-text-secondary hover:bg-surface-raised disabled:opacity-50 transition-default cursor-pointer"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={() => onConfirm({ force })}
            disabled={!canConfirm}
            className={`rounded-md px-4 py-2 text-sm font-medium transition-default disabled:opacity-50 cursor-pointer ${
              variant === "hard"
                ? "bg-danger text-white hover:opacity-90"
                : "bg-accent text-white hover:opacity-90"
            }`}
          >
            {busy ? "Processando..." : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
