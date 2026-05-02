"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

export type ToastVariant = "default" | "success" | "error" | "warning";

export interface Toast {
  id: number;
  message: string;
  variant: ToastVariant;
  duration: number;
}

interface ToastContextValue {
  toast: (message: string, opts?: { variant?: ToastVariant; duration?: number }) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

let nextId = 1;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timersRef = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
  }, []);

  const toast = useCallback<ToastContextValue["toast"]>(
    (message, opts) => {
      const id = nextId++;
      const variant = opts?.variant ?? "default";
      const duration = opts?.duration ?? 5000;
      setToasts((prev) => [...prev, { id, message, variant, duration }]);
      const timer = setTimeout(() => dismiss(id), duration);
      timersRef.current.set(id, timer);
    },
    [dismiss],
  );

  useEffect(() => {
    const timers = timersRef.current;
    return () => {
      for (const t of timers.values()) clearTimeout(t);
      timers.clear();
    };
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div
        aria-live="polite"
        aria-atomic="true"
        className="pointer-events-none fixed bottom-4 right-4 z-[60] flex flex-col gap-2"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            role="status"
            className={`pointer-events-auto min-w-[240px] max-w-md rounded-lg border px-4 py-3 text-[13px] shadow-lg transition-default ${
              t.variant === "success"
                ? "border-ok/30 bg-ok/10 text-ok"
                : t.variant === "error"
                ? "border-danger/30 bg-danger/10 text-danger"
                : t.variant === "warning"
                ? "border-warn/30 bg-warn/10 text-warn"
                : "border-border bg-surface-raised text-text"
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <span className="break-words">{t.message}</span>
              <button
                type="button"
                onClick={() => dismiss(t.id)}
                className="text-text-muted hover:text-text transition-default cursor-pointer text-[16px] leading-none"
                aria-label="Fechar"
              >
                ×
              </button>
            </div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return ctx;
}
