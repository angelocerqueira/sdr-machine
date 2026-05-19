"use client";

import { useState } from "react";

interface Props {
  apiUrl: string;
}

export function SetupClaudeDesktop({ apiUrl }: Props) {
  const [copied, setCopied] = useState(false);

  const snippet = JSON.stringify({
    mcpServers: {
      "sdr-machine": {
        url: apiUrl,
        auth: { type: "bearer", token: "<COLE_SEU_TOKEN_AQUI>" },
      },
    },
  }, null, 2);

  async function copySnippet() {
    try {
      await navigator.clipboard.writeText(snippet);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  }

  return (
    <section style={{ marginTop: 32 }}>
      <h3 style={{ fontSize: 16, fontWeight: 500, marginBottom: 8 }}>
        Conectar Claude Desktop
      </h3>
      <ol style={{ fontSize: 14, lineHeight: 1.7, color: "var(--text)", paddingLeft: 24, margin: 0 }}>
        <li>Gere um token acima e copie o valor (lembre: aparece só uma vez).</li>
        <li>
          Abra o arquivo de configuração do Claude Desktop:
          <ul style={{ paddingLeft: 18, marginTop: 4 }}>
            <li><strong>macOS:</strong> <code style={{ fontFamily: "var(--font-jetbrains-mono, monospace)", fontSize: 12 }}>~/Library/Application Support/Claude/claude_desktop_config.json</code></li>
            <li><strong>Windows:</strong> <code style={{ fontFamily: "var(--font-jetbrains-mono, monospace)", fontSize: 12 }}>%APPDATA%\Claude\claude_desktop_config.json</code></li>
          </ul>
        </li>
        <li>Cole esse trecho (substitua <code>&lt;COLE_SEU_TOKEN_AQUI&gt;</code> pelo token gerado):</li>
      </ol>

      <div style={{
        position: "relative",
        marginTop: 12,
        padding: 16,
        background: "var(--surface-2)",
        border: "1px solid var(--border)",
        borderRadius: 8,
      }}>
        <pre style={{
          margin: 0,
          fontFamily: "var(--font-jetbrains-mono, monospace)",
          fontSize: 12,
          color: "var(--text)",
          overflow: "auto",
        }}>
          {snippet}
        </pre>
        <button
          type="button"
          onClick={copySnippet}
          style={{
            position: "absolute",
            top: 8,
            right: 8,
            padding: "4px 10px",
            background: copied ? "var(--salvia, #88c08a)" : "var(--surface)",
            color: copied ? "white" : "var(--text)",
            border: "1px solid var(--border)",
            borderRadius: 6,
            fontSize: 12,
            cursor: "pointer",
          }}
        >
          {copied ? "Copiado ✓" : "Copiar"}
        </button>
      </div>

      <p style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 12 }}>
        Após salvar, reinicie o Claude Desktop. O servidor &quot;sdr-machine&quot; vai
        aparecer na lista de ferramentas disponíveis.
      </p>
    </section>
  );
}
