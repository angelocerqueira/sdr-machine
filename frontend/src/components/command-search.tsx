"use client";

import { useEffect } from "react";

interface CommandSearchProps {
  open: boolean;
  onClose: () => void;
}

export function CommandSearch({ open, onClose }: CommandSearchProps) {
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

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[200] flex items-start justify-center pt-[20vh]">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-lg mx-4 bg-surface border border-border rounded-xl shadow-2xl overflow-hidden">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border-subtle">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-text-muted shrink-0">
            <circle cx="7" cy="7" r="5" />
            <path d="M11 11l3.5 3.5" />
          </svg>
          <input
            autoFocus
            type="text"
            placeholder="Buscar leads, jobs, nichos..."
            className="flex-1 bg-transparent text-sm text-text placeholder:text-text-muted outline-none"
          />
          <kbd className="font-[family-name:var(--font-mono)] text-[10px] text-text-muted bg-surface-raised border border-border rounded px-1.5 py-0.5">
            ESC
          </kbd>
        </div>
        <div className="px-4 py-8 text-center">
          <p className="text-sm text-text-muted">Busca global em breve...</p>
        </div>
      </div>
    </div>
  );
}
