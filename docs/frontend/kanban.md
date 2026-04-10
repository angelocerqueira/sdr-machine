# Kanban Board

Documentação técnica do board de Kanban para visualização e gestão do pipeline de leads.

---

## 1. Visão Geral

O Kanban board é a interface principal de gestão de leads do SDR Machine. Cada coluna representa um estágio do pipeline, e leads são representados como cards arrastáveis. A página `/kanban` combina dois componentes principais:

- **PipelineControls** -- barra superior com botões para disparar as 4 fases do pipeline.
- **KanbanBoard** -- board com colunas, filtros, ordenação e painel lateral de detalhes.

```tsx
// app/(main)/kanban/page.tsx
export default function KanbanPage() {
  return (
    <div className="space-y-6">
      <PipelineControls onJobDone={() => window.location.reload()} />
      <KanbanBoard />
    </div>
  );
}
```

Quando um job finaliza (`onJobDone`), a página inteira recarrega via `window.location.reload()` para refletir os novos dados.

---

## 2. Colunas

As colunas do Kanban são definidas pela constante `KANBAN_COLUMNS` em `frontend/src/lib/types.ts`:

```ts
export const KANBAN_COLUMNS = [
  { id: "scraped",        label: "Scrapeado" },
  { id: "enriched",       label: "Analisado" },
  { id: "disqualified",   label: "Desqualificado" },
  { id: "failed",         label: "Falhou" },
  { id: "lp_generated",   label: "LP Gerada" },
  { id: "outreach_ready", label: "Msg Pronta" },
  { id: "outreach_sent",  label: "Msg Enviada" },
  { id: "responded",      label: "Respondeu" },
  { id: "in_call",        label: "Em Call" },
  { id: "closed",         label: "Fechado" },
  { id: "delivered",      label: "Entregue" },
] as const;
```

### Significado de cada coluna

| id | label | Descrição |
|----|-------|-----------|
| `scraped` | Scrapeado | Lead recém-capturado do Google Maps. Aguarda enriquecimento. |
| `enriched` | Analisado | Lead com análise de site concluída (SSL, responsividade, PageSpeed, diagnóstico). |
| `disqualified` | Desqualificado | Lead descartado pelo diagnóstico de IA (ex: já tem site profissional, empresa grande). |
| `failed` | Falhou | Erro em alguma fase do pipeline. |
| `lp_generated` | LP Gerada | Landing page personalizada gerada via Claude API. |
| `outreach_ready` | Msg Pronta | 3 mensagens de WhatsApp geradas e prontas para envio. |
| `outreach_sent` | Msg Enviada | Mensagem inicial enviada ao lead. |
| `responded` | Respondeu | Lead respondeu à mensagem. |
| `in_call` | Em Call | Reunião marcada com o lead. |
| `closed` | Fechado | Negócio fechado. |
| `delivered` | Entregue | Serviço entregue ao cliente. |

### Estilo visual

As colunas `disqualified` e `failed` recebem estilo diferenciado:

```tsx
className={`... ${
  isOver
    ? "border-accent/40 bg-accent-subtle"        // Drop target ativo
    : id === "disqualified" || id === "failed"
    ? "border-danger/20 bg-danger/[0.02]"         // Colunas de "problema"
    : "border-border"                              // Colunas normais
}`}
```

O badge de contagem também muda de cor:

```tsx
className={`... ${
  total > 0 && (id === "disqualified" || id === "failed")
    ? "bg-danger/10 text-danger"        // Vermelho para colunas de problema
    : total > 0
    ? "bg-accent-subtle text-accent"    // Verde para colunas com leads
    : "bg-surface-raised text-text-muted"  // Neutro para colunas vazias
}`}
```

---

## 3. Drag and Drop

O board usa `@dnd-kit/core` para drag-and-drop. A implementação envolve três camadas:

### DndContext (KanbanBoard)

O `KanbanBoard` envolve todas as colunas em um `DndContext`:

```tsx
const sensors = useSensors(
  useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
);

<DndContext sensors={sensors} collisionDetection={pointerWithin} onDragEnd={handleDragEnd}>
  <div className="flex gap-3 overflow-x-auto pb-4">
    {KANBAN_COLUMNS.map((col) => (
      <KanbanColumn key={col.id} id={col.id} ... />
    ))}
  </div>
</DndContext>
```

- **Sensor:** `PointerSensor` com `distance: 8` -- o drag só inicia depois de mover 8px, evitando conflito com cliques.
- **Collision detection:** `pointerWithin` -- detecta em qual coluna o ponteiro está durante o drag.

### Droppable Columns (KanbanColumn)

Cada coluna se registra como drop zone via `useDroppable`:

```tsx
const { setNodeRef, isOver } = useDroppable({ id });
// id = status da coluna (ex: "enriched")
```

O `isOver` controla o feedback visual (borda accent + fundo highlight).

### Draggable Cards (KanbanCard)

Cada card se registra como draggable via `useDraggable`:

```tsx
const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
  id: lead.id,
  data: { lead },  // Dados do lead acessíveis no handleDragEnd
});
```

O `transform` é aplicado via `CSS.Transform.toString(transform)` para posicionar o card durante o drag. O `isDragging` ativa a classe `kanban-card-dragging` (definida em `globals.css`).

### handleDragEnd

Quando o drop acontece, o `KanbanBoard` processa a mudança:

```tsx
const handleDragEnd = async (event: DragEndEvent) => {
  const { active, over } = event;
  if (!over) return;

  const lead = active.data.current?.lead as Lead | undefined;
  const newStatus = over.id as string;

  if (!lead || lead.status === newStatus) return;

  const sourceStatus = lead.status;

  // 1. Optimistic count update
  setCounts((prev) => ({
    ...prev,
    [sourceStatus]: Math.max(0, (prev[sourceStatus] || 0) - 1),
    [newStatus]: (prev[newStatus] || 0) + 1,
  }));

  try {
    // 2. API call
    await updateLead(lead.id, { status: newStatus });
  } catch {
    // 3. Rollback on failure
    setCounts((prev) => ({
      ...prev,
      [sourceStatus]: (prev[sourceStatus] || 0) + 1,
      [newStatus]: Math.max(0, (prev[newStatus] || 0) - 1),
    }));
  }

  // 4. Refresh both columns
  setRefreshKeys((prev) => ({
    ...prev,
    [sourceStatus]: (prev[sourceStatus] || 0) + 1,
    [newStatus]: (prev[newStatus] || 0) + 1,
  }));
};
```

---

## 4. Filtros

A barra de filtros no topo do board oferece 4 controles:

### Campo de busca (search)

```tsx
<input
  type="text"
  placeholder="Buscar por nome ou telefone..."
  value={search}
  onChange={(e) => setSearch(e.target.value)}
/>
```

Busca textual por nome ou telefone do lead. O valor é enviado como `?search=...` para a API.

### Select de nicho (filterNicho)

```tsx
<select value={filterNicho} onChange={(e) => setFilterNicho(e.target.value)}>
  <option value="">Todos nichos</option>
  {nichos.map((n) => <option key={n} value={n}>{n}</option>)}
</select>
```

Valores carregados via `getLeadFilters()` que retorna os nichos únicos existentes no banco.

### Select de cidade (filterCidade)

Mesmo padrão do nicho, com cidades únicas.

### Score mínimo (filterScoreMin)

```tsx
<input
  type="number"
  placeholder="Score min"
  value={filterScoreMin}
  onChange={(e) => setFilterScoreMin(e.target.value)}
/>
```

Filtra leads com `opportunity_score >= valor`. Enviado como `?score_min=...`.

### Propagação dos filtros

Todos os filtros são propagados para:

1. **`getLeadCounts(params)`** -- para atualizar as contagens no header das colunas.
2. **Cada `KanbanColumn`** -- via props `filterNicho`, `filterCidade`, `filterScoreMin`, `search`.

Cada coluna constrói os query params:

```tsx
const buildParams = useCallback(() => {
  const params: Record<string, string> = {
    status: id,
    per_page: String(PER_PAGE),  // PER_PAGE = 20
  };
  if (filterNicho) params.nicho = filterNicho;
  if (filterCidade) params.cidade = filterCidade;
  if (filterScoreMin) params.score_min = filterScoreMin;
  if (search) params.search = search;
  params.order_by = orderBy || "score_desc";
  return params;
}, [id, filterNicho, filterCidade, filterScoreMin, search, orderBy]);
```

Mudanças nos filtros disparam um `useEffect` que recarrega a primeira página de cada coluna.

---

## 5. Sorting

O select de ordenação oferece 5 opções:

```tsx
<select value={orderBy} onChange={(e) => setOrderBy(e.target.value)}>
  <option value="score_desc">Maior score</option>
  <option value="score_asc">Menor score</option>
  <option value="created_desc">Mais recente</option>
  <option value="updated_desc">Atualizado recente</option>
  <option value="name_asc">Nome A-Z</option>
</select>
```

O valor é enviado como `?order_by=...` na query de cada coluna. A ordenação default é `score_desc` (leads com maior score de oportunidade primeiro).

A ordenação é processada no backend -- o frontend apenas envia o parâmetro e renderiza os resultados na ordem recebida.

---

## 6. Optimistic Updates

O drag-and-drop implementa update otimista em duas camadas:

### Camada 1: Contagens

Antes de chamar a API, as contagens das colunas origem e destino são atualizadas imediatamente:

```ts
setCounts((prev) => ({
  ...prev,
  [sourceStatus]: Math.max(0, (prev[sourceStatus] || 0) - 1),
  [newStatus]: (prev[newStatus] || 0) + 1,
}));
```

Se a API falhar, os contadores são revertidos:

```ts
setCounts((prev) => ({
  ...prev,
  [sourceStatus]: (prev[sourceStatus] || 0) + 1,
  [newStatus]: Math.max(0, (prev[newStatus] || 0) - 1),
}));
```

### Camada 2: Dados das colunas

Independente de sucesso ou falha da API, ambas as colunas afetadas são forçadas a recarregar seus dados via `refreshKeys`:

```ts
setRefreshKeys((prev) => ({
  ...prev,
  [sourceStatus]: (prev[sourceStatus] || 0) + 1,
  [newStatus]: (prev[newStatus] || 0) + 1,
}));
```

Cada `KanbanColumn` observa `refreshKey` no `useEffect` de carregamento:

```tsx
useEffect(() => {
  // ... carrega primeira página
}, [buildParams, refreshKey, id]);
```

Incrementar o `refreshKey` força o efeito a rodar novamente, recarregando os leads da coluna do backend.

---

## 7. Lead Sheet

Clicar em um card do Kanban abre o `LeadSheet` -- um painel lateral que desliza da direita.

### Fluxo de abertura

1. `KanbanCard` chama `onSelect(lead.id)` ao clicar.
2. `KanbanColumn` propaga via prop `onSelectLead`.
3. `KanbanBoard` atualiza `selectedLeadId` state.
4. `LeadSheet` renderiza quando `leadId !== null`.

```tsx
// No KanbanBoard:
<LeadSheet leadId={selectedLeadId} onClose={() => setSelectedLeadId(null)} />
```

### Conteúdo do painel

O painel exibe, de cima para baixo:

1. **Header fixo:** badge de score, nome, nicho/cidade, botão fechar.
2. **Grid de informações:** telefone, rating, website, status.
3. **Gaps detectados:** pills com `opportunity_reasons`.
4. **Fontes de enriquecimento:** lista de providers com status (ok/skipped/error).
5. **Diagnóstico:** `ServiceLevelTabs` (se `service_levels` presente) ou `DiagnosticPanel` (legacy).
6. **Botões de ação:** contextual ao status do lead (Enriquecer, Gerar LP, etc.).
7. **Preview da LP:** iframe com a LP gerada, link "Tela cheia".
8. **Versões da LP:** lista de versões com botão para ativar versões anteriores.
9. **Mensagens de outreach:** lista de mensagens com tipo, texto e link WhatsApp.

### Fechamento

- Clicar no backdrop (overlay escuro atrás do painel).
- Clicar no botão X no header.
- Pressionar `Escape`.

### Score color bar

O footer do painel tem uma barra de 2px colorida pelo score do lead:

```tsx
<div className={`h-0.5 w-full shrink-0 ${
  score >= 60 ? "bg-accent"     // Verde
  : score >= 40 ? "bg-warning"  // Amarelo
  : "bg-border"                 // Neutro
}`} />
```

---

## 8. Status Counts

O header de cada coluna exibe o total de leads naquele status.

### Carregamento

O `KanbanBoard` chama `getLeadCounts(params)` no mount e quando filtros mudam. A resposta é um `Record<string, number>`:

```ts
// Exemplo de resposta:
{ "scraped": 42, "enriched": 15, "lp_generated": 8, "outreach_ready": 3 }
```

Os counts são passados para cada `KanbanColumn` via prop `count`:

```tsx
{KANBAN_COLUMNS.map((col) => (
  <KanbanColumn
    key={col.id}
    id={col.id}
    label={col.label}
    count={counts[col.id] || 0}
    ...
  />
))}
```

### Sincronização

A `KanbanColumn` mantém um state `total` que sincroniza com duas fontes:

1. **Prop `count` do pai:** sincronizado via `useEffect`:
   ```tsx
   useEffect(() => {
     setTotal(count);
   }, [count]);
   ```

2. **Resposta do `getLeads`:** quando a coluna carrega seus leads, atualiza `total` com o valor real da API:
   ```tsx
   getLeads(params).then((data) => {
     setLeads(data.items);
     setTotal(data.total);  // Corrige com o valor real
   });
   ```

### Scroll infinito e contagens

A coluna exibe `PER_PAGE = 20` leads por vez. O `hasMore` é calculado como `leads.length < total`, e o scroll infinito carrega páginas adicionais quando o usuário se aproxima do final da lista (< 80px do fundo):

```tsx
const handleScroll = useCallback(() => {
  const el = scrollRef.current;
  if (!el) return;
  const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  if (nearBottom) loadMore();
}, [loadMore]);
```

O `loadMore` carrega a próxima página e concatena com os leads existentes:

```tsx
getLeads(params).then((data) => {
  setLeads((prev) => [...prev, ...data.items]);
  setTotal(data.total);
  setPage(nextPage);
});
```
