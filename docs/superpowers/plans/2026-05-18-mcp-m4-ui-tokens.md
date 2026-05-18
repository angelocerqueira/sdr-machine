# MCP M-4 UI Tokens Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** UI em `/app/settings/mcp` pra user gerar/listar/revogar tokens MCP sem tocar SQL. Token plain mostrado UMA VEZ no momento de criação (modal "copie agora"). Inclui docs inline de setup Claude Desktop.

**Architecture:** Backend ganha 3 endpoints REST sob `/api/workspace/mcp-tokens` (list, create, revoke). Frontend monta nova rota em `/app/settings/mcp` reusando padrões existentes do settings (`/app/settings/integracoes`). Componente `TokenCreatedModal` mostra plain token com botão Copiar, dismissable (irreversível — depois só last4 visível). Documentação setup Claude Desktop embedded na própria página (JSON snippet com botão Copiar).

**Tech Stack:** FastAPI + SQLAlchemy + pytest backend · Next.js 16 + React 19 + TypeScript frontend

**Spec:** [`docs/superpowers/specs/2026-05-18-mcp-server-m0-architecture.md`](../specs/2026-05-18-mcp-server-m0-architecture.md) §7 (Auth + setup UX)

**Depende:** M-1 mergeado (schema `mcp_tokens` + token utilities). Independente de M-2/M-3 funcionalmente.

---

## Notas de execução

- Branch: `feat/mcp-m4-ui-tokens`. Baseia em main com M-1+ merged.
- Backend tests: `cd backend && venv/bin/pytest`
- Frontend lint: `cd frontend && npm run lint`
- Sem testes frontend automatizados (project pattern). Validação manual.
- Commits Conventional Commits, escopo `mcp` ou `settings`

---

## File Structure

### Backend

| File | Action | Responsibility |
|---|---|---|
| `backend/app/routers/mcp_tokens_router.py` | Create | 3 endpoints REST: list, create, revoke |
| `backend/app/main.py` | Modify | Import + register router |
| `backend/tests/mcp/test_tokens_router.py` | Create | 6 testes E2E HTTP |

### Frontend

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/lib/api-mcp.ts` | Create | Fetch wrappers + types |
| `frontend/src/lib/settings-types.ts` | Modify | Adicionar `McpTokenSummary` type |
| `frontend/src/app/app/settings/mcp/page.tsx` | Create | Página list + create + revoke + docs |
| `frontend/src/app/app/settings/layout.tsx` | Modify | Adicionar item "MCP" na nav |
| `frontend/src/components/settings/token-created-modal.tsx` | Create | Modal show-once com botão Copiar |
| `frontend/src/components/settings/setup-claude-desktop.tsx` | Create | Bloco docs inline com JSON snippet |
| `frontend/src/components/settings/mcp-tokens-list.tsx` | Create | Tabela tokens existentes + revoke button |

---

## Task 1: Backend — CRUD endpoints `/api/workspace/mcp-tokens`

**Files:**
- Create: `backend/app/routers/mcp_tokens_router.py`
- Create: `backend/tests/mcp/test_tokens_router.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Criar branch**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git checkout main && git pull origin main
git checkout -b feat/mcp-m4-ui-tokens
```

- [ ] **Step 2: Test falhando**

Create `backend/tests/mcp/test_tokens_router.py`:

```python
from app.models import McpToken
from app.mcp.tokens import generate_token, hash_token


def test_list_tokens_empty(client):
    r = client.get("/api/workspace/mcp-tokens")
    assert r.status_code == 200
    assert r.json() == []


def test_create_token_returns_plain_once(client, db):
    r = client.post("/api/workspace/mcp-tokens", json={"name": "claude-laptop"})
    assert r.status_code == 201
    body = r.json()
    assert "token" in body  # plain mostrado APENAS aqui
    assert len(body["token"]) == 64
    assert body["last4"] == body["token"][-4:]
    assert body["name"] == "claude-laptop"
    assert body["revoked_at"] is None

    # Confirmar persistência: row existe, hash bate
    row = db.query(McpToken).filter_by(name="claude-laptop").first()
    assert row is not None
    assert row.token_hash == hash_token(body["token"])
    assert row.workspace_id == 1


def test_create_token_requires_name(client):
    r = client.post("/api/workspace/mcp-tokens", json={})
    assert r.status_code == 422


def test_list_tokens_shows_last4_not_full(client, db):
    plain = generate_token()
    db.add(McpToken(
        workspace_id=1, name="existing", token_hash=hash_token(plain),
        last4=plain[-4:],
    ))
    db.commit()

    r = client.get("/api/workspace/mcp-tokens")
    items = r.json()
    assert len(items) == 1
    item = items[0]
    assert item["name"] == "existing"
    assert item["last4"] == plain[-4:]
    assert "token" not in item  # NUNCA expor plain depois de criação
    assert "token_hash" not in item  # nem hash


def test_revoke_token_marks_revoked(client, db):
    plain = generate_token()
    db.add(McpToken(
        workspace_id=1, name="revokeme", token_hash=hash_token(plain), last4="abcd",
    ))
    db.commit()
    tok = db.query(McpToken).filter_by(name="revokeme").first()

    r = client.delete(f"/api/workspace/mcp-tokens/{tok.id}")
    assert r.status_code == 204

    db.refresh(tok)
    assert tok.revoked_at is not None


def test_revoke_unknown_token_returns_404(client):
    r = client.delete("/api/workspace/mcp-tokens/9999")
    assert r.status_code == 404


def test_list_excludes_revoked_by_default(client, db):
    from datetime import datetime
    plain_a = generate_token()
    plain_b = generate_token()
    db.add_all([
        McpToken(workspace_id=1, name="active", token_hash=hash_token(plain_a), last4="aaaa"),
        McpToken(workspace_id=1, name="revoked", token_hash=hash_token(plain_b), last4="bbbb",
                 revoked_at=datetime.utcnow()),
    ])
    db.commit()

    r = client.get("/api/workspace/mcp-tokens")
    items = r.json()
    assert len(items) == 1
    assert items[0]["name"] == "active"
```

- [ ] **Step 3: Rodar — deve falhar**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_tokens_router.py -v
```

Expected: FAIL com 404 (router não registrado).

- [ ] **Step 4: Implementar router**

Create `backend/app/routers/mcp_tokens_router.py`:

```python
"""CRUD endpoints pros MCP tokens — usados pela UI /app/settings/mcp."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.integrations.tenant import get_current_workspace_id
from app.mcp.tokens import generate_token, hash_token, list_tokens, revoke_token
from app.models import McpToken

router = APIRouter(prefix="/api/workspace/mcp-tokens", tags=["mcp-tokens"])


class TokenSummary(BaseModel):
    """Não inclui token_hash nem plain — só metadata + last4."""
    id: int
    name: str
    last4: str
    created_at: datetime
    last_used_at: Optional[datetime]
    revoked_at: Optional[datetime]

    model_config = {"from_attributes": True}


class TokenCreatedOut(TokenSummary):
    """Inclui plain token — único momento que ele aparece em qualquer response."""
    token: str


class TokenCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)


@router.get("", response_model=list[TokenSummary])
def list_mcp_tokens(request: Request, db: Session = Depends(get_db)):
    ws = get_current_workspace_id(request)
    rows = list_tokens(db, workspace_id=ws, include_revoked=False)
    return rows


@router.post("", response_model=TokenCreatedOut, status_code=201)
def create_mcp_token(
    payload: TokenCreateIn, request: Request, db: Session = Depends(get_db),
):
    ws = get_current_workspace_id(request)
    plain = generate_token()
    token = McpToken(
        workspace_id=ws,
        name=payload.name,
        token_hash=hash_token(plain),
        last4=plain[-4:],
    )
    db.add(token)
    db.commit()
    db.refresh(token)

    return TokenCreatedOut(
        id=token.id, name=token.name, last4=token.last4,
        created_at=token.created_at, last_used_at=token.last_used_at,
        revoked_at=token.revoked_at, token=plain,
    )


@router.delete("/{token_id}", status_code=204)
def revoke_mcp_token(token_id: int, request: Request, db: Session = Depends(get_db)):
    ws = get_current_workspace_id(request)
    row = db.query(McpToken).filter_by(id=token_id, workspace_id=ws).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Token not found")
    if row.revoked_at is None:
        revoke_token(db, row.token_hash)
    return None
```

- [ ] **Step 5: Registrar router em `main.py`**

Edit `backend/app/main.py`:

```python
# Linha de imports — adicionar:
from app.routers import mcp_tokens_router
```

E após os outros `app.include_router(...)`:

```python
app.include_router(mcp_tokens_router.router)
```

- [ ] **Step 6: Rodar tests**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_tokens_router.py -v
```

Expected: 7 PASS.

- [ ] **Step 7: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/app/routers/mcp_tokens_router.py backend/app/main.py backend/tests/mcp/test_tokens_router.py
git commit -m "feat(mcp): CRUD endpoints /api/workspace/mcp-tokens"
```

---

## Task 2: Frontend — api wrappers + types

**Files:**
- Create: `frontend/src/lib/api-mcp.ts`
- Modify: `frontend/src/lib/settings-types.ts`

- [ ] **Step 1: Adicionar types em `settings-types.ts`**

Edit `frontend/src/lib/settings-types.ts`. Adicionar ao final:

```typescript
export interface McpTokenSummary {
  id: number;
  name: string;
  last4: string;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}

export interface McpTokenCreated extends McpTokenSummary {
  token: string;  // plain — só aparece UMA VEZ na resposta de create
}
```

- [ ] **Step 2: Criar `api-mcp.ts`**

Create `frontend/src/lib/api-mcp.ts`:

```typescript
import type { McpTokenCreated, McpTokenSummary } from "./settings-types";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getSessionToken(): string | null {
  const cookies = document.cookie.split("; ");
  for (const c of cookies) {
    if (
      c.startsWith("__Secure-better-auth.session_data=") ||
      c.startsWith("better-auth.session_data=")
    ) {
      try {
        const val = decodeURIComponent(c.split("=").slice(1).join("="));
        const data = JSON.parse(atob(val));
        return data?.session?.session?.token || null;
      } catch {
        /* ignore */
      }
    }
  }
  for (const c of cookies) {
    if (
      c.startsWith("__Secure-better-auth.session_token=") ||
      c.startsWith("better-auth.session_token=")
    ) {
      const val = decodeURIComponent(c.split("=").slice(1).join("="));
      return val.split(".")[0];
    }
  }
  return null;
}

async function authedFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getSessionToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API}${path}`, { ...init, headers, credentials: "include" });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`${res.status}: ${txt}`);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const listMcpTokens = () =>
  authedFetch<McpTokenSummary[]>("/api/workspace/mcp-tokens");

export const createMcpToken = (name: string) =>
  authedFetch<McpTokenCreated>("/api/workspace/mcp-tokens", {
    method: "POST",
    body: JSON.stringify({ name }),
  });

export const revokeMcpToken = (id: number) =>
  authedFetch<void>(`/api/workspace/mcp-tokens/${id}`, { method: "DELETE" });
```

- [ ] **Step 3: Lint**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/frontend && npm run lint -- --max-warnings=1
```

Expected: 0 errors. 1 pre-existing warning OK.

- [ ] **Step 4: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add frontend/src/lib/api-mcp.ts frontend/src/lib/settings-types.ts
git commit -m "feat(mcp): frontend api wrappers + types"
```

---

## Task 3: `TokenCreatedModal` — mostra plain token uma vez

**Files:**
- Create: `frontend/src/components/settings/token-created-modal.tsx`
- Create: `frontend/src/components/settings/token-created-modal.css`

- [ ] **Step 1: Criar CSS**

Create `frontend/src/components/settings/token-created-modal.css`:

```css
.tcm-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 50;
  display: grid;
  place-items: center;
  padding: 20px;
  opacity: 0;
  animation: tcm-fade 200ms ease-out forwards;
}

@keyframes tcm-fade {
  to { opacity: 1; }
}

.tcm-sheet {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
  max-width: 540px;
  width: 100%;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.tcm-title {
  font-size: 18px;
  font-weight: 500;
  margin: 0 0 6px;
  color: var(--text);
}

.tcm-warn {
  font-size: 13px;
  color: var(--mostarda, #e6c45c);
  margin: 0 0 16px;
}

.tcm-token-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 16px;
}

.tcm-token-text {
  flex: 1;
  font-family: var(--font-jetbrains-mono, monospace);
  font-size: 12px;
  color: var(--text);
  user-select: all;
  word-break: break-all;
}

.tcm-copy-btn {
  padding: 6px 12px;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
}
.tcm-copy-btn.copied {
  background: var(--salvia, #88c08a);
}

.tcm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.tcm-btn {
  padding: 8px 16px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}
.tcm-btn.primary {
  background: var(--accent);
  color: white;
  border-color: var(--accent);
}
```

- [ ] **Step 2: Criar componente**

Create `frontend/src/components/settings/token-created-modal.tsx`:

```tsx
"use client";

import { useState } from "react";
import "./token-created-modal.css";

interface Props {
  token: string;
  name: string;
  onClose: () => void;
}

export function TokenCreatedModal({ token, name, onClose }: Props) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(token);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback: selection-only
    }
  }

  return (
    <div className="tcm-backdrop" role="dialog" aria-modal="true" aria-label="Token criado">
      <div className="tcm-sheet">
        <h2 className="tcm-title">Token gerado: {name}</h2>
        <p className="tcm-warn">
          ⚠ Esse token aparece <strong>apenas uma vez</strong>. Copie agora — se você perder, terá que gerar outro.
        </p>

        <div className="tcm-token-box">
          <code className="tcm-token-text">{token}</code>
          <button
            type="button"
            className={`tcm-copy-btn ${copied ? "copied" : ""}`}
            onClick={copy}
          >
            {copied ? "Copiado ✓" : "Copiar"}
          </button>
        </div>

        <div className="tcm-actions">
          <button type="button" className="tcm-btn primary" onClick={onClose}>
            Já copiei, fechar
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Lint**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/frontend && npm run lint -- --max-warnings=1
```

Expected: 0 errors.

- [ ] **Step 4: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add frontend/src/components/settings/token-created-modal.tsx frontend/src/components/settings/token-created-modal.css
git commit -m "feat(mcp): TokenCreatedModal — plain token mostrado uma vez"
```

---

## Task 4: `SetupClaudeDesktop` — docs inline com snippet copy

**Files:**
- Create: `frontend/src/components/settings/setup-claude-desktop.tsx`

- [ ] **Step 1: Criar componente**

Create `frontend/src/components/settings/setup-claude-desktop.tsx`:

```tsx
"use client";

import { useState } from "react";

interface Props {
  apiUrl: string;  // URL do backend, ex: https://api.sdrmachine.com/api/mcp
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
```

- [ ] **Step 2: Lint**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/frontend && npm run lint -- --max-warnings=1
```

- [ ] **Step 3: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add frontend/src/components/settings/setup-claude-desktop.tsx
git commit -m "feat(mcp): bloco docs setup Claude Desktop"
```

---

## Task 5: `McpTokensList` — tabela tokens + revoke

**Files:**
- Create: `frontend/src/components/settings/mcp-tokens-list.tsx`

- [ ] **Step 1: Criar componente**

Create `frontend/src/components/settings/mcp-tokens-list.tsx`:

```tsx
"use client";

import { useState } from "react";
import { revokeMcpToken } from "@/lib/api-mcp";
import type { McpTokenSummary } from "@/lib/settings-types";

interface Props {
  tokens: McpTokenSummary[];
  onRevoked: () => void;  // reload list após revoke
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
    <table style={{
      width: "100%",
      borderCollapse: "collapse",
      fontSize: 14,
    }}>
      <thead>
        <tr style={{
          textAlign: "left",
          fontSize: 12,
          color: "var(--text-muted)",
          textTransform: "uppercase",
          letterSpacing: 0.04,
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
              fontSize: 12,
              color: "var(--text-muted)",
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
```

- [ ] **Step 2: Lint**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/frontend && npm run lint -- --max-warnings=1
```

- [ ] **Step 3: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add frontend/src/components/settings/mcp-tokens-list.tsx
git commit -m "feat(mcp): McpTokensList tabela + botão revoke"
```

---

## Task 6: Página `/app/settings/mcp`

**Files:**
- Create: `frontend/src/app/app/settings/mcp/page.tsx`
- Modify: `frontend/src/app/app/settings/layout.tsx`

- [ ] **Step 1: Criar página**

Create `frontend/src/app/app/settings/mcp/page.tsx`:

```tsx
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

      {/* Form gerar novo */}
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

      {/* Lista tokens */}
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
```

- [ ] **Step 2: Adicionar item "MCP" no settings nav**

Edit `frontend/src/app/app/settings/layout.tsx`. Localizar lista de items do nav (deve ter Perfil, Integrações, Targeting, Avançado). Adicionar "MCP" entre Targeting e Avançado:

```tsx
const NAV = [
  { key: "perfil", label: "Perfil", href: "/app/settings/perfil" },
  { key: "integracoes", label: "Integrações", href: "/app/settings/integracoes" },
  { key: "targeting", label: "Targeting", href: "/app/settings/targeting" },
  { key: "mcp", label: "MCP", href: "/app/settings/mcp" },
  { key: "avancado", label: "Avançado", href: "/app/settings/avancado" },
];
```

> O arquivo `layout.tsx` exato pode ter shape diferente — adapte. Se não tem array hardcoded, adicione o link no JSX correspondente.

- [ ] **Step 3: Lint + build**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/frontend && npm run lint -- --max-warnings=1
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/frontend && npm run build 2>&1 | tail -10
```

Expected: lint 0 errors, build success.

- [ ] **Step 4: Validar manualmente no browser**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/frontend && npm run dev
```

http://localhost:3000/app/settings/mcp:
- Página carrega
- Form gerar com input name + botão "Gerar token"
- Após gerar: modal aparece com token plain + botão Copiar
- Modal "Já copiei, fechar" dismissa
- Lista mostra novo token com `••••<last4>` e last_used_at "—"
- Setup Claude Desktop section visível com JSON snippet + botão copiar
- Revogar token: confirmação → row some

- [ ] **Step 5: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add frontend/src/app/app/settings/mcp/ frontend/src/app/app/settings/layout.tsx
git commit -m "feat(mcp): página /app/settings/mcp completa"
```

---

## Task 7: Push + PR

- [ ] **Step 1: Suite backend**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest --deselect tests/test_outreach.py 2>&1 | tail -5
```

Expected: ~790 PASS (backend baseline + 7 novos M-4 router tests).

- [ ] **Step 2: Push**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git push -u origin feat/mcp-m4-ui-tokens
```

- [ ] **Step 3: Abrir PR**

```bash
gh pr create --base main --title "feat(mcp): M-4 UI tokens em /app/settings/mcp" --body "$(cat <<'EOF'
## Summary

**Backend (3 endpoints REST):**
- \`GET /api/workspace/mcp-tokens\` — list (sem hash nem plain, só metadata + last4)
- \`POST /api/workspace/mcp-tokens\` — create (retorna plain UMA VEZ)
- \`DELETE /api/workspace/mcp-tokens/{id}\` — revoke

**Frontend (\`/app/settings/mcp\`):**
- Form "Gerar token novo" com input nome
- Lista tokens ativos (nome, ••••last4, criado em, último uso) + botão revogar
- \`TokenCreatedModal\` mostra plain token UMA VEZ com botão Copiar e aviso
- \`SetupClaudeDesktop\` section com JSON snippet pra colar em config.json + botão Copiar
- Item "MCP" adicionado ao settings nav

## Test Plan

- [x] 7 testes backend (list, create, revoke happy + edge)
- [x] Frontend lint + build pass
- [ ] **Manual:**
  - Gerar token → modal aparece → copiar → fechar
  - Token aparece na lista com ••••<last4>
  - Revogar token → confirm dialog → row some
  - Copiar JSON snippet do Setup Claude Desktop
  - Colar token + config no Claude Desktop, reiniciar, ver SDR Machine na lista de tools

## Não coberto

- Prompts pre-built + subscriptions SSE (M-5)
- Validação de unicidade no nome do token (não bloqueia)
- Audit log de uso (V2)
EOF
)"
```

---

## Self-Review

**Spec coverage** (vs M-0 §7):

| Spec item | Task |
|---|---|
| `GET /api/workspace/mcp-tokens` list | Task 1 |
| `POST /api/workspace/mcp-tokens` create (plain UMA VEZ) | Task 1 |
| `DELETE /api/workspace/mcp-tokens/{id}` revoke | Task 1 |
| Plain token mostrado apenas no momento de criação (UI modal) | Task 3 |
| Token + claude_desktop_config.json snippet exibido | Task 4 |
| Listar tokens com last4 + last_used_at + revoke | Task 5 |
| Página `/app/settings/mcp` | Task 6 |
| Item "MCP" no settings nav | Task 6 |

**Placeholder scan:** Nenhum step usa "TBD" / "implement later". Note técnica explicit pro Task 6 Step 2 ("o arquivo layout.tsx exato pode ter shape diferente — adapte") é orientação ao engineer, não placeholder no plan.

**Type consistency:**
- `McpTokenSummary` (sem token) usado em list/revoke responses
- `McpTokenCreated extends McpTokenSummary` com `token: string` SÓ em create
- Backend `TokenSummary` Pydantic = `McpTokenSummary` TypeScript ✓
- Backend `TokenCreatedOut(TokenSummary)` = `McpTokenCreated` TypeScript ✓

---

## Execution Handoff

Após M-4 merged, próximo é **M-5 (prompts + subscriptions)** que finaliza o MVP.

Plan complete and saved to `docs/superpowers/plans/2026-05-18-mcp-m4-ui-tokens.md`.
