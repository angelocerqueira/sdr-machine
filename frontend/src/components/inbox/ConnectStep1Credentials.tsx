"use client";

import { useEffect, useState } from "react";
import {
  getIntegration,
  updateIntegration,
  testIntegration,
  type TestResult,
} from "@/lib/api-settings";

interface Props {
  onValidated: () => void;  // chama quando teste passou — wizard avança pra step 2
}

export function ConnectStep1Credentials({ onValidated }: Props) {
  const [baseUrl, setBaseUrl] = useState("");
  const [instance, setInstance] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [webhookSecret, setWebhookSecret] = useState("");
  const [hasApiKey, setHasApiKey] = useState(false);
  const [hasSecret, setHasSecret] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [test, setTest] = useState<TestResult | null>(null);

  useEffect(() => {
    getIntegration("evolution").then((d) => {
      setBaseUrl((d.config.base_url as string) ?? "");
      setInstance((d.config.instance as string) ?? "");
      setHasApiKey(Boolean(d.config.has_api_key));
      setHasSecret(Boolean(d.config.has_webhook_secret));
    }).catch(() => { /* primeiro setup, sem row ainda */ });
  }, []);

  async function saveAndTest() {
    setSaving(true);
    setTest(null);
    try {
      const config: Record<string, unknown> = { base_url: baseUrl, instance };
      if (apiKey) config.api_key = apiKey;
      if (webhookSecret) config.webhook_secret = webhookSecret;
      await updateIntegration("evolution", config);
      setSaving(false);
      setTesting(true);
      const res = await testIntegration("evolution");
      setTest(res);
      if (res.ok) {
        setTimeout(onValidated, 400);  // pequena pausa pra user ver "✓"
      }
    } catch (e) {
      setTest({ ok: false, latency_ms: 0, error: e instanceof Error ? e.message : String(e) });
    } finally {
      setSaving(false);
      setTesting(false);
    }
  }

  const disabled = !baseUrl || !instance || (!hasApiKey && !apiKey) || (!hasSecret && !webhookSecret);

  return (
    <div>
      <p style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 0, marginBottom: 20 }}>
        Credenciais do seu servidor Evolution. <strong>api_key</strong> e <strong>webhook_secret</strong> ficam cifrados no banco.
      </p>

      <div className="connect-form-field">
        <label className="connect-form-label">Base URL</label>
        <input
          className="connect-form-input mono"
          type="url"
          placeholder="https://evolution.seuhost.com"
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
        />
      </div>

      <div className="connect-form-field">
        <label className="connect-form-label">Instance name</label>
        <input
          className="connect-form-input"
          placeholder="sdr"
          value={instance}
          onChange={(e) => setInstance(e.target.value)}
        />
        <span className="connect-form-hint">Nome da instância criada no painel Evolution.</span>
      </div>

      <div className="connect-form-field">
        <label className="connect-form-label">
          API key {hasApiKey && <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>(••••)</span>}
        </label>
        <input
          className="connect-form-input"
          type="password"
          placeholder={hasApiKey ? "Cole pra trocar" : "Sua API key"}
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
        />
      </div>

      <div className="connect-form-field">
        <label className="connect-form-label">
          Webhook secret {hasSecret && <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>(••••)</span>}
        </label>
        <input
          className="connect-form-input"
          type="password"
          placeholder={hasSecret ? "Cole pra trocar" : "Gere com openssl rand -hex 32"}
          value={webhookSecret}
          onChange={(e) => setWebhookSecret(e.target.value)}
        />
        <span className="connect-form-hint">HMAC pra validar webhooks. Você cola no painel Evolution depois.</span>
      </div>

      <button
        className="connect-btn primary"
        onClick={saveAndTest}
        disabled={disabled || saving || testing}
        style={{ width: "100%", marginTop: 4 }}
      >
        {saving ? "Salvando…" : testing ? "Testando…" : "Salvar e testar"}
      </button>

      {test && (
        <div className={`connect-test-row ${test.ok ? "ok" : "err"}`}>
          {test.ok ? (
            <>✓ Conectado ({test.latency_ms} ms) — avançando…</>
          ) : (
            <>✗ {test.error || "Falhou. Verifique URL/instance/key."}</>
          )}
        </div>
      )}
    </div>
  );
}
