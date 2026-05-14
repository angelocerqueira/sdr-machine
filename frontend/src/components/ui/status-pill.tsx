"use client";

import { useEffect, useRef, useState, forwardRef, useImperativeHandle } from "react";
import { KANBAN_COLUMNS } from "@/lib/types";

interface StatusPillProps {
  status: string;
  className?: string;
  onStatusChange?: (newStatus: string) => void;
  disabled?: boolean;
}

export interface StatusPillHandle {
  open: () => void;
}

const STATUS_CONFIG: Record<string, { label: string; classes: string }> = {
  scraped:        { label: "Scrapeado",     classes: "text-ink-3 bg-surface-raised border-border" },
  enriched:       { label: "Analisado",     classes: "text-[oklch(0.56_0.11_230)] bg-[oklch(0.96_0.03_230)] border-transparent" },
  lp_generated:   { label: "LP Gerada",     classes: "text-accent-ink bg-accent-soft border-transparent" },
  outreach_ready: { label: "Outreach",      classes: "text-[oklch(0.52_0.13_300)] bg-[oklch(0.96_0.03_300)] border-transparent" },
  outreach_sent:  { label: "Msg Enviada",   classes: "text-warn bg-warn-soft border-transparent" },
  responded:      { label: "Respondeu",     classes: "text-ok bg-ok-soft border-transparent" },
  in_call:        { label: "Em conversa",   classes: "text-[oklch(0.54_0.14_200)] bg-[oklch(0.96_0.03_200)] border-transparent" },
  closed:         { label: "Fechado",       classes: "text-text-strong bg-surface-raised border-transparent" },
  delivered:      { label: "Entregue",      classes: "text-ink-0 bg-paper-3 border-transparent" },
  disqualified:   { label: "Descartado",    classes: "text-ink-4 bg-surface-raised border-border" },
  failed:         { label: "Falhou",        classes: "text-danger bg-danger-soft border-transparent" },
};

const BASE_CLASSES = "inline-flex items-center gap-1.5 h-[22px] pl-1.5 pr-2.5 text-[11px] font-medium tracking-[0.01em] rounded-full font-mono border";

export const StatusPill = forwardRef<StatusPillHandle, StatusPillProps>(function StatusPill(
  { status, className = "", onStatusChange, disabled },
  ref,
) {
  const config = STATUS_CONFIG[status] ?? { label: status, classes: "text-ink-3 bg-surface-raised" };
  const interactive = !!onStatusChange && !disabled;

  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  useImperativeHandle(ref, () => ({ open: () => interactive && setOpen(true) }), [interactive]);

  useEffect(() => {
    if (!open) return;
    function onDocClick(e: MouseEvent) {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  if (!interactive) {
    return (
      <span className={`${BASE_CLASSES} ${config.classes} ${className}`}>
        <span className="w-1.5 h-1.5 rounded-full bg-current shrink-0" />
        {config.label}
      </span>
    );
  }

  return (
    <div ref={wrapRef} className="relative inline-block">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        title="Alterar status (s)"
        className={`${BASE_CLASSES} ${config.classes} ${className} cursor-pointer hover:opacity-80 transition-opacity`}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-current shrink-0" />
        {config.label}
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" className="shrink-0 -mr-1 opacity-60">
          <path d="M2.5 4l2.5 2.5L7.5 4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {open && (
        <div
          role="menu"
          className="absolute left-0 top-[calc(100%+6px)] z-50 min-w-[180px] py-1 rounded-md border bg-surface shadow-lg"
          style={{ borderColor: "var(--border)", background: "var(--surface)" }}
        >
          {KANBAN_COLUMNS.map((col) => {
            const cfg = STATUS_CONFIG[col.id] ?? { label: col.label, classes: "" };
            const isCurrent = col.id === status;
            return (
              <button
                key={col.id}
                type="button"
                role="menuitem"
                disabled={isCurrent}
                onClick={() => {
                  setOpen(false);
                  if (!isCurrent) onStatusChange?.(col.id);
                }}
                className={`w-full flex items-center justify-between gap-2 px-3 py-1.5 text-[12px] text-left font-mono transition-default ${
                  isCurrent ? "opacity-50 cursor-default" : "hover:bg-surface-raised cursor-pointer"
                }`}
              >
                <span className="flex items-center gap-2">
                  <span className={`inline-flex items-center justify-center w-3 h-3 rounded-full ${cfg.classes}`}>
                    <span className="w-1 h-1 rounded-full bg-current" />
                  </span>
                  <span>{cfg.label}</span>
                </span>
                {isCurrent && (
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none" className="opacity-60">
                    <path d="M2 5l2 2 4-4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
});
