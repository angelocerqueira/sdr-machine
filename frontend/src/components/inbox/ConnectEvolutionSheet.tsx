"use client";

import { useEffect, useState } from "react";
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

function ConnectEvolutionSheetInner({ initialStep, onClose, onConnected }: InnerProps) {
  const [step, setStep] = useState<1 | 2>(initialStep);

  // Esc fecha
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <>
      <div className="connect-sheet-backdrop" onClick={onClose} />
      <aside className="connect-sheet" role="dialog" aria-modal="true" aria-label="Conectar Evolution">
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
