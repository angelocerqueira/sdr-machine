# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SDR Machine is a sales development automation platform that scrapes business listings, analyzes their web presence, generates personalized landing pages via LLM API, and creates WhatsApp outreach messages. The project is written in Portuguese (Brazilian) — UI text, variable names like `nicho`/`cidade`, and pipeline output are all in pt-BR.

## Architecture

**Backend:** FastAPI + SQLAlchemy + PostgreSQL 16 + Alembic (in `backend/`)
**Frontend:** Next.js 16 (App Router) + React 19 + TypeScript + Tailwind CSS 4 (in `frontend/`)
**Deployment:** Railway (backend via root Dockerfile) + Vercel (frontend)

### 4-Stage Pipeline

Each stage runs as a FastAPI background task, creating a `Job` record and streaming progress via SSE:

1. **Scrape** — Calls Apify Google Places API for each niche×city combination, deduplicates leads
2. **Enrich** — Usa um orquestrador inteligente (`enrichment/orchestrator.py`) com 6 providers plugáveis (CnpjProvider, WebsiteCrawlerProvider, SchemaOrgProvider, TechStackProvider, EmailDiscovererProvider, ApolloProvider). Executa em 4 fases ordenadas: Discovery (CNPJ) → Crawl (website, schema.org, tech stack) → Contact (email, Apollo) → Scoring. Providers compartilham estado via `EnrichmentContext`. Suporta `skip_providers` e `force_providers` para override. Calcula opportunity score (0-100, higher = worse site = more opportunity) com 10+ sinais
3. **Generate** — Calls LLM API (model configurable via `LLM_MODEL`) to produce standalone HTML landing pages per lead
4. **Outreach** — Generates 3 WhatsApp messages per lead (initial, 48h followup, final) with pre-filled wa.me links

### Lead Status Flow

`scraped` → `enriched` → `lp_generated` → `outreach_ready` → `outreach_sent` → `responded` → `in_call` → `closed` → `delivered`

### Database Models

Four tables: `jobs`, `leads`, `landing_pages`, `outreach_messages`. Lead has a PostgreSQL trigger for auto-updating `updated_at`. Leads belong to Jobs (SET NULL on delete), OutreachMessages and LandingPages belong to Leads (CASCADE on delete). Lead inclui 9 campos de enriquecimento: `email`, `cnpj`, `razao_social`, `porte`, `cnae`, `data_fundacao` (Date), `socios` (JSON), `tech_stack` (JSON), `enrichment_sources` (JSON). Indexes em `email` e `cnpj` além dos existentes (status, nicho, cidade, opportunity_score).

### Frontend ↔ Backend

`lib/api.ts` is a typed fetch wrapper pointing at `NEXT_PUBLIC_API_URL`. All API calls go through it. Real-time job progress uses SSE via `EventSource` on `GET /api/jobs/{id}/stream`.

### Authentication

Better Auth (email/password, session-based). Frontend stores session in PostgreSQL via `lib/auth.ts`. Backend validates session tokens via `middleware/auth.py` against the same `session` table. Session lasts 30 days, cookie cache 7 days with auto-refresh on 401.

### Frontend Design System

Dark theme using CSS custom properties in `globals.css`. Fonts: Geist (headings + body), Geist Mono (mono) — loaded via `next/font/google`. Accent color is emerald (#34d399). Kanban board uses `@dnd-kit` for drag-and-drop. Marketing LP uses Remotion (hero) + Framer Motion (scroll animations).

## Development Commands

### Start local environment (backend + PostgreSQL)
```bash
docker compose up --build
```
Backend runs on http://localhost:8000 with hot-reload. PostgreSQL on port 5432.

### Start frontend dev server
```bash
cd frontend && npm install && npm run dev
```
Frontend runs on http://localhost:3000.

### Run backend tests
```bash
cd backend && pytest
```
Tests use SQLite in-memory DB (overrides the PostgreSQL dependency via `conftest.py`).

### Run frontend lint
```bash
cd frontend && npm run lint
```

### Create a new Alembic migration
```bash
cd backend && alembic revision --autogenerate -m "description"
```

### Apply migrations
```bash
cd backend && alembic upgrade head
```

## Environment Variables

**Backend** (`backend/.env`, see `backend/.env.example`):
- `DATABASE_URL` — PostgreSQL connection string
- `APIFY_TOKEN` — For Google Maps scraping
- `ANTHROPIC_API_KEY` / `LLM_API_KEY` — For LLM API (LP generation)
- `FRONTEND_URL` — Vercel frontend URL (added to CORS origins)
- `BUSINESS_NAME`, `YOUR_NAME`, `YOUR_WHATSAPP`, `YOUR_EMAIL`, `YOUR_WEBSITE` — Used in outreach message templates
- `HUNTER_API_KEY` — For email discovery via Hunter.io (optional)
- `APOLLO_API_KEY` — For contact enrichment via Apollo.io (optional)

**Frontend** (`frontend/.env.local`):
- `NEXT_PUBLIC_API_URL` — Backend URL (default: http://localhost:8000)
- `DATABASE_URL` — Same PostgreSQL as backend (needed by Better Auth server-side)

## Key Patterns

- Pipeline stages are independent modules in `backend/app/pipeline/`. Each has a main function that processes leads and updates the DB.
- Background tasks catch per-lead exceptions and log errors to `job.result_summary["errors"]` without stopping the entire job.
- O enriquecimento usa o padrão orchestrator (`pipeline/enrichment/orchestrator.py`) com providers plugáveis. O `enricher.py` legado ainda existe como thin wrapper via `enrich_lead_via_orchestrator()`. O scoring agora vive em `enrichment/scoring.py` e é aditivo: inclui sinais clássicos (SSL, responsividade, PageSpeed, etc.) mais sinais novos (tech stack defasado, email genérico, dados estruturados, empresa antiga com site ruim). Lead sem website = 95 pts.
- The root `Dockerfile` runs `alembic upgrade head` before starting uvicorn (migrations on deploy).
- CORS is configured in `main.py` to allow the frontend origin (`FRONTEND_URL` env var).
- Auth: Better Auth sessions validated by backend `middleware/auth.py`. Frontend sends Bearer token via Authorization header. Cookie cache auto-refreshes on 401.
- CSV import: `POST /api/pipeline/csv-import` accepts multipart form (file + nicho + cidade). Runs as background task like other pipeline stages.
- LP preview (`/lp/[id]`): public page with generated LP iframe + floating chat widget + blueprint + mission control, all fed by real enrichment data.
