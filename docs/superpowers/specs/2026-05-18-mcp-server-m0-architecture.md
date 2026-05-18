# MCP — M-0 Architecture Spec

> **Foundation spec.** Sub-specs M-1 a M-N referenciam termos, schema e patterns definidos aqui.
> **Status:** brainstorm approved, ready to plan.
> **Owner:** Angelo
> **Codename:** MCP (Model Context Protocol)

## 1. Objetivo

Expor o SDR Machine como **MCP server** acessível por Claude Desktop (e outros LLM clients compatíveis), com **approval gate** pra ações irreversíveis. Operador conversa com Claude pra triagear leads, sugerir respostas, e disparar ações — Claude executa via tools com confirmação humana onde necessário.

Casos de uso primários:
1. **Co-pilot do operador** — operador trabalhando no Lead App / Inbox abre Claude Desktop ao lado e usa pra acelerar tarefas
2. **Agent autônomo (futuro)** — Claude opera com mais autonomia, pedindo aprovação só em ações sensíveis
3. **Dev/admin dogfooding** — debug/inspeção de prod via prompt sem precisar abrir UI

Coexistência: produto web (`/app/*`) continua sendo o primary surface. MCP é canal alternativo, não substituto.

**Não-MVP nesta spec**: Direção B (SDR consumindo MCPs externos como Slack/HubSpot). Foi mencionada no brainstorm mas fica como spec separada futura (M-B).

## 2. Conceitos

### Tool
Função exposta via MCP que LLM pode invocar. 3 classes:

| Classe | Approval | Pattern |
|---|---|---|
| **🟢 Read** | Nenhum | Chamada direta |
| **🟡 Soft-write** | Conversacional | Server prompt instrui Claude a confirmar com user antes |
| **🔴 Hard-write** | Server-side gate | `prepare_*` → `commit_action(id)` two-phase commit |

### Resource
Endpoint URI-style read-only. Cached client-side. Subscriptions opcionais (SSE) pra real-time.

### Prompt
Template de workflow pré-definido. LLM client pode listar disponíveis e o user escolher um pra rodar (ex: `triage_hot_leads`).

### Pending action
Linha em `pending_actions` (Postgres) representando uma ação preparada aguardando commit. TTL 5min.

## 3. Schema (Postgres)

Nova tabela criada em **M-1**:

```python
class PendingAction(Base):
    __tablename__ = "pending_actions"

    id = Column(String(40), primary_key=True)              # UUID gerado server-side
    workspace_id = Column(Integer, nullable=False, default=1)
    action_type = Column(String(60), nullable=False)        # ex: "send_message", "delete_lead"
    params = Column(JSON, nullable=False)                   # input do prepare_*
    preview = Column(JSON, nullable=False)                  # snapshot pro user revisar
    created_by_token_hash = Column(String(80), nullable=False)  # quem criou (token hash)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=False)           # default now+5min
    committed_at = Column(DateTime)                          # timestamp se foi commitada
    cancelled_at = Column(DateTime)                          # timestamp se cancelada
    result = Column(JSON)                                    # output após commit

    __table_args__ = (
        Index("ix_pending_actions_expires", "expires_at"),
        Index("ix_pending_actions_workspace", "workspace_id", "created_at"),
    )
```

Reaper: cron leve no startup do server limpa rows com `expires_at < now` E `committed_at IS NULL AND cancelled_at IS NULL` → marca `cancelled_at`. Não deleta (audit trail).

## 4. Tools catalog

### 🟢 READ tools (sem gate)

| Tool | Args | Retorno |
|---|---|---|
| `list_leads` | `filter: {status?, nicho?, cidade?, score_min?, has_email?, search?}, limit=20, offset=0` | `{items: LeadSummary[], total, page}` |
| `get_lead` | `id: int` | `LeadDetail` (full + enrichment + tech_stack + reviews) |
| `list_conversations` | `filter: {unread?, status?, search?}` | `ConversationSummary[]` |
| `get_conversation` | `id: int` | `ConversationDetail` (msgs ordenadas + lead context) |
| `list_jobs` | `status?, type?, limit=10` | `Job[]` |
| `get_job` | `id: int` | `Job` (com result_summary, errors, progress) |
| `dashboard_stats` | — | `{total_leads, by_status, avg_score, conversion_rate, leads_by_day}` |
| `conversion_funnel` | `period: "7d" \| "30d" \| "90d"` | Stats agregados |
| `list_landing_pages` | `lead_id: int` | `LandingPage[]` |
| `get_lp_html` | `lp_id: int` | `{html: string, public_url: string}` |
| `workspace_profile` | — | `{business_name, your_name, ...}` |
| `workspace_targeting` | — | `{niches, cities, min_rating, ...}` |
| `list_pending_actions` | `include_expired?: bool` | `PendingAction[]` |

### 🟡 SOFT-WRITE tools (conversational confirm via prompt)

Server inicializa client com system-prompt instructive: "Para tools soft-write, sempre confirme com user antes de chamar mostrando diff."

| Tool | Args | Side effect |
|---|---|---|
| `update_lead_status` | `id, new_status: string` | Muda Lead.status |
| `update_lead_fields` | `id, patch: {nome?, telefone?, email?, perfil_lead?}` | Edita campos |
| `mark_conversation_read` | `conv_id: int` | Zera unread_count |
| `update_workspace_profile` | `patch: ProfileIn` | Edita config do remetente |
| `update_workspace_targeting` | `patch: TargetingIn` | Edita targeting |

### 🔴 HARD-WRITE tools (two-phase commit)

Pattern fixo: `prepare_*(args) -> {action_id, preview, expires_at}` então `commit_action(action_id)` executa.

Gate cobre **send outbound + delete + pipeline em massa** (decisão de scope do brainstorm).

| Prepare tool | Preview contém | Commit faz |
|---|---|---|
| `prepare_send_message` | `{to_phone, body_rendered, lead_nome, idempotency_key}` | Chama `EvolutionAdapter.send_text`, grava `ConversationMessage` |
| `prepare_bulk_send` | `{count, recipients_sample (5), template, estimated_minutes}` | Disparo em massa via job background |
| `prepare_delete_lead` | `{lead_summary, related_data: {msgs_count, lps_count, jobs_count}}` | DELETE lead + cascades |
| `prepare_delete_conversations` | `{count, sample (3)}` | DELETE conversations + msgs |
| `prepare_run_pipeline` | `{stage, eligible_count, estimated_cost_usd, eta_minutes}` | Dispara `_run_*` background job |
| `prepare_classify_leads` | `{count, level, estimated_llm_calls, estimated_cost_usd}` | Background classification |
| `prepare_generate_lps` | `{count, estimated_cost_usd}` | LP generation em massa |

E os controles:

| Tool | Args | Função |
|---|---|---|
| `commit_action` | `action_id: str` | Executa a ação preparada. Valida ownership por token. Idempotente (commit 2x retorna mesmo result). |
| `cancel_action` | `action_id: str` | Invalida sem executar. |

## 5. Resources catalog

```
leads://list?status=outreach_ready&score_min=70   # query params suportados
leads://{id}
leads://{id}/messages
leads://{id}/landing-pages
conversations://list
conversations://{id}
conversations://{id}/messages
jobs://list
jobs://{id}
workspace://profile
workspace://targeting
workspace://integrations                           # NUNCA retorna secrets, só status
pending_actions://list
```

**Subscriptions** (SSE — MCP `resources/subscribe`):

| Resource | Notifica quando |
|---|---|
| `conversations://list` | Inbound chega (webhook P2 emit) |
| `jobs://{id}` | Progress event do background job (já tem SSE em `/api/jobs/{id}/stream`) |

Implementação reusa o evento store de pipeline (já existe `_job_events` in-memory).

## 6. Prompts pre-built

Templates de workflow expostos via MCP `prompts/list`:

| Prompt name | Inputs | Workflow |
|---|---|---|
| `triage_hot_leads` | `min_score?: int=70, days_silent?: int=5` | List leads matchando filtros → sugere prioridade |
| `reply_suggestion` | `conversation_id: int` | Lê conversa + lead context → gera 2-3 opções de resposta com tons distintos |
| `lead_meeting_prep` | `lead_id: int` | Resumo executivo: score, sinais, histórico, scripts sugeridos |
| `weekly_pipeline_review` | `period?: "7d"="7d"` | Dashboard stats + funnel + top performers + bottlenecks |

Estes são definidos em **M-3** (post foundation + tools).

## 7. Auth + Transport

### Transport: HTTP/SSE no backend Railway

Decisão: **HTTP, não stdio**. Backend já roda como serviço; expor endpoint MCP-compliant é menor footprint que manter binário stdio local.

- Endpoint: `POST /api/mcp` (JSON-RPC 2.0) + `GET /api/mcp/sse` (Server-Sent Events pra subscriptions)
- Conforme spec MCP: `Content-Type: application/json` no POST, eventos SSE no GET

### Auth: Bearer token workspace-scoped

Novo tipo de credencial: **MCP token**. Gerado em `/app/settings/mcp` (UI nova em M-4):
- User clica "Gerar token MCP" → backend gera UUID, hash em `mcp_tokens` table
- UI mostra token plain UMA VEZ ("copie agora, não será mostrado de novo")
- User cola no Claude Desktop `~/Library/Application Support/Claude/claude_desktop_config.json`:
  ```jsonc
  {
    "mcpServers": {
      "sdr-machine": {
        "url": "https://sdr-machine.up.railway.app/api/mcp",
        "auth": { "type": "bearer", "token": "<paste here>" }
      }
    }
  }
  ```
- Backend valida Bearer token em cada request → deriva `workspace_id` da row
- Token pode ser revogado (delete row) ou rotacionado (gerar novo, deletar antigo)

### Schema `mcp_tokens` (M-1)

```python
class McpToken(Base):
    __tablename__ = "mcp_tokens"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, nullable=False)
    name = Column(String(120), nullable=False)       # rótulo dado pelo user, ex: "claude-desktop-laptop"
    token_hash = Column(String(80), nullable=False, unique=True)  # SHA-256 do token plain
    last4 = Column(String(4), nullable=False)         # últimos 4 chars pra UI mostrar
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime)                    # update toda request
    revoked_at = Column(DateTime)

    __table_args__ = (
        Index("ix_mcp_tokens_hash", "token_hash"),
        Index("ix_mcp_tokens_workspace", "workspace_id"),
    )
```

### Rate limiting

In-memory bucket por token: 60 req/min default. Per-tool override possível (ex: `prepare_bulk_send` limitado a 5/min).

## 8. Multi-tenancy

- `mcp_tokens.workspace_id` define escopo. Toda tool/resource filtra por isso.
- Cross-workspace zero — token de workspace A não pode ler leads de workspace B.
- `pending_actions.workspace_id` + `created_by_token_hash` garantem que apenas o caller que criou pode commitar.

## 9. Logging + audit

Toda invocação tool gera log estruturado:
```
mcp.tool.invoked tool=send_message workspace=1 token_last4=a1b2
mcp.tool.completed tool=send_message workspace=1 duration_ms=450
mcp.action.prepared action_id=abc type=send_message workspace=1
mcp.action.committed action_id=abc workspace=1 duration_ms=380
mcp.action.expired action_id=xyz workspace=1
```

V2: tabela `mcp_audit_log` materializada por job diário. MVP = logs do Railway.

## 10. Roadmap

| Sub-projeto | Escopo | Estima | Depende |
|---|---|---|---|
| **M-0** (este doc) | Arquitetura, decisões, catalog | — | — |
| **M-1** | Schema (`mcp_tokens`, `pending_actions`) + MCP server skeleton (FastAPI route `/api/mcp` JSON-RPC + SSE) + token auth middleware | ~3 dias | M-0 |
| **M-2** | READ tools (todas as 13) + Resources catalog | ~2 dias | M-1 |
| **M-3** | Soft-write tools (5) + Hard-write `prepare_*` + `commit_action` + `cancel_action` | ~3 dias | M-2 |
| **M-4** | UI `/app/settings/mcp` — gerar/listar/revogar tokens + docs setup Claude Desktop | ~2 dias | M-1 |
| **M-5** | Prompts pre-built (4) + subscriptions SSE pra conversations/jobs | ~2 dias | M-3 |

**Total estimado**: ~12 dias full-time pro MVP funcional. Coexiste com produto web atual.

## 11. Out-of-scope explícito

- **Direção B** (SDR consumindo MCPs externos como Slack/HubSpot) — spec separada **M-B**, prioridade depois
- **Multi-user dentro do mesmo workspace** — token = workspace, não user. Se múltiplos operadores do mesmo workspace usam, todos compartilham audit trail
- **Webhook events sobre MCP actions** (notificar Slack quando Claude manda msg, etc) — fica pra M-B
- **Pricing/billing usage tracking** — token_usage stats são MVP simples (count requests), full billing fora
- **Audit log materializado** — V2
- **Self-hosted MCP server option (stdio)** — só HTTP por enquanto
- **OpenAI Assistants compatibility layer** — só MCP por enquanto

## 12. Risco e mitigação

| Risco | Mitigação |
|---|---|
| LLM hallucina `lead_id` e tenta operar em lead errado | `prepare_*` retorna preview com `lead_nome` + `telefone` — user vê o que vai acontecer antes de commit |
| `commit_action` chamado 2x (retry, double-click) | Idempotente por `committed_at` set — segunda chamada retorna mesmo result |
| Token vazado | UI revoke instant + scope é só workspace do user. Rate limit limita estrago em janela curta |
| Pending actions table cresce indefinidamente | Reaper diário marca expired; opcionalmente delete rows >30 dias antigos |
| Multi-tenant cross-leak | Server filtra TUDO por `workspace_id` derivado do token. Audit em testes pra cada tool |
| Cliente MCP malformado faz request bizarra | JSON-RPC tem schema; FastAPI/Pydantic valida; erros bem-formados retornados |

## 13. Decisões em aberto (resolvidas nos sub-specs)

- M-1: lib MCP em Python? Opções: oficial Anthropic SDK (se existir Python server-side), implementação custom de JSON-RPC. Confirmar no momento de impl.
- M-2: como tipar retornos? Pydantic models compartilhados com `app/schemas.py` ou TypedDict dedicado pra resposta MCP?
- M-3: estrutura de `pending_actions.preview` JSON — schema livre ou Pydantic discriminated union por `action_type`?
- M-5: prompts são definidos em código Python OU markdown files no repo + loader? Tradeoff: refactor-friendly vs version-control-friendly.

---

**Status final:** spec foundation completa. Próximo passo é planejar M-1 (schema + skeleton server) quando user priorizar.
