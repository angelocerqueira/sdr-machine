# Lead App — Paginação "Carregar mais" (Spec 2 de 3)

**Data:** 2026-04-20
**Escopo:** substituir `per_page: 100` hardcoded por paginação incremental na master list.
**Specs relacionados:** `2026-04-20-leads-ui-bugs-design.md`, `2026-04-20-leads-marketing-diagnostic-design.md`.

## Contexto

`use-lead-app.ts:69` pede `per_page=100` hardcoded. Quando o banco cresce acima de 100 leads qualificados:
- Master list trunca silenciosamente (sem aviso)
- Busca/filtro aparentam "não funcionar" porque o lead pode estar além do limite
- J/K nav só alcança os 100 primeiros

Backend já suporta paginação completa (`page`, `per_page`, `total`) em `routers/leads.py:107-114`.

## Objetivo

Permitir que o usuário carregue leads além do primeiro batch via botão "Carregar mais". Sem regressão no comportamento atual quando a lista é pequena.

## Abordagem

**Estado no hook `use-lead-app.ts`:**

```ts
const PER_PAGE = 30;
const [page, setPage] = useState(1);
const [total, setTotal] = useState(0);
const [hasMore, setHasMore] = useState(false);
```

`fetchLeads(searchTerm, filter, pageNum, append)`:
- Se `append=false`: substitui `leads` (reset — primeira página, busca, ou filtro)
- Se `append=true`: concatena ao estado existente
- Atualiza `total` do response
- `setHasMore(accumulated.length < res.total)`

**Três gatilhos de reset (`append=false`):**
1. Mount inicial
2. `handleSearch` (debounced 300ms)
3. `handleFilter`

**Um gatilho de append (`append=true`):**
- `loadMore()` exposto pelo hook, chamado pelo botão em `LaMaster`

**UI `la-master.tsx`:**

No final do `<div className="la-master-body">`, após todos os grupos:

```tsx
{hasMore && !loading && (
  <div className="la-master-load-more">
    <button
      className="btn btn-ghost btn-sm"
      onClick={onLoadMore}
      disabled={loadingMore}
    >
      {loadingMore ? "Carregando…" : `Carregar mais (${total - leads.length} restantes)`}
    </button>
  </div>
)}
```

Estado `loadingMore` separado de `loading` — spinner skeleton só mostra no fetch inicial, não no append.

## Mudanças

### `frontend/src/components/leads/use-lead-app.ts`

Substituir `fetchLeads` atual por versão com `page` e `append`:

```ts
const PER_PAGE = 30;
const [page, setPage] = useState(1);
const [total, setTotal] = useState(0);
const [loadingMore, setLoadingMore] = useState(false);

const fetchLeads = useCallback((
  searchTerm: string,
  filter: string,
  pageNum: number,
  append: boolean
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
      setLeads((prev) => append ? [...prev, ...items] : items);
      setTotal(res.total);
      setPage(pageNum);
    })
    .catch(() => {})
    .finally(() => {
      if (append) setLoadingMore(false);
      else setLeadsLoading(false);
    });
}, []);

const loadMore = useCallback(() => {
  fetchLeads(search, statusFilter, page + 1, true);
}, [fetchLeads, search, statusFilter, page]);
```

Resets mudam pra `fetchLeads(..., 1, false)`. Retornar `loadMore`, `loadingMore`, `total`, `hasMore` (derivado: `leads.length < total`).

### `frontend/src/components/leads/la-master.tsx`

- Adicionar props `onLoadMore`, `loadingMore`, `hasMore`, `total`
- Renderizar botão "Carregar mais" no final do `la-master-body`

### `frontend/src/app/app/leads/[id]/page.tsx`

- Destructar `loadMore`, `loadingMore`, `hasMore` do hook e passar ao `<LaMaster>`

### `frontend/src/components/leads/lead-app.css`

- Adicionar `.la-master-load-more` (padding centralizado, borda superior leve)

## Interação com J/K nav

`use-lead-app.ts:143-155` — navegação de teclado opera sobre `leads` carregados. Com paginação, atingir o fim (`currentIndex === leads.length - 1`) não faz nada. **Aceitável** — usuário clica "Carregar mais" explicitamente.

Alternativa descartada: auto-trigger `loadMore` quando pressionar J no último lead. Complicou pouco valor.

## Interação com busca/filtro

Quando `handleSearch` ou `handleFilter` rodam:
- `setPage(1)` implícito via `fetchLeads(..., 1, false)`
- `leads` é substituído (não appended)
- `total` reflete resultado filtrado — "Carregar mais" opera sobre o filtro ativo

## Arquivos afetados

| Arquivo | Linhas alteradas |
|---|---|
| `frontend/src/components/leads/use-lead-app.ts` | +~30 (estado page/total, loadMore) |
| `frontend/src/components/leads/la-master.tsx` | +3 props, +6 linhas JSX |
| `frontend/src/app/app/leads/[id]/page.tsx` | +3 props destructured |
| `frontend/src/components/leads/lead-app.css` | +~8 linhas CSS |

## Critérios de aceite

- Primeira renderização mostra até 30 leads (antes: 100)
- Se `total > 30`, botão "Carregar mais (N restantes)" aparece no fim da lista
- Clicar carrega próximos 30 leads e anexa à lista atual sem resetar scroll
- Busca/filtro resetam pra página 1
- `hasMore=false` esconde o botão
- `total` do contador da header (`la-master-count`) reflete o `total` do backend (não só `leads.length`)

## Fora de escopo

- Scroll infinito automático
- Virtualização da lista (react-window etc.) — só se estourar performance em 500+ leads
- Paginação explícita (< 1 2 3 >)
