"use client";

import { useState } from "react";
import { revokeMcpToken } from "@/lib/api-mcp";
import type { McpTokenSummary } from "@/lib/settings-types";

interface Props {
  tokens: McpTokenSummary[];
  onRevoked: () => void;
}

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export function McpTokensList({ tokens, onRevoked }: Props) {
  const [revoking, setRevoking] = useState<number | null>(null);

  async function handleRevoke(id: number, name: string) {
    if (!confirm(`Revogar token "${name}"? Claude Desktop com esse token vai parar de funcionar imediatamente.`)) return;
    setRevoking(id);
    try {
      await revokeMcpToken(id);
      onRevoked();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Erro ao revogar");
    } finally {
      setRevoking(null);
    }
  }

  if (tokens.length === 0) {
    return (
      <div style={{
        padding: 24, textAlign: "center", color: "var(--text-muted)",
        fontSize: 14, border: "1px dashed var(--border)", borderRadius: 8,
      }}>
        Nenhum token gerado ainda.
      </div>
    );
  }

  return (
    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
      <thead>
        <tr style={{
          textAlign: "left", fontSize: 12, color: "var(--text-muted)",
          textTransform: "uppercase", letterSpacing: 0.04,
          borderBottom: "1px solid var(--border)",
        }}>
          <th style={{ padding: "8px 12px" }}>Nome</th>
          <th style={{ padding: "8px 12px" }}>Token</th>
          <th style={{ padding: "8px 12px" }}>Criado em</th>
          <th style={{ padding: "8px 12px" }}>Último uso</th>
          <th style={{ padding: "8px 12px" }} />
        </tr>
      </thead>
      <tbody>
        {tokens.map((t) => (
          <tr key={t.id} style={{ borderBottom: "1px solid var(--border)" }}>
            <td style={{ padding: "10px 12px" }}>
              <strong>{t.name}</strong>
            </td>
            <td style={{
              padding: "10px 12px",
              fontFamily: "var(--font-jetbrains-mono, monospace)",
              fontSize: 12, color: "var(--text-muted)",
            }}>
              ••••{t.last4}
            </td>
            <td style={{ padding: "10px 12px", color: "var(--text-muted)", fontSize: 13 }}>
              {fmtDate(t.created_at)}
            </td>
            <td style={{ padding: "10px 12px", color: "var(--text-muted)", fontSize: 13 }}>
              {fmtDate(t.last_used_at)}
            </td>
            <td style={{ padding: "10px 12px", textAlign: "right" }}>
              <button
                type="button"
                onClick={() => handleRevoke(t.id, t.name)}
                disabled={revoking === t.id}
                style={{
                  padding: "4px 10px",
                  background: "transparent",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  color: "var(--terra)",
                  cursor: revoking === t.id ? "not-allowed" : "pointer",
                  fontSize: 12,
                }}
              >
                {revoking === t.id ? "Revogando…" : "Revogar"}
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
