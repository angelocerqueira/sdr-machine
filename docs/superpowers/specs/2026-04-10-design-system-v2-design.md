# Design System v2 — SDR Machine

**Data:** 2026-04-10
**Status:** Aprovado (brainstorming)
**Referências:** Apollo CRM (layout/densidade), Clay (responsividade)

## Resumo

Redesign do design system do SDR Machine, migrando de um dark minimalista (preto absoluto + Outfit/DM Sans) para um dark denso Apollo-like (cinza-chumbo + Geist). Escopo: tokens + layout do app (sidebar agrupada + top bar fixa). Páginas internas herdam os novos tokens automaticamente mas não são redesenhadas individualmente.

## Decisões de Design

| Decisão | Escolha | Alternativas descartadas |
|---------|---------|--------------------------|
| Direção visual | Apollo-like dark denso | Refinamento do atual, Clay-like light |
| Accent color | Emerald puro (#34d399) | Amarelo Apollo, Híbrido emerald+yellow |
| Escopo | Tokens + layout (sidebar + top bar) | Só tokens, Redesign completo página a página |
| Sidebar | Agrupada (~260px desktop), 3 seções | Flat 3 itens |
| Top bar | Busca cmd+k, CTA, créditos, avatar | Com notificações |
| Tipografia | Geist + Geist Mono | Outfit+DM Sans+JetBrains (atual), Inter |
| Responsividade | Mobile-first (min-width breakpoints) | Desktop-first |

## Design Tokens

### Cores

```
--color-bg:              #111113
--color-surface:         #1a1a1d
--color-surface-raised:  #242428
--color-surface-overlay: #2c2c32
--color-border:          #333339
--color-border-subtle:   #27272d
--color-text:            #f0f0f3
--color-text-secondary:  #9898a3
--color-text-muted:      #5a5a66
--color-accent:          #34d399
--color-accent-dim:      #059669
--color-accent-subtle:   rgba(52, 211, 153, 0.08)
--color-accent-glow:     rgba(52, 211, 153, 0.15)
--color-danger:          #f87171
--color-warning:         #fbbf24
--color-info:            #60a5fa
```

Racional: surfaces ~10-15% mais claros que o DS v1 para o efeito "cinza-chumbo" Apollo em vez do "preto absoluto" anterior.

### Tipografia

```
--font-heading: 'Geist', system-ui, sans-serif
--font-body:    'Geist', system-ui, sans-serif
--font-mono:    'Geist Mono', monospace
```

Heading e body usam a mesma família (Geist) — diferenciação vem de weight e size, não de família. Mono para labels, badges, scores e dados numéricos.

**Escala de tamanhos:**

| Token | Valor | Uso |
|-------|-------|-----|
| xs | 11px | Micro labels, badges |
| sm | 12px | Captions, metadata |
| base | 13px | Body text, sidebar items, table cells |
| md | 14px | Inputs, buttons |
| lg | 16px | Section headings |
| xl | 20px | Page titles |
| 2xl | 24px | Stat numbers grandes |

**Weights:** 400 (regular), 500 (medium), 600 (semibold), 700 (bold).

### Spacing

| Token | Valor |
|-------|-------|
| xs | 4px |
| sm | 6px |
| md | 8px |
| lg | 12px |
| xl | 16px |
| 2xl | 20px |
| 3xl | 24px |
| 4xl | 32px |

### Border Radius

| Token | Valor | Uso |
|-------|-------|-----|
| sm | 4px | Badges, chips pequenos |
| md | 6px | Buttons, inputs, dropdowns |
| lg | 8px | Cards, content boxes |
| xl | 12px | Modals, panels |
| full | 9999px | Pills, chips, avatars |

### Shadows

Sem box-shadow visível. Hierarquia vem exclusivamente de border + surface levels (padrão Apollo dark). Exceção: card hover glow usa `box-shadow: 0 0 0 1px var(--accent-subtle), 0 4px 16px -4px rgba(0,0,0,0.4)`.

### Transitions

| Token | Valor | Uso |
|-------|-------|-----|
| fast | 150ms ease | Hover states, buttons |
| normal | 200ms ease | Sidebar, panels |
| slow | 250ms ease | Drawer mobile, modals |

## Layout Shell

### Top Bar (novo componente)

- **Altura:** 52px
- **Position:** fixed top, z-index 100
- **Background:** `var(--surface)` com `border-bottom: 1px solid var(--border)`
- **Conteúdo (esquerda → direita):**
  1. Hamburger button (mobile only, abre sidebar drawer)
  2. Logo (24px, gradient emerald) + "SDR Machine" (desktop only)
  3. Busca global (cmd+k) — `var(--surface-raised)`, max-width 420px, com ícone lupa + kbd shortcut
  4. Spacer (flex: 1)
  5. Créditos — mono, dot verde + "2.4k créditos" (hidden mobile)
  6. CTA "Novo Job" — btn-primary emerald
  7. Avatar (28px circle, iniciais)

### Sidebar (redesign)

- **Width:** 260px (desktop), 56px icon-only (tablet), drawer (mobile)
- **Position:** fixed left, top 52px (abaixo da top bar)
- **Background:** `var(--surface)` com `border-right: 1px solid var(--border)`
- **Seções agrupadas:**
  - **Pipeline:** Dashboard, Kanban (com badge count), Jobs
  - **Dados:** Leads, Contas
  - **Config:** Settings
- **Labels de seção:** `var(--font-mono)`, 10px, uppercase, tracking 0.1em, `var(--text-muted)`
- **Item ativo:** `var(--surface-raised)` background + barra emerald 3px no left
- **Item hover:** `var(--surface-raised)` background
- **Badge:** mono 10px, `var(--accent-subtle)` bg, `var(--accent)` text, pill shape
- **Rodapé:** Status "Pipeline" separado por border-top (hidden tablet/mobile)

### Main Content

- **Margin:** left 260px (desktop), left 56px (tablet), left 0 (mobile)
- **Margin top:** 52px (altura da top bar)
- **Padding:** 24px (desktop), 20px (tablet), 16px (mobile)
- **Background:** `var(--bg)`

### Breakpoints (mobile-first)

| Breakpoint | Nome | Sidebar | Top bar | Grid stats | Grid status |
|------------|------|---------|---------|------------|-------------|
| Base | Mobile | Drawer (hidden) | Hamburger, sem nome, sem créditos | 2 cols | 2 cols |
| ≥768px | Tablet (md) | 56px icon-only | Sem hamburger, sem nome, com créditos | 2 cols | 3 cols |
| ≥1024px | Desktop (lg) | 260px full | Completa | 4 cols | 5 cols |

Sidebar mobile abre como drawer com overlay (`rgba(0,0,0,0.6)` + `backdrop-filter: blur(4px)`).

## Componentes Base

### Buttons

| Variante | Background | Color | Border |
|----------|-----------|-------|--------|
| primary | `var(--accent)` | `var(--bg)` | none |
| secondary | `var(--surface-raised)` | `var(--text)` | 1px `var(--border)` |
| ghost | transparent | `var(--text-secondary)` | none |
| danger | `rgba(248,113,113,0.1)` | `var(--danger)` | 1px `rgba(248,113,113,0.2)` |

Sizes: sm (12px, 5px 10px), default (13px, 8px 16px), lg (14px, 10px 20px), icon (34x34px).
Radius: `var(--radius-md)` (6px). Hover: darken/lighten 10%.

### Inputs

- **Background:** `var(--surface-raised)`
- **Border:** 1px `var(--border-subtle)`, focus → `var(--accent)` + `box-shadow: 0 0 0 3px var(--accent-subtle)`
- **Error state:** border `var(--danger)`, focus shadow `rgba(248,113,113,0.1)`
- **Size:** 13px font, 8px 12px padding
- **Select:** Same style + chevron SVG no right

### Chips

- **Default:** `var(--surface-raised)` bg, 1px `var(--border-subtle)`, `var(--text-secondary)`
- **Active:** `var(--accent-subtle)` bg, `rgba(52,211,153,0.25)` border, `var(--accent)` text
- **Radius:** 999px (pill)
- **Close:** ✕ com opacity 0.5 → 1 on hover

### Tabs

- **Flex row** com `border-bottom: 1px solid var(--border-subtle)`
- **Tab default:** `var(--text-secondary)`, `border-bottom: 2px solid transparent`
- **Tab active:** `var(--text)`, `border-bottom-color: var(--accent)`
- **Size:** 13px, padding 10px 16px

### Badges

Retangulares, radius 4px. Variantes: accent, warning, danger, info, muted. Mono 10px, uppercase, tracking 0.06em.

### Status Pills

Pill (radius full) com dot animável. Variantes seguem semântica: accent (positivo), warning (pendente), danger (erro). Mono 10px, uppercase.

### Cards

- **Background:** `var(--surface)`
- **Border:** 1px `var(--border-subtle)`
- **Radius:** `var(--radius-lg)` (8px)
- **Hover:** border emerald sutil + glow shadow
- **Conteúdo:** title (14px semibold) + desc (12px secondary) + footer com score + pill

### Table Rows

- **Headers:** mono 10px uppercase, `var(--text-muted)`
- **Cells:** 13px, `var(--text-secondary)`, names em `var(--text)` + weight 500
- **Row hover:** `var(--surface-raised)` background
- **Dividers:** `border-bottom: 1px solid var(--border-subtle)`

### Scores

Mono, font-feature-settings "tnum" 1, 3 níveis de cor:
- High (≥60): `var(--accent)` — verde/emerald
- Mid (40-59): `var(--warning)` — amarelo
- Low (<40): `var(--text-muted)` — cinza

### Tooltip

- **Background:** `var(--surface-overlay)`
- **Border:** 1px `var(--border)`
- **Radius:** 6px
- **Font:** 11px, `var(--text-secondary)`
- **Position:** absolute acima do trigger, com seta CSS

## Utilitários CSS Mantidos

- `.card-glow` — hover glow nos cards (atualizar cores)
- `.status-pill` — atualizar pra usar novos tokens
- `.score-high`, `.score-mid`, `.score-low` — manter pattern, atualizar valores
- `.bg-dots` — manter, atualizar cor do dot
- `.stat-number` — manter tabular nums, trocar font
- `.skeleton` — atualizar surface colors
- `.sheet-backdrop` / `.sheet-enter` — manter animações

## Fora de Escopo

- Redesign interno das páginas (Dashboard, Kanban, Jobs, Lead detail)
- Command palette funcional (busca é placeholder visual nesta fase)
- Endpoint real de créditos (placeholder estático no top bar)
- Páginas novas (Leads listagem, Contas)
- Dark/light mode toggle
- Animações de entrada/exit (Framer Motion, etc)

## Impacto nos Arquivos Existentes

| Arquivo | Mudança |
|---------|---------|
| `globals.css` | Reescrever tokens `@theme`, atualizar utilitários |
| `layout.tsx` | Trocar fonts (Geist via `next/font/google`), remover Outfit/DM Sans/JetBrains |
| `(main)/layout.tsx` | Novo shell: TopBar + Sidebar redesenhada + main wrapper responsivo |
| `sidebar.tsx` | Reescrever: grupos, badges, icon-only mode, drawer mobile |
| Novo: `top-bar.tsx` | Componente da top bar (busca, CTA, créditos, avatar) |
| Novo: `command-search.tsx` | Placeholder visual do cmd+k (modal stub) |
| `stats-card.tsx` | Atualizar classes pra novos tokens |
| `kanban-board.tsx` | Classes herdam automaticamente |
| `kanban-card.tsx` | Classes herdam automaticamente |
| Todos os componentes | Atualizar referências de font-family inline (se houver) pra usar os novos tokens |

## Mockups de Referência

Mockups interativos salvos em `.superpowers/brainstorm/`:
- `shell.html` — Layout completo com 3 breakpoints (redimensionar browser pra testar)
- `components.html` — Catálogo de todos os componentes base
