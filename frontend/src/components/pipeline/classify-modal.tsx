"use client";

import { useEffect, useState } from "react";
import { classifyLeads } from "@/lib/api";

interface ClassifyModalProps {
  open: boolean;
  onStarted: (jobId: number) => void;
  onCancel: () => void;
}

export function ClassifyModal({ open, onStarted, onCancel }: ClassifyModalProps) {
  const [scope, setScope] = useState<"unclassified" | "all">("unclassified");
  const [force, setForce] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    document.addEventListener("keydown", handleEsc);
    return () => document.removeEventListener("keydown", handleEsc);
  }, [open, onCancel]);

  if (!open) return null;

  async function handleStart() {
    setBusy(true);
    setError(null);
    try {
      const { id } = await classifyLeads({ scope, force });
      onStarted(id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erro ao iniciar classificação";
      // 409 from backend: "classification job already in progress"
      setError(msg);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 sheet-backdrop" onClick={onCancel} />
      <div className="relative bg-surface rounded-xl border border-border p-6 max-w-md w-full mx-4 shadow-xl">
        <h3 className="text-[15px] font-semibold text-text mb-4">Classificar leads</h3>

        <div className="space-y-4 text-[13px] text-text-secondary mb-6">
          {/* Scope */}
          <div>
            <label className="block text-[11px] font-semibold text-text-muted uppercase tracking-wider font-[family-name:var(--font-mono)] mb-1.5">
              Escopo
            </label>
            <select
              value={scope}
              onChange={(e) => setScope(e.target.value as "unclassified" | "all")}
              className="w-full px-3 py-2 rounded-lg border border-border bg-surface-raised text-text text-[13px] focus:outline-none focus:border-accent transition-default"
            >
              <option value="unclassified">Apenas não classificados</option>
              <option value="all">Todos os leads</option>
            </select>
          </div>

          {/* Force checkbox */}
          <label className="flex items-start gap-2.5 cursor-pointer">
            <input
              type="checkbox"
              checked={force}
              onChange={(e) => setForce(e.target.checked)}
              className="mt-0.5 accent-accent"
            />
            <span className="text-[13px] text-text-secondary leading-snug">
              Forçar re-classificação de nicho (mesmo com hash inalterado)
            </span>
          </label>
        </div>

        {error && (
          <div className="mb-4 px-3 py-2 rounded-lg border border-danger/20 bg-danger/5">
            <p className="text-danger text-xs font-[family-name:var(--font-mono)]">{error}</p>
          </div>
        )}

        <div className="flex gap-3 justify-end">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-[13px] text-text-secondary hover:text-text bg-surface-raised hover:bg-surface-overlay border border-border rounded-lg transition-default"
          >
            Cancelar
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={handleStart}
            className="px-4 py-2 text-[13px] text-bg font-medium rounded-lg transition-default bg-accent hover:bg-accent-dim disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {busy ? "Iniciando..." : "Iniciar"}
          </button>
        </div>
      </div>
    </div>
  );
}
