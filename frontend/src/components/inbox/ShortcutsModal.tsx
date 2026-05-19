"use client";

import { useEffect } from "react";

interface Props {
  open: boolean;
  onClose: () => void;
}

const SHORTCUTS: { keys: string[]; label: string }[] = [
  { keys: ["J", "↓"], label: "Próxima conversa" },
  { keys: ["K", "↑"], label: "Conversa anterior" },
  { keys: ["1"], label: "Filtro: Todas" },
  { keys: ["2"], label: "Filtro: Não lidas" },
  { keys: ["3"], label: "Filtro: Respondidas" },
  { keys: ["4"], label: "Filtro: Ganho" },
  { keys: ["⌘", "K"], label: "Buscar conversas" },
  { keys: ["Enter"], label: "Enviar mensagem (no composer)" },
  { keys: ["⇧", "Enter"], label: "Quebrar linha (no composer)" },
  { keys: ["Esc"], label: "Voltar pra lista" },
  { keys: ["?"], label: "Mostrar este painel" },
];

export function ShortcutsModal({ open, onClose }: Props) {
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="inbox-shortcuts-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Atalhos do teclado"
    >
      <div className="inbox-shortcuts-modal" onClick={(e) => e.stopPropagation()}>
        <header className="inbox-shortcuts-header">
          <h2>Atalhos do teclado</h2>
          <button type="button" onClick={onClose} aria-label="Fechar">✕</button>
        </header>
        <ul className="inbox-shortcuts-list">
          {SHORTCUTS.map((s, i) => (
            <li key={i} className="inbox-shortcuts-item">
              <span className="inbox-shortcuts-label">{s.label}</span>
              <span className="inbox-shortcuts-keys">
                {s.keys.map((k, j) => (
                  <kbd key={j}>{k}</kbd>
                ))}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
