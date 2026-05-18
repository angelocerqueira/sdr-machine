"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getIntegration, updateIntegration, deleteIntegration } from "@/lib/api-settings";
import { SecretField } from "@/components/settings/secret-field";
import { TestButton } from "@/components/settings/test-button";
import { StatusBadge } from "@/components/settings/status-badge";
import { WebhookUrlField } from "@/components/settings/webhook-url-field";
import { PROVIDER_META, type IntegrationSummary, type ProviderId } from "@/lib/settings-types";

const PROVIDER_FIELDS: Record<ProviderId, { secrets: { key: string; label: string }[]; plain: { key: string; label: string; type?: string }[] }> = {
  resend:    { secrets: [{ key: "api_key", label: "API key" }, { key: "webhook_secret", label: "Webhook secret (opcional)" }],
               plain:   [{ key: "from_email", label: "From email", type: "email" }, { key: "from_name", label: "From name" }, { key: "reply_to", label: "Reply-to (opcional)", type: "email" }] },
  telegram:  { secrets: [{ key: "bot_token", label: "Bot token" }],
               plain:   [{ key: "chat_id", label: "Chat ID" }] },
  apify:     { secrets: [{ key: "token", label: "API token" }], plain: [] },
  llm:       { secrets: [{ key: "api_key", label: "API key" }],
               plain:   [{ key: "model", label: "Modelo" }, { key: "base_url", label: "Base URL", type: "url" }] },
  hunter:    { secrets: [{ key: "api_key", label: "API key" }], plain: [] },
  apollo:    { secrets: [{ key: "api_key", label: "API key" }], plain: [] },
  langsmith: { secrets: [{ key: "api_key", label: "API key" }],
               plain:   [{ key: "project", label: "Projeto" }] },
  evolution: {
    secrets: [
      { key: "api_key", label: "API key" },
      { key: "webhook_secret", label: "Webhook secret (HMAC)" },
    ],
    plain: [
      { key: "base_url", label: "Base URL Evolution", type: "url" },
      { key: "instance", label: "Instance name" },
    ],
  },
};

export default function IntegrationDetail({ params }: { params: Promise<{ provider: string }> }) {
  const router = useRouter();
  const { provider } = use(params) as { provider: ProviderId };
  const meta = PROVIDER_META[provider];
  const fields = PROVIDER_FIELDS[provider];

  const [data, setData] = useState<IntegrationSummary | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    getIntegration(provider).then((d) => {
      setData(d);
      const init: Record<string, string> = {};
      fields.plain.forEach((f) => { init[f.key] = (d.config[f.key] as string) ?? ""; });
      setDraft(init);
    });
  }, [provider]);

  if (!data || !meta) return <div>Carregando…</div>;

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!data) return;
    setSaving(true);
    try {
      const payload: Record<string, unknown> = {};
      for (const f of fields.plain) {
        const v = draft[f.key];
        if (v !== undefined) payload[f.key] = v;
      }
      for (const f of fields.secrets) {
        const v = draft[f.key];
        if (v) payload[f.key] = v;
      }
      const next = await updateIntegration(provider, payload);
      setData(next);
      setToast("Configuração salva");
      setTimeout(() => setToast(null), 2000);
    } catch (e) {
      setToast(e instanceof Error ? e.message : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  }

  async function onRemove() {
    if (!confirm(`Remover ${meta.label}? Cadências em andamento podem falhar.`)) return;
    await deleteIntegration(provider);
    router.push("/app/settings/integracoes");
  }

  return (
    <form onSubmit={save}>
      <Link href="/app/settings/integracoes" style={{ fontSize: 13, color: "var(--text-muted)" }}>
        ← Voltar pra integrações
      </Link>
      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 8, marginBottom: 8 }}>
        <h2 style={{ fontSize: 22, fontWeight: 480, margin: 0 }}>{meta.label}</h2>
        <StatusBadge integration={data} />
      </header>
      <p style={{ color: "var(--text-muted)", fontSize: 14, marginBottom: 24 }}>
        {meta.description}
        {meta.docs && <> · <a href={meta.docs} target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent)" }}>Docs</a></>}
      </p>

      {fields.secrets.length > 0 && (
        <section className="settings-section" style={{ marginTop: 0, paddingTop: 0, borderTop: 0 }}>
          <h3 className="settings-section-title">Credenciais</h3>
          {fields.secrets.map((f) => (
            <div key={f.key} className="settings-field">
              <SecretField
                label={f.label}
                hasValue={Boolean(data.config[`has_${f.key}`])}
                last4={data.config[`${f.key}_last4`] as string | undefined}
                value={draft[f.key] || ""}
                onChange={(v) => setDraft((d) => ({ ...d, [f.key]: v }))}
                placeholder={`cole sua ${f.label.toLowerCase()} aqui`}
              />
            </div>
          ))}
        </section>
      )}

      {fields.plain.length > 0 && (
        <section className="settings-section">
          <h3 className="settings-section-title">Configuração</h3>
          {fields.plain.map((f) => (
            <div key={f.key} className="settings-field">
              <label className="settings-field-label">{f.label}</label>
              <input
                className="settings-input"
                type={f.type || "text"}
                value={draft[f.key] || ""}
                onChange={(e) => setDraft((d) => ({ ...d, [f.key]: e.target.value }))}
              />
            </div>
          ))}
        </section>
      )}

      {provider === "evolution" && (
        <section className="settings-section">
          <h3 className="settings-section-title">Webhook</h3>
          <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 8 }}>
            Configure essa URL no painel da Evolution API pra receber mensagens. Use o webhook secret como header <code>X-Sdr-Signature</code>.
          </p>
          <WebhookUrlField
            provider="evolution"
            hint="Eventos: messages.upsert (inbound) + messages.update (status)"
          />
        </section>
      )}

      <section className="settings-section">
        <h3 className="settings-section-title">Status</h3>
        {data.last_test_result ? (
          <p style={{ fontSize: 14, margin: 0 }}>
            Última verificação: {new Date(data.last_tested_at!).toLocaleString("pt-BR")} · {data.last_test_result.latency_ms}ms
            <br />
            {data.last_test_result.ok
              ? <span style={{ color: "var(--ok)" }}>✓ OK</span>
              : <span style={{ color: "var(--danger)" }}>✗ {data.last_test_result.error}</span>}
          </p>
        ) : (
          <p style={{ fontSize: 14, color: "var(--text-muted)", margin: 0 }}>Nunca testado.</p>
        )}
      </section>

      <div className="settings-actions" style={{ justifyContent: "space-between" }}>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <button type="submit" className="settings-btn settings-btn-primary" disabled={saving}>
            {saving ? "Salvando…" : "Salvar"}
          </button>
          <TestButton provider={provider} onResult={() => getIntegration(provider).then(setData)} />
          {toast && <span style={{ fontSize: 14, color: "var(--ok)" }}>{toast}</span>}
        </div>
        <button type="button" className="settings-btn settings-btn-danger" onClick={onRemove}>
          Remover
        </button>
      </div>
    </form>
  );
}
