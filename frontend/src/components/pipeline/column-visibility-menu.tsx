"use client";

import { useEffect, useRef, useState } from "react";
import { Icon } from "@/components/ui";

interface ColumnDescriptor {
  id: string;
  label: string;
}

interface Props {
  columns: ColumnDescriptor[];
  visibility: Record<string, boolean>;
  onChange: (next: Record<string, boolean>) => void;
}

const FIXED_COLUMNS = new Set(["select"]);

export function ColumnVisibilityMenu({ columns, visibility, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    function onClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const toggle = (id: string) => {
    if (FIXED_COLUMNS.has(id)) return;
    onChange({ ...visibility, [id]: !visibility[id] });
  };

  return (
    <div ref={menuRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="menu"
        className="inline-flex items-center gap-1 rounded-md border border-border bg-surface-raised px-3 py-1.5 text-[13px] text-text-secondary hover:text-text hover:border-border-strong transition-default cursor-pointer focus:outline-none focus:ring-2 focus:ring-accent/50"
      >
        <Icon name="settings" size={14} />
        Colunas
      </button>
      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full mt-1 z-30 min-w-[200px] rounded-md border border-border bg-surface shadow-lg p-1"
        >
          {columns.map((col) => {
            const isOn = visibility[col.id] !== false;
            const fixed = FIXED_COLUMNS.has(col.id);
            return (
              <button
                key={col.id}
                type="button"
                role="menuitemcheckbox"
                aria-checked={isOn}
                disabled={fixed}
                onClick={() => toggle(col.id)}
                className={`flex w-full items-center justify-between gap-2 rounded px-2 py-1.5 text-left text-[13px] transition-default ${
                  fixed
                    ? "text-text-muted cursor-not-allowed"
                    : "text-text-secondary hover:bg-surface-raised hover:text-text cursor-pointer"
                }`}
              >
                <span>{col.label}</span>
                {isOn && !fixed && (
                  <Icon name="check" size={12} className="text-accent" />
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
