# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this frontend.

## Stack

Next.js 16 (App Router) + React 19 + TypeScript 5 (strict) + Tailwind CSS 4 + @dnd-kit (drag-and-drop)

## Commands

```bash
npm run dev      # Dev server on http://localhost:3000
npm run build    # Production build
npm run lint     # ESLint (flat config, core-web-vitals + TypeScript)
```

Env vars: `NEXT_PUBLIC_API_URL` (backend URL, default `http://localhost:8000`), `DATABASE_URL` (PostgreSQL, same as backend — needed by Better Auth server-side).

## Path Alias

`@/*` maps to `./src/*` — use `@/components/foo` and `@/lib/api` for imports.

## Design System

Design system "Instrumento" — anti-cockpit, pró-ofício. All theming lives in `src/app/globals.css` via CSS custom properties in `:root` / `[data-theme="dark"]`, mapped to Tailwind v4 via `@theme inline` block (no tailwind.config file).

- **Colors:** Paper/ink/line palette (warm off-white light, cool charcoal dark). Accent is OKLCH blue (hue 256). Semantic colors are desaturated: ok (salvia), warn (mostarda), danger (terracotta). Primitives: `--paper-0..3`, `--ink-0..5`, `--line-1..3`. Semantic aliases: `--bg`, `--surface`, `--text`, `--border` etc. Tailwind utilities: `bg-bg`, `text-text-muted`, `border-border-strong`, `bg-accent-soft`, etc.
- **Fonts:** Inter Tight (sans) + JetBrains Mono (mono) — loaded via `next/font/google` in `layout.tsx` as `--font-inter-tight` / `--font-jetbrains-mono`. Weights: 400 (body), 460 (label), 480 (heading), 500 (btn), 600 (rare). Numbers always in mono with `tabular-nums`.
- **Theme:** Light/dark via `data-theme` attribute on `<html>`, persisted in localStorage. Default: dark. Toggle reads/writes `sdr-theme` key.
- **Custom utilities:** `.card-glow`, `.score-high`/`.score-mid`/`.score-low`, `.kanban-card-dragging`, `.bg-dots`, `.stat-number`, `.skeleton`, `.pulse-glow`
- **DS Components (`components/ui/`):** `Icon` (30+ stroke SVGs), `Tag`, `Badge`, `Kbd`, `StatusPill` (11 lead statuses), `ScoreRing` (SVG 0-100), `PipeMini` (pipeline stepper). Import from `@/components/ui`.

Score colors: terracotta (80-100, "aja agora"), mostarda (50-79), salvia (0-49). Alto score = oportunidade quente, não "parabéns".

## Architecture

```
src/
├── app/
│   ├── (marketing)/        # Public landing page
│   │   ├── layout.tsx       # Marketing layout (navbar, no sidebar)
│   │   └── page.tsx         # LP with all sections
│   ├── app/                 # Authenticated product (requires login)
│   │   ├── layout.tsx       # App layout: TopBar + Sidebar + main area (max-w-7xl)
│   │   ├── page.tsx         # Dashboard (stats cards + status breakdown)
│   │   ├── kanban/page.tsx  # Pipeline controls + drag-drop kanban board
│   │   ├── jobs/page.tsx    # Job history table with status indicators
│   │   └── leads/[id]/page.tsx # Lead detail: score, info grid, LP iframe, messages
│   ├── lp/[id]/page.tsx     # Public LP preview (no auth)
│   ├── login/page.tsx       # Login page
│   ├── layout.tsx           # Root layout
│   └── globals.css          # Design tokens + utilities
├── components/
│   ├── ui/                  # DS primitives (Icon, Tag, Badge, Kbd, StatusPill, ScoreRing, PipeMini)
│   ├── marketing/           # LP-specific components (navbar, hero, sections, practice-block)
│   ├── remotion/            # Remotion compositions (hero animation)
│   ├── shared/              # Reusable between LP and app (agent-chat, digital-blueprint, mission-control, chat-widget)
│   └── *.tsx                # App UI components (flat)
└── lib/
    ├── api.ts               # Typed fetch wrapper + all endpoint functions
    ├── auth.ts              # Better Auth server config (session, cookies, database)
    ├── auth-client.ts       # Better Auth React client
    ├── types.ts             # Interfaces + KANBAN_COLUMNS
    ├── practice-types.ts    # Types for Veja na Pratica components
    ├── practice-data.ts     # Mock data for LP marketing
    ├── chat-templates.ts    # Niche-specific chat templates (6 + fallback)
    └── lead-to-practice.ts  # Lead enrichment -> component props transformers
```

### API Layer (`lib/api.ts`)

`fetchAPI<T>()` is the base wrapper — adds JSON headers, `credentials: "include"`, and Bearer token from session cookie. Auto-refreshes session cache on 401 before logging out. All endpoints are individual exported functions. `streamJob()` is the exception: it uses `EventSource` (SSE) instead of fetch, streaming real-time job progress and auto-closing on "done"/"error" events. `importCSV()` uses raw `fetch` + `FormData` (no JSON wrapper).

### State Management

Pure React hooks only (`useState`, `useEffect`, `useCallback`, `useRef`). No global state, no React Query/SWR. Data is fetched in `useEffect` per page.

### Kanban Drag-and-Drop

`kanban-board.tsx` uses `@dnd-kit/core` with `pointerWithin` collision detection. On drop, it applies an **optimistic local update** then calls `updateLead()` — if the API call fails, the local state is reverted to the previous snapshot.

### Real-Time Job Progress

`job-progress.tsx` subscribes to `GET /api/jobs/{id}/stream` via `EventSource`. It accumulates log messages, auto-scrolls, and closes the stream when the job finishes. `pipeline-controls.tsx` renders this component and calls `onJobDone` (which triggers a page reload) on completion.

## Conventions

- All UI text is **Portuguese (pt-BR)**. Dates use `toLocaleString("pt-BR")`. Status/type labels are mapped via hard-coded dictionaries in each page.
- `KANBAN_COLUMNS` in `types.ts` defines the 9-stage lead pipeline order — add new statuses there.
- App components are flat `.tsx` files in `components/`. Subdirectories: `ui/` (DS primitives), `marketing/` (LP sections), `remotion/` (hero animation), `shared/` (reusable between LP and app).
- Icons via `<Icon name="..." />` from `@/components/ui` — custom stroke SVGs, no external icon library.
- Filters on the kanban board are dynamically derived from the current lead data (niches, cities).
- The LP preview in lead detail is an iframe pointing at the backend HTML endpoint (`/api/leads/{id}/lp`).
- All authenticated app routes live under `/app/*`. Internal links must use the `/app` prefix (e.g., `/app/kanban`, not `/kanban`).
- The marketing LP at `/` is public and uses its own layout without sidebar/top-bar.
