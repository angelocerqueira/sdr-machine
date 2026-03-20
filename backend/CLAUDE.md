# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this backend.

## Stack

FastAPI 0.115 + SQLAlchemy 2.0 + PostgreSQL 16 + Alembic + Pydantic-settings + sse-starlette

External APIs: Apify (Google Maps scraping), Anthropic Claude (LP generation), Google PageSpeed Insights (free, no auth).

## Commands

```bash
# Run with Docker (from repo root)
docker compose up --build        # API on :8000 + PostgreSQL on :5432, hot-reload

# Run tests (SQLite in-memory, no Docker needed)
cd backend && pytest

# Migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Configuration (`app/config.py`)

Pydantic `BaseSettings` loading from `.env` (see `.env.example`). Key vars:

| Var | Default | Notes |
|-----|---------|-------|
| `DATABASE_URL` | `postgresql://...localhost:5432/sdr_machine` | |
| `APIFY_TOKEN` | (required) | Google Maps scraper |
| `ANTHROPIC_API_KEY` | (required) | Claude API for LP generation |
| `CLAUDE_MODEL` | `claude-sonnet-4-20250514` | Configurable |
| `FRONTEND_URL` | `http://localhost:3000` | Added to CORS origins |
| `API_URL` | `http://localhost:8000` | Used in LP preview links and outreach messages |
| `BUSINESS_NAME`, `YOUR_NAME`, `YOUR_WHATSAPP`, `YOUR_EMAIL`, `YOUR_WEBSITE` | Defaults in config | Used in landing pages and outreach templates |
| `TARGET_NICHES`, `TARGET_CITIES` | Lists in config | Default search parameters |
| `MIN_RATING` | 3.0 | Google Maps filter |
| `OPPORTUNITY_SCORE_THRESHOLD` | 40 | Lead qualification cutoff |

## Database Models (`app/models.py`)

Three tables: `jobs`, `leads`, `outreach_messages`.

- **Lead** has indexes on `status`, `nicho`, `cidade`, `opportunity_score`. Has a PostgreSQL trigger for auto-updating `updated_at` (created in the Alembic migration, not in app code).
- **Lead → OutreachMessages**: cascade delete. **Job → Leads**: SET NULL on delete.
- All schemas in `app/schemas.py` use `from_attributes = True` for ORM ↔ Pydantic conversion. `LeadSummaryOut` excludes `lp_html` to keep list responses small.

## API Routes

| Router | Prefix | Key endpoints |
|--------|--------|---------------|
| `routers/leads.py` | `/api/leads` | CRUD + filters (status, nicho, cidade, score_min) + `/lp` (returns HTML) + `/messages` |
| `routers/dashboard.py` | `/api/dashboard` | `/stats` — totals, avg score, leads_by_status, conversion_rate |
| `routers/settings.py` | `/api/settings` | Read-only config for frontend |
| `routers/pipeline.py` | `/api/pipeline` + `/api/jobs` | POST scrape/enrich/generate/outreach + job list/detail + SSE stream |

Health check: `GET /api/health`.

Status validation in `leads.py` uses a `VALID_STATUSES` set (13 values including failure states). Returns 422 on invalid status.

Pagination: `offset = (page-1) * per_page`, default page=1, per_page=20.

## Pipeline Architecture (`app/pipeline/`)

Each stage is a module with a main function, run as a **FastAPI BackgroundTask** (thread, not async):

### 1. Scraper (`scraper.py`)
- `scrape_all(nichos, cidades, max_results)` → iterates niche×city, calls Apify `compass/crawler-google-places` actor (sync run, 120s timeout)
- Deduplicates by phone or name. Filters by `min_rating`.
- Returns empty list on HTTP errors (silent fail).

### 2. Enricher (`enricher.py`)
- `enrich_lead_data(website)` → fetches site (10s timeout, first 15KB of HTML), runs BeautifulSoup analysis, calls PageSpeed API (1s sleep between calls for rate limiting)
- **Scoring algorithm** (0–100, higher = worse site = more opportunity):
  - No website → 95 pts. Site down → 85 pts.
  - No SSL +15, not responsive +15, no WhatsApp +10, no CTA +10, no analytics +8, no chatbot +8, PageSpeed <50 +10, thin content (<200 words) +10, template site +5, few images +5
  - Capped at 100. Each condition adds a reason string to `opportunity_reasons`.

### 3. Generator (`generator.py`)
- `generate_landing_page(lead_data)` → calls Claude API directly via httpx (not the SDK), 8000 max tokens, 120s timeout
- Prompt specifies 10 HTML requirements: standalone, responsive, niche-matched colors, sections (hero, stats, services, testimonial, CTA, footer), credibility banner with business info, CSS animations, no external deps except Google Fonts
- Strips markdown code fences from response if present. Returns empty string on failure.

### 4. Outreach (`outreach.py`)
- `generate_messages(lead_id, lead_data)` → produces 3 messages (initial, followup_48h, followup_final)
- Template-based (no AI). Differentiates between leads with a bad site vs no site at all.
- Generates pre-filled `wa.me` links with URL-encoded message text. Phone cleaned and prefixed with `55` (Brazil).

## Background Task & SSE Patterns

**In-memory event store**: `_job_events: dict[int, list[dict]]` in `pipeline.py`. Events auto-cleanup 60s after job completes via `threading.Timer`.

**Job runner pattern** (each `_run_*` function):
1. Creates fresh `SessionLocal()` (not request-scoped `get_db()` — avoids cross-thread session sharing)
2. Updates job status to "running", emits "started"
3. Loops over items, emits "progress" with current/total after each
4. On success: status="done", `result_summary={success, total, errors}`
5. On exception: `db.rollback()`, status="failed", `error_message` (truncated 500 chars), emits "error"
6. Always closes session in `finally`

Per-lead errors set `lead.status = "{stage}_failed"` but don't stop the job.

**SSE streaming**: `GET /api/jobs/{id}/stream` → `EventSourceResponse` yielding JSON events every 0.5s. Stops on "done"/"error" event.

## Testing (`tests/`)

- **Database**: SQLite in-memory, tables created/dropped per test via `setup_db` fixture
- **Fixtures**: `client` (TestClient with DB override), `sample_lead` (pre-populated lead)
- **Files**: `test_leads_api.py` (CRUD + filters), `test_dashboard_api.py` (stats), `test_pipeline_api.py` (job creation)
- Background tasks are mocked in pipeline tests

## Deployment

- Root `Dockerfile`: Python 3.12-slim, runs `alembic upgrade head` then uvicorn. Uses `$PORT` env var (Railway).
- `backend/Dockerfile`: Same but without migrations in CMD (for docker-compose dev).
- CORS: localhost:3000 + `FRONTEND_URL` from config.
