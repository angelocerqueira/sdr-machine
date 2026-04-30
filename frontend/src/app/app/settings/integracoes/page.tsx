"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listIntegrations } from "@/lib/api-settings";
import { StatusBadge } from "@/components/settings/status-badge";
import { PROVIDER_META, type IntegrationSummary } from "@/lib/settings-types";

export default function IntegracoesPage() {
  const [items, setItems] = useState<IntegrationSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listIntegrations().then(setItems).finally(() => setLoading(false));
  }, []);

  if (loading) return <div>Carregando…</div>;

  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 480, marginBottom: 8 }}>Integrações</h2>
      <p style={{ color: "var(--text-muted)", marginBottom: 24, fontSize: 14 }}>
        Credenciais de APIs externas. Cada provider pode ser testado depois de configurado.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16 }}>
        {items.map((it) => {
          const meta = PROVIDER_META[it.provider];
          return (
            <Link
              key={it.provider}
              href={`/app/settings/integracoes/${it.provider}`}
              className="settings-card"
            >
              <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <strong>{meta.label}</strong>
                <StatusBadge integration={it} />
              </header>
              <p style={{ fontSize: 13, color: "var(--text-muted)", margin: 0, marginBottom: 12 }}>
                {meta.description}
              </p>
              {it.last_tested_at && (
                <p style={{ fontSize: 12, color: "var(--text-muted)", margin: 0 }}>
                  testado em {new Date(it.last_tested_at).toLocaleString("pt-BR")}
                </p>
              )}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
