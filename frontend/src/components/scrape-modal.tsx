"use client";

import { useState, useEffect, useCallback } from "react";
import { getSettings } from "@/lib/api";

interface ScrapeModalProps {
  open: boolean;
  onConfirm: (params: { nichos: string[]; cidades: string[]; max_results: number; fontes: string[] }) => void;
  onCancel: () => void;
}

export function ScrapeModal({ open, onConfirm, onCancel }: ScrapeModalProps) {
  const [nichos, setNichos] = useState<string[]>([]);
  const [cidades, setCidades] = useState<string[]>([]);
  const [nichoInput, setNichoInput] = useState("");
  const [cidadeInput, setCidadeInput] = useState("");
  const [maxResults, setMaxResults] = useState(50);
  const [fontes, setFontes] = useState<string[]>(["google_maps", "cnpj"]);
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

  const addNicho = useCallback(() => {
    const val = nichoInput.trim();
    if (val && !nichos.includes(val)) {
      setNichos((prev) => [...prev, val]);
    }
    setNichoInput("");
  }, [nichoInput, nichos]);

  const addCidade = useCallback(() => {
    const val = cidadeInput.trim();
    if (val && !cidades.includes(val)) {
      setCidades((prev) => [...prev, val]);
    }
    setCidadeInput("");
  }, [cidadeInput, cidades]);

  const toggleFonte = useCallback((fonte: string) => {
    setFontes((prev) =>
      prev.includes(fonte) ? prev.filter((f) => f !== fonte) : [...prev, fonte]
    );
  }, []);

  const handleConfirm = useCallback(() => {
    // Include current input values if not yet added
    const finalNichos = [...nichos];
    const finalCidades = [...cidades];
    if (nichoInput.trim() && !finalNichos.includes(nichoInput.trim())) {
      finalNichos.push(nichoInput.trim());
    }
    if (cidadeInput.trim() && !finalCidades.includes(cidadeInput.trim())) {
      finalCidades.push(cidadeInput.trim());
    }
    if (finalNichos.length === 0 || finalCidades.length === 0 || fontes.length === 0) return;
    onConfirm({
      nichos: finalNichos,
      cidades: finalCidades,
      max_results: maxResults,
      fontes,
    });
    setNichos([]);
    setCidades([]);
    setNichoInput("");
    setCidadeInput("");
    setMaxResults(50);
    setFontes(["google_maps", "cnpj"]);
  }, [nichos, cidades, nichoInput, cidadeInput, maxResults, fontes, onConfirm]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, addFn: () => void) => {
      if (e.key === "Enter") {
        e.preventDefault();
        addFn();
      }
    },
    []
  );

  if (!open) return null;

  const hasNichos = nichos.length > 0 || nichoInput.trim().length > 0;
  const hasCidades = cidades.length > 0 || cidadeInput.trim().length > 0;

  const inputClass =
    "w-full px-3 py-2 bg-surface-raised border border-border rounded-lg text-[13px] text-text placeholder:text-text-muted focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-default";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 sheet-backdrop" onClick={onCancel} />
      <div className="relative bg-surface rounded-xl border border-border p-6 max-w-md w-full mx-4 shadow-xl">
        <h3 className="text-[15px] font-semibold text-text mb-1">Buscar Negócios</h3>
        <p className="text-[12px] text-text-muted mb-5">
          Buscar negócios por nicho e cidade. Adicione múltiplos nichos/cidades com Enter.
        </p>

        <div className="space-y-4">
          {/* Nichos */}
          <div>
            <label className="block text-[11px] font-semibold text-text-secondary uppercase tracking-wider mb-1.5 font-[family-name:var(--font-mono)]">
              Nichos
            </label>
            {nichos.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-2">
                {nichos.map((n) => (
                  <span
                    key={n}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-accent-subtle border border-accent/20 text-[11px] text-accent font-[family-name:var(--font-mono)]"
                  >
                    {n}
                    <button
                      onClick={() => setNichos((prev) => prev.filter((x) => x !== n))}
                      className="hover:text-text transition-colors ml-0.5"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
            <input
              type="text"
              value={nichoInput}
              onChange={(e) => setNichoInput(e.target.value)}
              onKeyDown={(e) => handleKeyDown(e, addNicho)}
              placeholder="Ex: dentista, restaurante, academia..."
              className={inputClass}
              list="nicho-suggestions"
              autoFocus
            />
            <datalist id="nicho-suggestions">
              {suggestedNichos
                .filter((n) => !nichos.includes(n))
                .map((n) => (
                  <option key={n} value={n} />
                ))}
            </datalist>
          </div>

          {/* Cidades */}
          <div>
            <label className="block text-[11px] font-semibold text-text-secondary uppercase tracking-wider mb-1.5 font-[family-name:var(--font-mono)]">
              Cidades
            </label>
            {cidades.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-2">
                {cidades.map((c) => (
                  <span
                    key={c}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-accent-subtle border border-accent/20 text-[11px] text-accent font-[family-name:var(--font-mono)]"
                  >
                    {c}
                    <button
                      onClick={() => setCidades((prev) => prev.filter((x) => x !== c))}
                      className="hover:text-text transition-colors ml-0.5"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
            <input
              type="text"
              value={cidadeInput}
              onChange={(e) => setCidadeInput(e.target.value)}
              onKeyDown={(e) => handleKeyDown(e, addCidade)}
              placeholder="Ex: Chapecó SC, Florianópolis SC..."
              className={inputClass}
              list="cidade-suggestions"
            />
            <datalist id="cidade-suggestions">
              {suggestedCidades
                .filter((c) => !cidades.includes(c))
                .map((c) => (
                  <option key={c} value={c} />
                ))}
            </datalist>
          </div>

          {/* Max results */}
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


          {/* Fontes */}
          <div>
            <label className="block text-[11px] font-semibold text-text-secondary uppercase tracking-wider mb-1.5 font-[family-name:var(--font-mono)]">
              Fontes de busca
            </label>
            <div className="flex gap-4">
              {[
                { key: "google_maps", label: "Google Maps" },
                { key: "cnpj", label: "CNPJ / Receita Federal" },
              ].map(({ key, label }) => (
                <label key={key} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={fontes.includes(key)}
                    onChange={() => toggleFonte(key)}
                    className="w-3.5 h-3.5 accent-accent"
                  />
                  <span className="text-[12px] text-text-secondary">{label}</span>
                </label>
              ))}
            </div>
            {fontes.length === 0 && (
              <p className="text-[11px] text-danger mt-1">Selecione ao menos uma fonte.</p>
            )}
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
            disabled={!hasNichos || !hasCidades || fontes.length === 0}
            className="px-4 py-2 text-[13px] text-bg font-medium rounded-lg transition-default bg-accent hover:bg-accent-dim disabled:opacity-30 disabled:cursor-not-allowed"
          >
            Executar Scraping
          </button>
        </div>
      </div>
    </div>
  );
}
