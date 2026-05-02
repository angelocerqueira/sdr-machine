# Pipeline Redesign — Design Spec

**Data:** 2026-05-02
**Status:** Proposto (aguarda aprovação para implementação em PR única)
**Autor:** Angelo + Claude
**Protótipo:** `~/Downloads/SDR (1)/Pipeline.html` (+ assets `pipeline-*.jsx`, `pipeline.css`, `pipeline-data.jsx`)

---

## 1. Motivação

A tela `/app/pipeline` hoje funciona — multi-select, bulk actions, kanban, tabela, polling, banner de filtros, funnel — mas a hierarquia visual está quebrada. O screenshot que abriu este redesign mostrou 4 problemas simultâneos:

1. **Muralha de filtros sem hierarquia.** 9 selects + 2 inputs + busca + toggle de view, todos no mesmo nível visual, ocupando duas linhas. O olho não tem onde pousar primeiro.
2. **Funil pequeno e apagado.** Caixinhas sem progress bar, sem taxa de conversão entre etapas, posicionado depois do toolbar (deveria ancorar a leitura da página). Não responde "quantos leads em cada estágio?" rápido.
3. **Tabela sem cor e sem sinal.** Score é número cinza, sinais ("sem site", "sem WhatsApp") aparecem como tags mas sem priorização. O operador olha 50 linhas e não consegue identificar o lead "quente" em 2s.
4. **Botão "Colunas" e ações flutuando soltos.** Header da página + PipelineControls + Toolbar + FiltrosAtivosBanner + Funnel formam 5 blocos verticais com pesos similares — falta um "topo de página" que diga o que fazer agora.

O protótipo em `Pipeline.html` resolve os 4 com decisões de DS já validadas:

- Page header com **eyebrow + h1 + subtítulo + ações primárias** (Exportar, Filtros avançados, Enriquecer 391).
- Funnel grande com **barras de progresso por etapa** e **taxa de conversão entre setas**.
- Toolbar de filtros baseada em **chips compactos** (Todos os nichos ▾, Cidades ▾, Score ▾, Mais filtros [3]) + busca com `⌘K` + sort + view toggle.
- Cards de kanban com **rail colorido lateral**, score badge proeminente, sinais com tone (danger/warn/ok), quick actions on hover.
- Tabela com **score colorido + barra**, niche chip, sinais, ícones de contato (phone/mail/wa) e linha realçada para `score ≥ 80`.

Este spec descreve como portar essas decisões para o repo preservando 100% do comportamento de bulk + filtros + polling já em produção.

## 2. Decisões travadas

Confirmadas pelo usuário antes da escrita do spec:

| # | Decisão | Resposta do usuário |
|---|---------|---------------------|
| 1 | Implementar em PR única ou faseado? | "pode ser unica" |
| 2 | Wiring das quick actions: phone/mail/sparkle/more? | "tel: abre whatsapp (wa.me/...). mail, temos que pensar se isso deveria iniciar a cadência de email via resend, deixa como TODO por hora. ok 4. ok 5. sim. melhorias visuais." |
| 3 | Hot lead highlight (score ≥ 80) sempre ligado? | "ok" (sim, sempre ligado, sem toggle) |
| 4 | Density toggle (compact/comfortable)? | "ok" (sim, com persistência localStorage) |
| 5 | Comportamento preservado (multi-select, modais, polling, etc.)? | "sim. melhorias visuais" |

Decisões derivadas (não levantadas mas implícitas):

- **Não trazer** o sidebar redesign do protótipo (`PlSidebar` em `pipeline-funnel.jsx`). O `AppSidebar` atual é mobile-first com avatar dropdown; o protótipo é só estético e simplório.
- **Não trazer** o `PlTopbar` do protótipo. O topbar do app já existe em `app/app/layout.tsx` com busca global + theme toggle.
- **Não trazer** `PIPELINE_TWEAK_DEFAULTS` (modo operator/funnel-first, painel de tweaks). Fora de escopo.
- **Trazer** todo o resto: page header, funnel, toolbar, kanban card, kanban column, tabela, density toggle, hot highlight.

## 3. Arquitetura

### 3.1 Mapping protótipo → repo

| Protótipo (`~/Downloads/SDR (1)/`) | Existe no repo? | Ação |
|---|---|---|
| `PlPageHeader` (em `pipeline-funnel.jsx`) | Não — header inline em `app/app/pipeline/page.tsx` linhas 98-105 | Criar `pipeline-page-header.tsx` |
| `PlFunnel` | Sim, `components/pipeline/pipeline-funnel.tsx` | Reescrever (visual + progress bars + taxas) |
| `PlToolbar` | Sim, `components/pipeline/pipeline-toolbar.tsx` | Reescrever (chips + Mais filtros expandable + sort + view toggle) |
| `PlKanbanCard` | Sim, `components/kanban-card.tsx` (usado por `kanban-board.tsx`) | Reescrever (rail + score badge + sinais + actions) |
| `PlKanbanColumn` | Implícito em `components/kanban-board.tsx` | Reescrever header de coluna (pip + count badge + more) |
| `PlKanban` | Sim, `components/pipeline/pipeline-kanban.tsx` (wrapper de `kanban-board.tsx`) | Manter wrapper, atualizar `kanban-board.tsx` |
| `PlTable` | Sim, `components/pipeline/pipeline-table.tsx` | Reescrever cells (score colorido, niche chip, sinais, contact icons, hot row) |
| `PlSidebar` / `PlTopbar` | N/A | **Ignorar** (já existe `AppSidebar` + topbar do app) |
| `pipeline-data.jsx` (sinais, helpers) | Parcial — `lib/types.ts` tem `KANBAN_COLUMNS` | Adicionar `lib/pipeline-signals.ts` (mapper + tones) |

### 3.2 Componentes preservados sem mudança

Estes ficam intocados. O redesign não os afeta:

- `bulk-action-bar.tsx`, `bulk-confirm-modal.tsx`, `bulk-result-modal.tsx`, `classify-modal.tsx`
- `column-visibility-menu.tsx`, `select-all-banner.tsx`
- `filtros-ativos-banner.tsx` (banner de filtros ativos com botão Limpar)
- `use-bulk-selection.ts`, `use-pipeline-counts.ts`
- `pipeline-controls.tsx`, `job-progress.tsx`
- Toast system (`components/ui/toast.tsx`), focus trap, polling, telemetria

### 3.3 Estratégia de CSS

O protótipo usa `pipeline.css` (~831 linhas) com namespace `pl-*`. Duas opções:

**A) Tudo em Tailwind utility classes.** Pró: consistente com o resto do repo, sem CSS file novo. Contra: ~30 componentes virariam tijolões de className; algumas combinações (ex: `pl-tbl-score-bar` com gradient + width dinâmico) são feias em Tailwind.

**B) Portar `pipeline.css` para `frontend/src/components/pipeline/pipeline.css`** importado uma vez no `pipeline/page.tsx`, com `pl-*` namespace mantido. Pró: 1:1 com o protótipo, fácil de auditar. Contra: introduz arquivo CSS novo num repo onde tudo é Tailwind v4.

**Decisão: B — portar CSS.** Motivos: Lead App já usa o mesmo padrão (`components/leads/lead-app.css`, ~2000 linhas, importado uma vez). Preserva fidelidade ao protótipo. Mantém Tailwind v4 para o resto do app. CSS usa as CSS variables já definidas em `globals.css` (não introduz tokens novos).

**Caveat:** Adaptar nomes de variáveis CSS do protótipo para os do projeto. O protótipo usa `--surface-raised` enquanto o repo usa `--paper-2` mapeado via `--surface-raised` no `globals.css`. Verifiquei via grep (já confirmado nas instruções): `--score-high`, `--score-mid`, `--score-low`, `--ok`, `--warn`, `--danger`, `--ok-soft`, `--warn-soft`, `--danger-soft`, `--accent-soft` existem todos. Se algum não existir 1:1, adicionar alias no início do `pipeline.css`.

### 3.4 Estrutura final de arquivos

```
frontend/src/
├── app/app/pipeline/
│   └── page.tsx                          # Refatorado (header → componente; resto igual)
├── components/pipeline/
│   ├── pipeline.css                      # NOVO (port de pipeline.css do protótipo)
│   ├── pipeline-page-header.tsx          # NOVO (eyebrow + h1 + sub + ações)
│   ├── pipeline-funnel.tsx               # Reescrito
│   ├── pipeline-toolbar.tsx              # Reescrito (chips + expandable + density)
│   ├── pipeline-table.tsx                # Reescrito (cells redesenhadas)
│   ├── pipeline-kanban.tsx               # Wrapper (passa props novos pro board)
│   ├── use-pipeline-density.ts           # NOVO (hook localStorage compact/comfortable)
│   ├── (resto igual)                     # bulk-*, modals, banners, hooks
├── components/
│   ├── kanban-board.tsx                  # Atualizado (header de coluna + passa density/hot)
│   ├── kanban-card.tsx                   # Reescrito (rail + score badge + sinais + actions)
└── lib/
    └── pipeline-signals.ts               # NOVO (deriva sinais de opportunity_reasons)
```

## 4. Componentes em detalhe

### 4.1 `PipelinePageHeader`

**Visual.** Layout em 2 linhas:

```
SDR · PIPELINE                                    [Exportar] [Filtros avançados] [▶ Enriquecer 391]
Pipeline
391 leads scrapeados, esperando análise. Conversão atual: 0,8% · próximo passo: enriquecer.
```

- Eyebrow `t-eyebrow` (mono uppercase, 11px, text-muted)
- H1 `text-2xl font-bold tracking-tight font-[family-name:var(--font-heading)]`
- Sub: pt-BR, dinâmico baseado em `counts` (próximo passo = primeiro estágio com leads)
- Ações:
  - **Exportar** (`btn-secondary`) — abre menu/dropdown ou trigger direto pra `exportToCSV()`. Wireup: usar a função existente em `pipeline-table.tsx` linha que já implementa CSV export (extrair pra util).
  - **Filtros avançados** (`btn-secondary`) — atalho que **expande "Mais filtros"** no toolbar. Estado controlado via `useState` no parent ou via `URLSearchParams.get("adv")`. Decisão: `URLSearchParams` (consistente com filtros do toolbar).
  - **Enriquecer N** (`btn-primary`) — N é `counts.scraped`. On-click: abre `BulkConfirmModal` com `action="enrich"` e `lead_ids` resolvidos via `getLeadIds({status: "scraped", ...filters})`. Reusa o flow existente.

**Props.**

```tsx
interface PipelinePageHeaderProps {
  counts: Record<string, number>;
  conversionRate: number; // calculada igual ao funnel atual
  onExport: () => void;
  onToggleAdvancedFilters: () => void;
  onEnrichScraped: () => void;
}
```

**Comportamento.**

- Botão "Enriquecer N" é **condicional**: se `counts.scraped === 0`, esconde ou desabilita.
- Sub muda dinamicamente: "X leads scrapeados, esperando análise" / "Y leads enriquecidos, prontos pra LP" / etc., conforme o primeiro estágio com leads.
- Mobile (< 640px): ações empilham (`flex-wrap` + `gap-2`); H1 fica em linha separada.

**A11y.** H1 é o único `<h1>` da página (page header virou componente, mas mantém `<h1>` único). `aria-label` nos botões de ícone. "Enriquecer 391" tem texto, dispensa label.

### 4.2 `PipelineFunnel`

**Visual.** Bloco grande, bordered, com 2 linhas:

- Header: `FUNIL · 5 ESTÁGIOS · CLIQUE PRA FILTRAR` à esquerda · `CONVERSÃO FIM-A-FIM 0,8%` à direita.
- Body: 5 blocos de etapa intercalados com setas.

```
┌─ funnel ─────────────────────────────────────────────────────────────────────┐
│ FUNIL · 5 ESTÁGIOS · CLIQUE PRA FILTRAR              CONVERSÃO FIM-A-FIM 0,8%│
│ ┌─────────┐  →   ┌─────────┐  →   ┌─────────┐  →   ┌──────────┐  →   ┌────┐ │
│ │ 01      │ 12,5%│ 02      │ 28%  │ 03      │ 50%  │ 04       │ 30%  │ 05 │ │
│ │ Scraped │      │Analisado│      │ LP      │      │ Outreach │      │... │ │
│ │ 391     │      │ 49      │      │ 14      │      │ 7        │      │  3 │ │
│ │ ████░░  │      │ ██░░░░  │      │ █░░░░░  │      │ ░░░░░░   │      │..  │ │
│ │ 78%     │      │ 9,8%    │      │ 2,8%    │      │ 1,4%     │      │... │ │
│ │ rode... │      │ leads...│      │ analise │      │ enviar   │      │... │ │
│ └─────────┘      └─────────┘      └─────────┘      └──────────┘      └────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

Cada etapa:
- Número prefix mono `01..05`
- Label (Scrapeado / Analisado / LP Gerada / Msg Enviada / Respondeu)
- Count grande mono tabular-nums
- Progress bar — width = `count / total_leads_in_pipeline * 100`. Cor por estágio (cool gradient, ou tom único `--accent`).
- % do total mono small
- Hint pt-BR: "rode enriquecer", "leads em análise", "leads com LP pronta", "aguardando resposta", "fechando"

Setas entre etapas:
- Texto "→" mono
- Taxa de transição = `count[next] / count[prev] * 100` em mono small acima da seta

**Comportamento.**

- Click na etapa: toggle `?status=<id>` (mantém o comportamento atual, `pipeline-funnel.tsx` linhas 40-48).
- Etapa ativa: borda accent + fundo `--accent-soft`.
- Hover: borda mais forte.
- Tooltip no count: "X scraped + Y enriched downstream = Z entered" (se quisermos honestidade — no mínimo manter cálculo do `everEnteredPipeline` atual).

**Conversão fim-a-fim.** Manter cálculo atual:
```ts
const everEnteredPipeline = PROGRESS_STATUSES.reduce((sum, s) => sum + (counts[s] ?? 0), 0);
const responded = counts.responded ?? 0;
const respondedRate = everEnteredPipeline > 0 ? (responded / everEnteredPipeline) * 100 : 0;
```

**Mobile.** Em < 768px, funnel vira **horizontal scroll** (`overflow-x-auto` + `scroll-snap`), cada etapa com `min-width: 160px`. Setas entre etapas escondem em < 480px (só count + bar visível).

### 4.3 `PipelineToolbar`

**Visual.** 2 linhas:

```
[ 🔍 Buscar lead, telefone, cidade...  ⌘K ]  [Todos os nichos ▾] [Todas cidades ▾] [Score: ≥0 ▾] [Mais filtros [3]]   [Maior score ▾]   [Kanban|Tabela] [⊟ density]
```

- **Busca** com ícone à esquerda + Kbd `⌘K` à direita. Width fluido.
- **Chips de filtro** (4):
  - Todos os nichos ▾ — abre dropdown (lista de `nichos` do `getLeadFilters()`).
  - Todas cidades ▾ — idem.
  - Score: ≥0 ▾ — popover com slider min/max.
  - Mais filtros [N] — N = count de filtros ativos não-óbvios (perfil_lead, nicho_canonico, has_telefone, has_email). Click expande linha 2.
- **Sort** mono (Maior score, Menor score, Prioridade, Recente, Atualizado, Nome A-Z). Igual ao atual.
- **View toggle** [Kanban|Tabela]. Igual ao atual (`handleViewChange`).
- **Density toggle** (só em view=table) — botão ícone `⊟` (compact) / `☰` (comfortable). Toggle alterna `localStorage["sdr-pipeline-density"]`.

Linha 2 (expansível, `aria-expanded`):

```
[Perfil: todos ▾] [Nicho canônico: todos ▾] [Telefone: qualquer ▾] [Email: qualquer ▾]
```

**Estado de "Mais filtros".**

- Estado em `URLSearchParams.get("adv")` = "1" → expandido.
- Click em "Mais filtros" toggle isto.
- Click em "Filtros avançados" no page header → seta `adv=1` e foca primeiro select da linha 2.
- Persiste no URL (compartilhável).

**Chips dropdowns.**

- Implementar como `<details>` + `<summary>` para acessibilidade barata, ou popover com `useState` + `useRef` + click outside (alinhado ao padrão do `column-visibility-menu.tsx`). **Decisão: popover com state local** (evita estilização inconsistente de `<details>` cross-browser).
- Cada chip mostra count interno: "Todos os nichos" → "Nichos · 3" se 3 selecionados (futuro multi-select, fora de escopo agora). Por agora: single-select como hoje, label do valor selecionado.

**Comportamento preservado.**

- Todos os filtros via `URLSearchParams` (igual hoje).
- `getLeadFilters()` populates `nichos` + `cidades` lists.
- Toggle de view persistido em `localStorage["sdr-pipeline-view"]` + URL `?view=`.
- Telemetria `track("pipeline_view_toggled", ...)` mantida.

**Density.**

- Ver § 5.2.

### 4.4 `KanbanCard` (reescrito)

**Visual.**

```
┌─┬────────────────────────────────────┐
│█│ Açougue Boi Bom              [ 84]│  ← rail colorido (3px) + score badge
│█│ açougue · ★ 4,2 (18) · São Paulo  │
│█│ [● Sem site] [Sem WhatsApp]       │
│█│                                    │
│█│ [✨ Enriquecer] [📞] [✉] [⋯]      │  ← actions on hover
└─┴────────────────────────────────────┘
```

- **Rail esquerdo:** 3px de cor por score (terracotta/mostarda/salvia).
- **Card body:** 12px padding. Light bg `--surface`.
- **Head:** `<h3>` nome (15px, weight 480, line-clamp 1) + score badge (terracotta/mostarda/salvia bg + número).
- **Meta line:** mono 11px text-muted: nicho lower · ★ rating mono · (reviews) · cidade.
- **Sinais:** chips coloridos (max 3 visíveis, +N se >3). Tone:
  - `danger` (terracotta-soft bg + dot): "Sem site", "Sem HTTPS", "Site offline"
  - `warn` (mostarda-soft bg): "Sem WhatsApp", "Site lento", "Não responsivo"
  - `ok` (salvia-soft bg): "Tem site", "Tem WhatsApp" (raro mostrar)
  - `muted` (line bg): default
- **Actions on hover** (`:hover .pl-card-actions { opacity: 1 }`):
  - `✨ Enriquecer` — text + icon. On-click: `runEnrich({lead_ids: [lead.id]})`.
  - `📞` — icon-only. Disabled se `!lead.telefone`. On-click: abre `https://wa.me/55<cleaned>` em nova aba.
  - `✉` — icon-only. **Disabled sempre por enquanto**, com tooltip "Cadência de email em breve". TODO: integrar com Resend.
  - `⋯` — kebab. Abre menu (Ver detalhes, Marcar como qualificado, Ver no leads app, etc.). Reusa pattern de `column-visibility-menu.tsx`.

**Hot lead.** Se `score ≥ 80`, adiciona classe `pl-card-hot`:
- Borda mais forte (`--score-high`)
- Box-shadow leve (glow terracotta)
- Sempre, não toggle.

**Drag.** Mantém `useDraggable` de `@dnd-kit/core` igual hoje. Classe `kanban-card-dragging` ao arrastar.

**Click no card.** Abre `/app/leads/{id}` (igual hoje, ou via `onClick` no `<article>`).

**Props.**

```tsx
interface KanbanCardProps {
  lead: LeadSummary;
  onEnrich: (id: number) => void;
  onMore: (id: number, anchor: HTMLElement) => void;
  density: "compact" | "comfortable";
}
```

### 4.5 `KanbanColumn`

**Header redesenhado.**

```
[● red]  SCRAPEADO              [391]  ⋯
```

- Pip dot 8px colorido (cor varia por estágio).
- Título mono uppercase 11px tracking-wide.
- Count: pill bordered tabular-nums.
- More: kebab abre "Selecionar todos / Bulk enrich / Limpar" (futuro).

**Body.** Stack de cards, `gap-2`. Empty state quando `leads.length === 0`:

```
[ icon ]
Nenhum lead
rode enriquecer pra popular
```

**Wiring.** `kanban-board.tsx` já gerencia colunas. Atualizar header dele com este markup.

### 4.6 `PipelineTable`

**Header:** Nome ↕ · Nicho · Cidade · Score ↕ · Sinais · Contato · Status · Atualizado · (actions).

**Score cell.**
```
84 ████░░░░░░  (terracotta)
```
- Número grande tabular-nums colorido por classe (`pl-tbl-score-high`/mid/low).
- Barra horizontal 60px com width = `score%`.

**Niche cell.** Chip pill com label do nicho.

**Sinais cell.** Mostra max 2 chips inline. Resto vira "+3" expansível.

**Contato cell.** 3 ícones inline:
- 📞 — `ok` (text-ok) se `telefone`, `off` (text-muted) caso contrário.
- ✉ — idem para `email`.
- WA — sempre `off` por enquanto (não validamos WhatsApp). Tooltip "WhatsApp não validado".

**Status cell.** `StatusPill` igual hoje (preserva).

**Atualizado cell.** Relativo: "há 2h", "ontem", "12 abr". Util novo em `lib/format.ts` (ou inline).

**Actions cell.** On-hover: ✨ + ⋯. Igual ao card.

**Hot row.** `score ≥ 80` → background `--score-high-soft` (terracotta soft) + borda esquerda accent. Sempre ligado.

**Density.** § 5.2.

**Comportamento preservado.**

- Multi-select via `useBulkSelection` (checkbox col 1, sticky).
- Sort por score/nome via TanStack Table (atual).
- Virtualização via TanStack Virtual (atual).
- Paginação: `page` + `per_page` URL params (atual).
- CSV export (atual, mover trigger pro page header).
- Column visibility menu (atual).

## 5. Features novas

### 5.1 Hot lead highlight

- **Threshold:** `score ≥ 80`
- **Sempre ligado.** Sem toggle.
- **Visual:** card com glow terracotta + borda mais forte; row tabela com bg terracotta-soft + border-l accent.
- **Reasoning.** Lead 80+ é o que importa pra SDR — destaque silencioso, não alarme.

### 5.2 Density toggle

- **Estados:** `compact` (default na tabela, 32px row height, 11px font) | `comfortable` (40px row height, 13px font).
- **Persistência:** `localStorage.setItem("sdr-pipeline-density", value)`.
- **Aplicação:** classe no wrapper (`pl-tbl-compact` / `pl-tbl-comfortable`). CSS toggla padding + font-size + line-height.
- **Onde aparece:** botão ícone na toolbar, **só na view=table**. Em kanban: density é fixa (kanban já é compact-by-design).
- **Hook:** `use-pipeline-density.ts`:

```ts
export function usePipelineDensity() {
  const [density, setDensity] = useState<"compact" | "comfortable">(() => {
    if (typeof window === "undefined") return "compact";
    const stored = localStorage.getItem("sdr-pipeline-density");
    return stored === "comfortable" ? "comfortable" : "compact";
  });

  const toggle = useCallback(() => {
    setDensity((prev) => {
      const next = prev === "compact" ? "comfortable" : "compact";
      try { localStorage.setItem("sdr-pipeline-density", next); } catch {}
      return next;
    });
  }, []);

  return { density, toggle };
}
```

### 5.3 Sinais derivados

`lib/pipeline-signals.ts` exporta:

```ts
export type SignalTone = "danger" | "warn" | "ok" | "muted";
export interface Signal { key: string; label: string; tone: SignalTone; }

const REASON_TO_SIGNAL: Record<string, { label: string; tone: SignalTone }> = {
  "Sem website":         { label: "Sem site",       tone: "danger" },
  "Site sem SSL":        { label: "Sem HTTPS",      tone: "danger" },
  "Site fora do ar":     { label: "Site offline",   tone: "danger" },
  "Site não responsivo": { label: "Não responsivo", tone: "warn" },
  "Sem WhatsApp":        { label: "Sem WhatsApp",   tone: "warn" },
  "Sem CTA claro":       { label: "Sem CTA",        tone: "warn" },
  "PageSpeed baixo":     { label: "Site lento",     tone: "warn" },
  "Sem analytics":       { label: "Sem analytics",  tone: "muted" },
  "Sem chatbot":         { label: "Sem chatbot",    tone: "muted" },
  // ... cobrir todas as strings de scoring.py
};

export function deriveSignals(reasons: string[]): Signal[] {
  return reasons
    .map((r) => REASON_TO_SIGNAL[r])
    .filter(Boolean)
    .map((s, i) => ({ key: `sig-${i}`, ...s }))
    .sort((a, b) => TONE_ORDER[a.tone] - TONE_ORDER[b.tone]); // danger first
}
```

**Fallback:** strings sem mapping viram `tone: "muted"` com label = string crua.

**Verificar:** auditar `backend/app/pipeline/enrichment/scoring.py` pra extrair lista exata de reasons. Faz parte da implementação, não do spec.

### 5.4 Quick actions wiring

| Action | Card / Tabela | Implementação |
|---|---|---|
| ✨ Enriquecer | Card hover · Row hover | `runEnrich({lead_ids: [lead.id]})` (já existe) |
| 📞 Phone | Card hover · Row hover | `window.open(\`https://wa.me/55${cleanPhone(lead.telefone)}\`, "_blank")`. Disabled se `!lead.telefone`. |
| ✉ Email | Card hover · Row hover | **Disabled.** Tooltip: "Cadência de email em breve". TODO: trigger Resend cadence. |
| ⋯ Mais | Card hover · Row hover | Abre menu: Ver detalhes (`/app/leads/{id}`), Marcar como qualificado, Editar, Excluir. |

**Util `cleanPhone`:**

```ts
export function cleanPhone(phone: string | null | undefined): string {
  if (!phone) return "";
  return phone.replace(/\D/g, "");
}
```

Onde já vive: `backend/app/pipeline/outreach.py` faz isso em Python para os links wa.me. Replicar em `lib/format.ts` no frontend.

## 6. Comportamento preservado (garantia explícita)

Esta lista NÃO MUDA com o redesign:

1. **Multi-select** com `useBulkSelection` (checkbox sticky, Shift+click range, Ctrl+A select page, sessionStorage).
2. **Banner de seleção** (`SelectAllBanner`) e **bulk action bar** (`BulkActionBar`) sticky bottom.
3. **Modais** de confirm/result (`BulkConfirmModal`, `BulkResultModal`, `ClassifyModal`) com focus trap e ESC isolation.
4. **Filtros via URL** (todos os params atuais: status, nicho, cidade, score_min, score_max, has_telefone, has_email, search, perfil_lead, nicho_canonico, order_by, page, per_page, view).
5. **Polling** de counts via `usePipelineCounts` (5s, snapshot diff, banner "X novos desde a última carga").
6. **SSE** de jobs via `streamJob()` em `pipeline-controls.tsx`.
7. **CSV import + export** (export move pro page header; import permanece em `pipeline-controls.tsx`).
8. **Banner de filtros ativos** (`FiltrosAtivosBanner`) — fica entre toolbar e funnel.
9. **Column visibility menu** na tabela.
10. **Telemetria** (`track("pipeline_view_toggled", ...)` etc.).
11. **Auth** + Better Auth session refresh.
12. **Mobile defaults** (view=kanban no mobile via matchMedia lazy initializer).
13. **Drag-and-drop** no kanban (`@dnd-kit`, optimistic update + rollback).

## 7. Acessibilidade

- **Contrast.** Todas as cores derivadas dos tokens DS Instrumento já passam WCAG AA (validado em PR 4.B do redesign anterior).
- **Keyboard.** Tab order: page header → toolbar (busca → chips → sort → view → density) → funnel (etapas como botões) → tabela/kanban.
- **Screen readers.** Sinais têm `aria-label="Sinal: {label}"`. Score badge tem `aria-label="Score {n} de 100"`. Funnel etapas são `<button aria-pressed={active}>`.
- **Focus visible.** Outline accent 2px em todos os interactive elements (já no DS).
- **Hot lead.** Não codifica info **só** por cor — o score numérico está ao lado.
- **Tooltips.** `title` HTML padrão (suficiente para v1; tooltip-component se precisar).

## 8. Responsividade

| Breakpoint | Page header | Toolbar | Funnel | View padrão |
|---|---|---|---|---|
| < 480px | Stack vertical, ações em linha 2 wrap | Busca full-width, chips wrap, sort stack | Horizontal scroll, sem setas | Kanban (1 col) |
| 480-768px | H1 + ações lado a lado | Busca + chips em 2 linhas | Horizontal scroll com setas | Kanban (1 col) |
| 768-1024px | Lado a lado | Single line, "Mais filtros" colapsado | Single line, sem scroll | Kanban (3 cols) |
| > 1024px | Lado a lado | Single line | Single line, gaps generosos | Kanban (5 cols) ou Tabela |

Mobile-first: começar pelo CSS mobile, escalar via `min-width` (alinhado à preference no `MEMORY.md → feedback_mobile_first`).

## 9. Implementação

### 9.1 Phases (commits dentro do PR único)

Ordem importa (cada commit fica deployable, mas mistura visual):

1. **`feat(pipeline): import pipeline.css + pipeline-signals util`**
   - Port `pipeline.css` adaptado pros tokens locais.
   - `lib/pipeline-signals.ts` com mapper.
   - `lib/format.ts` com `cleanPhone`, `formatRelativeDate`.
   - Sem mudança visual ainda.

2. **`feat(pipeline): page header component`**
   - Cria `pipeline-page-header.tsx`.
   - Substitui `<div>...<h2>Pipeline</h2></div>` em `page.tsx`.
   - Wireup Exportar (extrai do table), Filtros avançados (URL `adv=1`), Enriquecer N (modal).

3. **`feat(pipeline): redesign funnel`**
   - Reescreve `pipeline-funnel.tsx` com progress bars + setas com taxa.
   - Mantém `handleClick` (URL toggle).

4. **`feat(pipeline): redesign toolbar with chips + advanced expandable`**
   - Reescreve `pipeline-toolbar.tsx` com chips popover + linha 2 expandable + density toggle (só table view).
   - Adiciona `use-pipeline-density.ts`.
   - Sincroniza `adv=1` URL param ↔ estado expandido.

5. **`feat(pipeline): redesign kanban card and column`**
   - Reescreve `kanban-card.tsx` com rail + score badge + sinais + actions.
   - Atualiza `kanban-board.tsx` com header de coluna (pip + count badge).
   - Hot highlight `score >= 80`.

6. **`feat(pipeline): redesign table cells`**
   - Reescreve cells de `pipeline-table.tsx` (score colorido + barra, niche chip, sinais, contact icons, hot row).
   - Aplica density classes.
   - Mantém TanStack Table + Virtual + multi-select.

7. **`chore(pipeline): mobile-first audit + responsive fixes`**
   - Testar em 375/768/1024/1440. Ajustar `pipeline.css` media queries.

8. **`docs: add pipeline redesign spec`** (opcional — este doc).

### 9.2 Critérios de aceitação

Para cada commit, antes de fechar:

- [ ] `npm run lint` passa.
- [ ] `npm run build` passa.
- [ ] Visualmente fiel ao protótipo (comparar lado a lado em browser).
- [ ] Comportamento preservado (lista § 6).
- [ ] Mobile (375px) renderiza sem overflow horizontal indesejado.
- [ ] Dark theme aplica corretamente (`data-theme="dark"`).
- [ ] Telemetria continua disparando (`pipeline_view_toggled`, etc.).
- [ ] Multi-select + bulk actions funcionam fim-a-fim numa run manual.

### 9.3 Riscos

| Risco | Mitigação |
|---|---|
| `pipeline.css` introduz conflito com Tailwind v4 | Escopar tudo via `pl-*` e testar interação com utility classes nos componentes vizinhos. Mesmo padrão do `lead-app.css`. |
| Sinais de scoring.py mudaram desde o último audit | Auditar `enrichment/scoring.py` no commit 1 antes de mapear. Fallback `tone: "muted"` cobre strings desconhecidas. |
| Density toggle quebra row height da virtualização TanStack | TanStack Virtual aceita `estimateSize` dinâmico — passar callback que lê `density` state. |
| "Filtros avançados" no header conflita com toggle do toolbar | Single source of truth: `URLSearchParams.get("adv")`. Header apenas seta param; toolbar lê e expande. |
| Hot highlight competindo com row select highlight | Z-order: select > hot. Background select com `--accent-soft` opaco. |
| Quick actions on hover não acessíveis via keyboard | Tornar visíveis ao `focus-within` do row/card também (`:focus-within .pl-card-actions { opacity: 1 }`). |
| Mobile performance com `pipeline.css` 800+ linhas | CSS é estático e cached pelo Next; sem JS overhead. Ok. |

## 10. Out of scope

Itens do protótipo que **não** entram neste PR:

- `PIPELINE_TWEAK_DEFAULTS` modos operator/funnel-first.
- Painel de tweaks (`tweaks-panel.jsx`).
- `PlSidebar` redesign (mantém `AppSidebar`).
- `PlTopbar` redesign (mantém topbar do app).
- Dropdown multi-select nos chips (single-select por agora).
- Cadência de email via Resend (✉ disabled com TODO).
- WhatsApp validation real (ícone WA fica `off` sempre).
- Bulk actions no header de coluna (kebab `⋯` da coluna fica TODO).
- Score popover/slider no chip (chip por agora abre dropdown simples ou número).
- Dark theme tweaks novos (usa o atual como está).

Itens fora do escopo geral:

- Mudanças no backend (sinais derivam de `opportunity_reasons` já existente).
- Novos endpoints.
- Novos campos no Lead.
- A11y avançado (skip links, landmarks formais — fora do scope do redesign).

## 11. Referências

- Protótipo: `~/Downloads/SDR (1)/Pipeline.html` + JSXs + `pipeline.css`
- Spec do bulk actions (PRs 71-75): `docs/superpowers/specs/2026-05-01-bulk-actions-table-view-design.md`
- DS Instrumento: `frontend/src/app/globals.css`
- Lead App pattern (CSS port): `frontend/src/components/leads/lead-app.css`
- Backend scoring (fonte de `opportunity_reasons`): `backend/app/pipeline/enrichment/scoring.py`
