# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SDR Machine is a sales development automation platform that scrapes Google Maps business listings, analyzes their web presence, generates personalized landing pages via Claude API, and creates WhatsApp outreach messages. The project is written in Portuguese (Brazilian) — UI text, variable names like `nicho`/`cidade`, and pipeline output are all in pt-BR.

## Architecture

**Backend:** FastAPI + SQLAlchemy + PostgreSQL 16 + Alembic (in `backend/`)
**Frontend:** Next.js 16 (App Router) + React 19 + TypeScript + Tailwind CSS 4 (in `frontend/`)
**Deployment:** Railway (backend via root Dockerfile) + Vercel (frontend)

### 4-Stage Pipeline

Each stage runs as a FastAPI background task, creating a `Job` record and streaming progress via SSE:

1. **Scrape** — Calls Apify Google Places API for each niche×city combination, deduplicates leads
2. **Enrich** — Crawls lead websites, checks SSL/responsiveness/PageSpeed, calculates opportunity score (0-100, higher = worse site = more opportunity)
3. **Generate** — Calls Claude API (claude-sonnet-4-20250514) to produce standalone HTML landing pages per lead
4. **Outreach** — Generates 3 WhatsApp messages per lead (initial, 48h followup, final) with pre-filled wa.me links

### Lead Status Flow

`scraped` → `enriched` → `lp_generated` → `outreach_ready` → `outreach_sent` → `responded` → `in_call` → `closed` → `delivered`

### Database Models

Three tables: `jobs`, `leads`, `outreach_messages`. Lead has a PostgreSQL trigger for auto-updating `updated_at`. Leads belong to Jobs (SET NULL on delete), OutreachMessages belong to Leads (CASCADE on delete).

### Frontend ↔ Backend

`lib/api.ts` is a typed fetch wrapper pointing at `NEXT_PUBLIC_API_URL`. All API calls go through it. Real-time job progress uses SSE via `EventSource` on `GET /api/jobs/{id}/stream`.

### Frontend Design System

Dark theme using CSS custom properties in `globals.css`. Three fonts: Outfit (headings), DM Sans (body), JetBrains Mono (mono). Accent color is emerald (#34d399). Kanban board uses `@dnd-kit` for drag-and-drop.

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
- `ANTHROPIC_API_KEY` — For Claude API (LP generation)
- `BUSINESS_NAME`, `YOUR_NAME`, `YOUR_WHATSAPP`, `YOUR_EMAIL`, `YOUR_WEBSITE` — Used in outreach message templates

**Frontend** (`frontend/.env.local`):
- `NEXT_PUBLIC_API_URL` — Backend URL (default: http://localhost:8000)

## Key Patterns

- Pipeline stages are independent modules in `backend/app/pipeline/`. Each has a main function that processes leads and updates the DB.
- Background tasks catch per-lead exceptions and log errors to `job.result_summary["errors"]` without stopping the entire job.
- The opportunity score in `enricher.py` is additive: points are given for missing SSL, no responsiveness, no CTA, poor PageSpeed, etc. A lead with no website at all scores 95.
- The root `Dockerfile` runs `alembic upgrade head` before starting uvicorn (migrations on deploy).
- CORS is configured in `main.py` to allow the frontend origin.
