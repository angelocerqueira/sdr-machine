"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { getLeads } from "@/lib/api";
import type { Lead } from "@/lib/types";

interface CommandSearchProps {
  open: boolean;
  onClose: () => void;
}

export function CommandSearch({ open, onClose }: CommandSearchProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  // Keyboard shortcut to open
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        document.dispatchEvent(new CustomEvent("toggle-command-search"));
      }
      if (e.key === "Escape" && open) {
        onClose();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  // Debounced search
  const handleSearch = useCallback((value: string) => {
    setQuery(value);
    setSelectedIndex(0);

    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (value.length < 2) {
      setResults([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    debounceRef.current = setTimeout(() => {
      getLeads({ search: value, per_page: "5" })
        .then((res) => setResults(res.items))
        .catch(() => setResults([]))
        .finally(() => setLoading(false));
    }, 300);
  }, []);

  // Navigate to lead
  const navigateTo = useCallback((lead: Lead) => {
    onClose();
    router.push(`/app/leads/${lead.id}`);
  }, [onClose, router]);

  // Keyboard navigation in results
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && results.length > 0) {
      e.preventDefault();
      navigateTo(results[selectedIndex]);
    }
  }, [results, selectedIndex, navigateTo]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[200] flex items-start justify-center pt-[20vh]">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-lg mx-4 bg-surface border border-border rounded-xl shadow-2xl overflow-hidden">
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border-subtle">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-text-muted shrink-0">
            <circle cx="7" cy="7" r="5" />
            <path d="M11 11l3.5 3.5" />
          </svg>
          <input
            autoFocus
            type="text"
            value={query}
            onChange={(e) => handleSearch(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Buscar leads por nome, nicho, cidade..."
            className="flex-1 bg-transparent text-sm text-text placeholder:text-text-muted outline-none"
          />
          {loading && (
            <span className="w-4 h-4 border-2 border-text-muted border-t-accent rounded-full animate-spin shrink-0" />
          )}
          <kbd className="font-[family-name:var(--font-mono)] text-[10px] text-text-muted bg-surface-raised border border-border rounded px-1.5 py-0.5">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-[300px] overflow-y-auto">
          {query.length < 2 && (
            <div className="px-4 py-8 text-center">
              <p className="text-sm text-text-muted">Digite ao menos 2 caracteres</p>
            </div>
          )}

          {query.length >= 2 && !loading && results.length === 0 && (
            <div className="px-4 py-8 text-center">
              <p className="text-sm text-text-muted">Nenhum resultado para &quot;{query}&quot;</p>
            </div>
          )}

          {results.length > 0 && (
            <div className="py-2">
              <p className="px-4 py-1 text-[10px] font-semibold text-text-muted uppercase tracking-wider font-[family-name:var(--font-mono)]">
                Leads
              </p>
              {results.map((lead, i) => (
                <button
                  key={lead.id}
                  onClick={() => navigateTo(lead)}
                  className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                    i === selectedIndex
                      ? "bg-surface-raised"
                      : "hover:bg-surface-raised/50"
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-text truncate">{lead.nome}</p>
                    <p className="text-[11px] text-text-muted truncate">
                      {[lead.nicho, lead.cidade].filter(Boolean).join(" · ") || "—"}
                    </p>
                  </div>
                  {lead.opportunity_score !== null && (
                    <span className={`text-xs font-[family-name:var(--font-mono)] font-semibold shrink-0 ${
                      lead.opportunity_score >= 60 ? "text-accent" :
                      lead.opportunity_score >= 40 ? "text-warning" : "text-text-muted"
                    }`}>
                      {lead.opportunity_score}
                    </span>
                  )}
                  <span className="text-[10px] text-text-muted font-[family-name:var(--font-mono)] uppercase shrink-0">
                    {lead.status}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
