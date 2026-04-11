"use client";

import { useState, useEffect, useCallback } from "react";

interface CsvImportModalProps {
  open: boolean;
  onConfirm: (file: File, nicho: string, cidade: string) => void;
  onCancel: () => void;
}

function CsvImportModalInner({ onConfirm, onCancel }: Omit<CsvImportModalProps, "open">) {
  const [file, setFile] = useState<File | null>(null);
  const [nicho, setNicho] = useState("");
  const [cidade, setCidade] = useState("");
  const [preview, setPreview] = useState<string[][]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    document.addEventListener("keydown", handleEsc);
    return () => document.removeEventListener("keydown", handleEsc);
  }, [onCancel]);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;

    if (!f.name.endsWith(".csv")) {
      setError("Selecione um arquivo .csv");
      return;
    }
    if (f.size > 5 * 1024 * 1024) {
      setError("Arquivo excede limite de 5MB");
      return;
    }

    setError("");
    setFile(f);

    // Preview first 5 rows
    const reader = new FileReader();
    reader.onload = (evt) => {
      const text = evt.target?.result as string;
      const lines = text.split("\n").filter((l) => l.trim());
      const rows = lines.slice(0, 6).map((line) =>
        line.split(",").map((cell) => cell.trim().replace(/^"|"$/g, ""))
      );
      setPreview(rows);
    };
    reader.readAsText(f);
  }, []);

  const handleConfirm = useCallback(() => {
    if (!file) return;
    onConfirm(file, nicho.trim(), cidade.trim());
  }, [file, nicho, cidade, onConfirm]);

  const inputClass =
    "w-full px-3 py-2 bg-surface-raised border border-border rounded-lg text-[13px] text-text placeholder:text-text-muted focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-default";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 sheet-backdrop" onClick={onCancel} />
      <div className="relative bg-surface rounded-xl border border-border p-6 max-w-lg w-full mx-4 shadow-xl">
        <h3 className="text-[15px] font-semibold text-text mb-1">Importar CSV</h3>
        <p className="text-[12px] text-text-muted mb-5">
          Importe leads de um arquivo CSV. Colunas aceitas: nome, telefone, website, endereco, email, cidade, nicho, rating.
        </p>

        <div className="space-y-4">
          {/* File input */}
          <div>
            <label className="block text-[11px] font-semibold text-text-secondary uppercase tracking-wider mb-1.5 font-[family-name:var(--font-mono)]">
              Arquivo CSV
            </label>
            <input
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              className="w-full text-[13px] text-text-secondary file:mr-3 file:px-3 file:py-1.5 file:rounded-md file:border file:border-border file:bg-surface-raised file:text-[12px] file:text-text-secondary file:font-medium file:cursor-pointer hover:file:bg-surface-overlay transition-default"
            />
            {error && (
              <p className="text-[11px] text-danger mt-1">{error}</p>
            )}
          </div>

          {/* Preview */}
          {preview.length > 0 && (
            <div>
              <label className="block text-[11px] font-semibold text-text-secondary uppercase tracking-wider mb-1.5 font-[family-name:var(--font-mono)]">
                Preview ({preview.length > 1 ? preview.length - 1 : 0} linhas)
              </label>
              <div className="overflow-x-auto rounded-lg border border-border">
                <table className="w-full text-[11px]">
                  <thead>
                    <tr className="bg-surface-raised">
                      {preview[0]?.map((header, i) => (
                        <th key={i} className="px-2 py-1.5 text-left text-text-muted font-[family-name:var(--font-mono)] font-medium whitespace-nowrap">
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.slice(1).map((row, ri) => (
                      <tr key={ri} className="border-t border-border-subtle">
                        {row.map((cell, ci) => (
                          <td key={ci} className="px-2 py-1 text-text-secondary whitespace-nowrap max-w-[150px] truncate">
                            {cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Nicho + Cidade */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] font-semibold text-text-secondary uppercase tracking-wider mb-1.5 font-[family-name:var(--font-mono)]">
                Nicho (opcional)
              </label>
              <input
                type="text"
                value={nicho}
                onChange={(e) => setNicho(e.target.value)}
                placeholder="Ex: dentista"
                className={inputClass}
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-text-secondary uppercase tracking-wider mb-1.5 font-[family-name:var(--font-mono)]">
                Cidade (opcional)
              </label>
              <input
                type="text"
                value={cidade}
                onChange={(e) => setCidade(e.target.value)}
                placeholder="Ex: São Paulo"
                className={inputClass}
              />
            </div>
          </div>
          <p className="text-[10px] text-text-muted">
            Nicho e cidade são aplicados aos leads que não tiverem essas colunas no CSV.
          </p>
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
            disabled={!file}
            className="px-4 py-2 text-[13px] text-bg font-medium rounded-lg transition-default bg-accent hover:bg-accent-dim disabled:opacity-30 disabled:cursor-not-allowed"
          >
            Importar
          </button>
        </div>
      </div>
    </div>
  );
}

export function CsvImportModal({ open, onConfirm, onCancel }: CsvImportModalProps) {
  if (!open) return null;
  return <CsvImportModalInner key="csv-modal" onConfirm={onConfirm} onCancel={onCancel} />;
}
