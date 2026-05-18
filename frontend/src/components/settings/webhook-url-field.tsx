"use client";

import { useEffect, useState } from "react";
import { getProviderWebhookUrl } from "@/lib/api-settings";
import type { ProviderId } from "@/lib/settings-types";
import "./webhook-url-field.css";

interface Props {
  provider: ProviderId;
  label?: string;
  hint?: string;
}

export function WebhookUrlField({ provider, label = "URL do webhook", hint }: Props) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getProviderWebhookUrl(provider)
      .then((res) => {
        if (!cancelled) setUrl(res.url);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => { cancelled = true; };
  }, [provider]);

  async function copy() {
    if (!url) return;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
      return;
    } catch {
      // Clipboard API failed (insecure context, permissions). Try execCommand fallback.
    }
    const input = document.querySelector<HTMLInputElement>(`input[data-webhook-url="${provider}"]`);
    input?.select();
    const ok = document.execCommand("copy");
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } else {
      setError("Falha ao copiar — selecione o campo e use Ctrl/Cmd+C");
    }
  }

  return (
    <div className="settings-field">
      <label className="settings-field-label">{label}</label>
      {error ? (
        <div className="webhook-url-empty">Erro: {error}</div>
      ) : !url ? (
        <div className="webhook-url-empty">Carregando…</div>
      ) : (
        <div className="webhook-url-field">
          <input
            type="text"
            readOnly
            value={url}
            data-webhook-url={provider}
            className="webhook-url-input"
            onFocus={(e) => e.currentTarget.select()}
          />
          <button
            type="button"
            className={`webhook-url-copy ${copied ? "copied" : ""}`}
            onClick={copy}
          >
            {copied ? "Copiado ✓" : "Copiar"}
          </button>
        </div>
      )}
      {hint && <div className="webhook-url-hint">{hint}</div>}
    </div>
  );
}
