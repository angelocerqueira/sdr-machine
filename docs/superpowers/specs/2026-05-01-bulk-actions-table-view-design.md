# Bulk Actions + Table View — Spec

**Data:** 2026-05-01
**Status:** Spec aprovado, aguardando plano de implementação
**Discovery base:** [`docs/superpowers/discovery/2026-05-01-bulk-actions-table-view.md`](../discovery/2026-05-01-bulk-actions-table-view.md)
**Autor:** Angelo + Claude

---

## Resumo

Adicionar uma view de tabela paralela ao kanban (toggle, não substituição) com seleção múltipla e barra de ações em massa. Resolve o gargalo de operação massiva (300+ leads) que hoje exige drag manual no kanban. Backend já aceita `lead_ids[]` em enrich/generate/outreach; spec adiciona endpoints faltantes (bulk PATCH, bulk DELETE, preview de custo) e a UI completa.

## Motivação

Operador precisa re-enriquecer 300+ leads de uma coluna do kanban após upgrade de scoring/provider. Hoje só dá pra arrastar 1 por 1; UI não suporta multi-select. Padrão consagrado em ferramentas similares (Clay, Apollo, Linear): tabela com checkbox + action bar sticky.

## Decisões (já travadas no discovery)

| # | Pergunta | Decisão |
|---|---|---|
| 1 | Substituir kanban? | Não. Toggle Kanban ↔ Tabela |
| 2 | Lib tabela | TanStack Table v8 + TanStack Virtual |
| 3 | Saved views scope | Workspace (single-tenant hoje, schema preparado) |
| 4 | Limite bulk via IDs | 5000 hard. Acima = endpoint `by_filter` futuro (não build agora) |
| 5 | Undo bulk | Adiado |
| 6 | Updates server-state | Polling 5s em counts. SSE só se dor aparecer |
| 7 | State seleção | `Set<number>` em React state + sessionStorage |
| 8 | Filtros | Query string completa (saved views = salvar URL depois) |

---

## Arquitetura

### Roteamento

Rota nova **`/app/pipeline`** com query param `view=kanban|table` (default `kanban`).

- **Migração:** `/app/kanban` permanece e redireciona pra `/app/pipeline?view=kanban` via Next redirect (preserva links externos).
- **Sidebar:** item "Pipeline" (ícone unificado) substitui "Kanban".
- **Estado da view** persistido em localStorage (`sdr-pipeline-view`) — toggle lembra última escolha.

### Camadas

```
/app/pipeline
├── page.tsx                  # Orquestra view + filtros (query string)
├── components/pipeline/
│   ├── pipeline-toolbar.tsx  # Filtros + toggle view + funnel + filtros ativos banner
│   ├── pipeline-kanban.tsx   # Wrapper do kanban-board atual (refactor leve)
│   ├── pipeline-table.tsx    # Nova tabela TanStack
│   ├── bulk-action-bar.tsx   # Sticky bottom action bar
│   ├── bulk-confirm-modal.tsx # Confirm forte (typed-input opcional)
│   ├── bulk-result-modal.tsx  # Modal de detalhes pós-job (erros parciais)
│   ├── select-all-banner.tsx  # Banner "selecionar todos N do filtro"
│   ├── column-visibility-menu.tsx
│   └── use-bulk-selection.ts  # Hook do Set + sessionStorage
```

`pipeline-toolbar.tsx` é compartilhada entre kanban e table — mesmos filtros, mesmo funnel, mesma URL.

---

## Backend

### Endpoints novos

#### 1. `PATCH /api/leads/bulk`

```python
# Request
{
  "lead_ids": [1, 2, 3],          # required, max 5000
  "data": {
    "status": "outreach_ready",   # any field from LeadUpdate schema
    # outros campos editáveis (ex: pacote_sugerido, prioridade)
  }
}

# Response 200
{
  "updated": 3,
  "errors": [
    {"lead_id": 5, "error": "Invalid status"}
  ]
}
```

**Validações:**
- `len(lead_ids) <= 5000` → 422 `{"detail": "Bulk size exceeded (5000 max)"}`
- `data.status` validado contra `VALID_STATUSES` (já existe).
- Reaproveita `LeadUpdate` Pydantic schema (mesmo do PATCH unitário).
- Roda em **uma transação** com `bulk_update_mappings` quando possível, fallback per-id se houver coluna calculada (ex: trigger `updated_at` já trata).

**Auditoria:** loga `{user_id, action: "bulk_update", lead_ids, fields, ts}` em uma tabela `audit_log` futura — fora do escopo, mas deixa o hook preparado (função `_audit()` no router que hoje só faz `print`).

#### 2. `DELETE /api/leads/bulk`

```python
# Request
{
  "lead_ids": [1, 2, 3]   # max 5000
}

# Response 200
{
  "deleted": 3,
  "errors": []
}
```

**Cascata** já existe nas FKs (`outreach_messages`, `landing_pages` deletam junto).

#### 3. `POST /api/pipeline/preview`

Dry-run que retorna estimativa antes do dispatch. Habilita G5 (cost meter) e desbloqueia confirm modal informado.

```python
# Request
{
  "action": "enrich" | "generate" | "outreach" | "classify",
  "lead_ids": [1, 2, 3],
  "options": {
    "force_providers": [],       # passa adiante pra estimar Apollo/Hunter
    "skip_providers": []
  }
}

# Response 200
{
  "action": "enrich",
  "total_leads": 3,
  "eligible": 3,                # = total_leads - skipped (skipped = leads que o runner pula)
  "skipped": 0,
  "skipped_reasons": {},        # apenas {"disqualified": N} hoje
  "cost_estimate": {
    "currency": "USD",
    "total": 0.15,
    "breakdown": [
      {"provider": "apollo", "calls": 3, "cost": 0.15},
      {"provider": "hunter", "calls": 3, "cost": 0.0}
    ]
  },
  "quota_status": [
    {"provider": "apollo", "used": 743, "limit": 1000, "would_hit_limit": false}
  ],
  "warnings": []                # ["12 leads fora do estágio scraped/enrich_failed serão reprocessados."]
}
```

**Contrato (preview = espelho do runner):**

- **`enrich`** — runner aceita todos os leads em `lead_ids` independente do status. `eligible = total_leads`, `skipped_reasons = {}`. Leads já fora do estágio natural (`scraped`/`enrich_failed`) viram **warning** ("N leads fora do estágio scraped/enrich_failed serão reprocessados."), não skip.
- **`generate`** — runner pula `disqualified`. `skipped_reasons` aceita apenas `{"disqualified": N}`.
- **`outreach`** — runner pula `disqualified`. `skipped_reasons` aceita apenas `{"disqualified": N}`. Leads fora da janela natural (`lp_generated`/`outreach_ready`/`outreach_failed`) viram **warning** — runner ainda processa, mensagens podem ser redundantes.
- **`classify`** — sem filtragem; classifier lida com qualquer status.

`SkippedReason` é tipado como `Literal["disqualified"]` em `app/schemas.py`.

**Implementação inicial:** retorna `total_leads`, `eligible/skipped`, `warnings`. `cost_estimate` e `quota_status` ficam stubbed (`null`) e são preenchidos depois quando `integration_settings` expor metadata de quota — não bloqueia este spec.

### Endpoints já prontos (sem mudança)

- `POST /api/pipeline/enrich` — body `{lead_ids, force_providers, skip_providers}`. Funciona como-é.
- `POST /api/pipeline/generate` — body `{lead_ids, max_count}`. Funciona como-é.
- `POST /api/pipeline/outreach` — body `{lead_ids}`. Funciona como-é.
- `GET /api/leads` — já suporta todos os filtros que a tabela precisa.
- `GET /api/leads/counts` — já agrupa por status com filtros aplicados.
- `GET /api/leads/filters` — distinct nichos/cidades.

### Schemas Pydantic (`app/schemas.py`)

```python
class BulkLeadUpdate(BaseModel):
    lead_ids: list[int] = Field(min_length=1, max_length=5000)
    data: LeadUpdate

class BulkLeadDelete(BaseModel):
    lead_ids: list[int] = Field(min_length=1, max_length=5000)

class BulkUpdateResult(BaseModel):
    updated: int
    errors: list[dict]   # [{lead_id: int, error: str}]

class BulkDeleteResult(BaseModel):
    deleted: int
    errors: list[dict]

class PipelinePreviewRequest(BaseModel):
    action: Literal["enrich", "generate", "outreach", "classify"]
    lead_ids: list[int] = Field(min_length=1, max_length=5000)
    options: dict = Field(default_factory=dict)

class PipelinePreviewResponse(BaseModel):
    action: str
    total_leads: int
    eligible: int
    skipped: int
    skipped_reasons: dict[str, int]
    cost_estimate: Optional[dict]
    quota_status: Optional[list[dict]]
    warnings: list[str]
```

### Migração (banco)

Nada nesta fase. (Saved views + audit log virão como migrações separadas quando construirmos G1/G9.)

---

## Frontend

### Toolbar (`pipeline-toolbar.tsx`)

Compartilhada entre kanban e tabela. Layout (mobile-first):

```
[ Pipeline · 347 leads ]                           [ Kanban | Tabela ]
[ 🔍 buscar... ]  [Nicho ▾] [Cidade ▾] [Score≥] [Perfil ▾] [Order ▾] [⋯ mais]

[Funnel: 347 → 89 → 34 → 12 → 3 (0.86%)]   ← G8, click filtra
[⚠ Filtros ativos: cidade=SP, score≥70  [limpar tudo]]   ← só se houver filtros
```

- Mobile (<768px): filtros colapsam num drawer "Filtros (3)".
- Toggle view: segmented control 2 opções, persiste em localStorage.
- Funnel de conversão: barra horizontal com 5 marcos (`scraped → enriched → lp_generated → outreach_sent → responded`). Click em marco = aplica filtro `status`.
- Banner filtros ativos: sticky logo abaixo da toolbar quando há filtros.

### Tabela (`pipeline-table.tsx`)

Stack: `@tanstack/react-table` + `@tanstack/react-virtual`.

#### Colunas

**Default visíveis** (desktop):

| Col | Source | Sortable | Width | Cell |
|---|---|---|---|---|
| ☐ Checkbox | client state | — | 40px | `<Checkbox />` |
| Nome | `lead.nome` | sim (`name_asc`) | flex | link → `/app/leads/[id]` |
| Cidade | `lead.cidade` | não (filter) | 140px | texto |
| Nicho | `lead.nicho_canonico` (label) ou `lead.nicho` | não | 160px | `Tag` (DS) |
| Score | `lead.opportunity_score` | sim | 80px | `ScoreRing` mini ou número colorido |
| Perfil | `lead.perfil_lead` | não | 140px | `Badge` colorido por perfil |
| Status | `lead.status` | não | 140px | `StatusPill` (DS) |
| Atualizado | `lead.updated_at` | sim | 120px | data relativa ("há 2h") |

**Opcionais** (toggle via column-visibility-menu):

`Telefone`, `Email`, `CNPJ`, `Razão Social`, `Tech stack` (chips), `Reviews` (rating + count), `Pacote`, `Prioridade`, `Job ID`, `Criado`.

**Default mobile** (<768px): só `Nome | Score | Status`. Toque na linha = abre Lead App.

#### Sort

- Header click → toggle `asc/desc/none`. Visualmente seta.
- Tabela faz request com `order_by=score_desc|score_asc|name_asc|created_desc|updated_desc`. Multi-sort fica fora do MVP (TanStack suporta, mas backend é single-sort).

#### Paginação

- **Server-side** com `per_page=50` default. Botões `[< Prev]  [1 2 3 ... 12]  [Next >]` no rodapé.
- Alternativa: scroll infinito (igual kanban-column). Decisão: **paginação clássica** na tabela. Justificativa: scroll infinito + multi-select cross-page fica confuso; paginação dá controle previsível.

#### Virtualização

`useVirtualizer` em rows (within page de 50, virtualiza visible window de ~15 rows). Crítico mesmo com page de 50 quando `density=compact`.

### Multi-select (`use-bulk-selection.ts`)

```typescript
type SelectionMode = "ids" | "all_filter";

interface BulkSelection {
  mode: SelectionMode;
  ids: Set<number>;        // sempre populado em modo ids; vazio em all_filter
  excludedIds: Set<number>; // só usado em modo all_filter (sub-deselect)
  filterSnapshot: Record<string, string>; // capturado quando entrou em all_filter
}
```

**Persistência:** `sessionStorage` chave `sdr-bulk-selection`. Limpa no logout.

**API do hook:**
```typescript
const sel = useBulkSelection();
sel.toggle(leadId);
sel.selectPage(visibleIds);
sel.selectAllFilter(currentFilters, totalCount);   // entra em modo all_filter
sel.clear();
sel.size();          // count efetivo (handles excluded)
sel.has(leadId);     // checa se id está selecionado
sel.materializeIds(); // retorna array<number> pra dispatch (max 5000, throws)
```

**Modos:**
- **`ids`**: contém Set explícito de IDs. Header check seleciona página visível, somando ao Set.
- **`all_filter`**: usuário clicou banner "selecionar todos N do filtro". Set fica vazio; `excludedIds` permite uncheck individual ("todos exceto estes 3").

**Materialização para dispatch:**
- Modo `ids` → retorna `[...ids]` direto.
- Modo `all_filter` → faz `getLeads({...filterSnapshot, page: 1, per_page: 5000, fields_only=id})` (ver endpoint abaixo). Se total > 5000, **bloqueia** com modal "Reduza o filtro pra ≤5000 leads ou aguarde endpoint by_filter (em breve)."

### Endpoint auxiliar `GET /api/leads/ids`

Pra materializar `all_filter` sem trafegar leads completos.

```python
# Request
GET /api/leads/ids?status=scraped&cidade=SP&...  # mesmos filtros do GET /api/leads

# Response 200
{
  "ids": [1, 2, 3, ...],  # max 5000
  "total": 4382,
  "truncated": false       # true se total > 5000
}
```

Backend: `query.with_entities(Lead.id).limit(5001)`. Se 5001+ → `truncated=true`, retorna primeiros 5000.

### Banner select-all (`select-all-banner.tsx`)

Aparece logo acima da tabela quando:
- Header check seleciona todos os 50 visíveis E
- `total > 50` (há mais leads no filtro além da página atual)

```
┌─────────────────────────────────────────────────────────────────┐
│ ℹ Os 50 desta página estão selecionados.                         │
│   [Selecionar todos os 347 leads do filtro →]  [Limpar seleção] │
└─────────────────────────────────────────────────────────────────┘
```

Cor: `bg-accent-subtle` com borda `border-accent/30`. Some quando `mode=all_filter` ou seleção limpa.

Em modo `all_filter`:
```
┌─────────────────────────────────────────────────────────────────┐
│ ✓ Todos os 347 leads do filtro selecionados.                    │
│   [Limpar seleção]                                               │
└─────────────────────────────────────────────────────────────────┘
```

### Action bar (`bulk-action-bar.tsx`)

Sticky bottom (acima do AppSidebar mobile). Aparece quando `sel.size() > 0`.

#### Layout desktop

```
┌──────────────────────────────────────────────────────────────────────────┐
│ [☐ 47 selecionados]  [Re-enriquecer] [Gerar LP] [Gerar mensagens]        │
│                      [Mover para ▾]  [Editar ▾]  [Exportar CSV]  [Excluir] [⨯ Limpar] │
└──────────────────────────────────────────────────────────────────────────┘
```

#### Mobile

Colapsa em 2 botões + overflow `[⋯ Ações (8)]` que abre bottom sheet.

#### Botões — comportamento

| Botão | Ação |
|---|---|
| `Re-enriquecer` | `POST /api/pipeline/preview` → modal confirm com summary → `POST /api/pipeline/enrich` |
| `Gerar LP` | preview → confirm → `POST /api/pipeline/generate` |
| `Gerar mensagens` | preview → confirm → `POST /api/pipeline/outreach` |
| `Mover para ▾` | dropdown com `KANBAN_COLUMNS` → confirm → `PATCH /api/leads/bulk {data: {status}}` |
| `Editar ▾` | dropdown: pacote, prioridade, perfil → confirm → `PATCH /api/leads/bulk` |
| `Exportar CSV` | client-side gerar CSV (não chama backend) |
| `Excluir` | confirm forte (typed) → `DELETE /api/leads/bulk` |
| `⨯ Limpar` | `sel.clear()` |

#### Estados desabilitados

- Job mesmo tipo já rodando: botão fica disabled, tooltip `"Já existe um job de {tipo} em andamento. Aguarde."` Source: `getPipelineStatus().running_jobs`.
- Seleção excede 5000 (modo `all_filter` com total > 5000): todos botões disabled, tooltip `"Reduza o filtro para ≤5000 leads."`

### Confirm modal (`bulk-confirm-modal.tsx`)

Dois níveis de severidade:

#### Soft (re-enriquecer, gerar LP, mover, editar)

```
┌──────────────────────────────────────────────────┐
│ Re-enriquecer 47 leads?                          │
│                                                  │
│ Custo estimado: $2.35 (Apollo)                   │
│ Quota Apollo: 743/1000 (após: 790/1000)          │
│                                                  │
│ ⚠ 12 leads já enriquecidos.                      │
│   ( ) Pular já enriquecidos (35 leads)           │
│   (•) Forçar re-enriquecimento (47 leads)        │
│                                                  │
│              [Cancelar]  [Re-enriquecer 47]      │
└──────────────────────────────────────────────────┘
```

Quando preview retorna `cost_estimate=null` ou `quota_status=null`, omite as linhas (graceful degradation).

#### Hard (excluir, mover pra `disqualified` em massa, action irreversível)

```
┌──────────────────────────────────────────────────┐
│ ⚠ Excluir 47 leads permanentemente?              │
│                                                  │
│ Esta ação não pode ser desfeita. Vai apagar:     │
│ • 47 leads                                       │
│ • mensagens e LPs associadas (cascade)           │
│                                                  │
│ Digite EXCLUIR pra confirmar:                    │
│ [____________________]                           │
│                                                  │
│              [Cancelar]  [Excluir]  ← disabled até match exato │
└──────────────────────────────────────────────────┘
```

### Resultado pós-job (`bulk-result-modal.tsx`)

Aparece quando o job termina (escuta SSE do job criado). Layout:

```
┌──────────────────────────────────────────────────┐
│ ✓ Job concluído                                  │
│                                                  │
│ 42 leads enriquecidos com sucesso                │
│ ⚠ 5 falhas:                                      │
│   • Lead 123 (Padaria X): timeout                │
│   • Lead 456 (Café Y): apollo quota              │
│   • Lead 789 (Bar Z): connection refused         │
│   • [+ 2 mais]                                   │
│                                                  │
│ [Re-tentar falhas]  [Fechar]                     │
└──────────────────────────────────────────────────┘
```

`Re-tentar falhas` re-seleciona os IDs que falharam e dispara o mesmo bulk action.

### CSV export

Client-side, sem chamar backend. Pega `sel.materializeIds()` → fetch detalhado → gera CSV.

**Otimização:** quando seleção <= 50 e estão na página atual, usa dados já carregados. Acima disso, faz `getLeads({ids: [...], per_page: 5000})` — exige adicionar suporte a `?id_in=1,2,3` no endpoint `GET /api/leads`.

**Decisão:** v1 só permite export de até 50 (linhas visíveis). Acima dá warning "Reduza a seleção pra ≤50 ou exporte página por página." (Aceita o trade-off — export-import loop é growth pós-MVP.)

**Formato CSV:**
```
lead_id,public_id,nome,telefone,email,cidade,nicho,score,status,atualizado_em,wa_link
123,abc-def,"Padaria X",+5511999...,"contato@x.com",São Paulo,padaria,87,enriched,2026-04-30T10:00,https://wa.me/...
```

UTF-8 BOM no início (Excel pt-BR abre direito).

### Polling de counts

Hook `usePipelineCounts(filters)` em `pipeline-toolbar.tsx`:
- Polls `getLeadCounts(filters)` a cada 5s.
- Compara com snapshot anterior. Se `total` mudou ou um status mudou >10%, mostra banner:
  ```
  Lista atualizada — 12 leads novos. [Atualizar]
  ```
- Banner é dismissable; click "Atualizar" refetch tabela.

### Job badge no AppSidebar

Item "Jobs" no AppSidebar ganha badge numérico quando há jobs `running` ou `done` nas últimas 60s.
- Source: novo hook `useActiveJobs()` que pollar `GET /api/jobs?status=running` a cada 5s.
- Click no item navega pra `/app/jobs` (já existe).
- Toast quando job termina: `"Bulk enrich concluído: 42 OK, 5 erros [Ver detalhes]"` — abre `bulk-result-modal`.

---

## Fluxos completos (happy paths re-mapeados com a UI)

### H1 — Re-enriquecer 300+ scraped

1. `/app/pipeline?view=table&status=scraped`
2. Header check seleciona página (50). Banner aparece.
3. Click "Selecionar todos os 347 do filtro" → `getLeads/ids` retorna `[..]` ou `truncated=true`.
4. Action bar mostra "347 selecionados". Click "Re-enriquecer".
5. `POST /api/pipeline/preview` → modal `"Re-enriquecer 347 leads? Custo: $17.35"`.
6. Confirm → `POST /api/pipeline/enrich {lead_ids: [...]}`. Modal fecha.
7. Toast `"Job iniciado"`. Badge no sidebar Jobs.
8. SSE flui em background. Job termina → toast `"Concluído: 312 OK, 35 falhas [Detalhes]"`.

### H4 — Excluir lixo

1. Filtra `score_min=0` + `score_max=30` (adicionar `score_max` no backend) + `telefone IS NULL` (filtro novo).
2. Select all → "Excluir".
3. Modal hard: digita "EXCLUIR".
4. `DELETE /api/leads/bulk`. Toast `"73 leads excluídos"`. Tabela refetch.

> **Nota:** filtro `score_max` e `has_telefone` precisam ser adicionados ao `GET /api/leads`. Custo baixo, vale incluir nesta fase.

---

## Edge cases — comportamento exato

| Caso | Spec |
|---|---|
| Filtro muda com seleção `ids` ativa | Mantém Set. Mostra `"47 selecionados (3 fora do filtro atual)"` na action bar. Botão `[Limpar fora do filtro]`. |
| Filtro muda em modo `all_filter` | Pergunta: `"Sua seleção 'todos do filtro' será limpa pelo novo filtro. Continuar?"` Cancel volta filtro. |
| F5 / nova aba | sessionStorage preserva. Em nova aba é fresh. |
| Logout | Limpa sessionStorage. |
| 5001 leads em `all_filter` | Banner muda pra `"4382 leads — limite atual de 5000 excedido. Refine o filtro."` Action bar: botões disabled. |
| Sort + paginação + select cross-page | Set persiste através de mudanças de página. Header check só toca página visível atual. |
| Race: lead movido por outro usuário | Refetch após qualquer bulk action exitoso. Polling captura mudanças contínuas. |
| Job mesmo tipo já rodando | Botão disabled com tooltip. Não enfilera. |
| Erro parcial | Modal de detalhes. Botão "Re-tentar falhas" repõe seleção com IDs falhados. |
| Mobile: 11 colunas | 3 visíveis default. Column-visibility-menu controla. |
| Toque acidental checkbox | Hit area 40×40px. Long-press (500ms) entra em select mode. |
| Seleção vazia em filtro vazio | Action bar não aparece. |
| Bulk move pulando etapas | Permite. Confirm soft com warning amarelo `"Você está pulando 3 etapas do funil. OK?"` |

---

## Telemetria (PostHog — preparar pro futuro)

Eventos a disparar (apenas estruturar onde — instrumentação real fica pra outra task):

- `pipeline_view_toggled` (props: `from`, `to`)
- `bulk_selection_started` (props: `mode`, `count`, `filters`)
- `bulk_action_dispatched` (props: `action`, `count`, `cost_estimate`, `forced`)
- `bulk_action_completed` (props: `action`, `success`, `failed`, `duration_ms`)
- `column_visibility_changed` (props: `column`, `visible`)
- `csv_exported` (props: `count`)

---

## Acessibilidade

- Checkbox header com `aria-checked={"mixed" | true | false}` (estado indeterminate quando seleção parcial).
- Action bar com `role="region"` + `aria-label="Ações em massa"`.
- Confirm modal com `role="dialog"`, focus trap, ESC fecha (exceto hard-confirm que exige typed).
- Tabela com `<table>` semântico (TanStack Table headless permite). `aria-sort` no header.
- Atalhos teclado:
  - `Cmd+A` na tabela = selecionar página visível
  - `Esc` = limpar seleção
  - `Shift+click` em row = seleção range (entre último e atual)

---

## Definição de pronto

- [ ] Toggle Kanban ↔ Tabela funciona, persiste preferência
- [ ] Tabela com 8 colunas default, sortable + paginada (50/page)
- [ ] Multi-select com 3 modos (none/page/all_filter), Set persistido em sessionStorage
- [ ] Banner select-all aparece/desaparece corretamente
- [ ] Action bar com 8 ações, todas disparam endpoint correto
- [ ] Confirm soft (com preview de custo quando disponível) e confirm hard (typed-input)
- [ ] Modal de resultado pós-job com detalhes de erros + re-tentar falhas
- [ ] CSV export até 50 leads (warning acima)
- [ ] Polling 5s em counts + banner "lista atualizada"
- [ ] Badge no sidebar Jobs
- [ ] Filtros ativos banner no toolbar
- [ ] Funnel de conversão clicável no toolbar
- [ ] Mobile: 3 colunas + bottom sheet pra ações
- [ ] Endpoints `PATCH/DELETE /api/leads/bulk`, `POST /api/pipeline/preview`, `GET /api/leads/ids`
- [ ] Atalhos `Cmd+A`, `Esc`, `Shift+click`
- [ ] Filtros novos: `score_max`, `has_telefone`, `has_email`
- [ ] Tests:
  - Backend: bulk endpoints (happy + 5000 limit + invalid status)
  - Frontend: hook de seleção (3 modos, transições, sessionStorage)

---

## Pendências fora do escopo (futuro)

- Saved views workspace (G1)
- Smart segments dinâmicos (G2)
- Bulk action playbooks (G3)
- Schedule routines (G4)
- Bulk inline edit avançado (G6)
- Tags/labels custom (G7)
- Activity feed (G9)
- Undo bulk (adiado por decisão)
- Insights de operação (G11)
- CSV import-loop (parte de G12)
- Endpoint `by_filter` para >5000

## Referências

- Discovery: [`docs/superpowers/discovery/2026-05-01-bulk-actions-table-view.md`](../discovery/2026-05-01-bulk-actions-table-view.md)
- Backend bulk-ready: `backend/app/routers/pipeline.py:144-300`
- Kanban atual: `frontend/src/components/kanban-board.tsx`, `kanban-column.tsx`
- Tipos: `frontend/src/lib/types.ts`
- DS: `frontend/src/components/ui/`
