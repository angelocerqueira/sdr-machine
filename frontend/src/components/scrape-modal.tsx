"use client";

import { useState, useEffect, useCallback } from "react";
import { getSettings } from "@/lib/api";

interface ScrapeModalProps {
  open: boolean;
  onConfirm: (params: { nichos: string[]; cidades: string[]; max_results: number }) => void;
  onCancel: () => void;
}

export function ScrapeModal({ open, onConfirm, onCancel }: ScrapeModalProps) {
  const [nicho, setNicho] = useState("");
  const [cidade, setCidade] = useState("");
  const [maxResults, setMaxResults] = useState(50);
  const [suggestedNichos, setSuggestedNichos] = useState<string[]>([]);
  const [suggestedCidades, setSuggestedCidades] = useState<string[]>([]);

  useEffect(() => {
    if (!open) return;
    getSettings()
      .then((s) => {
        setSuggestedNichos(s.target_niches);
        setSuggestedCidades(s.target_cities);
      })
      .catch(() => {});
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    document.addEventListener("keydown", handleEsc);
    return () => document.removeEventListener("keydown", handleEsc);
  }, [open, onCancel]);

  const handleConfirm = useCallback(() => {
    if (!nicho.trim() || !cidade.trim()) return;
    onConfirm({
      nichos: [nicho.trim()],
      cidades: [cidade.trim()],
      max_results: maxResults,
    });
    setNicho("");
    setCidade("");
    setMaxResults(50);
  }, [nicho, cidade, maxResults, onConfirm]);

  if (!open) return null;

  const inputClass =
    "w-full px-3 py-2 bg-surface-raised border border-border rounded-lg text-[13px] text-text placeholder:text-text-muted focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-default";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 sheet-backdrop" onClick={onCancel} />
      <div className="relative bg-surface rounded-xl border border-border p-6 max-w-md w-full mx-4 shadow-xl">
        <h3 className="text-[15px] font-semibold text-text mb-1">Scraping Google Maps</h3>
        <p className="text-[12px] text-text-muted mb-5">
          Buscar negócios por nicho e cidade no Google Maps.
        </p>

        <div className="space-y-4">
          <div>
            <label className="block text-[11px] font-semibold text-text-secondary uppercase tracking-wider mb-1.5 font-[family-name:var(--font-mono)]">
              Nicho
            </label>
            <input
              type="text"
              value={nicho}
              onChange={(e) => setNicho(e.target.value)}
              placeholder="Ex: dentista, restaurante, academia..."
              className={inputClass}
              list="nicho-suggestions"
              autoFocus
            />
            <datalist id="nicho-suggestions">
              {suggestedNichos.map((n) => (
                <option key={n} value={n} />
              ))}
            </datalist>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-text-secondary uppercase tracking-wider mb-1.5 font-[family-name:var(--font-mono)]">
              Cidade
            </label>
            <input
              type="text"
              value={cidade}
              onChange={(e) => setCidade(e.target.value)}
              placeholder="Ex: Chapecó SC, Florianópolis SC..."
              className={inputClass}
              list="cidade-suggestions"
            />
            <datalist id="cidade-suggestions">
              {suggestedCidades.map((c) => (
                <option key={c} value={c} />
              ))}
            </datalist>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-text-secondary uppercase tracking-wider mb-1.5 font-[family-name:var(--font-mono)]">
              Máximo de resultados
            </label>
            <input
              type="number"
              value={maxResults}
              onChange={(e) => setMaxResults(Math.max(1, Math.min(100, Number(e.target.value))))}
              min={1}
              max={100}
              className={inputClass}
            />
          </div>
        </div>

        <div className="flex gap-3 justify-end mt-6">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-[13px] text-text-secondary hover:text-text bg-surface-raised hover:bg-surface-overlay border border-border rounded-lg transition-default"
          >
            Cancelar
          </button>
          <button
            onClick={handleConfirm}
            disabled={!nicho.trim() || !cidade.trim()}
            className="px-4 py-2 text-[13px] text-bg font-medium rounded-lg transition-default bg-accent hover:bg-accent-dim disabled:opacity-30 disabled:cursor-not-allowed"
          >
            Executar Scraping
          </button>
        </div>
      </div>
    </div>
  );
}
