"use client";

import { useState } from "react";
import { Icon } from "@/components/ui";

interface Props {
  label: string;
  hasValue: boolean;
  last4?: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}

export function SecretField({ label, hasValue, last4, value, onChange, placeholder }: Props) {
  const [editing, setEditing] = useState(!hasValue);

  if (!editing) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <div>
          <div style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 4 }}>{label}</div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14 }}>
            <Icon name="check" size={14} style={{ color: "var(--ok)" }} />
            <span>Configurado · termina em <code>{last4 ?? "????"}</code></span>
          </div>
        </div>
        <button
          type="button"
          className="settings-btn settings-btn-ghost"
          onClick={() => { setEditing(true); onChange(""); }}
        >
          Substituir
        </button>
      </div>
    );
  }

  return (
    <div>
      <label style={{ fontSize: 13, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>{label}</label>
      <div style={{ display: "flex", gap: 8 }}>
        <input
          type="password"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="settings-input"
          autoComplete="off"
          style={{ flex: 1 }}
        />
        {hasValue && (
          <button
            type="button"
            className="settings-btn settings-btn-ghost"
            onClick={() => { setEditing(false); onChange(""); }}
          >
            Cancelar
          </button>
        )}
      </div>
      {hasValue && (
        <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 6 }}>
          Vazio mantém a chave atual. Preencha pra substituir.
        </p>
      )}
    </div>
  );
}
