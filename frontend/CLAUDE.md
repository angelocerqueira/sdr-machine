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

Single env var: `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`).

## Path Alias

`@/*` maps to `./src/*` — use `@/components/foo` and `@/lib/api` for imports.

## Design System

All theming lives in `src/app/globals.css` via CSS custom properties inside a `@theme` inline block (Tailwind v4 — there is no tailwind.config file).

- **Colors:** `--color-bg`, `--color-surface`, `--color-accent` (#34d399 emerald), `--color-danger`, `--color-warning`, `--color-info`, plus `-secondary`, `-muted`, `-subtle` variants
- **Fonts:** Outfit (headings), DM Sans (body), JetBrains Mono (mono) — loaded via `next/font/google` in `layout.tsx`, applied through `--font-*` CSS vars
- **Custom utilities:** `.card-glow`, `.status-pill`, `.score-high`/`.score-mid`/`.score-low`, `.kanban-card-dragging`, `.bg-dots`, `.stat-number` (tabular nums)

Opportunity score drives color everywhere: green (≥60), yellow (40–59), muted (<40).

## Architecture

```
src/
├── app/                    # Next.js App Router pages
│   ├── layout.tsx          # Root layout: Sidebar + main area (max-w-7xl)
│   ├── page.tsx            # Dashboard (stats cards + status breakdown)
│   ├── kanban/page.tsx     # Pipeline controls + drag-drop kanban board
│   ├── jobs/page.tsx       # Job history table with status indicators
│   └── leads/[id]/page.tsx # Lead detail: score, info grid, LP iframe, messages
├── components/             # All UI components (flat, no nesting)
└── lib/
    ├── api.ts              # Typed fetch wrapper + all endpoint functions
    └── types.ts            # Interfaces (Lead, Job, OutreachMessage, etc.) + KANBAN_COLUMNS
```

### API Layer (`lib/api.ts`)

`fetchAPI<T>()` is the base wrapper — adds JSON headers, throws on non-ok. All endpoints are individual exported functions. `streamJob()` is the exception: it uses `EventSource` (SSE) instead of fetch, streaming real-time job progress and auto-closing on "done"/"error" events.

### State Management

Pure React hooks only (`useState`, `useEffect`, `useCallback`, `useRef`). No global state, no React Query/SWR. Data is fetched in `useEffect` per page.

### Kanban Drag-and-Drop

`kanban-board.tsx` uses `@dnd-kit/core` with `pointerWithin` collision detection. On drop, it applies an **optimistic local update** then calls `updateLead()` — if the API call fails, the local state is reverted to the previous snapshot.

### Real-Time Job Progress

`job-progress.tsx` subscribes to `GET /api/jobs/{id}/stream` via `EventSource`. It accumulates log messages, auto-scrolls, and closes the stream when the job finishes. `pipeline-controls.tsx` renders this component and calls `onJobDone` (which triggers a page reload) on completion.

## Conventions

- All UI text is **Portuguese (pt-BR)**. Dates use `toLocaleString("pt-BR")`. Status/type labels are mapped via hard-coded dictionaries in each page.
- `KANBAN_COLUMNS` in `types.ts` defines the 9-stage lead pipeline order — add new statuses there.
- Components are flat `.tsx` files in `components/` — no subdirectories, no barrel exports.
- Inline SVGs for icons (no icon library).
- Filters on the kanban board are dynamically derived from the current lead data (niches, cities).
- The LP preview in lead detail is an iframe pointing at the backend HTML endpoint (`/api/leads/{id}/lp`).
