"use client";
import { useState } from "react";
import { testIntegration } from "@/lib/api-settings";
import type { ProviderId, TestResult } from "@/lib/settings-types";

export function TestButton({ provider, onResult }: { provider: ProviderId; onResult?: (r: TestResult) => void }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true); setError(null);
    try {
      const r = await testIntegration(provider);
      setResult(r);
      onResult?.(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <button type="button" className="settings-btn settings-btn-ghost" onClick={run} disabled={loading}>
        {loading ? "Testando…" : "Testar conexão"}
      </button>
      {result && (
        <span style={{ fontSize: 12, color: result.ok ? "var(--ok)" : "var(--danger)" }}>
          {result.ok ? `✓ OK · ${result.latency_ms}ms` : `✗ ${result.error || "Falhou"}`}
        </span>
      )}
      {error && <span style={{ fontSize: 12, color: "var(--danger)" }}>{error}</span>}
    </div>
  );
}
