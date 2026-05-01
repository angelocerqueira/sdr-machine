# Bulk Actions + Table View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir view de tabela paralela ao kanban (toggle) com seleção múltipla e barra de ações em massa. Resolve gargalo de operação massiva (300+ leads). Backend ganha endpoints bulk + preview + ids; frontend ganha rota `/app/pipeline` unificada com TanStack Table + multi-select.

**Architecture:** Toggle Kanban ↔ Tabela em rota única `/app/pipeline?view=...`. Multi-select via `Set<number>` com 3 modos (none/page/all_filter), persistido em sessionStorage. Backend adiciona 4 endpoints (`PATCH /api/leads/bulk`, `DELETE /api/leads/bulk`, `POST /api/pipeline/preview`, `GET /api/leads/ids`). Limite hard de 5000 leads via IDs.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + Pydantic backend; Next.js 16 + React 19 + Tailwind 4 + `@tanstack/react-table` + `@tanstack/react-virtual` frontend; pytest + SQLite in-memory.

**Spec:** `docs/superpowers/specs/2026-05-01-bulk-actions-table-view-design.md`

---

## File Structure

### Backend novo
```
backend/
├── tests/
│   ├── test_leads_bulk.py        # PATCH/DELETE bulk
│   ├── test_pipeline_preview.py  # POST /pipeline/preview
│   └── test_leads_ids.py         # GET /leads/ids
```

### Backend modificado
- `app/routers/leads.py` — `+PATCH /bulk`, `+DELETE /bulk`, `+GET /ids`, filtros novos (`score_max`, `has_telefone`, `has_email`)
- `app/routers/pipeline.py` — `+POST /pipeline/preview`
- `app/schemas.py` — `BulkLeadUpdate`, `BulkLeadDelete`, `BulkUpdateResult`, `BulkDeleteResult`, `PipelinePreviewRequest`, `PipelinePreviewResponse`

### Frontend novo
```
frontend/src/
├── app/app/pipeline/
│   └── page.tsx                       # Orquestra view + filtros (query string)
├── components/pipeline/
│   ├── pipeline-toolbar.tsx           # Filtros + view toggle + funnel + filtros ativos
│   ├── pipeline-kanban.tsx            # Wrapper do kanban-board (refactor leve)
│   ├── pipeline-table.tsx             # Nova tabela TanStack
│   ├── pipeline-table-row.tsx         # Linha virtualizada
│   ├── pipeline-table-pagination.tsx
│   ├── bulk-action-bar.tsx            # Sticky bottom
│   ├── bulk-confirm-modal.tsx         # Soft + hard
│   ├── bulk-result-modal.tsx          # Erros parciais + re-tentar
│   ├── select-all-banner.tsx
│   ├── column-visibility-menu.tsx
│   ├── filtros-ativos-banner.tsx
│   ├── pipeline-funnel.tsx            # Funnel clicável
│   └── use-bulk-selection.ts          # Hook Set + sessionStorage
├── components/dashboard/
│   └── job-badge.tsx                  # Badge no AppSidebar item Jobs
└── lib/
    └── csv-export.ts                  # Util client-side
```

### Frontend modificado
- `src/lib/api.ts` — `+bulkUpdateLeads`, `+bulkDeleteLeads`, `+previewPipeline`, `+getLeadIds`, filtros novos
- `src/lib/types.ts` — tipos bulk
- `src/components/app-sidebar.tsx` — Pipeline substitui Kanban, badge Jobs
- `src/app/app/kanban/page.tsx` — redirect `/app/pipeline?view=kanban`
- `src/app/app/layout.tsx` — wire polling counts global se necessário
- `frontend/package.json` — `+@tanstack/react-table`, `+@tanstack/react-virtual`

---

## PR 1: Backend bulk + preview + ids

Foundation. Sem PR2-5, este já merge limpo: endpoints existem, ninguém chama ainda.

### Task 1.1: Schemas Pydantic

**Files:**
- Modify: `backend/app/schemas.py`

- [ ] **Step 1: Adicionar schemas bulk**

Add ao final de `schemas.py`:

```python
from typing import Literal

class BulkLeadUpdate(BaseModel):
    lead_ids: list[int] = Field(min_length=1, max_length=5000)
    data: LeadUpdate

class BulkLeadDelete(BaseModel):
    lead_ids: list[int] = Field(min_length=1, max_length=5000)

class BulkUpdateError(BaseModel):
    lead_id: int
    error: str

class BulkUpdateResult(BaseModel):
    updated: int
    errors: list[BulkUpdateError]

class BulkDeleteResult(BaseModel):
    deleted: int
    errors: list[BulkUpdateError]

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
    cost_estimate: dict | None = None
    quota_status: list[dict] | None = None
    warnings: list[str]

class LeadIdsResponse(BaseModel):
    ids: list[int]
    total: int
    truncated: bool
```

- [ ] **Step 2: Verificar import de `LeadUpdate`** já existente.

Run: `cd backend && python -c "from app.schemas import BulkLeadUpdate; print('ok')"`
Expected: `ok`

### Task 1.2: `PATCH /api/leads/bulk`

**Files:**
- Modify: `backend/app/routers/leads.py`

- [ ] **Step 1: Adicionar endpoint**

Antes do `@router.patch("/{lead_id}")` existente:

```python
@router.patch("/bulk", response_model=BulkUpdateResult)
def bulk_update_leads(payload: BulkLeadUpdate, db: Session = Depends(get_db)):
    update_data = payload.data.model_dump(exclude_unset=True)
    if not update_data:
        return BulkUpdateResult(updated=0, errors=[])

    if "status" in update_data and update_data["status"] not in VALID_STATUSES:
        raise HTTPException(422, detail=f"Invalid status: {update_data['status']}")

    leads = db.query(Lead).filter(Lead.id.in_(payload.lead_ids)).all()
    found_ids = {l.id for l in leads}
    errors = [
        BulkUpdateError(lead_id=lid, error="Lead not found")
        for lid in payload.lead_ids if lid not in found_ids
    ]

    updated = 0
    for lead in leads:
        try:
            for k, v in update_data.items():
                setattr(lead, k, v)
            updated += 1
        except Exception as exc:
            errors.append(BulkUpdateError(lead_id=lead.id, error=str(exc)[:200]))

    db.commit()
    return BulkUpdateResult(updated=updated, errors=errors)
```

- [ ] **Step 2: Importar schemas**

Add no topo:
```python
from app.schemas import (
    JobOut, LandingPageOut, LeadListOut, LeadOut, LeadSummaryOut, LeadUpdate,
    OutreachMessageOut, ReclassifyRequest,
    BulkLeadUpdate, BulkLeadDelete, BulkUpdateResult, BulkDeleteResult,
    BulkUpdateError, LeadIdsResponse,
)
```

- [ ] **Step 3: Smoke test manual**

```bash
cd backend && uvicorn app.main:app --reload &
curl -X PATCH http://localhost:8000/api/leads/bulk \
  -H "Content-Type: application/json" \
  -d '{"lead_ids":[1,2],"data":{"status":"enriched"}}'
```
Expected: `{"updated":N,"errors":[]}` (ou erros se IDs não existirem).

### Task 1.3: `DELETE /api/leads/bulk`

**Files:**
- Modify: `backend/app/routers/leads.py`

- [ ] **Step 1: Adicionar endpoint**

```python
@router.delete("/bulk", response_model=BulkDeleteResult)
def bulk_delete_leads(payload: BulkLeadDelete, db: Session = Depends(get_db)):
    leads = db.query(Lead).filter(Lead.id.in_(payload.lead_ids)).all()
    found_ids = {l.id for l in leads}
    errors = [
        BulkUpdateError(lead_id=lid, error="Lead not found")
        for lid in payload.lead_ids if lid not in found_ids
    ]
    deleted = 0
    for lead in leads:
        try:
            db.delete(lead)
            deleted += 1
        except Exception as exc:
            errors.append(BulkUpdateError(lead_id=lead.id, error=str(exc)[:200]))
    db.commit()
    return BulkDeleteResult(deleted=deleted, errors=errors)
```

### Task 1.4: `GET /api/leads/ids`

**Files:**
- Modify: `backend/app/routers/leads.py`

- [ ] **Step 1: Adicionar endpoint**

Aceita os mesmos query params do `GET /api/leads`. Reutilizar lógica de filtros (extrair em função privada `_apply_filters(query, ...)` se virar duplicação).

```python
@router.get("/ids", response_model=LeadIdsResponse)
def list_lead_ids(
    status: str | None = None,
    nicho: str | None = None,
    cidade: str | None = None,
    score_min: int | None = None,
    score_max: int | None = None,
    has_telefone: bool | None = None,
    has_email: bool | None = None,
    search: str | None = None,
    perfil_lead: str | None = None,
    nicho_canonico: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Lead.id)
    query = _apply_lead_filters(
        query, status=status, nicho=nicho, cidade=cidade,
        score_min=score_min, score_max=score_max,
        has_telefone=has_telefone, has_email=has_email,
        search=search, perfil_lead=perfil_lead, nicho_canonico=nicho_canonico,
    )
    total = query.count()
    rows = query.limit(5001).all()
    truncated = len(rows) > 5000
    ids = [r[0] for r in rows[:5000]]
    return LeadIdsResponse(ids=ids, total=total, truncated=truncated)
```

- [ ] **Step 2: Refatorar filtros em `_apply_lead_filters`**

Extrair toda a lógica de `if nicho: query = query.filter(...)` do `list_leads()` em função privada que recebe a query e retorna a query filtrada. `list_leads`, `lead_counts` e `list_lead_ids` chamam.

### Task 1.5: Filtros novos (`score_max`, `has_telefone`, `has_email`)

**Files:**
- Modify: `backend/app/routers/leads.py`

- [ ] **Step 1: Adicionar params no `_apply_lead_filters`, `list_leads`, `lead_counts`**

```python
if score_max is not None:
    query = query.filter(Lead.opportunity_score <= score_max)
if has_telefone is not None:
    query = query.filter(Lead.telefone.isnot(None) if has_telefone else Lead.telefone.is_(None))
if has_email is not None:
    query = query.filter(Lead.email.isnot(None) if has_email else Lead.email.is_(None))
```

### Task 1.6: `POST /api/pipeline/preview`

**Files:**
- Modify: `backend/app/routers/pipeline.py`

- [ ] **Step 1: Adicionar endpoint stub**

Versão inicial sem cost/quota (preenchidos depois). Calcula `eligible/skipped` baseado nos filtros que cada `_run_*` aplica.

```python
@router.post("/pipeline/preview", response_model=PipelinePreviewResponse)
def preview_pipeline(payload: PipelinePreviewRequest, db: Session = Depends(get_db)):
    leads = db.query(Lead).filter(Lead.id.in_(payload.lead_ids)).all()
    total = len(leads)

    skipped_reasons: dict[str, int] = {}
    warnings: list[str] = []
    eligible = total

    if payload.action == "enrich":
        already = sum(1 for l in leads if l.status not in ("scraped", "enrich_failed"))
        if already > 0:
            skipped_reasons["already_enriched"] = already
            warnings.append(f"{already} leads já enriquecidos. Use force_providers para reprocessar.")
            if not payload.options.get("force_providers"):
                eligible -= already

    elif payload.action == "generate":
        disq = sum(1 for l in leads if l.status == "disqualified")
        if disq > 0:
            skipped_reasons["disqualified"] = disq
            eligible -= disq

    elif payload.action == "outreach":
        no_lp = sum(1 for l in leads if l.status not in ("lp_generated", "outreach_ready", "outreach_failed"))
        if no_lp > 0:
            skipped_reasons["no_lp"] = no_lp
            eligible -= no_lp
            warnings.append(f"{no_lp} leads sem LP gerada. Gere LP antes do outreach.")

    return PipelinePreviewResponse(
        action=payload.action,
        total_leads=total,
        eligible=eligible,
        skipped=total - eligible,
        skipped_reasons=skipped_reasons,
        cost_estimate=None,
        quota_status=None,
        warnings=warnings,
    )
```

- [ ] **Step 2: Importar schemas**

```python
from app.schemas import (..., PipelinePreviewRequest, PipelinePreviewResponse)
```

### Task 1.7: Tests backend

**Files:**
- Create: `backend/tests/test_leads_bulk.py`
- Create: `backend/tests/test_leads_ids.py`
- Create: `backend/tests/test_pipeline_preview.py`

- [ ] **Step 1: Bulk update tests**

Casos:
- happy: 3 IDs válidos com `data.status` válido → `updated=3`
- IDs mistos (válidos + inexistentes) → erros + updated parcial
- 0 IDs → 422
- 5001 IDs → 422
- status inválido → 422

- [ ] **Step 2: Bulk delete tests**

Casos:
- happy: deleta + cascade em messages/LPs
- IDs inexistentes → erros não-bloqueantes
- 5001 IDs → 422

- [ ] **Step 3: `GET /leads/ids` tests**

Casos:
- happy: retorna IDs + total = len
- truncamento: insere 5001 leads, espera `truncated=true`, len(ids)=5000
- com filtros: `?status=scraped&cidade=SP`

- [ ] **Step 4: `POST /pipeline/preview` tests**

Casos:
- enrich com mix de scraped + enriched → eligible exclui já enriquecidos sem force
- enrich com `force_providers` → eligible = total
- generate excluindo disqualified
- outreach com leads sem LP

- [ ] **Step 5: Run tests**

```bash
cd backend && pytest tests/test_leads_bulk.py tests/test_leads_ids.py tests/test_pipeline_preview.py -v
```
Expected: tudo verde.

### Task 1.8: PR 1 commit + push

- [ ] **Step 1: Commit + branch**

```bash
git checkout -b feat/bulk-actions-backend
git add backend/
git commit -m "feat(api): bulk leads endpoints + pipeline preview + ids endpoint (PR 1/5)"
git push -u origin feat/bulk-actions-backend
gh pr create --title "feat(api): bulk leads + preview + ids (PR 1/5)" --body "..."
```

---

## PR 2: Frontend table base

Tabela funcional com toggle, sem multi-select. Já desbloqueia inspeção/sort por todas colunas.

### Task 2.1: Dependências

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Instalar TanStack**

```bash
cd frontend && npm i @tanstack/react-table @tanstack/react-virtual
```

### Task 2.2: API wrapper

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/types.ts`

- [ ] **Step 1: Tipos**

Em `types.ts`:
```typescript
export interface BulkUpdateError {
  lead_id: number;
  error: string;
}
export interface BulkUpdateResult {
  updated: number;
  errors: BulkUpdateError[];
}
export interface BulkDeleteResult {
  deleted: number;
  errors: BulkUpdateError[];
}
export interface LeadIdsResponse {
  ids: number[];
  total: number;
  truncated: boolean;
}
export type PipelineAction = "enrich" | "generate" | "outreach" | "classify";
export interface PipelinePreviewRequest {
  action: PipelineAction;
  lead_ids: number[];
  options?: Record<string, unknown>;
}
export interface PipelinePreviewResponse {
  action: PipelineAction;
  total_leads: number;
  eligible: number;
  skipped: number;
  skipped_reasons: Record<string, number>;
  cost_estimate: { currency: string; total: number; breakdown: Array<{ provider: string; calls: number; cost: number }> } | null;
  quota_status: Array<{ provider: string; used: number; limit: number; would_hit_limit: boolean }> | null;
  warnings: string[];
}
```

- [ ] **Step 2: Funções API**

Em `api.ts`:
```typescript
export const bulkUpdateLeads = (lead_ids: number[], data: Record<string, unknown>) =>
  fetchAPI<BulkUpdateResult>("/api/leads/bulk", { method: "PATCH", body: JSON.stringify({ lead_ids, data }) });

export const bulkDeleteLeads = (lead_ids: number[]) =>
  fetchAPI<BulkDeleteResult>("/api/leads/bulk", { method: "DELETE", body: JSON.stringify({ lead_ids }) });

export const getLeadIds = (params?: Record<string, string>) => {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return fetchAPI<LeadIdsResponse>(`/api/leads/ids${qs}`);
};

export const previewPipeline = (payload: PipelinePreviewRequest) =>
  fetchAPI<PipelinePreviewResponse>("/api/pipeline/preview", { method: "POST", body: JSON.stringify(payload) });
```

### Task 2.3: Rota `/app/pipeline`

**Files:**
- Create: `frontend/src/app/app/pipeline/page.tsx`
- Modify: `frontend/src/app/app/kanban/page.tsx`

- [ ] **Step 1: Page com query string state**

`pipeline/page.tsx`:
```tsx
"use client";
import { useSearchParams, useRouter } from "next/navigation";
import { PipelineToolbar } from "@/components/pipeline/pipeline-toolbar";
import { PipelineKanban } from "@/components/pipeline/pipeline-kanban";
import { PipelineTable } from "@/components/pipeline/pipeline-table";

export default function PipelinePage() {
  const sp = useSearchParams();
  const view = (sp.get("view") || localStorage.getItem("sdr-pipeline-view") || "kanban") as "kanban" | "table";

  return (
    <div className="space-y-4">
      <PipelineToolbar view={view} />
      {view === "table" ? <PipelineTable /> : <PipelineKanban />}
    </div>
  );
}
```

- [ ] **Step 2: Redirect kanban → pipeline**

`kanban/page.tsx`:
```tsx
import { redirect } from "next/navigation";
export default function Page() {
  redirect("/app/pipeline?view=kanban");
}
```

### Task 2.4: PipelineKanban (wrap kanban-board)

**Files:**
- Create: `frontend/src/components/pipeline/pipeline-kanban.tsx`

- [ ] **Step 1: Wrap mínimo**

Apenas re-export do `KanbanBoard` atual. Refactor zero (filtros e funnel migram pra toolbar em tasks futuras; manter dois lugares por ora é OK).

```tsx
"use client";
import { KanbanBoard } from "@/components/kanban-board";
export function PipelineKanban() { return <KanbanBoard />; }
```

> **Nota:** posteriormente extrair filtros do `KanbanBoard` pra `pipeline-toolbar`. Tracking issue.

### Task 2.5: PipelineToolbar

**Files:**
- Create: `frontend/src/components/pipeline/pipeline-toolbar.tsx`

- [ ] **Step 1: Layout base**

Replica os filtros do `kanban-board.tsx` (busca, nicho, cidade, score_min, perfil, nicho_canonico, order_by) + segmented control de view. Todos filtros vivem em **query string** (`useSearchParams`), não state local.

```tsx
function setQuery(key: string, value: string | null) {
  const sp = new URLSearchParams(searchParams.toString());
  if (value) sp.set(key, value); else sp.delete(key);
  router.replace(`?${sp.toString()}`);
}
```

- [ ] **Step 2: Toggle view**

Segmented control com 2 opções (Kanban / Tabela). Ao clicar:
- Atualiza query string `?view=...`
- Persiste em localStorage `sdr-pipeline-view`

- [ ] **Step 3: Verificar persistência manual**

Abrir tabela, F5, voltar pra tabela. Ok.

### Task 2.6: PipelineTable estrutura básica

**Files:**
- Create: `frontend/src/components/pipeline/pipeline-table.tsx`
- Create: `frontend/src/components/pipeline/pipeline-table-row.tsx`
- Create: `frontend/src/components/pipeline/pipeline-table-pagination.tsx`

- [ ] **Step 1: Definição de colunas (TanStack)**

```tsx
const columns: ColumnDef<Lead>[] = [
  { id: "select", header: ..., cell: ... },  // placeholder, vazio em PR 2
  { accessorKey: "nome", header: "Nome", cell: linkToLeadApp, enableSorting: true },
  { accessorKey: "cidade", header: "Cidade" },
  { accessorKey: "nicho_canonico", header: "Nicho", cell: nichoTag },
  { accessorKey: "opportunity_score", header: "Score", cell: scoreCell, enableSorting: true },
  { accessorKey: "perfil_lead", header: "Perfil", cell: perfilBadge },
  { accessorKey: "status", header: "Status", cell: statusPill },
  { accessorKey: "updated_at", header: "Atualizado", cell: relTime, enableSorting: true },
];
```

- [ ] **Step 2: Fetch + state**

Hook `usePipelineLeads(filters, page, perPage, sort)` que chama `getLeads`. Retorna `{ items, total, loading }`.

- [ ] **Step 3: Render**

```tsx
<table>
  <thead>{ /* getHeaderGroups + sort handlers */ }</thead>
  <tbody>{ rows.map(row => <PipelineTableRow row={row} />) }</tbody>
</table>
<PipelineTablePagination total={total} page={page} perPage={50} onChange={setPage} />
```

- [ ] **Step 4: Virtualização**

`useVirtualizer` no tbody. `count = rows.length`, `estimateSize = () => 48` (compact density).

- [ ] **Step 5: Sort wire**

Header click → atualiza `order_by` na query string. Map TanStack sort → `score_desc|score_asc|name_asc|updated_desc`.

- [ ] **Step 6: Loading + empty states**

Skeleton 5 rows enquanto carrega. Empty: `"Nenhum lead encontrado. Tente ajustar filtros."`

### Task 2.7: AppSidebar — Pipeline substitui Kanban

**Files:**
- Modify: `frontend/src/components/app-sidebar.tsx`

- [ ] **Step 1: Renomear item**

Trocar entry "Kanban" por "Pipeline", apontando pra `/app/pipeline`. Manter ícone (ou trocar pra um mais semântico se DS tiver).

- [ ] **Step 2: Verificar mobile drawer**

Smoke test: 320px, drawer abre, item clicável.

### Task 2.8: PR 2 commit

- [ ] **Step 1: Branch + commit**

```bash
git checkout -b feat/pipeline-table-base
git add frontend/
git commit -m "feat(pipeline): rota unificada /app/pipeline com toggle kanban/tabela (PR 2/5)"
gh pr create --title "feat(pipeline): table view base + toggle (PR 2/5)" --body "..."
```

---

## PR 3: Multi-select + action bar + confirm modals

Coração da feature. PR 1 e 2 mergeados.

### Task 3.1: Hook `use-bulk-selection`

**Files:**
- Create: `frontend/src/components/pipeline/use-bulk-selection.ts`

- [ ] **Step 1: Tipos + hook**

```typescript
type SelectionMode = "ids" | "all_filter";
interface SelectionState {
  mode: SelectionMode;
  ids: Set<number>;
  excludedIds: Set<number>;
  filterSnapshot: Record<string, string>;
  totalInFilter: number;
}

export function useBulkSelection() {
  // load from sessionStorage
  // expose: toggle, selectPage, selectAllFilter, clear, has, size, materializeIds
  // persist on every change
}
```

- [ ] **Step 2: `materializeIds()`**

```typescript
async function materializeIds(): Promise<number[]> {
  if (state.mode === "ids") return [...state.ids];
  const { ids, truncated } = await getLeadIds(state.filterSnapshot);
  if (truncated) throw new Error("BULK_LIMIT_EXCEEDED");
  return ids.filter(id => !state.excludedIds.has(id));
}
```

- [ ] **Step 3: `size()` correto em ambos modos**

- mode=ids: `state.ids.size`
- mode=all_filter: `state.totalInFilter - state.excludedIds.size`

### Task 3.2: Wire checkboxes na tabela

**Files:**
- Modify: `frontend/src/components/pipeline/pipeline-table.tsx`
- Modify: `frontend/src/components/pipeline/pipeline-table-row.tsx`

- [ ] **Step 1: Coluna checkbox**

```tsx
{
  id: "select",
  size: 40,
  header: ({ table }) => (
    <Checkbox
      checked={pageAllSelected ? true : pageAnySelected ? "indeterminate" : false}
      onChange={() => sel.togglePage(visibleIds)}
    />
  ),
  cell: ({ row }) => (
    <Checkbox checked={sel.has(row.original.id)} onChange={() => sel.toggle(row.original.id)} />
  ),
}
```

- [ ] **Step 2: Shift+click range**

Guardar `lastClickedId`. Em shift+click, seleciona todos entre `lastClickedId` e `current` na ordem visível.

- [ ] **Step 3: Cmd+A**

Listener no scope da tabela: `Cmd/Ctrl+A` → `sel.togglePage(visibleIds)`. Preventa default só quando foco está dentro da tabela.

- [ ] **Step 4: Esc**

`Esc` → `sel.clear()`.

### Task 3.3: SelectAllBanner

**Files:**
- Create: `frontend/src/components/pipeline/select-all-banner.tsx`

- [ ] **Step 1: 3 estados**

```tsx
if (mode === "all_filter") {
  // banner verde "Todos os N do filtro selecionados [Limpar]"
}
if (pageAllSelected && total > pageSize) {
  // banner azul "Os 50 desta página estão selecionados. [Selecionar todos os 347 →]"
}
return null;
```

- [ ] **Step 2: Wire selectAllFilter**

Click → `getLeadIds(filters)` → se `truncated` → modal warning. Senão → `sel.selectAllFilter(filters, total)`.

### Task 3.4: BulkActionBar

**Files:**
- Create: `frontend/src/components/pipeline/bulk-action-bar.tsx`

- [ ] **Step 1: Sticky bottom**

```tsx
<div className="fixed bottom-0 left-[64px] right-0 bg-surface border-t shadow-lg z-40 ... mobile collapses">
```

`left-[64px]` desktop, `left-0` mobile. Aparece quando `sel.size() > 0`.

- [ ] **Step 2: Botões + handlers**

| Botão | Handler |
|---|---|
| Re-enriquecer | `handleAction("enrich")` |
| Gerar LP | `handleAction("generate")` |
| Gerar mensagens | `handleAction("outreach")` |
| Mover para ▾ | dropdown com `KANBAN_COLUMNS`, click → `handleBulkUpdate({status: id})` |
| Editar ▾ | dropdown: pacote, prioridade, perfil |
| Exportar CSV | `handleExport()` (Task 5.x) |
| Excluir | `handleDelete()` |
| Limpar | `sel.clear()` |

`handleAction(action)`:
1. `materializeIds()` — se throw `BULK_LIMIT_EXCEEDED`, modal "Reduza filtro pra ≤5000".
2. `previewPipeline({action, lead_ids})` → response.
3. Abre `BulkConfirmModal` com summary.
4. On confirm → `runEnrich/runGenerate/runOutreach({lead_ids})` → toast "Job iniciado" + clear seleção.

`handleBulkUpdate(data)`:
1. `materializeIds()`.
2. `BulkConfirmModal` (sem preview, mostra contagem).
3. On confirm → `bulkUpdateLeads(ids, data)` → toast resultado + refetch tabela.

`handleDelete()`:
1. `materializeIds()`.
2. `BulkConfirmModal` modo `hard` (typed-input).
3. On confirm → `bulkDeleteLeads(ids)` → toast + refetch.

- [ ] **Step 3: Estados disabled**

Hook `usePipelineStatus()` polls `getPipelineStatus()` cada 5s. Botões `Re-enriquecer/Gerar LP/Gerar mensagens` ficam disabled se `running_jobs.includes("enrich"|"generate"|"outreach")`.

- [ ] **Step 4: Mobile bottom-sheet**

`<768px`: action bar mostra só `[N selecionados] [⋯]` com bottom-sheet pras 8 ações.

### Task 3.5: BulkConfirmModal

**Files:**
- Create: `frontend/src/components/pipeline/bulk-confirm-modal.tsx`

- [ ] **Step 1: Props**

```typescript
interface Props {
  open: boolean;
  onClose: () => void;
  onConfirm: (options?: { force?: boolean }) => void;
  variant: "soft" | "hard";
  title: string;
  description: React.ReactNode;
  confirmLabel: string;
  preview?: PipelinePreviewResponse;
  hardConfirmKeyword?: string;  // ex: "EXCLUIR"
}
```

- [ ] **Step 2: Render soft**

Se `preview`: mostra `total_leads`, `eligible/skipped`, `cost_estimate?`, `quota_status?`, `warnings`. Radio "Pular já enriquecidos / Forçar" se `skipped_reasons.already_enriched`.

- [ ] **Step 3: Render hard**

Input texto. Botão confirm disabled até `value === hardConfirmKeyword`. Cor `bg-danger`.

### Task 3.6: PR 3 commit

- [ ] **Step 1: Branch + commit + PR**

```bash
git checkout -b feat/pipeline-bulk-select
git add frontend/
git commit -m "feat(pipeline): multi-select + action bar + confirm modals (PR 3/5)"
gh pr create --title "feat(pipeline): bulk selection + actions (PR 3/5)" --body "..."
```

---

## PR 4: Polling + result modal + funnel + filtros novos

Glue layer que conecta jobs em background com a UI e adiciona observabilidade.

### Task 4.1: Polling counts

**Files:**
- Create: `frontend/src/components/pipeline/use-pipeline-counts.ts`
- Modify: `frontend/src/components/pipeline/pipeline-toolbar.tsx`

- [ ] **Step 1: Hook**

```typescript
export function usePipelineCounts(filters: Record<string, string>) {
  const [counts, setCounts] = useState({});
  const [stale, setStale] = useState<{newTotal: number} | null>(null);
  // poll a cada 5s
  // diff: se newTotal != lastTotal mais de 5%, set stale
  // expose refetch()
}
```

- [ ] **Step 2: Banner "lista atualizada"**

Render acima da tabela quando `stale`. Click → refetch + dismiss.

### Task 4.2: PipelineFunnel

**Files:**
- Create: `frontend/src/components/pipeline/pipeline-funnel.tsx`
- Modify: `frontend/src/components/pipeline/pipeline-toolbar.tsx`

- [ ] **Step 1: Render**

Barra horizontal com 5 marcos (`scraped → enriched → lp_generated → outreach_sent → responded`). Source: `usePipelineCounts` agregando os states.

- [ ] **Step 2: Click**

Click em marco = aplica `?status=...` na URL.

### Task 4.3: FiltrosAtivosBanner

**Files:**
- Create: `frontend/src/components/pipeline/filtros-ativos-banner.tsx`
- Modify: `frontend/src/components/pipeline/pipeline-toolbar.tsx`

- [ ] **Step 1: Render**

Lê query string. Se algum filtro setado, render `"Filtros ativos: cidade=SP, score≥70  [limpar tudo]"`.

- [ ] **Step 2: Limpar tudo**

Limpa todos os params exceto `view`.

### Task 4.4: Job badge no AppSidebar

**Files:**
- Create: `frontend/src/components/dashboard/job-badge.tsx`
- Modify: `frontend/src/components/app-sidebar.tsx`

- [ ] **Step 1: Hook `useActiveJobs`**

Polls `getJobs({status: "running"})` cada 5s + jobs done últimos 60s.

- [ ] **Step 2: Render badge**

`<span className="absolute top-0 right-0 bg-accent rounded-full text-[10px] ...">{count}</span>`. Hide quando 0.

### Task 4.5: BulkResultModal

**Files:**
- Create: `frontend/src/components/pipeline/bulk-result-modal.tsx`
- Modify: `frontend/src/components/dashboard/job-badge.tsx` ou hook global

- [ ] **Step 1: Hook global de jobs concluídos**

Quando `useActiveJobs` detecta job que mudou de `running → done|done_with_errors|failed`:
- Toast com summary
- Click no toast abre `BulkResultModal` com `job.result_summary`

- [ ] **Step 2: Modal**

Lista até 10 erros. `[+ N mais]` expande. Botão "Re-tentar falhas" extrai IDs do `errors[].lead_id` e re-popula seleção (precisa expor sel via context global ou store).

> **Decisão:** se "re-tentar falhas" exige store global, simplificar v1: botão só copia IDs pro clipboard. Re-tentar manual depois.

### Task 4.6: Filtros novos na toolbar

**Files:**
- Modify: `frontend/src/components/pipeline/pipeline-toolbar.tsx`

- [ ] **Step 1: Adicionar campos**

`score_max`, `has_telefone` (toggle 3-state: any/sim/não), `has_email` (idem). Wire via query string.

### Task 4.7: PR 4 commit

```bash
git checkout -b feat/pipeline-jobs-funnel
git add frontend/
git commit -m "feat(pipeline): polling + funnel + result modal + job badge (PR 4/5)"
gh pr create ...
```

---

## PR 5: Polish (column visibility, mobile, CSV, a11y, telemetria)

Última milha.

### Task 5.1: ColumnVisibilityMenu

**Files:**
- Create: `frontend/src/components/pipeline/column-visibility-menu.tsx`
- Modify: `frontend/src/components/pipeline/pipeline-table.tsx`

- [ ] **Step 1: Definir colunas opcionais**

Adicionar ao `columns[]`: `telefone`, `email`, `cnpj`, `razao_social`, `tech_stack`, `reviews`, `pacote_sugerido`, `prioridade`, `job_id`, `created_at`.

- [ ] **Step 2: Menu**

Botão `⋮ Colunas` no header da tabela. Dropdown com checkbox por coluna. Estado em `localStorage` (`sdr-table-columns`).

### Task 5.2: Mobile defaults

**Files:**
- Modify: `frontend/src/components/pipeline/pipeline-table.tsx`

- [ ] **Step 1: Detectar viewport**

`useMediaQuery("(max-width: 768px)")`. Mobile: força colunas `nome | score | status` somente.

- [ ] **Step 2: Hit area checkbox 40px**

Padding extra no `<th>/<td>` da coluna select pra ≥40px clickable.

### Task 5.3: CSV export

**Files:**
- Create: `frontend/src/lib/csv-export.ts`
- Modify: `frontend/src/components/pipeline/bulk-action-bar.tsx`

- [ ] **Step 1: Util**

```typescript
export function exportLeadsCSV(leads: Lead[]) {
  const headers = ["lead_id","public_id","nome","telefone","email","cidade","nicho","score","status","atualizado_em"];
  const rows = leads.map(l => headers.map(h => escapeCSV(l[h])));
  const csv = "﻿" + [headers, ...rows].map(r => r.join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  // trigger download
}
```

- [ ] **Step 2: Limite v1**

Em `handleExport()`:
- Se `sel.size() > 50` → toast "Reduza pra ≤50 leads pra exportar."
- Senão → fetch detalhes + gera CSV.

### Task 5.4: Acessibilidade

**Files:**
- Modify: vários componentes pipeline

- [ ] **Step 1: ARIA na tabela**

- `<table role="table">`, `<th aria-sort="ascending|descending|none">` no header.
- Checkbox header com `aria-checked={"mixed"|true|false}`.

- [ ] **Step 2: Modal focus trap**

Confirma que `BulkConfirmModal` e `BulkResultModal` têm focus trap. Usar lib `focus-trap-react` se não houver primitive interno.

- [ ] **Step 3: ESC no modal**

ESC fecha exceto em modo `hard` (exige typed).

### Task 5.5: Telemetria PostHog

**Files:**
- Create: `frontend/src/lib/telemetry.ts`
- Modify: vários componentes pipeline

- [ ] **Step 1: Wrapper**

Stub `track(event, props)` que vira no-op se PostHog não tá inicializado. Apenas estrutura.

- [ ] **Step 2: Disparar eventos**

- `pipeline_view_toggled` no toggle
- `bulk_selection_started` quando `size()` muda de 0 → >0
- `bulk_action_dispatched` antes do dispatch
- `bulk_action_completed` no toast pós-job
- `column_visibility_changed`
- `csv_exported`

### Task 5.6: Verificação ponta-a-ponta

- [ ] **Step 1: Smoke test happy paths H1-H7 do spec**

Manual no `npm run dev`. Cada um: passa ou abre issue.

- [ ] **Step 2: Edge cases tabelados no spec**

Pelo menos: filtro muda com seleção, F5 preserva, 5001 truncamento, race com bulk move.

- [ ] **Step 3: Lint + build**

```bash
cd frontend && npm run lint && npm run build
```

- [ ] **Step 4: Tests backend**

```bash
cd backend && pytest
```

### Task 5.7: PR 5 commit

```bash
git checkout -b feat/pipeline-polish
git add .
git commit -m "feat(pipeline): polish - column visibility, mobile, CSV, a11y, telemetria (PR 5/5)"
gh pr create ...
```

---

## Definição de pronto (rollup)

Todos os checkboxes do spec marcados:

- [ ] Toggle Kanban ↔ Tabela funciona, persiste preferência
- [ ] Tabela 8 colunas default, sortable, paginada (50/page)
- [ ] Multi-select 3 modos, sessionStorage
- [ ] SelectAllBanner aparece/desaparece corretamente
- [ ] Action bar com 8 ações
- [ ] Confirm soft (com preview) + hard (typed-input)
- [ ] BulkResultModal com erros parciais
- [ ] CSV export até 50 leads
- [ ] Polling 5s + banner atualização
- [ ] Job badge sidebar
- [ ] Filtros ativos banner
- [ ] Funnel clicável
- [ ] Mobile: 3 cols + bottom sheet
- [ ] Endpoints `PATCH/DELETE /api/leads/bulk`, `POST /api/pipeline/preview`, `GET /api/leads/ids`
- [ ] Atalhos `Cmd+A`, `Esc`, `Shift+click`
- [ ] Filtros novos: `score_max`, `has_telefone`, `has_email`
- [ ] Tests backend + smoke frontend

## Ordem sugerida de merge

PR 1 (backend) → PR 2 (table base) → PR 3 (multi-select) → PR 4 (jobs glue) → PR 5 (polish).

PRs 1 e 2 independentes (podem ser paralelos). PR 3 depende de 1+2. PR 4 depende de 3. PR 5 depende de 4.
