# Lead App Pagination — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir `per_page: 100` hardcoded da master list por paginação incremental via botão "Carregar mais" (30 leads por batch).

**Architecture:** Estado `page`/`total` no hook `use-lead-app.ts`. Fetch com `append=true` concatena ao invés de substituir. Botão renderizado no rodapé da master list. Backend já suporta (`routers/leads.py`). Spec: `docs/superpowers/specs/2026-04-20-leads-pagination-design.md`.

**Tech Stack:** Next.js 16 / React 19 / TypeScript.

---

## File Structure

- `frontend/src/components/leads/use-lead-app.ts` — estado page + loadMore + total
- `frontend/src/components/leads/la-master.tsx` — renderizar botão "Carregar mais"
- `frontend/src/app/app/leads/[id]/page.tsx` — passar props loadMore/loadingMore/total/hasMore
- `frontend/src/components/leads/lead-app.css` — estilo `.la-master-load-more`

---

## Task 1: Refatorar `fetchLeads` pra aceitar page + append

**Files:**
- Modify: `frontend/src/components/leads/use-lead-app.ts`

- [ ] **Step 1: Adicionar constante e estados novos**

Em `use-lead-app.ts`, após `const [statusFilter, setStatusFilter] = useState("all");` (linha 61), adicionar:

```ts
  const PER_PAGE = 30;
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);
```

- [ ] **Step 2: Refatorar fetchLeads com params page + append**

Substituir o `fetchLeads` inteiro (linhas 68-80) por:

```ts
  const fetchLeads = useCallback((
    searchTerm: string,
    filter: string,
    pageNum: number,
    append: boolean,
  ) => {
    const params: Record<string, string> = {
      per_page: String(PER_PAGE),
      page: String(pageNum),
      order_by: "score_desc",
    };
    if (searchTerm) params.search = searchTerm;
    if (filter === "hot") params.score_min = "80";
    else if (filter === "enriched") params.status = "enriched";
    else if (filter === "new") params.status = "scraped";

    if (append) setLoadingMore(true);
    else setLeadsLoading(true);

    getLeads(params)
      .then((res) => {
        const items = res.items.map(mapLeadToItem);
        setLeads((prev) => (append ? [...prev, ...items] : items));
        setTotal(res.total);
        setPage(pageNum);
      })
      .catch(() => {})
      .finally(() => {
        if (append) setLoadingMore(false);
        else setLeadsLoading(false);
      });
  }, []);
```

- [ ] **Step 3: Atualizar callsites de reset**

Substituir:

```ts
  // Initial fetch
  useEffect(() => { fetchLeads("", "all"); }, [fetchLeads]); // eslint-disable-line react-hooks/set-state-in-effect -- intentional: fetch on mount
```

por:

```ts
  // Initial fetch
  useEffect(() => { fetchLeads("", "all", 1, false); }, [fetchLeads]); // eslint-disable-line react-hooks/set-state-in-effect -- intentional: fetch on mount
```

Substituir `handleSearch`:

```ts
  const handleSearch = useCallback((q: string) => {
    setSearch(q);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchLeads(q, statusFilter), 300);
  }, [fetchLeads, statusFilter]);
```

por:

```ts
  const handleSearch = useCallback((q: string) => {
    setSearch(q);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchLeads(q, statusFilter, 1, false), 300);
  }, [fetchLeads, statusFilter]);
```

Substituir `handleFilter`:

```ts
  const handleFilter = useCallback((f: string) => {
    setStatusFilter(f);
    fetchLeads(search, f);
  }, [fetchLeads, search]);
```

por:

```ts
  const handleFilter = useCallback((f: string) => {
    setStatusFilter(f);
    fetchLeads(search, f, 1, false);
  }, [fetchLeads, search]);
```

Substituir `refreshLeads`:

```ts
  const refreshLeads = useCallback(() => {
    fetchLeads(search, statusFilter);
  }, [fetchLeads, search, statusFilter]);
```

por:

```ts
  const refreshLeads = useCallback(() => {
    fetchLeads(search, statusFilter, 1, false);
  }, [fetchLeads, search, statusFilter]);
```

- [ ] **Step 4: Adicionar loadMore**

Após `refreshLeads`, adicionar:

```ts
  const loadMore = useCallback(() => {
    fetchLeads(search, statusFilter, page + 1, true);
  }, [fetchLeads, search, statusFilter, page]);
```

- [ ] **Step 5: Expor na return**

Substituir o return final (linhas 161-180) por:

```ts
  return {
    activeTab,
    setActiveTab,
    leads,
    leadsLoading,
    loadingMore,
    lead,
    leadLoading,
    leadError,
    messages,
    currentIndex,
    total,
    hasMore: leads.length < total,
    search,
    handleSearch,
    statusFilter,
    handleFilter,
    loadMore,
    refreshLead,
    refreshLeads,
    refreshMessages,
  };
```

- [ ] **Step 6: Lint**

```bash
cd frontend && npm run lint
```

Expected: sem erros em `use-lead-app.ts`.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/leads/use-lead-app.ts
git commit -m "feat(leads): add pagination state to use-lead-app hook

Introduce page, total, loadingMore, hasMore. fetchLeads accepts
page+append params. Search/filter reset to page 1; loadMore
concatenates. per_page dropped from 100 to 30.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Adicionar botão "Carregar mais" na master list

**Files:**
- Modify: `frontend/src/components/leads/la-master.tsx`

- [ ] **Step 1: Expandir props**

Em `la-master.tsx`, substituir:

```ts
interface LaMasterProps {
  activeId: number;
  onSelect: (id: number) => void;
  leads: LeadListItem[];
  loading?: boolean;
  search: string;
  onSearch: (q: string) => void;
  statusFilter: string;
  onFilter: (f: string) => void;
}
```

por:

```ts
interface LaMasterProps {
  activeId: number;
  onSelect: (id: number) => void;
  leads: LeadListItem[];
  loading?: boolean;
  loadingMore?: boolean;
  hasMore?: boolean;
  total?: number;
  onLoadMore?: () => void;
  search: string;
  onSearch: (q: string) => void;
  statusFilter: string;
  onFilter: (f: string) => void;
}
```

- [ ] **Step 2: Receber props na função**

Substituir:

```ts
export function LaMaster({ activeId, onSelect, leads, loading, search, onSearch, statusFilter, onFilter }: LaMasterProps) {
```

por:

```ts
export function LaMaster({
  activeId,
  onSelect,
  leads,
  loading,
  loadingMore,
  hasMore,
  total,
  onLoadMore,
  search,
  onSearch,
  statusFilter,
  onFilter,
}: LaMasterProps) {
```

- [ ] **Step 3: Usar total (não leads.length) no contador**

Substituir:

```tsx
          <div className="la-master-count">{leads.length}</div>
```

por:

```tsx
          <div className="la-master-count">{total ?? leads.length}</div>
```

- [ ] **Step 4: Renderizar botão "Carregar mais" no final da lista**

No `<div className="la-master-body">`, logo após o `groups.map(...)` fechar (antes do `</div>` que fecha `la-master-body`), adicionar:

```tsx
        {!loading && hasMore && onLoadMore && (
          <div className="la-master-load-more">
            <button
              className="btn btn-ghost btn-sm"
              onClick={onLoadMore}
              disabled={loadingMore}
            >
              {loadingMore ? "Carregando…" : `Carregar mais (${(total ?? 0) - leads.length} restantes)`}
            </button>
          </div>
        )}
```

Bloco final de `la-master-body` deve ficar assim:

```tsx
      <div className="la-master-body">
        {loading ? (
          // ... skeleton ...
        ) : groups.length === 0 ? (
          // ... empty state ...
        ) : (
          groups.map((g) => (
            // ... items ...
          ))
        )}
        {!loading && hasMore && onLoadMore && (
          <div className="la-master-load-more">
            <button
              className="btn btn-ghost btn-sm"
              onClick={onLoadMore}
              disabled={loadingMore}
            >
              {loadingMore ? "Carregando…" : `Carregar mais (${(total ?? 0) - leads.length} restantes)`}
            </button>
          </div>
        )}
      </div>
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/leads/la-master.tsx
git commit -m "feat(leads): add 'Carregar mais' button to master list

Renders at end of list when hasMore. Shows remaining count.
Disabled during loadingMore. Counter in header now reflects
backend total, not just loaded length.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Passar props novas do page.tsx

**Files:**
- Modify: `frontend/src/app/app/leads/[id]/page.tsx`

- [ ] **Step 1: Destructurar estados novos do hook**

Em `page.tsx`, substituir o destructuring atual (linhas 85-103) por:

```ts
  const {
    activeTab,
    setActiveTab,
    leads,
    leadsLoading,
    loadingMore,
    lead: rawLead,
    leadLoading,
    leadError,
    messages,
    currentIndex,
    total,
    hasMore,
    search,
    handleSearch,
    statusFilter,
    handleFilter,
    loadMore,
    refreshLead,
    refreshLeads,
    refreshMessages,
  } = useLeadApp(activeId);
```

- [ ] **Step 2: Passar pro LaMaster**

Substituir o `<LaMaster>` (linhas 188-197) por:

```tsx
      <LaMaster
        activeId={activeId}
        onSelect={(id) => router.push(`/app/leads/${id}`)}
        leads={leads}
        loading={leadsLoading}
        loadingMore={loadingMore}
        hasMore={hasMore}
        total={total}
        onLoadMore={loadMore}
        search={search}
        onSearch={handleSearch}
        statusFilter={statusFilter}
        onFilter={handleFilter}
      />
```

- [ ] **Step 3: Lint**

```bash
cd frontend && npm run lint
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/app/leads/[id]/page.tsx
git commit -m "feat(leads): wire pagination props from hook to LaMaster

Pass loadingMore, hasMore, total, loadMore through to enable
'Carregar mais' button.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Estilos CSS pro botão "Carregar mais"

**Files:**
- Modify: `frontend/src/components/leads/lead-app.css`

- [ ] **Step 1: Adicionar classe .la-master-load-more**

Ao final de `lead-app.css`, adicionar:

```css
.la-master-load-more {
  padding: 16px 12px;
  display: flex;
  justify-content: center;
  border-top: 1px solid var(--line-1);
  margin-top: 8px;
}

.la-master-load-more .btn {
  min-width: 180px;
  justify-content: center;
  font-size: 12px;
}
```

- [ ] **Step 2: Verify visual**

```bash
cd frontend && npm run dev
```

Criar (ou já ter) >30 leads no banco. Abrir `/app/leads/<id>`. Verificar:
- Master list mostra primeiros 30
- No rodapé: "Carregar mais (N restantes)"
- Clicar → carrega próximos 30, acumula, scroll preserva
- Botão desaparece quando chega no total
- Header mostra `total` completo (não 30)

Casos de teste:
- Busca "salão" com muitos resultados → loadMore funciona no filtro
- Filtro "Hot" + loadMore → preserva filtro

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/leads/lead-app.css
git commit -m "style(leads): style for 'Carregar mais' button

Centered, top border, consistent with master list rhythm.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Final verification

- [ ] **Step 1: Build**

```bash
cd frontend && npm run build
```

Expected: build passa.

- [ ] **Step 2: Smoke test full**

- Primeiro load: 30 leads
- Clicar "Carregar mais" 2x: 90 leads acumulados
- Buscar: reset pra 30
- Filtro Hot: reset pra 30, botão se `total > 30`
- J/K nav: navega entre leads carregados, para no fim (user precisa clicar Carregar mais)
