# WhatsApp Inbox — P5 Settings UI Card Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar card "WhatsApp (Evolution)" em `/app/settings/integracoes` com formulário de credenciais, botão "Testar conexão" e URL do webhook pra copiar — substituindo o setup manual via SQL.

**Architecture:** Backend já está pronto (PROVIDER_SCHEMAS.evolution + endpoint `/api/workspace/integrations/evolution/webhook-url` criados em P0-P2). Este plan é puramente frontend: estender `PROVIDER_META` + `PROVIDER_FIELDS` no settings UI existente + criar componente reutilizável de webhook URL display com botão copiar.

**Tech Stack:** Next.js 16 App Router · React 19 · TypeScript · DS Instrumento

**Spec:** `docs/superpowers/specs/2026-05-16-whatsapp-inbox-design.md` (§6)

---

## Notas de execução

- Branch: `feat/whatsapp-inbox-p5-settings-ui`. Baseia em `main` (P0-P2 merged) ou em `feat/whatsapp-inbox-p4-frontend` se quiser stack PRs.
- Frontend lint: `cd frontend && npm run lint`
- Frontend dev: `cd frontend && npm run dev`
- Sem testes frontend automatizados — validação manual via dev server.
- Commits Conventional Commits, escopo `settings`.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/lib/settings-types.ts` | Modify | Adicionar `"evolution"` em `ProviderId` + `PROVIDER_META.evolution` |
| `frontend/src/lib/api-settings.ts` | Modify | Adicionar `getEvolutionWebhookUrl()` |
| `frontend/src/app/app/settings/integracoes/[provider]/page.tsx` | Modify | Adicionar `evolution` em `PROVIDER_FIELDS` |
| `frontend/src/components/settings/webhook-url-field.tsx` | Create | Componente "URL + botão copiar" |
| `frontend/src/components/settings/webhook-url-field.css` | Create | Estilos do componente |

---

## Task 1: Backend — confirmar endpoints existentes

> **Não cria código.** Validação que backend está pronto pra P5.

- [ ] **Step 1: Confirmar Evolution provider schema**

```bash
cd backend && grep -A 8 "EvolutionConfig" app/integrations/schemas.py
```

Expected: ver campos `base_url`, `instance`, `api_key`, `webhook_secret`.

- [ ] **Step 2: Confirmar endpoint webhook-url**

```bash
cd backend && grep -A 12 "get_webhook_url" app/routers/workspace_settings.py
```

Expected: ver função registrada em `/integrations/{provider}/webhook-url`.

- [ ] **Step 3: Confirmar tester Evolution**

```bash
cd backend && grep -A 10 "check_evolution\|run_test" app/integrations/testers.py
```

Expected: ver função `check_evolution` registrada no `_TESTERS`.

Se algum desses 3 não existir, parar e abrir issue. Não prosseguir com P5.

---

## Task 2: Frontend — adicionar Evolution em PROVIDER_META

**Files:**
- Modify: `frontend/src/lib/settings-types.ts`

- [ ] **Step 1: Estender `ProviderId` type**

Edit `frontend/src/lib/settings-types.ts`:

Antes:
```typescript
export type ProviderId =
  | "resend" | "telegram" | "apify" | "llm"
  | "hunter" | "apollo" | "langsmith";
```

Depois:
```typescript
export type ProviderId =
  | "resend" | "telegram" | "apify" | "llm"
  | "hunter" | "apollo" | "langsmith" | "evolution";
```

- [ ] **Step 2: Estender `PROVIDER_META`**

No mesmo arquivo, dentro do objeto `PROVIDER_META`:

```typescript
export const PROVIDER_META: Record<ProviderId, { label: string; description: string; docs?: string }> = {
  resend:    { label: "Resend",    description: "Email transacional para cadência de outreach",    docs: "https://resend.com/docs" },
  telegram:  { label: "Telegram",  description: "Alertas de cadência (respostas, falhas)",         docs: "https://core.telegram.org/bots/api" },
  apify:     { label: "Apify",     description: "Scraping de Google Maps",                          docs: "https://docs.apify.com" },
  llm:       { label: "LLM",       description: "Geração de landing pages, copy e diagnósticos",   docs: "" },
  hunter:    { label: "Hunter",    description: "Descoberta de email por domínio",                  docs: "https://hunter.io/api-documentation" },
  apollo:    { label: "Apollo",    description: "Enriquecimento de contato",                        docs: "https://apolloio.github.io/apollo-api-docs/" },
  langsmith: { label: "LangSmith", description: "Tracing de chains LLM",                            docs: "https://docs.smith.langchain.com" },
  evolution: { label: "WhatsApp (Evolution)", description: "Envio e recebimento de mensagens WhatsApp via Evolution API", docs: "https://doc.evolution-api.com" },
};
```

- [ ] **Step 3: Lint**

```bash
cd frontend && npm run lint -- --max-warnings=0
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git checkout -b feat/whatsapp-inbox-p5-settings-ui
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add frontend/src/lib/settings-types.ts
git commit -m "feat(settings): adicionar Evolution em PROVIDER_META"
```

---

## Task 3: Frontend — api wrapper webhook URL

**Files:**
- Modify: `frontend/src/lib/api-settings.ts`

- [ ] **Step 1: Adicionar função `getEvolutionWebhookUrl`**

Edit `frontend/src/lib/api-settings.ts`. Adicionar ao final do arquivo (após os outros exports):

```typescript
export const getProviderWebhookUrl = (provider: ProviderId) =>
  authedFetch<{ url: string }>(`/api/workspace/integrations/${provider}/webhook-url`);
```

- [ ] **Step 2: Lint**

```bash
cd frontend && npm run lint -- --max-warnings=0
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/api-settings.ts
git commit -m "feat(settings): api wrapper pra webhook URL"
```

---

## Task 4: Frontend — componente WebhookUrlField

**Files:**
- Create: `frontend/src/components/settings/webhook-url-field.tsx`
- Create: `frontend/src/components/settings/webhook-url-field.css`

- [ ] **Step 1: Criar CSS**

Create `frontend/src/components/settings/webhook-url-field.css`:

```css
.webhook-url-field {
  display: flex;
  gap: 8px;
  align-items: stretch;
  margin-top: 4px;
}

.webhook-url-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface-2);
  color: var(--text);
  font-family: var(--mono, monospace);
  font-size: 12px;
  user-select: all;
  cursor: text;
  outline: none;
}

.webhook-url-copy {
  padding: 8px 14px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 120ms, color 120ms;
}

.webhook-url-copy:hover {
  background: var(--accent);
  color: white;
  border-color: var(--accent);
}

.webhook-url-copy.copied {
  background: var(--salvia, #88c08a);
  color: white;
  border-color: var(--salvia, #88c08a);
}

.webhook-url-empty {
  color: var(--text-muted);
  font-size: 13px;
  padding: 8px 0;
}

.webhook-url-hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-muted);
}
```

- [ ] **Step 2: Criar componente**

Create `frontend/src/components/settings/webhook-url-field.tsx`:

```tsx
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
    } catch {
      // fallback: select input
      const input = document.querySelector<HTMLInputElement>(`input[data-webhook-url="${provider}"]`);
      input?.select();
      document.execCommand("copy");
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
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
```

- [ ] **Step 3: Lint**

```bash
cd frontend && npm run lint -- --max-warnings=0
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/settings/webhook-url-field.tsx frontend/src/components/settings/webhook-url-field.css
git commit -m "feat(settings): componente WebhookUrlField com botão copiar"
```

---

## Task 5: Frontend — adicionar Evolution em PROVIDER_FIELDS

**Files:**
- Modify: `frontend/src/app/app/settings/integracoes/[provider]/page.tsx`

- [ ] **Step 1: Adicionar entry em `PROVIDER_FIELDS`**

Edit `frontend/src/app/app/settings/integracoes/[provider]/page.tsx`.

Procurar o objeto `PROVIDER_FIELDS`. Adicionar entry `evolution`:

```typescript
const PROVIDER_FIELDS: Record<ProviderId, { secrets: { key: string; label: string }[]; plain: { key: string; label: string; type?: string }[] }> = {
  resend:    { /* já existe */ },
  telegram:  { /* já existe */ },
  apify:     { /* já existe */ },
  llm:       { /* já existe */ },
  hunter:    { /* já existe */ },
  apollo:    { /* já existe */ },
  langsmith: { /* já existe */ },
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
```

- [ ] **Step 2: Wire WebhookUrlField no render**

No mesmo arquivo, no JSX do componente `IntegrationDetail`, adicionar abaixo do form section (mas dentro do `<form>`):

```tsx
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
```

E adicionar import no topo:
```typescript
import { WebhookUrlField } from "@/components/settings/webhook-url-field";
```

- [ ] **Step 3: Lint**

```bash
cd frontend && npm run lint -- --max-warnings=0
```

Expected: PASS.

- [ ] **Step 4: Validar manualmente**

```bash
cd frontend && npm run dev
```

Em http://localhost:3000/app/settings/integracoes:
- Lista mostra card "WhatsApp (Evolution)" desconectado

Em http://localhost:3000/app/settings/integracoes/evolution:
- Formulário com 4 campos: base_url, instance, api_key, webhook_secret
- Seção "Webhook" com URL `http://localhost:8000/api/webhooks/whatsapp/1/evolution` + botão Copiar
- Preencher api_key + webhook_secret + base_url + instance, salvar
- Clicar "Testar conexão" → 200 se Evolution rodando, erro detalhado se não

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/app/settings/integracoes/[provider]/page.tsx
git commit -m "feat(settings): card Evolution com formulário + webhook URL"
```

---

## Task 6: Smoke + push + PR

- [ ] **Step 1: Smoke completo no browser**

Subir backend + frontend:
```bash
docker compose up -d  # backend
cd frontend && npm run dev
```

Validar:
1. `/app/settings/integracoes` mostra card Evolution
2. Card abre detail page
3. Form aceita os 4 campos
4. Save persiste em DB (verificar via psql ou via reload)
5. Após save, voltar e ver "configurado" badge
6. "Testar conexão" funciona (mock httpx ou Evolution real)
7. Webhook URL exibe valor correto (composto de `api_url` env + workspace_id + provider)
8. Copiar funciona — paste em qualquer lugar tem a URL

- [ ] **Step 2: Lint final**

```bash
cd frontend && npm run lint -- --max-warnings=0
```

Expected: PASS sem warnings novos.

- [ ] **Step 3: Push da branch**

```bash
git push -u origin feat/whatsapp-inbox-p5-settings-ui
```

- [ ] **Step 4: Abrir PR**

```bash
gh pr create --base main --title "feat(settings): P5 — card WhatsApp Evolution em /app/settings/integracoes" --body "$(cat <<'EOF'
## Summary

UI pra configurar Evolution sem tocar SQL diretamente:
- Adiciona `"evolution"` ao `ProviderId` types + `PROVIDER_META`
- Form fields: `base_url`, `instance`, `api_key`, `webhook_secret`
- Reutiliza fluxo existente de Secret/Plain fields + Save + Test
- Componente novo `WebhookUrlField` com botão copiar — fala com endpoint `/api/workspace/integrations/{provider}/webhook-url` (já criado em P2)
- Hint sobre eventos esperados (messages.upsert + messages.update)

Backend não muda — schema, tester e webhook-url já estavam prontos em P0-P2.

## Test Plan

- [x] Frontend lint sem warnings
- [x] Manual: criar config Evolution via UI, salvar, ver row em `integration_settings` cifrada
- [x] Manual: clicar "Testar conexão" — retorna ok com Evolution rodando ou erro 422/500 explícito
- [x] Manual: URL webhook copiada bate com `${API_URL}/api/webhooks/whatsapp/1/evolution`
- [ ] **Manual com Evolution real (smoke do P2):** apontar URL copiada na admin Evolution, enviar inbound, ver chegar em /app/inbox (precisa de P4 mergeado)
EOF
)"
```

---

## Self-Review

**Spec coverage** (vs `2026-05-16-whatsapp-inbox-design.md` §6):
- ✅ Card "WhatsApp" no card grid → Task 2
- ✅ Provider select (Evolution) — único provider, sem dropdown (Z-API/Cloud API são backlog)
- ✅ Campos por provider — Task 5 (base_url, instance, api_key, webhook_secret)
- ✅ Botão "Testar conexão" — já existe no fluxo padrão (reusa `TestButton` do projeto)
- ✅ Webhook URL exibido pra copiar — Task 4, 5
- ❌ Toggle "Pausar envios" — NÃO incluído neste plan. Depende de P3 (dispatch_outreach). Sem dispatch, não há envio pra pausar. Adicionar quando P3 entrar.

**Não coberto neste plan** (próximos PRs):
- Kill switch toggle (depende de P3)
- Multiprovider dropdown (Z-API, Cloud API são backlog)
- Status do provider em tempo real (health_check no card list) — pode ser próximo P5.5 se útil
- Rotacionar webhook_secret via UI (hoje user re-paste manualmente)

**Placeholder scan:** nenhum step usa "TBD" ou "appropriate error handling".

**Type consistency:**
- `ProviderId` estendido em `settings-types.ts` (Task 2) consumido em `[provider]/page.tsx` (Task 5) e `WebhookUrlField` (Task 4)
- `getProviderWebhookUrl` definido Task 3, consumido Task 4
- Backend endpoint `/api/workspace/integrations/{provider}/webhook-url` retorna `{ url: string }` — bate com type do api wrapper
