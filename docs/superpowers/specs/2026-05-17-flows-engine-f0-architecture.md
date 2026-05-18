# Flows Engine — F-0 Architecture Spec

> **Foundation spec.** F-1 a F-5 referenciam termos, schema e semantics definidos aqui.
> **Status:** approved high-level, ready to plan.
> **Owner:** Angelo
> **Codename:** Flows

## 1. Objetivo

Substituir a cadência de outreach hardcoded (5 toques fixos `initial → bump_d2 → insight_d5 → angle_d9 → breakup_d14`, gerada por `pipeline/outreach/generator.py`) por **fluxos configuráveis** que misturam WhatsApp + email + delays + branches condicionais.

Casos de uso primários:
1. **Prospecção fria** — sequência de toques outbound (refactor da cadência atual)
2. **Reativação de dormentes** — fluxo separado que recebe leads sem resposta há ≥30d
3. **Trigger por comportamento** — branch baseado em resposta detectada (sim/não/keyword) ou status

Coexistência: a cadência atual **continua funcionando** sem alteração. Flows é feature opcional, ativada por workspace, gradualmente substituirá o generator atual.

## 2. Conceitos

### Flow
Template definido pelo workspace. Estrutura: DAG (Directed Acyclic Graph) com nodes tipados e edges direcionadas. Identificado por `(workspace_id, name)` unique.

### Node
Unidade de trabalho dentro do flow. Tipos do MVP:

| Tipo | Categoria | Função |
|---|---|---|
| `start` | Control | Entry point implícito (1 por flow, criado auto) |
| `send_whatsapp` | Action | Envia mensagem WA via `WhatsAppProvider` (registry P1) |
| `send_email` | Action | Envia email via Resend adapter (F-2) |
| `wait` | Control | Pausa execução por `delay` configurável ou até `until_event` |
| `branch_on_reply` | Condition | Bifurca: respondeu (qualquer/keyword) → A, não respondeu → B |
| `set_status` | Action | Atualiza `Lead.status` pra valor configurável |
| `end` | Control | Termina o `FlowRun` (pode ter múltiplas — diferentes saídas) |

Edges saem de cada node com semântica dependente do tipo:
- Action/Control linear: 1 edge `out` (próximo node)
- `branch_on_reply`: 2 edges `out_yes` / `out_no`
- `end`: 0 edges

### FlowRun
Instância de execução. **Uma por (flow, lead)** ativa por vez. Estados:
- `pending` — criada, ainda não iniciada
- `running` — executando (current_node atualizado conforme avança)
- `waiting` — pausada em `wait` ou `branch_on_reply` aguardando timeout
- `completed` — atingiu `end`
- `cancelled` — interrompida (lead respondeu durante delay com flow configurado pra parar, ou cancelamento manual)
- `failed` — erro irrecuperável (provider down após retries, config inválida)

### FlowRunStep
Histórico de execução. Uma linha por node visitado dentro de um run. Inclui timestamp, status (`success`/`failed`/`skipped`), payload (msg enviada, erro retornado, etc). Permite debug step-by-step (F-5).

## 3. Schema (Postgres)

Migrations criadas em **F-1**. Skeleton aqui pra referência:

```python
class Flow(Base):
    __tablename__ = "flows"
    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, nullable=False, default=1)
    name = Column(String(120), nullable=False)
    description = Column(Text)
    enabled = Column(Boolean, nullable=False, default=False)
    version = Column(Integer, nullable=False, default=1)  # incrementa em edits
    triggers = Column(JSON, nullable=False, default=list)  # ver §4
    nodes = Column(JSON, nullable=False, default=list)  # array de {id, type, position, params}
    edges = Column(JSON, nullable=False, default=list)  # array de {id, source, target, label}
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_flows_workspace_name"),
        Index("ix_flows_workspace_enabled", "workspace_id", "enabled"),
    )


class FlowRun(Base):
    __tablename__ = "flow_runs"
    id = Column(Integer, primary_key=True)
    flow_id = Column(Integer, ForeignKey("flows.id", ondelete="CASCADE"), nullable=False)
    flow_version = Column(Integer, nullable=False)  # snapshot pro caso de edit mid-run
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    workspace_id = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    current_node_id = Column(String(40))  # ID lógico do node dentro do flow.nodes
    next_run_at = Column(DateTime, index=True)  # quando o engine deve revisitar
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    cancel_reason = Column(Text)
    state = Column(JSON, nullable=False, default=dict)  # contexto livre por run
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("flow_id", "lead_id", "status",
                         name="uq_flow_runs_one_active_per_pair"),  # parcial; ver nota
        Index("ix_flow_runs_status_next_run", "status", "next_run_at"),
    )
```

> **Nota uq parcial:** Postgres não suporta unique constraint condicional. Aplicar via partial index `WHERE status IN ('pending','running','waiting')` em raw SQL na migration.

```python
class FlowRunStep(Base):
    __tablename__ = "flow_run_steps"
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("flow_runs.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String(40), nullable=False)
    node_type = Column(String(40), nullable=False)
    status = Column(String(20), nullable=False)  # success/failed/skipped
    payload = Column(JSON, nullable=False, default=dict)  # input/output do step
    error = Column(Text)
    started_at = Column(DateTime, nullable=False, server_default=func.now())
    finished_at = Column(DateTime)

    __table_args__ = (
        Index("ix_flow_run_steps_run_started", "run_id", "started_at"),
    )
```

### Relação com modelos existentes
- `FlowRun.lead_id` → `Lead.id` (CASCADE delete)
- Nodes `send_whatsapp` criam `ConversationMessage` (P0 schema) com `outreach_message_id=NULL`. Idempotência por `provider_message_id`.
- Nodes `send_email` criam linha em tabela nova `email_messages` (definida em F-2).
- Nodes `set_status` mudam `Lead.status` — mesma coluna usada pela cadência atual. Não conflita.

### Versionamento
Edit de flow incrementa `Flow.version`. Runs já criados mantêm `flow_version` snapshot do momento de criação. Lê a versão correspondente em `flow_versions` (tabela secundária — ver F-1) ou trata edit como cópia (preferido — simplifica).

## 4. Triggers

`Flow.triggers` é JSON array. Cada trigger é uma das formas:

```jsonc
// Manual — habilitado por default; nenhuma config além de "type"
{ "type": "manual" }

// Auto status change — escuta mudanças em Lead.status
{
  "type": "lead_status",
  "from": ["outreach_ready"],          // opcional; default = qualquer
  "to": ["outreach_sent_via_flow"]      // obrigatório
}

// Auto webhook externo — POST recebido em /api/flows/{flow_id}/trigger
{
  "type": "external_webhook",
  "secret_field": "webhook_secret"      // referência a chave em IntegrationSettings; HMAC-validated
}
```

**MVP cobre os 3 tipos.** Schedule trigger (cron) fica pra v2 — Postgres tem queue agendada via `next_run_at`, então adicionar schedule é só inserir runs com `next_run_at` future via cron externo. Não bloqueia arquitetura.

## 5. Engine semantics

### Modelo de execução
Engine = **worker thread persistente** rodando dentro do processo FastAPI (single-instance Railway hoje). Detalhes em F-1, semantics aqui:

```
loop forever:
    1. SELECT * FROM flow_runs
       WHERE status IN ('pending', 'waiting')
         AND (next_run_at IS NULL OR next_run_at <= now())
       ORDER BY next_run_at ASC LIMIT 50
       FOR UPDATE SKIP LOCKED;

    2. for run in rows:
        try:
            node = resolve_node(run.flow, run.current_node_id or 'start')
            outcome = execute_node(node, run, db)
            advance(run, outcome)
        except RetryableError as e:
            schedule_retry(run, e)  # backoff exponencial
        except FatalError as e:
            mark_failed(run, e)
    3. sleep(2s)  # tick interval
```

`FOR UPDATE SKIP LOCKED` garante que se algum dia rodar com múltiplos workers (Railway scale-out), runs não duplicam.

### Idempotência
- `send_whatsapp` usa `idempotency_key = f"flow_run_{run.id}_node_{node.id}"`. Provider (P1) já suporta.
- `send_email` análogo (F-2 implementa).
- Steps duplicados (mesmo node executando 2x num run) são **erro de bug** — o engine não deveria avançar sem marcar step. Detectado por `FlowRunStep` count por (run_id, node_id) > 1.

### Resume após reboot
Worker re-seleciona runs com `status IN ('pending', 'waiting')` no startup. Sem fila external. Inerente do schema.

### `wait` semantics
- `params.delay_seconds`: pausa fixa. Engine seta `next_run_at = now + delay`, status=`waiting`.
- `params.until_event` (opcional): pausa até evento específico (default = `lead_reply`). Pode combinar com `timeout_seconds`: se evento não chegar, segue após timeout. Se chegar antes, próxima edge é tomada imediatamente. Implementação: **listener** em webhook P2 verifica se há run aguardando esse lead+evento, força wake-up zerando `next_run_at`.

### `branch_on_reply` semantics
- `params.window_seconds`: quanto tempo esperar resposta. Default = 86400 (1 dia).
- `params.match`: `"any"` (qualquer resposta), `"keyword"` (regex em `params.pattern`).
- Comportamento:
  - Engine vê o node → entra em `waiting`, `next_run_at = now + window`.
  - Se inbound WA chegar dentro da janela (P2 webhook detecta): `branch=yes`, force-resume.
  - Se timeout: `branch=no`, segue edge `out_no`.

### Cancellation
- Lead responde durante delay (e flow tem `cancel_on_reply: true` no node `wait`): run vira `cancelled`, `cancel_reason="lead_replied"`.
- API manual `DELETE /api/flows/runs/{id}`: força `cancelled`.

## 6. Validação de flow

Antes de habilitar (`enabled=true`):
- `start` node existe e tem exatamente 1 edge `out`
- Cada node referenciado existe em `nodes`
- Cada edge tem `source` e `target` válidos
- Grafo é **acíclico** (DFS detecta ciclo → erro)
- Todo path do `start` termina em `end` (BFS)
- Nodes `branch_on_reply` têm exatamente 2 edges (`out_yes` + `out_no`)
- Nodes `send_*` têm `params.body` não-vazio (templates aceitos com variáveis tipo `{{lead.nome}}`)

Validação roda em **PUT /api/flows/{id}** antes de salvar (server-side) **e** no editor (F-4, client-side mirror).

## 7. Templates de mensagem

`send_whatsapp.params.body` e `send_email.params.body` aceitam template Jinja-like:

- Variáveis disponíveis: `{{lead.nome}}`, `{{lead.nicho}}`, `{{lead.cidade}}`, `{{lead.email}}`, `{{lead.lp_url}}`, `{{workspace.business_name}}`, `{{workspace.your_name}}`
- Sem condicionais/loops (Jinja com sandbox restritivo). Cobre 95% dos casos sem virar mini-linguagem.
- Render no momento do send (não no save) — dados frescos.

LP URL opcional: se lead tem `lp_id`, `{{lead.lp_url}}` resolve. Senão, render como string vazia (editor mostra warning se template referencia variável que pode ser vazia).

## 8. Multi-tenancy

- `Flow.workspace_id` indexa tudo. Constante 1 hoje, scaffold pra futuro.
- Cross-workspace zero por garantia de FK + filtros nos services.
- Trigger `external_webhook` autenticado por HMAC com secret cifrado em `IntegrationSettings` (provider="flows") workspace-scoped. Reusa infra do P2.

## 9. Métricas (out-of-scope MVP, design-friendly)

Hooks no engine pra emitir eventos:
- `flow_run.started`
- `flow_run.completed` (com `duration_seconds`)
- `flow_node.executed` (com `node_type`, `duration_ms`)
- `flow_node.error`

V1 = logs estruturados. V2 = tabela `flow_metrics_daily` agregada por cron + dashboard F-5.

## 10. Roadmap (referência F-1 a F-5)

| Sub-projeto | Escopo | Estima | Depende |
|---|---|---|---|
| **F-1** | Schema + engine + 6 nodes MVP (`start`, `send_whatsapp`, `send_email`, `wait`, `branch_on_reply`, `set_status`, `end`) | ~1 semana | F-0 |
| **F-2** | Resend email adapter + provider contract | ~3 dias | F-0 |
| **F-3** | API CRUD `/api/flows` + triggers (manual, lead_status, external_webhook) | ~3 dias | F-1 |
| **F-4** | Visual editor (react-flow) + paleta + sidebar config + validação client-side | ~1-1.5 sem | F-3 |
| **F-5** | Runtime UI: lista flows + lista runs + debug step-by-step + métricas básicas | ~3-4 dias | F-3 |

## 11. Out-of-scope explícito (não-MVP)

- Tagging system (`set_tag` node) — depende de feature de tags em Lead
- Schedule trigger (cron) — adicionável post-launch sem mudar schema
- A/B testing de variantes de mensagem
- Loops (back-edges) — proibidos pelo validador (DAG only)
- Sub-flows / composição
- Versionamento avançado (rollback, diff visual)
- Multi-canal extra (SMS, Telegram) — só WA + email no MVP
- Métricas agregadas dashboard
- Permissões granulares (Read-only flows, Approve-before-enable)

## 12. Risco e mitigação

| Risco | Mitigação |
|---|---|
| Engine trava num node lento (LLM render demorado) | Timeout por node (default 30s), step marca `failed` se exceder. |
| Lead responde durante `wait` mas worker não acorda | Webhook P2 ativo modifica `next_run_at` do run match → tick acorda em ≤2s. |
| Flow editado mid-run com versão diferente | `FlowRun.flow_version` snapshot. Engine lê definição da versão certa (F-1 schema decide: snapshot full ou tabela versionada). |
| Múltiplas instâncias Railway competindo runs | `FOR UPDATE SKIP LOCKED` garante exclusão mútua. |
| Worker crashou no meio do node | Step ficou `started_at` setado, `finished_at` NULL. Reaper no startup marca como `failed` (reuso do padrão `_reap_orphaned_jobs` em `main.py`). |

## 13. Decisões em aberto (resolvidas nos sub-specs)

- F-1: tabela única de flows com JSON nodes/edges, ou tabela separada `flow_nodes`/`flow_edges`? (Recomendado: JSON columns; queries de execução não precisam de filtro por node)
- F-2: contrato `EmailProvider` (analogia a `WhatsAppProvider`) ou função simples send_email? (Recomendado: contrato — permite Sendgrid/Mailgun futuro)
- F-4: react-flow vs @xyflow/react (sucessor) — confirmar maintained version no momento de impl

---

**Status final:** spec foundation pronta. Os 5 sub-specs abaixo referenciam termos definidos aqui.
