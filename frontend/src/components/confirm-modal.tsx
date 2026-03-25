"use client";

import { useEffect } from "react";

interface ConfirmModalProps {
  open: boolean;
  title: string;
  children: React.ReactNode;
  confirmLabel?: string;
  confirmVariant?: "accent" | "danger";
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmModal({
  open,
  title,
  children,
  confirmLabel = "Confirmar",
  confirmVariant = "accent",
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  useEffect(() => {
    if (!open) return;
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    document.addEventListener("keydown", handleEsc);
    return () => document.removeEventListener("keydown", handleEsc);
  }, [open, onCancel]);

  if (!open) return null;

  const btnColor = confirmVariant === "danger"
    ? "bg-danger hover:bg-danger/80"
    : "bg-accent hover:bg-accent-dim";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 sheet-backdrop" onClick={onCancel} />
      <div className="relative bg-surface rounded-xl border border-border p-6 max-w-md w-full mx-4 shadow-xl">
        <h3 className="text-[15px] font-semibold text-text mb-3">{title}</h3>
        <div className="text-[13px] text-text-secondary mb-6">{children}</div>
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-[13px] text-text-secondary hover:text-text bg-surface-raised hover:bg-surface-overlay border border-border rounded-lg transition-default"
          >
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 text-[13px] text-bg font-medium rounded-lg transition-default ${btnColor}`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
