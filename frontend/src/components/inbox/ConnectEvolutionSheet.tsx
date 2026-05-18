"use client";

import { useEffect, useRef, useState } from "react";
import { ConnectStep1Credentials } from "./ConnectStep1Credentials";
import { ConnectStep2QR } from "./ConnectStep2QR";
import "./connect-evolution-sheet.css";

interface Props {
  open: boolean;
  initialStep?: 1 | 2;
  onClose: () => void;
  onConnected: () => void;
}

interface InnerProps {
  initialStep: 1 | 2;
  onClose: () => void;
  onConnected: () => void;
}

const FOCUSABLE_SELECTOR =
  'input:not([disabled]), button:not([disabled]), [href], textarea:not([disabled])';

function ConnectEvolutionSheetInner({ initialStep, onClose, onConnected }: InnerProps) {
  const [step, setStep] = useState<1 | 2>(initialStep);
  const sheetRef = useRef<HTMLElement>(null);
  const previousActiveRef = useRef<HTMLElement | null>(null);

  // Esc fecha
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  // Focus trap + restore
  useEffect(() => {
    previousActiveRef.current = document.activeElement as HTMLElement | null;
    const sheet = sheetRef.current;
    if (!sheet) return;

    const focusables = sheet.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
    focusables[0]?.focus();

    function onKey(e: KeyboardEvent) {
      if (e.key !== "Tab") return;
      if (!sheet) return;
      const items = Array.from(
        sheet.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
      );
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      const active = document.activeElement as HTMLElement | null;
      if (e.shiftKey && active === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && active === last) {
        e.preventDefault();
        first.focus();
      }
    }
    window.addEventListener("keydown", onKey);
    const previous = previousActiveRef.current;
    return () => {
      window.removeEventListener("keydown", onKey);
      previous?.focus?.();
    };
  }, []);

  return (
    <>
      <div className="connect-sheet-backdrop" onClick={onClose} aria-hidden="true" />
      <aside
        ref={sheetRef}
        className="connect-sheet"
        role="dialog"
        aria-modal="true"
        aria-label="Conectar Evolution"
      >
        <header className="connect-sheet-header">
          <h2 className="connect-sheet-title">Conectar Evolution API</h2>
          <button className="connect-sheet-close" onClick={onClose} aria-label="Fechar">×</button>
        </header>

        <div className="connect-sheet-stepper">
          <span className={`connect-sheet-step ${step === 1 ? "active" : "done"}`}>
            <span className="connect-sheet-step-dot" />
            01 · Credenciais
          </span>
          <span className="connect-sheet-step-sep" />
          <span className={`connect-sheet-step ${step === 2 ? "active" : ""}`}>
            <span className="connect-sheet-step-dot" />
            02 · Conectar WhatsApp
          </span>
        </div>

        <div className="connect-sheet-body">
          {step === 1 ? (
            <ConnectStep1Credentials onValidated={() => setStep(2)} />
          ) : (
            <ConnectStep2QR onConnected={onConnected} />
          )}
        </div>

        {step === 2 && (
          <div className="connect-sheet-footer">
            <button className="connect-btn" onClick={() => setStep(1)}>← Voltar</button>
            <button className="connect-btn" onClick={onClose}>Fechar</button>
          </div>
        )}
      </aside>
    </>
  );
}

export function ConnectEvolutionSheet({ open, initialStep = 1, onClose, onConnected }: Props) {
  if (!open) return null;
  // Inner remonta a cada open (state reseta naturalmente pro initialStep)
  return (
    <ConnectEvolutionSheetInner
      initialStep={initialStep}
      onClose={onClose}
      onConnected={onConnected}
    />
  );
}
