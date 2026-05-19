"use client";

import { useState } from "react";
import "./token-created-modal.css";

interface Props {
  token: string;
  name: string;
  onClose: () => void;
}

export function TokenCreatedModal({ token, name, onClose }: Props) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(token);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* fallback ignored */
    }
  }

  return (
    <div className="tcm-backdrop" role="dialog" aria-modal="true" aria-label="Token criado">
      <div className="tcm-sheet">
        <h2 className="tcm-title">Token gerado: {name}</h2>
        <p className="tcm-warn">
          ⚠ Esse token aparece <strong>apenas uma vez</strong>. Copie agora — se você perder, terá que gerar outro.
        </p>

        <div className="tcm-token-box">
          <code className="tcm-token-text">{token}</code>
          <button
            type="button"
            className={`tcm-copy-btn ${copied ? "copied" : ""}`}
            onClick={copy}
          >
            {copied ? "Copiado ✓" : "Copiar"}
          </button>
        </div>

        <div className="tcm-actions">
          <button type="button" className="tcm-btn primary" onClick={onClose}>
            Já copiei, fechar
          </button>
        </div>
      </div>
    </div>
  );
}
