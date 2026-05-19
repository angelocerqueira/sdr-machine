"use client";

import { useEffect, useState } from "react";
import { listMcpTokens, createMcpToken } from "@/lib/api-mcp";
import type { McpTokenSummary } from "@/lib/settings-types";
import { McpTokensList } from "@/components/settings/mcp-tokens-list";
import { TokenCreatedModal } from "@/components/settings/token-created-modal";
import { SetupClaudeDesktop } from "@/components/settings/setup-claude-desktop";

export default function McpSettingsPage() {
  const [tokens, setTokens] = useState<McpTokenSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [newTokenName, setNewTokenName] = useState("");
  const [creating, setCreating] = useState(false);
  const [created, setCreated] = useState<{ token: string; name: string } | null>(null);

  const mcpUrl = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/mcp`;

  async function load() {
    setLoading(true);
    try {
      const rows = await listMcpTokens();
      setTokens(rows);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newTokenName.trim() || creating) return;
    setCreating(true);
    try {
      const result = await createMcpToken(newTokenName.trim());
      setCreated({ token: result.token, name: result.name });
      setNewTokenName("");
      await load();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Erro ao gerar token");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div style={{ maxWidth: 880 }}>
      <h2 style={{ fontSize: 22, fontWeight: 480, marginBottom: 8 }}>
        Tokens MCP
      </h2>
      <p style={{ color: "var(--text-muted)", marginBottom: 24, fontSize: 14, lineHeight: 1.6 }}>
        Servidor MCP do SDR Machine em <code style={{ fontFamily: "var(--font-jetbrains-mono, monospace)", fontSize: 12 }}>{mcpUrl}</code>.
        Cada token autentica um cliente (ex: Claude Desktop) com acesso completo ao seu workspace.
      </p>

      <section className="settings-section" style={{ marginBottom: 24 }}>
        <h3 className="settings-section-title">Gerar token novo</h3>
        <form onSubmit={handleCreate} style={{ display: "flex", gap: 8, alignItems: "stretch" }}>
          <input
            type="text"
            placeholder="ex: claude-desktop-laptop"
            value={newTokenName}
            onChange={(e) => setNewTokenName(e.target.value)}
            maxLength={120}
            required
            style={{
              flex: 1,
              padding: "8px 12px",
              border: "1px solid var(--border)",
              borderRadius: 8,
              background: "var(--surface-2)",
              color: "var(--text)",
              fontSize: 14,
            }}
          />
          <button
            type="submit"
            disabled={creating || !newTokenName.trim()}
            style={{
              padding: "8px 16px",
              background: "var(--accent)",
              color: "white",
              border: "none",
              borderRadius: 8,
              fontWeight: 500,
              cursor: creating ? "not-allowed" : "pointer",
              opacity: creating || !newTokenName.trim() ? 0.5 : 1,
            }}
          >
            {creating ? "Gerando…" : "Gerar token"}
          </button>
        </form>
      </section>

      <section className="settings-section" style={{ marginBottom: 32 }}>
        <h3 className="settings-section-title">Tokens ativos</h3>
        {loading ? (
          <div style={{ color: "var(--text-muted)", fontSize: 14 }}>Carregando…</div>
        ) : (
          <McpTokensList tokens={tokens} onRevoked={load} />
        )}
      </section>

      <SetupClaudeDesktop apiUrl={mcpUrl} />

      {created && (
        <TokenCreatedModal
          token={created.token}
          name={created.name}
          onClose={() => setCreated(null)}
        />
      )}
    </div>
  );
}
