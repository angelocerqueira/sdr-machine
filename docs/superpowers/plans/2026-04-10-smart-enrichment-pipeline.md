# Smart Enrichment Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite `enricher.py` as a modular provider-based enrichment pipeline with smart orchestration that decides which providers to run based on available lead data, supports user override, and adds new providers (CNPJ, tech stack, schema.org, email, Apollo).

**Architecture:** Replace the monolithic `enricher.py` with an `enrichment/` package. An `EnrichmentOrchestrator` reads the lead, plans which providers to run in phases (discovery → crawl → contact → scoring), and executes them while sharing an `EnrichmentContext` (to reuse crawled HTML). Providers implement a common `BaseProvider` interface. Score calculation is moved to its own module and incorporates new signals. Old `enricher.py` becomes a thin wrapper that calls the orchestrator (backward-compat for the pipeline task runner).

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, pytest, BeautifulSoup, requests, Pydantic-settings. New free dependencies: nothing new for Python stdlib; Wappalyzer pattern detection is done inline (no external library). Freemium APIs: Hunter.io (HTTP), Apollo.io (HTTP). Brazilian CNPJ: BrasilAPI (HTTP).

---

## File Structure

### New files (backend)

```
backend/app/pipeline/enrichment/
  __init__.py                    # public exports: orchestrator, types
  base_provider.py               # BaseProvider ABC + EnrichmentContext + ProviderResult
  orchestrator.py                # EnrichmentOrchestrator: plan + execute providers
  scoring.py                     # calculate_score (new) — uses all provider data
  providers/
    __init__.py                  # registry of provider instances
    website_crawler.py           # WebsiteCrawlerProvider — wraps fetch_website + analyze_html + social + PageSpeed
    schema_extractor.py          # SchemaOrgProvider — parses JSON-LD from context.html_content
    tech_stack.py                # TechStackProvider — pattern-matches tech from HTML/headers
    tech_stack_patterns.py       # dict of {pattern_regex -> {name, category}}
    cnpj_enricher.py             # CnpjProvider — BrasilAPI/ReceitaWS
    email_discoverer.py          # EmailDiscovererProvider — regex + patterns + optional Hunter.io
    apollo_enricher.py           # ApolloProvider — Apollo.io Organization enrichment
```

### New tests (backend)

```
backend/tests/enrichment/
  __init__.py
  test_base_provider.py
  test_orchestrator.py
  test_scoring.py
  test_website_crawler_provider.py
  test_schema_extractor.py
  test_tech_stack.py
  test_cnpj_enricher.py
  test_email_discoverer.py
  test_apollo_enricher.py
```

### Modified files (backend)

- `backend/app/models.py` — add new Lead columns
- `backend/app/schemas.py` — add fields to `LeadBase`/`LeadOut`; add `skip_providers`/`force_providers` to `EnrichRequest`
- `backend/app/config.py` — add `hunter_api_key`, `apollo_api_key` settings
- `backend/app/routers/pipeline.py` — `_run_enrich` passes override params, reads provider list in summary
- `backend/app/pipeline/enricher.py` — reduced to a thin wrapper that calls `EnrichmentOrchestrator` (preserves `enrich_lead_data` signature for backward compat)
- `backend/tests/test_enricher.py` — keep the top-level integration tests of `enrich_lead_data`, adapt for new fields
- `backend/alembic/versions/` — new migration adding columns

### New migration

```
backend/alembic/versions/i02_smart_enrichment_fields.py
```

### Frontend files (modified)

- `frontend/src/lib/types.ts` — add new Lead fields + `EnrichRequest` override fields
- `frontend/src/lib/api.ts` — update `runEnrich` signature
- `frontend/src/components/pipeline-controls.tsx` (or equivalent) — add expandable "Fontes de Enriquecimento" section with toggles

---

## Happy Paths & Edge Cases Catalog

This catalog documents what the pipeline MUST handle correctly. Every item maps to
at least one test in the tasks below. If you add a new test, pin it to an item here.

### Happy Paths

| ID | Scenario | Covered in |
|----|----------|-----------|
| HP1 | Lead with full website → crawler + schema + tech + email + apollo → score | Task 16 integration test |
| HP2 | Lead with only CNPJ → CNPJ provider discovers website → crawler chain runs | Task 11 orchestrator tests |
| HP3 | Lead with website (no email) → email discoverer finds email in HTML | Task 9 email tests |
| HP4 | Re-enriching an existing lead → sources replaced (not appended), existing flat fields preserved | Task 11 orchestrator tests |
| HP5 | Lead with partial data (only nome + telefone) → orchestrator returns valid result with empty plan | Task 11 orchestrator tests |

### Edge Cases (must not break)

**Input normalization:**
- EC1: Website without scheme (`www.example.com`, `example.com.br`) — Task 5
- EC2: Website with trailing slash / query / fragment (`https://x.com/?utm=a`) — Task 5
- EC3: Empty-string website `""` (distinct from `None`) — Task 5 + Task 11
- EC4: CNPJ with mask (`12.345.678/0001-90`) vs unmasked (`12345678000190`) — Task 8
- EC5: Email in mixed case / with surrounding whitespace — Task 9

**Existing-data preservation (CRITICAL):**
- EC6: Lead already has `email` → discoverer must NOT overwrite — Task 11 orchestrator tests
- EC7: Lead already has `website` → CNPJ's `discovered_website` must NOT overwrite — Task 11
- EC8: Lead already has `cnpj` / `razao_social` → providers must NOT overwrite — Task 11

**Idempotency:**
- EC9: Re-running enrichment replaces (not appends) `enrichment_sources` — Task 13 (consumer-side), Task 11 (orchestrator-side returns a fresh list)
- EC10: Re-running replaces `tech_stack` snapshot entirely — Task 11

**Parsing edge cases:**
- EC11: JSON-LD `@graph` wrapper (Yoast/WordPress pattern) — Task 6
- EC12: JSON-LD top-level array — Task 6
- EC13: HTML empty string `""` — Task 6 + Task 7
- EC14: Email regex false positives (e.g. `foo@2x.png` in srcset) — Task 9

**API edge cases:**
- EC15: BrasilAPI 200 with empty body — Task 8
- EC16: Hunter.io 402 (payment required / quota exceeded) — Task 9
- EC17: Apollo 200 with `organization: null` — Task 10
- EC18: Provider request timeout — Task 5, Task 8

**Orchestration edge cases:**
- EC19: Empty plan (all providers skipped) → `execute` returns valid result with score — Task 11
- EC20: Provider returns something other than `ProviderResult` → record as error, continue — Task 11
- EC21: `force_providers` overlaps with `skip_providers` → skip wins (explicit skip > implicit force) — Task 11

---

## Task Ordering Strategy

Tasks are TDD and dependency-ordered:

1. **Task 1**: DB migration + model changes (foundation — everything depends on new columns)
2. **Task 2**: Config — add HUNTER_API_KEY / APOLLO_API_KEY
3. **Task 3**: `BaseProvider` + `EnrichmentContext` + `ProviderResult` types
4. **Task 4**: `scoring.py` — new score calculation
5. **Task 5**: `WebsiteCrawlerProvider` — wraps existing crawler logic
6. **Task 6**: `SchemaOrgProvider`
7. **Task 7**: `TechStackProvider` + patterns
8. **Task 8**: `CnpjProvider`
9. **Task 9**: `EmailDiscovererProvider`
10. **Task 10**: `ApolloProvider`
11. **Task 11**: `EnrichmentOrchestrator` — planning + execution
12. **Task 12**: Refactor `enricher.py` into thin wrapper
13. **Task 13**: Update `_run_enrich` in pipeline router to accept override params
14. **Task 14**: Update `EnrichRequest` schema + frontend types
15. **Task 15**: Frontend — provider toggles in enrich panel
16. **Task 16**: Integration test end-to-end

---

## Task 1: Database Migration — New Lead Fields

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/alembic/versions/i02_smart_enrichment_fields.py`
- Modify: `backend/tests/test_leads_api.py` (verify new fields appear)

- [ ] **Step 1: Add new columns to Lead model**

Edit `backend/app/models.py` — inside the `Lead` class, after `social_profiles` line, add:

```python
    email = Column(String(255))
    cnpj = Column(String(18))
    razao_social = Column(String(255))
    porte = Column(String(50))
    cnae = Column(String(100))
    data_fundacao = Column(Date)
    socios = Column(JSON, default=list)
    tech_stack = Column(JSON, default=list)
    enrichment_sources = Column(JSON, default=list)
```

And add `Date` to the import at the top:

```python
from sqlalchemy import (
    Boolean, Column, Integer, String, Text, Numeric,
    DateTime, Date, ForeignKey, Index, JSON, UniqueConstraint, func
)
```

Add these indexes to `__table_args__`:

```python
    __table_args__ = (
        Index("idx_leads_status", "status"),
        Index("idx_leads_nicho", "nicho"),
        Index("idx_leads_cidade", "cidade"),
        Index("idx_leads_score", "opportunity_score"),
        Index("idx_leads_email", "email"),
        Index("idx_leads_cnpj", "cnpj"),
    )
```

- [ ] **Step 2: Generate Alembic migration**

Run:
```bash
cd backend && alembic revision --autogenerate -m "add smart enrichment fields to leads"
```

This creates a new file in `backend/alembic/versions/`. Open it and verify the autogenerated `upgrade()` adds the 9 columns and 2 indexes. If anything is missing (Alembic can miss JSON defaults), write the migration manually as:

```python
"""add smart enrichment fields to leads

Revision ID: i02_smart_enrichment_fields
Revises: h01_better_auth_tables
Create Date: 2026-04-10

"""
from alembic import op
import sqlalchemy as sa


revision = "i02_smart_enrichment_fields"
down_revision = "h01_better_auth_tables"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("leads", sa.Column("email", sa.String(length=255), nullable=True))
    op.add_column("leads", sa.Column("cnpj", sa.String(length=18), nullable=True))
    op.add_column("leads", sa.Column("razao_social", sa.String(length=255), nullable=True))
    op.add_column("leads", sa.Column("porte", sa.String(length=50), nullable=True))
    op.add_column("leads", sa.Column("cnae", sa.String(length=100), nullable=True))
    op.add_column("leads", sa.Column("data_fundacao", sa.Date(), nullable=True))
    op.add_column("leads", sa.Column("socios", sa.JSON(), nullable=True, server_default="[]"))
    op.add_column("leads", sa.Column("tech_stack", sa.JSON(), nullable=True, server_default="[]"))
    op.add_column("leads", sa.Column("enrichment_sources", sa.JSON(), nullable=True, server_default="[]"))
    op.create_index("idx_leads_email", "leads", ["email"])
    op.create_index("idx_leads_cnpj", "leads", ["cnpj"])


def downgrade():
    op.drop_index("idx_leads_cnpj", table_name="leads")
    op.drop_index("idx_leads_email", table_name="leads")
    op.drop_column("leads", "enrichment_sources")
    op.drop_column("leads", "tech_stack")
    op.drop_column("leads", "socios")
    op.drop_column("leads", "data_fundacao")
    op.drop_column("leads", "cnae")
    op.drop_column("leads", "porte")
    op.drop_column("leads", "razao_social")
    op.drop_column("leads", "cnpj")
    op.drop_column("leads", "email")
```

Verify `down_revision` matches the actual latest migration id shown by `alembic heads`. If `h01_better_auth_tables` is not the latest, replace with the correct id.

- [ ] **Step 3: Update `LeadBase` and `LeadOut` in schemas.py**

Edit `backend/app/schemas.py` — update `LeadBase`:

```python
class LeadBase(BaseModel):
    nome: str
    telefone: str | None = None
    email: str | None = None
    website: str | None = None
    endereco: str | None = None
    cidade: str | None = None
    nicho: str | None = None
    categoria: str | None = None
    rating: float | None = None
    reviews_count: int = 0
    google_maps_url: str | None = None
    top_reviews: list[str] = []
    cnpj: str | None = None
    razao_social: str | None = None
    porte: str | None = None
    cnae: str | None = None
    data_fundacao: str | None = None  # ISO date as string for JSON serialization
    socios: list = []
```

Update `LeadOut` to include the new enrichment fields (inherits `LeadBase`, so only add the non-base ones):

```python
class LeadOut(LeadBase):
    id: int
    public_id: str
    status: str
    opportunity_score: int | None = None
    opportunity_reasons: list[str] = []
    site_analysis: dict = {}
    social_profiles: dict = {}
    tech_stack: list = []
    enrichment_sources: list = []
    lp_html: str | None = None
    job_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

Also update `LeadSummaryOut` to include the new enrichment fields (copy same additions except `lp_html`).

- [ ] **Step 4: Run tests to verify schema still validates**

Run:
```bash
cd backend && pytest tests/test_leads_api.py -v
```

Expected: PASS (existing tests should still pass — new fields are all optional).

- [ ] **Step 5: Apply the migration to local DB**

Run:
```bash
cd backend && alembic upgrade head
```

Expected: Migration applies successfully. If running against Docker Postgres, restart the container first or run inside it.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models.py backend/app/schemas.py backend/alembic/versions/i02_smart_enrichment_fields.py
git commit -m "feat(db): add smart enrichment fields to leads table"
```

---

## Task 2: Config — Add Freemium API Keys

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/.env.example`

- [ ] **Step 1: Add HUNTER_API_KEY and APOLLO_API_KEY settings**

Edit `backend/app/config.py` — add after `langsmith_tracing` line:

```python
    hunter_api_key: str = ""
    apollo_api_key: str = ""
```

- [ ] **Step 2: Add example values to .env.example**

Read `backend/.env.example` first, then append:

```
# Optional enrichment providers
HUNTER_API_KEY=
APOLLO_API_KEY=
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/config.py backend/.env.example
git commit -m "feat(config): add HUNTER_API_KEY and APOLLO_API_KEY settings"
```

---

## Task 3: BaseProvider + EnrichmentContext

**Files:**
- Create: `backend/app/pipeline/enrichment/__init__.py`
- Create: `backend/app/pipeline/enrichment/base_provider.py`
- Create: `backend/tests/enrichment/__init__.py`
- Create: `backend/tests/enrichment/test_base_provider.py`

- [ ] **Step 1: Create empty package init files**

Create `backend/app/pipeline/enrichment/__init__.py` as an empty file (1 blank line).

Create `backend/tests/enrichment/__init__.py` as an empty file.

- [ ] **Step 2: Write failing test for BaseProvider contract**

Create `backend/tests/enrichment/test_base_provider.py`:

```python
"""Tests for BaseProvider ABC and helper types."""
import pytest
from app.pipeline.enrichment.base_provider import (
    BaseProvider,
    EnrichmentContext,
    ProviderResult,
)


def test_enrichment_context_defaults():
    ctx = EnrichmentContext()
    assert ctx.html_content is None
    assert ctx.response_headers == {}
    assert ctx.discovered_website is None


def test_enrichment_context_with_values():
    ctx = EnrichmentContext(
        html_content="<html></html>",
        response_headers={"Server": "nginx"},
        discovered_website="https://example.com",
    )
    assert ctx.html_content == "<html></html>"
    assert ctx.response_headers == {"Server": "nginx"}
    assert ctx.discovered_website == "https://example.com"


def test_provider_result_success():
    result = ProviderResult(
        success=True,
        data={"email": "a@b.com"},
        errors=[],
        source="email_discoverer",
    )
    assert result.success is True
    assert result.data == {"email": "a@b.com"}
    assert result.errors == []
    assert result.source == "email_discoverer"


def test_provider_result_failure():
    result = ProviderResult(
        success=False,
        data={},
        errors=["HTTP 500"],
        source="apollo",
    )
    assert result.success is False
    assert result.errors == ["HTTP 500"]


def test_base_provider_is_abstract():
    with pytest.raises(TypeError):
        BaseProvider()  # type: ignore


class _DummyProvider(BaseProvider):
    name = "dummy"
    display_name = "Dummy Provider"
    required_fields = ["website"]
    cost = "free"

    def can_run(self, lead) -> bool:
        return bool(getattr(lead, "website", None))

    def run(self, lead, context):
        return ProviderResult(
            success=True,
            data={"site_analysis": {"dummy": True}},
            errors=[],
            source=self.name,
        )


def test_provider_can_run_true():
    class FakeLead:
        website = "https://example.com"
    provider = _DummyProvider()
    assert provider.can_run(FakeLead()) is True


def test_provider_can_run_false():
    class FakeLead:
        website = None
    provider = _DummyProvider()
    assert provider.can_run(FakeLead()) is False


def test_provider_run_returns_result():
    class FakeLead:
        website = "https://example.com"
    provider = _DummyProvider()
    ctx = EnrichmentContext()
    result = provider.run(FakeLead(), ctx)
    assert result.success is True
    assert result.source == "dummy"
```

- [ ] **Step 3: Run test to verify it fails**

Run:
```bash
cd backend && pytest tests/enrichment/test_base_provider.py -v
```

Expected: FAIL with `ImportError: cannot import name 'BaseProvider'`.

- [ ] **Step 4: Implement base_provider.py**

Create `backend/app/pipeline/enrichment/base_provider.py`:

```python
"""Base types for enrichment providers."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import Lead


@dataclass
class EnrichmentContext:
    """Mutable context shared between providers during a single enrichment run.

    Providers can read values set by earlier providers (e.g. html_content from
    the Website Crawler) and write values for later providers to consume.
    """
    html_content: str | None = None
    response_headers: dict = field(default_factory=dict)
    discovered_website: str | None = None


@dataclass
class ProviderResult:
    """Result returned by a provider's run() method.

    - `data`: fields to merge into the Lead (keys should match Lead column names
      or nested dicts like `site_analysis`).
    - `errors`: non-fatal errors (do not stop subsequent providers).
    - `source`: provider name, used to build `enrichment_sources` audit trail.
    """
    success: bool
    data: dict
    errors: list[str]
    source: str


class BaseProvider(ABC):
    """Abstract base class for enrichment providers.

    Subclasses must set class attributes `name`, `display_name`,
    `required_fields`, `cost` and implement `can_run` and `run`.
    """
    name: str = ""
    display_name: str = ""
    required_fields: list[str] = []
    cost: str = "free"  # "free" | "freemium"

    @abstractmethod
    def can_run(self, lead: "Lead") -> bool:
        """Return True if the provider has the minimum data it needs."""

    @abstractmethod
    def run(self, lead: "Lead", context: EnrichmentContext) -> ProviderResult:
        """Execute enrichment. Should not raise — catch exceptions and return a
        ProviderResult with success=False and the error in `errors`.
        """
```

- [ ] **Step 5: Run test to verify pass**

Run:
```bash
cd backend && pytest tests/enrichment/test_base_provider.py -v
```

Expected: PASS (8 tests).

- [ ] **Step 6: Commit**

```bash
git add backend/app/pipeline/enrichment/__init__.py \
        backend/app/pipeline/enrichment/base_provider.py \
        backend/tests/enrichment/__init__.py \
        backend/tests/enrichment/test_base_provider.py
git commit -m "feat(enrichment): add BaseProvider ABC and context types"
```

---

## Task 4: Scoring Module

**Files:**
- Create: `backend/app/pipeline/enrichment/scoring.py`
- Create: `backend/tests/enrichment/test_scoring.py`

- [ ] **Step 1: Write failing tests for scoring**

Create `backend/tests/enrichment/test_scoring.py`:

```python
"""Tests for the enrichment scoring algorithm."""
from app.pipeline.enrichment.scoring import calculate_score


def test_no_website_base_score():
    lead_data = {"website": None}
    site_analysis = {}
    score, reasons = calculate_score(lead_data, site_analysis)
    assert score >= 40
    assert any("Sem website" in r for r in reasons)


def test_perfect_site_low_score():
    lead_data = {"website": "https://example.com", "email": "contato@example.com"}
    site_analysis = {
        "status": "ok",
        "has_ssl": True,
        "has_responsive_meta": True,
        "has_cta": True,
        "has_social_links": True,
        "pagespeed": 90,
        "structured_data": {"type": "LocalBusiness"},
    }
    score, reasons = calculate_score(lead_data, site_analysis)
    assert score <= 10
    assert reasons == [] or all("Sem" not in r for r in reasons)


def test_bad_site_accumulates_points():
    lead_data = {"website": "http://example.com", "email": "fulano@gmail.com"}
    site_analysis = {
        "status": "ok",
        "has_ssl": False,
        "has_responsive_meta": False,
        "has_cta": False,
        "has_social_links": False,
        "pagespeed": 30,
    }
    score, reasons = calculate_score(lead_data, site_analysis)
    # SSL 15 + responsive 15 + CTA 10 + PageSpeed 10 + social 5 + gmail 5 + no structured 3 = 63
    assert score >= 60
    assert any("SSL" in r or "HTTPS" in r for r in reasons)
    assert any("responsivo" in r.lower() for r in reasons)


def test_tech_stack_dated_adds_points():
    lead_data = {"website": "https://example.com"}
    site_analysis = {
        "status": "ok",
        "has_ssl": True,
        "has_responsive_meta": True,
        "has_cta": True,
        "has_social_links": True,
        "pagespeed": 90,
    }
    tech_stack = [{"name": "Adobe Flash", "category": "runtime"}]
    score, reasons = calculate_score(lead_data, site_analysis, tech_stack=tech_stack)
    assert any("defasado" in r.lower() or "flash" in r.lower() for r in reasons)


def test_score_capped_at_100():
    lead_data = {"website": None, "email": "x@gmail.com"}
    site_analysis = {"status": "no_website"}
    tech_stack = [{"name": "Adobe Flash", "category": "runtime"}]
    score, _ = calculate_score(lead_data, site_analysis, tech_stack=tech_stack)
    assert score <= 100


def test_gmail_email_adds_points():
    lead_data = {"website": "https://example.com", "email": "fulano@gmail.com"}
    site_analysis = {
        "status": "ok",
        "has_ssl": True,
        "has_responsive_meta": True,
        "has_cta": True,
        "has_social_links": True,
        "pagespeed": 90,
    }
    score_with_gmail, reasons = calculate_score(lead_data, site_analysis)
    lead_data_pro = {"website": "https://example.com", "email": "contato@example.com"}
    score_pro, _ = calculate_score(lead_data_pro, site_analysis)
    assert score_with_gmail > score_pro
    assert any("email" in r.lower() for r in reasons)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd backend && pytest tests/enrichment/test_scoring.py -v
```

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement scoring.py**

Create `backend/app/pipeline/enrichment/scoring.py`:

```python
"""Opportunity score calculation — replaces the algorithm in enricher.py.

Score is additive (higher = worse site = more opportunity) and capped at 100.
See docs/superpowers/specs/2026-04-10-smart-enrichment-pipeline-design.md §5.
"""
from datetime import date


_GENERIC_EMAIL_DOMAINS = {
    "gmail.com", "hotmail.com", "yahoo.com", "outlook.com", "yahoo.com.br",
    "bol.com.br", "uol.com.br", "live.com", "icloud.com",
}


_DATED_TECH_NAMES = {"adobe flash", "flash", "silverlight", "jquery 1", "jquery 2"}


def _is_generic_email(email: str | None) -> bool:
    if not email or "@" not in email:
        return False
    domain = email.split("@", 1)[1].strip().lower()
    return domain in _GENERIC_EMAIL_DOMAINS


def _has_dated_tech(tech_stack: list[dict] | None) -> bool:
    if not tech_stack:
        return False
    for tech in tech_stack:
        name = (tech.get("name") or "").lower()
        if any(dated in name for dated in _DATED_TECH_NAMES):
            return True
    return False


def calculate_score(
    lead_data: dict,
    site_analysis: dict,
    tech_stack: list[dict] | None = None,
    data_fundacao: date | None = None,
) -> tuple[int, list[str]]:
    """Calculate opportunity score from all enrichment data.

    Args:
        lead_data: dict with Lead fields (website, email, ...)
        site_analysis: dict produced by WebsiteCrawlerProvider
        tech_stack: list of {name, category} detected by TechStackProvider
        data_fundacao: company founding date from CNPJ provider

    Returns:
        (score, reasons) — score capped at 100
    """
    score = 0
    reasons: list[str] = []

    website = lead_data.get("website")
    status = site_analysis.get("status")

    # Base: no website
    if not website or status == "no_website":
        score += 40
        reasons.append("Sem website — oportunidade alta")

    # Site down / broken
    if status in ("connection_error", "timeout", "ssl_error"):
        score += 30
        reasons.append(f"Site com problemas técnicos: {status}")

    if website and status == "ok":
        if not site_analysis.get("has_ssl"):
            score += 15
            reasons.append("Sem HTTPS/SSL")

        if not site_analysis.get("has_responsive_meta"):
            score += 15
            reasons.append("Site não é responsivo (mobile)")

        if not site_analysis.get("has_cta"):
            score += 10
            reasons.append("Sem CTA claro (call-to-action)")

        if not site_analysis.get("has_social_links"):
            score += 5
            reasons.append("Sem links para redes sociais")

        pagespeed = site_analysis.get("pagespeed")
        if pagespeed is not None and pagespeed < 50:
            score += 10
            reasons.append(f"PageSpeed baixo ({pagespeed}/100)")

        if not site_analysis.get("structured_data"):
            score += 3
            reasons.append("Sem dados estruturados (schema.org)")

    # Tech stack signals
    if _has_dated_tech(tech_stack):
        score += 5
        reasons.append("Tech stack defasado detectado")

    # Email quality signal
    if _is_generic_email(lead_data.get("email")):
        score += 5
        reasons.append("Email não profissional (gmail/hotmail/etc)")

    # Established company with bad score
    if data_fundacao and score >= 50:
        try:
            years_old = date.today().year - data_fundacao.year
            if years_old >= 5:
                score += 2
                reasons.append(f"Empresa com {years_old} anos mas presença digital fraca")
        except Exception:
            pass

    return min(score, 100), reasons
```

- [ ] **Step 4: Run tests to verify pass**

Run:
```bash
cd backend && pytest tests/enrichment/test_scoring.py -v
```

Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/enrichment/scoring.py backend/tests/enrichment/test_scoring.py
git commit -m "feat(enrichment): add new opportunity score calculation module"
```

---

## Task 5: Website Crawler Provider

**Files:**
- Create: `backend/app/pipeline/enrichment/providers/__init__.py`
- Create: `backend/app/pipeline/enrichment/providers/website_crawler.py`
- Create: `backend/tests/enrichment/test_website_crawler_provider.py`

- [ ] **Step 1: Create providers package init**

Create `backend/app/pipeline/enrichment/providers/__init__.py` as empty file.

- [ ] **Step 2: Write failing tests**

Create `backend/tests/enrichment/test_website_crawler_provider.py`:

```python
"""Tests for WebsiteCrawlerProvider."""
from unittest.mock import patch, MagicMock

from app.pipeline.enrichment.base_provider import EnrichmentContext
from app.pipeline.enrichment.providers.website_crawler import WebsiteCrawlerProvider


class FakeLead:
    def __init__(self, website=None, nome="Test", nicho=None, cidade=None,
                 categoria=None, rating=None, reviews_count=0, top_reviews=None):
        self.website = website
        self.nome = nome
        self.nicho = nicho
        self.cidade = cidade
        self.categoria = categoria
        self.rating = rating
        self.reviews_count = reviews_count
        self.top_reviews = top_reviews or []


def test_can_run_with_website():
    lead = FakeLead(website="https://example.com")
    provider = WebsiteCrawlerProvider()
    assert provider.can_run(lead) is True


def test_can_run_without_website_uses_context():
    lead = FakeLead(website=None)
    provider = WebsiteCrawlerProvider()
    ctx = EnrichmentContext(discovered_website="https://found.com")
    # can_run can use context
    assert provider.can_run(lead, context=ctx) is True


def test_cannot_run_without_any_website():
    lead = FakeLead(website=None)
    provider = WebsiteCrawlerProvider()
    assert provider.can_run(lead) is False


@patch("app.pipeline.enrichment.providers.website_crawler.requests.get")
def test_run_populates_context_html(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><head><meta name=\"viewport\"></head><body></body></html>"
    mock_resp.url = "https://example.com"
    mock_resp.headers = {"Server": "nginx"}
    mock_get.return_value = mock_resp

    provider = WebsiteCrawlerProvider()
    lead = FakeLead(website="https://example.com")
    ctx = EnrichmentContext()

    with patch("app.pipeline.enrichment.providers.website_crawler.check_pagespeed",
               return_value={"performance_score": 80}):
        result = provider.run(lead, ctx)

    assert result.success is True
    assert ctx.html_content is not None
    assert "<html>" in ctx.html_content
    assert ctx.response_headers.get("Server") == "nginx"
    assert result.data["site_analysis"]["has_ssl"] is True


@patch("app.pipeline.enrichment.providers.website_crawler.requests.get")
def test_run_handles_connection_error(mock_get):
    import requests
    mock_get.side_effect = requests.exceptions.ConnectionError("boom")

    provider = WebsiteCrawlerProvider()
    lead = FakeLead(website="https://example.com")
    ctx = EnrichmentContext()
    result = provider.run(lead, ctx)

    # Not fatal — still success but with error status in data
    assert result.data["site_analysis"]["status"] == "connection_error"


@patch("app.pipeline.enrichment.providers.website_crawler.requests.get")
def test_run_handles_timeout(mock_get):
    import requests
    mock_get.side_effect = requests.exceptions.Timeout("slow")

    provider = WebsiteCrawlerProvider()
    lead = FakeLead(website="https://example.com")
    ctx = EnrichmentContext()
    result = provider.run(lead, ctx)
    assert result.data["site_analysis"]["status"] == "timeout"


# --- EC1, EC2, EC3: URL normalization ---

@patch("app.pipeline.enrichment.providers.website_crawler.requests.get")
def test_url_without_scheme_is_prefixed_with_https(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html></html>"
    mock_resp.url = "https://www.example.com"
    mock_resp.headers = {}
    mock_get.return_value = mock_resp

    provider = WebsiteCrawlerProvider()
    lead = FakeLead(website="www.example.com")
    ctx = EnrichmentContext()

    with patch("app.pipeline.enrichment.providers.website_crawler.check_pagespeed",
               return_value={"performance_score": 50}):
        provider.run(lead, ctx)

    called_url = mock_get.call_args[0][0]
    assert called_url.startswith("https://")


def test_empty_website_string_treated_as_missing():
    provider = WebsiteCrawlerProvider()
    lead = FakeLead(website="")
    assert provider.can_run(lead) is False


@patch("app.pipeline.enrichment.providers.website_crawler.requests.get")
def test_url_with_path_and_query_preserved(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html></html>"
    mock_resp.url = "https://x.com/about?ref=ad"
    mock_resp.headers = {}
    mock_get.return_value = mock_resp

    provider = WebsiteCrawlerProvider()
    lead = FakeLead(website="https://x.com/about?ref=ad")
    ctx = EnrichmentContext()

    with patch("app.pipeline.enrichment.providers.website_crawler.check_pagespeed",
               return_value={"performance_score": 50}):
        provider.run(lead, ctx)

    called_url = mock_get.call_args[0][0]
    assert called_url == "https://x.com/about?ref=ad"
```

- [ ] **Step 3: Run tests to verify they fail**

Run:
```bash
cd backend && pytest tests/enrichment/test_website_crawler_provider.py -v
```

Expected: FAIL with `ImportError`.

- [ ] **Step 4: Implement WebsiteCrawlerProvider**

Create `backend/app/pipeline/enrichment/providers/website_crawler.py`:

```python
"""Website Crawler Provider — fetches site HTML, analyzes SSL/responsive/CTA,
runs PageSpeed, extracts social URLs. Reuses the existing logic from the legacy
enricher module (fetch_website, analyze_html, check_pagespeed, scrape_social_profiles).

Populates context.html_content and context.response_headers for downstream providers.
"""
from __future__ import annotations

import time
import logging
import requests

from app.pipeline.enrichment.base_provider import (
    BaseProvider,
    EnrichmentContext,
    ProviderResult,
)
from app.pipeline.enricher import (
    analyze_html,
    check_pagespeed,
    scrape_social_profiles,
)
from app.config import settings

logger = logging.getLogger(__name__)


def _normalize_url(value: str | None) -> str | None:
    """Normalize a website value into a crawlable URL.

    Returns None for empty / None. Preserves path/query/fragment. Adds https://
    if no scheme is present.
    """
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    if value.startswith(("http://", "https://")):
        return value
    return f"https://{value}"


class WebsiteCrawlerProvider(BaseProvider):
    name = "website_crawler"
    display_name = "Website Crawler"
    required_fields = ["website"]
    cost = "free"

    def can_run(self, lead, context: EnrichmentContext | None = None) -> bool:
        if _normalize_url(getattr(lead, "website", None)):
            return True
        if context and _normalize_url(context.discovered_website):
            return True
        return False

    def run(self, lead, context: EnrichmentContext) -> ProviderResult:
        website = getattr(lead, "website", None) or (context.discovered_website if context else None)
        site_data: dict = {}
        html = ""

        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            html = resp.text[:15000]
            context.html_content = html
            context.response_headers = dict(resp.headers)
            site_data = {
                "status": "ok",
                "status_code": resp.status_code,
                "final_url": resp.url,
                "has_ssl": resp.url.startswith("https"),
                "content_length": len(resp.text),
            }
        except requests.exceptions.SSLError:
            site_data = {"status": "ssl_error", "has_ssl": False}
            errors.append("ssl_error")
        except requests.exceptions.ConnectionError:
            site_data = {"status": "connection_error", "error": "Site fora do ar"}
            errors.append("connection_error")
        except requests.exceptions.Timeout:
            site_data = {"status": "timeout", "error": "Site muito lento"}
            errors.append("timeout")
        except Exception as exc:
            site_data = {"status": "error", "error": str(exc)[:100]}
            errors.append(str(exc)[:100])

        html_analysis = analyze_html(html)

        pagespeed: dict = {}
        if site_data.get("status") == "ok":
            try:
                pagespeed = check_pagespeed(url)
                time.sleep(1)
            except Exception as exc:
                errors.append(f"pagespeed: {str(exc)[:100]}")

        site_analysis = {
            "status": site_data.get("status"),
            "has_ssl": site_data.get("has_ssl"),
            **html_analysis,
            "pagespeed": pagespeed.get("performance_score"),
        }

        social_profiles: dict = {}
        if settings.apify_token and not settings.skip_social_scraping:
            try:
                lead_info = {
                    "nome": getattr(lead, "nome", ""),
                    "cidade": getattr(lead, "cidade", ""),
                }
                social_profiles = scrape_social_profiles(
                    lead_info, html_analysis.get("social_urls", {})
                )
            except Exception as exc:
                errors.append(f"social: {str(exc)[:100]}")

        data = {
            "site_analysis": site_analysis,
            "social_profiles": social_profiles,
        }

        return ProviderResult(
            success=site_data.get("status") == "ok",
            data=data,
            errors=errors,
            source=self.name,
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run:
```bash
cd backend && pytest tests/enrichment/test_website_crawler_provider.py -v
```

Expected: PASS (5 tests).

- [ ] **Step 6: Commit**

```bash
git add backend/app/pipeline/enrichment/providers/__init__.py \
        backend/app/pipeline/enrichment/providers/website_crawler.py \
        backend/tests/enrichment/test_website_crawler_provider.py
git commit -m "feat(enrichment): add WebsiteCrawlerProvider"
```

---

## Task 6: Schema.org Extractor Provider

**Files:**
- Create: `backend/app/pipeline/enrichment/providers/schema_extractor.py`
- Create: `backend/tests/enrichment/test_schema_extractor.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/enrichment/test_schema_extractor.py`:

```python
"""Tests for SchemaOrgProvider."""
from app.pipeline.enrichment.base_provider import EnrichmentContext
from app.pipeline.enrichment.providers.schema_extractor import SchemaOrgProvider


class FakeLead:
    pass


HTML_WITH_JSONLD = """
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  "name": "Clinic XYZ",
  "telephone": "+554999887766",
  "openingHours": "Mo-Fr 08:00-18:00",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "Rua das Flores 123",
    "addressLocality": "Chapecó"
  }
}
</script>
</head><body></body></html>
"""

HTML_WITHOUT_JSONLD = "<html><body><p>nothing</p></body></html>"


def test_cannot_run_without_html():
    provider = SchemaOrgProvider()
    ctx = EnrichmentContext()
    assert provider.can_run(FakeLead(), context=ctx) is False


def test_can_run_with_html():
    provider = SchemaOrgProvider()
    ctx = EnrichmentContext(html_content="<html></html>")
    assert provider.can_run(FakeLead(), context=ctx) is True


def test_extracts_jsonld():
    provider = SchemaOrgProvider()
    ctx = EnrichmentContext(html_content=HTML_WITH_JSONLD)
    result = provider.run(FakeLead(), ctx)
    assert result.success is True
    structured = result.data["site_analysis"]["structured_data"]
    assert structured["type"] == "LocalBusiness"
    assert "Clinic XYZ" in structured.get("name", "")


def test_handles_no_jsonld():
    provider = SchemaOrgProvider()
    ctx = EnrichmentContext(html_content=HTML_WITHOUT_JSONLD)
    result = provider.run(FakeLead(), ctx)
    # Not an error — just nothing to extract
    assert result.success is True
    assert result.data["site_analysis"]["structured_data"] in (None, {}, [])


def test_handles_malformed_jsonld():
    bad_html = '<script type="application/ld+json">{not json}</script>'
    provider = SchemaOrgProvider()
    ctx = EnrichmentContext(html_content=bad_html)
    result = provider.run(FakeLead(), ctx)
    # Should not raise
    assert result.success is True


# --- EC11: @graph wrapper ---

def test_extracts_jsonld_with_graph_wrapper():
    html = """
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@graph": [
        {"@type": "WebSite", "name": "Site X"},
        {"@type": "LocalBusiness", "name": "Clinic X", "telephone": "+554999"}
      ]
    }
    </script>
    """
    provider = SchemaOrgProvider()
    ctx = EnrichmentContext(html_content=html)
    result = provider.run(FakeLead(), ctx)
    structured = result.data["site_analysis"]["structured_data"]
    # Prefer LocalBusiness over WebSite
    assert structured["type"] == "LocalBusiness"
    assert structured["name"] == "Clinic X"


# --- EC12: top-level array ---

def test_extracts_jsonld_top_level_array():
    html = """
    <script type="application/ld+json">
    [
      {"@type": "Organization", "name": "Org A"},
      {"@type": "LocalBusiness", "name": "Clinic Y"}
    ]
    </script>
    """
    provider = SchemaOrgProvider()
    ctx = EnrichmentContext(html_content=html)
    result = provider.run(FakeLead(), ctx)
    structured = result.data["site_analysis"]["structured_data"]
    assert structured["type"] in ("Organization", "LocalBusiness")


# --- EC13: empty html string ---

def test_empty_string_html():
    provider = SchemaOrgProvider()
    ctx = EnrichmentContext(html_content="")
    # can_run returns False for empty string (distinct from None)
    assert provider.can_run(FakeLead(), context=ctx) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd backend && pytest tests/enrichment/test_schema_extractor.py -v
```

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement SchemaOrgProvider**

Create `backend/app/pipeline/enrichment/providers/schema_extractor.py`:

```python
"""Schema.org Extractor — parses JSON-LD scripts from crawled HTML."""
from __future__ import annotations

import json
import logging
from bs4 import BeautifulSoup

from app.pipeline.enrichment.base_provider import (
    BaseProvider,
    EnrichmentContext,
    ProviderResult,
)

logger = logging.getLogger(__name__)


# Prefer these @types when multiple blocks are present (higher = preferred)
_TYPE_PRIORITY = {
    "LocalBusiness": 100,
    "Restaurant": 95,
    "MedicalBusiness": 95,
    "Store": 90,
    "Organization": 80,
    "Corporation": 80,
    "WebSite": 20,
    "WebPage": 10,
}


def _score_type(type_value) -> int:
    if isinstance(type_value, list) and type_value:
        type_value = type_value[0]
    if not isinstance(type_value, str):
        return 0
    return _TYPE_PRIORITY.get(type_value, 50)


def _flatten_candidates(data) -> list[dict]:
    """Return all dict candidates from a JSON-LD payload (handles @graph and arrays)."""
    if isinstance(data, list):
        out: list[dict] = []
        for item in data:
            out.extend(_flatten_candidates(item))
        return out
    if isinstance(data, dict):
        if "@graph" in data and isinstance(data["@graph"], list):
            return _flatten_candidates(data["@graph"])
        return [data]
    return []


def _build_structured(data: dict) -> dict:
    t = data.get("@type") or data.get("type") or ""
    return {
        "type": t if isinstance(t, str) else (t[0] if t else ""),
        "name": data.get("name", ""),
        "telephone": data.get("telephone", ""),
        "opening_hours": data.get("openingHours", ""),
        "address": data.get("address", {}),
        "raw": data,
    }


class SchemaOrgProvider(BaseProvider):
    name = "schema_extractor"
    display_name = "Schema.org Extractor"
    required_fields = []  # consumes context.html_content
    cost = "free"

    def can_run(self, lead, context: EnrichmentContext | None = None) -> bool:
        # Empty string is treated as "no html" (EC13)
        return bool(context and context.html_content)

    def run(self, lead, context: EnrichmentContext) -> ProviderResult:
        html = (context.html_content or "") if context else ""
        if not html:
            return ProviderResult(
                success=True,
                data={"site_analysis": {"structured_data": None}},
                errors=[],
                source=self.name,
            )

        candidates: list[dict] = []
        errors: list[str] = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            for script in soup.find_all("script", {"type": "application/ld+json"}):
                try:
                    text = script.string or script.get_text() or ""
                    if not text.strip():
                        continue
                    parsed = json.loads(text)
                    candidates.extend(_flatten_candidates(parsed))
                except (json.JSONDecodeError, ValueError) as exc:
                    errors.append(f"jsonld parse: {str(exc)[:80]}")
                    continue
        except Exception as exc:
            errors.append(f"soup: {str(exc)[:80]}")

        # Pick best candidate by type priority
        best = None
        best_score = -1
        for c in candidates:
            s = _score_type(c.get("@type") or c.get("type"))
            if s > best_score:
                best = c
                best_score = s

        structured = _build_structured(best) if best else {}

        return ProviderResult(
            success=True,
            data={"site_analysis": {"structured_data": structured}},
            errors=errors,
            source=self.name,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd backend && pytest tests/enrichment/test_schema_extractor.py -v
```

Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/enrichment/providers/schema_extractor.py \
        backend/tests/enrichment/test_schema_extractor.py
git commit -m "feat(enrichment): add SchemaOrgProvider for JSON-LD extraction"
```

---

## Task 7: Tech Stack Provider

**Files:**
- Create: `backend/app/pipeline/enrichment/providers/tech_stack_patterns.py`
- Create: `backend/app/pipeline/enrichment/providers/tech_stack.py`
- Create: `backend/tests/enrichment/test_tech_stack.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/enrichment/test_tech_stack.py`:

```python
"""Tests for TechStackProvider."""
from app.pipeline.enrichment.base_provider import EnrichmentContext
from app.pipeline.enrichment.providers.tech_stack import TechStackProvider


class FakeLead:
    pass


def test_cannot_run_without_html():
    provider = TechStackProvider()
    assert provider.can_run(FakeLead(), context=EnrichmentContext()) is False


def test_cannot_run_with_empty_string_html():
    # EC13: empty string is treated as "no html"
    provider = TechStackProvider()
    ctx = EnrichmentContext(html_content="")
    assert provider.can_run(FakeLead(), context=ctx) is False


def test_detects_wordpress():
    html = '<html><head><link rel="stylesheet" href="/wp-content/themes/x.css"></head></html>'
    ctx = EnrichmentContext(html_content=html)
    provider = TechStackProvider()
    result = provider.run(FakeLead(), ctx)
    assert result.success is True
    names = [t["name"] for t in result.data["tech_stack"]]
    assert "WordPress" in names


def test_detects_google_analytics():
    html = '<html><head><script src="https://www.googletagmanager.com/gtag/js"></script></head></html>'
    ctx = EnrichmentContext(html_content=html)
    provider = TechStackProvider()
    result = provider.run(FakeLead(), ctx)
    names = [t["name"] for t in result.data["tech_stack"]]
    assert "Google Analytics" in names or "Google Tag Manager" in names


def test_detects_from_headers():
    html = "<html></html>"
    ctx = EnrichmentContext(
        html_content=html,
        response_headers={"X-Powered-By": "PHP/7.4"},
    )
    provider = TechStackProvider()
    result = provider.run(FakeLead(), ctx)
    names = [t["name"] for t in result.data["tech_stack"]]
    assert "PHP" in names


def test_empty_html_returns_empty_stack():
    ctx = EnrichmentContext(html_content="<html></html>")
    provider = TechStackProvider()
    result = provider.run(FakeLead(), ctx)
    assert result.success is True
    assert result.data["tech_stack"] == []


def test_detects_wix_template():
    html = '<html><head><meta name="generator" content="Wix.com Website Builder"></head></html>'
    ctx = EnrichmentContext(html_content=html)
    provider = TechStackProvider()
    result = provider.run(FakeLead(), ctx)
    names = [t["name"] for t in result.data["tech_stack"]]
    assert "Wix" in names
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd backend && pytest tests/enrichment/test_tech_stack.py -v
```

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Create tech_stack_patterns.py**

Create `backend/app/pipeline/enrichment/providers/tech_stack_patterns.py`:

```python
"""Tech stack detection patterns.

Minimal set of patterns inspired by the Wappalyzer open-source dataset.
Format: list of (pattern_regex, name, category, source).
`source` is one of: "html", "header_value", "header_name".

This is intentionally small — can grow over time. Focus on common CMSs,
analytics tools, ecommerce platforms, and dated tech.
"""

HTML_PATTERNS = [
    # CMS
    (r"wp-content/|wp-includes/|/wp-json/", "WordPress", "cms"),
    (r"cdn\.shopify\.com|shopify\.com/s/", "Shopify", "ecommerce"),
    (r"wix\.com|static\.wixstatic\.com", "Wix", "website_builder"),
    (r"squarespace\.com|static1\.squarespace\.com", "Squarespace", "website_builder"),
    (r"webnode\.com|site123\.com", "Webnode/Site123", "website_builder"),
    (r"static\.parastorage\.com", "Wix", "website_builder"),
    # Analytics
    (r"googletagmanager\.com/gtag|gtag\.js", "Google Analytics", "analytics"),
    (r"googletagmanager\.com/gtm", "Google Tag Manager", "analytics"),
    (r"connect\.facebook\.net/.*fbevents\.js|fbq\(", "Facebook Pixel", "analytics"),
    (r"hotjar\.com/c/hotjar", "Hotjar", "analytics"),
    # Chat / CRM
    (r"tidio\.co|code\.tidio\.co", "Tidio", "chat"),
    (r"crisp\.chat", "Crisp", "chat"),
    (r"intercom\.io|widget\.intercom\.io", "Intercom", "chat"),
    (r"tawk\.to|embed\.tawk\.to", "Tawk.to", "chat"),
    # Frameworks
    (r"_next/static|__NEXT_DATA__", "Next.js", "framework"),
    (r"react\.production|react-dom", "React", "framework"),
    (r"vue\.min\.js|__vue__", "Vue.js", "framework"),
    # Dated
    (r"type=\"application/x-shockwave-flash\"|Adobe Flash", "Adobe Flash", "runtime"),
    (r"jquery-1\.|jquery\.min\.js\?v=1", "jQuery 1", "js_library"),
]

META_GENERATOR_PATTERNS = [
    (r"wix\.com", "Wix", "website_builder"),
    (r"wordpress", "WordPress", "cms"),
    (r"drupal", "Drupal", "cms"),
    (r"joomla", "Joomla", "cms"),
    (r"shopify", "Shopify", "ecommerce"),
    (r"squarespace", "Squarespace", "website_builder"),
]

HEADER_PATTERNS = [
    # (header_name_lower, regex_on_value, name, category)
    ("x-powered-by", r"php", "PHP", "language"),
    ("x-powered-by", r"asp\.net", "ASP.NET", "framework"),
    ("x-powered-by", r"express", "Express.js", "framework"),
    ("server", r"nginx", "Nginx", "web_server"),
    ("server", r"apache", "Apache", "web_server"),
    ("server", r"cloudflare", "Cloudflare", "cdn"),
]
```

- [ ] **Step 4: Implement TechStackProvider**

Create `backend/app/pipeline/enrichment/providers/tech_stack.py`:

```python
"""Tech Stack Detector — pattern-matches technologies from HTML and headers."""
from __future__ import annotations

import re
import logging
from bs4 import BeautifulSoup

from app.pipeline.enrichment.base_provider import (
    BaseProvider,
    EnrichmentContext,
    ProviderResult,
)
from app.pipeline.enrichment.providers.tech_stack_patterns import (
    HTML_PATTERNS,
    META_GENERATOR_PATTERNS,
    HEADER_PATTERNS,
)

logger = logging.getLogger(__name__)


class TechStackProvider(BaseProvider):
    name = "tech_stack"
    display_name = "Tech Stack Detector"
    required_fields = []  # consumes context
    cost = "free"

    def can_run(self, lead, context: EnrichmentContext | None = None) -> bool:
        return bool(context and context.html_content)

    def run(self, lead, context: EnrichmentContext) -> ProviderResult:
        html = context.html_content or ""
        headers = context.response_headers or {}
        detected: list[dict] = []
        seen: set[str] = set()

        def _add(name: str, category: str):
            if name in seen:
                return
            seen.add(name)
            detected.append({"name": name, "category": category})

        # Raw HTML regex
        for pattern, name, category in HTML_PATTERNS:
            try:
                if re.search(pattern, html, re.IGNORECASE):
                    _add(name, category)
            except re.error:
                continue

        # Meta generator
        try:
            soup = BeautifulSoup(html, "html.parser")
            gen = soup.find("meta", {"name": "generator"})
            if gen and gen.get("content"):
                content = gen["content"].lower()
                for pattern, name, category in META_GENERATOR_PATTERNS:
                    if re.search(pattern, content, re.IGNORECASE):
                        _add(name, category)
        except Exception:
            pass

        # Response headers
        headers_lower = {k.lower(): (v or "") for k, v in headers.items()}
        for header_name, regex, name, category in HEADER_PATTERNS:
            val = headers_lower.get(header_name, "")
            if val and re.search(regex, val, re.IGNORECASE):
                _add(name, category)

        return ProviderResult(
            success=True,
            data={"tech_stack": detected},
            errors=[],
            source=self.name,
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run:
```bash
cd backend && pytest tests/enrichment/test_tech_stack.py -v
```

Expected: PASS (6 tests).

- [ ] **Step 6: Commit**

```bash
git add backend/app/pipeline/enrichment/providers/tech_stack_patterns.py \
        backend/app/pipeline/enrichment/providers/tech_stack.py \
        backend/tests/enrichment/test_tech_stack.py
git commit -m "feat(enrichment): add TechStackProvider with pattern-based detection"
```

---

## Task 8: CNPJ Enricher Provider

**Files:**
- Create: `backend/app/pipeline/enrichment/providers/cnpj_enricher.py`
- Create: `backend/tests/enrichment/test_cnpj_enricher.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/enrichment/test_cnpj_enricher.py`:

```python
"""Tests for CnpjProvider."""
from unittest.mock import patch, MagicMock

from app.pipeline.enrichment.base_provider import EnrichmentContext
from app.pipeline.enrichment.providers.cnpj_enricher import CnpjProvider


class FakeLead:
    def __init__(self, cnpj=None, nome="Test", cidade=None, website=None):
        self.cnpj = cnpj
        self.nome = nome
        self.cidade = cidade
        self.website = website


def test_can_run_with_cnpj():
    provider = CnpjProvider()
    assert provider.can_run(FakeLead(cnpj="12.345.678/0001-90")) is True


def test_can_run_with_nome_and_cidade():
    provider = CnpjProvider()
    assert provider.can_run(FakeLead(nome="Clinica XYZ", cidade="Chapeco SC")) is True


def test_cannot_run_without_input():
    provider = CnpjProvider()
    assert provider.can_run(FakeLead(nome="", cidade=None)) is False


@patch("app.pipeline.enrichment.providers.cnpj_enricher.requests.get")
def test_enrich_from_cnpj(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "razao_social": "CLINICA XYZ LTDA",
        "nome_fantasia": "Clinica XYZ",
        "cnae_fiscal_descricao": "Atividades odontologicas",
        "porte": "ME",
        "data_inicio_atividade": "2018-05-10",
        "qsa": [{"nome_socio": "Fulano da Silva"}],
        "logradouro": "RUA X",
        "numero": "100",
        "municipio": "CHAPECO",
    }
    mock_get.return_value = mock_resp

    provider = CnpjProvider()
    lead = FakeLead(cnpj="12345678000190")
    ctx = EnrichmentContext()
    result = provider.run(lead, ctx)

    assert result.success is True
    assert result.data["razao_social"] == "CLINICA XYZ LTDA"
    assert result.data["porte"] == "ME"
    assert "Atividades odontologicas" in (result.data.get("cnae") or "")
    assert result.data["socios"] == [{"nome": "Fulano da Silva"}]


@patch("app.pipeline.enrichment.providers.cnpj_enricher.requests.get")
def test_handles_cnpj_not_found(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_get.return_value = mock_resp

    provider = CnpjProvider()
    lead = FakeLead(cnpj="99999999999999")
    ctx = EnrichmentContext()
    result = provider.run(lead, ctx)

    assert result.success is False
    assert result.data == {}


# --- EC4: CNPJ accepts masked and unmasked ---

@patch("app.pipeline.enrichment.providers.cnpj_enricher.requests.get")
def test_accepts_masked_cnpj(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"razao_social": "ACME LTDA"}
    mock_get.return_value = mock_resp

    provider = CnpjProvider()
    lead = FakeLead(cnpj="12.345.678/0001-90")
    result = provider.run(lead, EnrichmentContext())

    # URL must contain the stripped cnpj
    called_url = mock_get.call_args[0][0]
    assert "12345678000190" in called_url
    assert result.success is True


# --- EC15: BrasilAPI 200 with empty body ---

@patch("app.pipeline.enrichment.providers.cnpj_enricher.requests.get")
def test_handles_empty_body(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {}
    mock_get.return_value = mock_resp

    provider = CnpjProvider()
    lead = FakeLead(cnpj="12345678000190")
    result = provider.run(lead, EnrichmentContext())
    # Empty body → success=True but data is empty (nothing to merge)
    assert result.success is True
    assert result.data == {}


# --- EC18: CNPJ timeout ---

@patch("app.pipeline.enrichment.providers.cnpj_enricher.requests.get")
def test_handles_timeout(mock_get):
    import requests
    mock_get.side_effect = requests.exceptions.Timeout("slow")
    provider = CnpjProvider()
    result = provider.run(FakeLead(cnpj="12345678000190"), EnrichmentContext())
    assert result.success is False
    assert any("error" in e.lower() or "timeout" in e.lower() for e in result.errors)


@patch("app.pipeline.enrichment.providers.cnpj_enricher.requests.get")
def test_discovers_website_via_cnpj(mock_get):
    # Simulating response that includes website field (some CNPJ APIs return it)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "razao_social": "EMPRESA Y LTDA",
        "website": "https://empresay.com.br",
        "cnae_fiscal_descricao": "...",
        "porte": "EPP",
    }
    mock_get.return_value = mock_resp

    provider = CnpjProvider()
    lead = FakeLead(cnpj="12345678000190")
    ctx = EnrichmentContext()
    result = provider.run(lead, ctx)

    assert result.success is True
    assert ctx.discovered_website == "https://empresay.com.br"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd backend && pytest tests/enrichment/test_cnpj_enricher.py -v
```

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement CnpjProvider**

Create `backend/app/pipeline/enrichment/providers/cnpj_enricher.py`:

```python
"""CNPJ Enricher — consults BrasilAPI (free) for CNPJ data."""
from __future__ import annotations

import re
import logging
from datetime import datetime
import requests

from app.pipeline.enrichment.base_provider import (
    BaseProvider,
    EnrichmentContext,
    ProviderResult,
)

logger = logging.getLogger(__name__)

BRASILAPI_CNPJ_URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"


def _clean_cnpj(cnpj: str) -> str:
    return re.sub(r"\D", "", cnpj or "")


class CnpjProvider(BaseProvider):
    name = "cnpj_enricher"
    display_name = "CNPJ Enricher (BrasilAPI)"
    required_fields = ["cnpj"]  # or nome+cidade as fallback
    cost = "free"

    def can_run(self, lead, context: EnrichmentContext | None = None) -> bool:
        if getattr(lead, "cnpj", None):
            return True
        if getattr(lead, "nome", None) and getattr(lead, "cidade", None):
            # Without a CNPJ lookup by name API (BrasilAPI doesn't have one),
            # we cannot confidently run. Return False here — this case is only
            # handled by future provider extensions.
            return False
        return False

    def run(self, lead, context: EnrichmentContext) -> ProviderResult:
        cnpj_raw = getattr(lead, "cnpj", None)
        if not cnpj_raw:
            return ProviderResult(
                success=False, data={}, errors=["no cnpj"], source=self.name
            )

        cnpj = _clean_cnpj(cnpj_raw)
        if len(cnpj) != 14:
            return ProviderResult(
                success=False, data={}, errors=["invalid cnpj length"], source=self.name
            )

        try:
            resp = requests.get(
                BRASILAPI_CNPJ_URL.format(cnpj=cnpj), timeout=15
            )
        except Exception as exc:
            return ProviderResult(
                success=False,
                data={},
                errors=[f"http error: {str(exc)[:100]}"],
                source=self.name,
            )

        if resp.status_code != 200:
            return ProviderResult(
                success=False,
                data={},
                errors=[f"http {resp.status_code}"],
                source=self.name,
            )

        try:
            body = resp.json()
        except Exception as exc:
            return ProviderResult(
                success=False,
                data={},
                errors=[f"json: {str(exc)[:80]}"],
                source=self.name,
            )

        data: dict = {}
        if body.get("razao_social"):
            data["razao_social"] = body["razao_social"]
        if body.get("porte"):
            data["porte"] = body["porte"]
        if body.get("cnae_fiscal_descricao"):
            data["cnae"] = body["cnae_fiscal_descricao"]
        if body.get("data_inicio_atividade"):
            try:
                data["data_fundacao"] = datetime.strptime(
                    body["data_inicio_atividade"], "%Y-%m-%d"
                ).date().isoformat()
            except ValueError:
                pass

        qsa = body.get("qsa") or []
        socios = []
        for partner in qsa:
            nome = partner.get("nome_socio") or partner.get("nome") or ""
            if nome:
                socios.append({"nome": nome})
        if socios:
            data["socios"] = socios

        website = body.get("website") or ""
        if website and not getattr(lead, "website", None):
            context.discovered_website = website
            data["website"] = website

        # Empty body → success=True with empty data (nothing to merge, but no error)
        return ProviderResult(
            success=True,
            data=data,
            errors=[],
            source=self.name,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd backend && pytest tests/enrichment/test_cnpj_enricher.py -v
```

Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/enrichment/providers/cnpj_enricher.py \
        backend/tests/enrichment/test_cnpj_enricher.py
git commit -m "feat(enrichment): add CnpjProvider using BrasilAPI"
```

---

## Task 9: Email Discoverer Provider

**Files:**
- Create: `backend/app/pipeline/enrichment/providers/email_discoverer.py`
- Create: `backend/tests/enrichment/test_email_discoverer.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/enrichment/test_email_discoverer.py`:

```python
"""Tests for EmailDiscovererProvider."""
from unittest.mock import patch, MagicMock

from app.pipeline.enrichment.base_provider import EnrichmentContext
from app.pipeline.enrichment.providers.email_discoverer import EmailDiscovererProvider


class FakeLead:
    def __init__(self, website=None, email=None):
        self.website = website
        self.email = email


HTML_WITH_EMAIL = """
<html><body>
<a href="mailto:contato@clinica.com.br">Email</a>
Também: atendimento@clinica.com.br
</body></html>
"""

HTML_WITHOUT_EMAIL = "<html><body><p>nothing</p></body></html>"


def test_cannot_run_without_website_or_html():
    provider = EmailDiscovererProvider()
    assert provider.can_run(FakeLead(), context=EnrichmentContext()) is False


def test_can_run_with_html_in_context():
    provider = EmailDiscovererProvider()
    ctx = EnrichmentContext(html_content="<html></html>")
    lead = FakeLead(website="https://x.com")
    assert provider.can_run(lead, context=ctx) is True


def test_extracts_email_from_html():
    provider = EmailDiscovererProvider()
    ctx = EnrichmentContext(html_content=HTML_WITH_EMAIL)
    lead = FakeLead(website="https://clinica.com.br")
    result = provider.run(lead, ctx)
    assert result.success is True
    assert result.data["email"] in ("contato@clinica.com.br", "atendimento@clinica.com.br")
    found = result.data["site_analysis"]["emails_found"]
    assert "contato@clinica.com.br" in found
    assert "atendimento@clinica.com.br" in found


def test_skips_if_lead_already_has_email():
    # EC6: Lead already has email — discoverer must NOT populate `email` in data
    provider = EmailDiscovererProvider()
    ctx = EnrichmentContext(html_content=HTML_WITH_EMAIL)
    lead = FakeLead(website="https://x.com", email="existing@x.com")
    result = provider.run(lead, ctx)
    assert "email" not in result.data
    # But still records found emails in site_analysis
    assert len(result.data["site_analysis"]["emails_found"]) > 0


# --- EC14: email regex false positive ---

def test_ignores_image_filename_false_positives():
    # `foo@2x.png` is commonly used in srcset but looks like an email to regex
    html = '<img src="logo.png" srcset="logo@2x.png 2x, logo@3x.png 3x">'
    provider = EmailDiscovererProvider()
    ctx = EnrichmentContext(html_content=html)
    lead = FakeLead(website="https://x.com")
    result = provider.run(lead, ctx)
    # None of the @2x / @3x should end up as an email
    found = result.data["site_analysis"]["emails_found"]
    assert all(not e.endswith(".png") for e in found)
    assert all(not e.endswith(".jpg") for e in found)


# --- EC5: email normalization (mixed case + whitespace) ---

def test_normalizes_mixed_case_emails():
    html = '<a href="mailto:Contato@Clinica.COM.BR">  Contato@Clinica.COM.BR  </a>'
    provider = EmailDiscovererProvider()
    ctx = EnrichmentContext(html_content=html)
    lead = FakeLead(website="https://clinica.com.br")
    result = provider.run(lead, ctx)
    found = result.data["site_analysis"]["emails_found"]
    assert "contato@clinica.com.br" in found


# --- EC16: Hunter 402 quota exceeded ---

@patch("app.pipeline.enrichment.providers.email_discoverer.settings")
@patch("app.pipeline.enrichment.providers.email_discoverer.requests.get")
def test_hunter_402_recorded_as_error_not_crash(mock_get, mock_settings):
    mock_settings.hunter_api_key = "fake"
    mock_resp = MagicMock()
    mock_resp.status_code = 402
    mock_get.return_value = mock_resp

    provider = EmailDiscovererProvider()
    ctx = EnrichmentContext(html_content="<html></html>")
    lead = FakeLead(website="https://empresa.com")
    result = provider.run(lead, ctx)
    # Provider still succeeds (html extraction works); hunter error recorded
    assert result.success is True
    assert any("402" in e for e in result.errors)


def test_no_emails_returns_success_with_empty():
    provider = EmailDiscovererProvider()
    ctx = EnrichmentContext(html_content=HTML_WITHOUT_EMAIL)
    lead = FakeLead(website="https://x.com")
    result = provider.run(lead, ctx)
    assert result.success is True
    assert result.data["site_analysis"]["emails_found"] == []


@patch("app.pipeline.enrichment.providers.email_discoverer.settings")
@patch("app.pipeline.enrichment.providers.email_discoverer.requests.get")
def test_hunter_api_called_when_key_configured(mock_get, mock_settings):
    mock_settings.hunter_api_key = "fake_key"
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": {
            "emails": [
                {"value": "contato@empresa.com.br", "confidence": 90},
                {"value": "vendas@empresa.com.br", "confidence": 80},
            ]
        }
    }
    mock_get.return_value = mock_resp

    provider = EmailDiscovererProvider()
    ctx = EnrichmentContext(html_content="<html></html>")
    lead = FakeLead(website="https://empresa.com.br")
    result = provider.run(lead, ctx)

    assert result.success is True
    assert "contato@empresa.com.br" in result.data["site_analysis"]["emails_found"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd backend && pytest tests/enrichment/test_email_discoverer.py -v
```

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement EmailDiscovererProvider**

Create `backend/app/pipeline/enrichment/providers/email_discoverer.py`:

```python
"""Email Discoverer — extracts emails from crawled HTML + optional Hunter.io.

Hunter.io integration is optional; if HUNTER_API_KEY isn't set, the provider
runs with HTML-only extraction.
"""
from __future__ import annotations

import re
import logging
import requests

from app.pipeline.enrichment.base_provider import (
    BaseProvider,
    EnrichmentContext,
    ProviderResult,
)
from app.config import settings

logger = logging.getLogger(__name__)

# Permissive enough to catch real emails but excludes trailing punctuation.
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Local parts / domains that look like emails but aren't (srcset patterns, etc.)
_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico")

HUNTER_DOMAIN_URL = "https://api.hunter.io/v2/domain-search"

# Emails to ignore (tracking pixels, generic noreply)
_IGNORE_LOCAL_PARTS = {"noreply", "no-reply", "donotreply", "do-not-reply"}
_IGNORE_DOMAINS = {"sentry.io", "wixpress.com", "example.com"}


def _extract_domain(website: str) -> str:
    if not website:
        return ""
    match = re.search(r"https?://(?:www\.)?([^/]+)", website)
    if match:
        return match.group(1).lower()
    return ""


def _filter_emails(emails: list[str]) -> list[str]:
    result = []
    seen = set()
    for e in emails:
        e_lower = e.strip().lower()
        if e_lower in seen:
            continue
        # EC14: skip image filename false positives like `logo@2x.png`
        if e_lower.endswith(_IMAGE_EXTS):
            continue
        local, _, domain = e_lower.partition("@")
        if not local or not domain or "." not in domain:
            continue
        if local in _IGNORE_LOCAL_PARTS:
            continue
        if domain in _IGNORE_DOMAINS:
            continue
        # Skip local parts that are just digits+x (e.g. `2x`, `3x` from srcset)
        if re.fullmatch(r"\d+x", local):
            continue
        seen.add(e_lower)
        result.append(e_lower)
    return result


class EmailDiscovererProvider(BaseProvider):
    name = "email_discoverer"
    display_name = "Email Discoverer"
    required_fields = ["website"]
    cost = "freemium"

    def can_run(self, lead, context: EnrichmentContext | None = None) -> bool:
        has_html = bool(context and context.html_content)
        has_website = bool(getattr(lead, "website", None) or (context and context.discovered_website))
        return has_html or has_website

    def run(self, lead, context: EnrichmentContext) -> ProviderResult:
        html = (context.html_content or "") if context else ""
        emails_found: list[str] = []
        errors: list[str] = []

        # 1. Regex extraction from HTML
        if html:
            emails_found.extend(EMAIL_RE.findall(html))

        emails_found = _filter_emails(emails_found)

        # 2. Hunter.io (optional)
        website = getattr(lead, "website", None) or (context.discovered_website if context else None)
        if settings.hunter_api_key and website:
            domain = _extract_domain(website)
            if domain:
                try:
                    resp = requests.get(
                        HUNTER_DOMAIN_URL,
                        params={
                            "domain": domain,
                            "api_key": settings.hunter_api_key,
                            "limit": 10,
                        },
                        timeout=15,
                    )
                    if resp.status_code == 200:
                        body = resp.json() or {}
                        hunter_emails = [
                            e.get("value")
                            for e in (body.get("data", {}).get("emails") or [])
                            if e.get("value")
                        ]
                        for e in _filter_emails(hunter_emails):
                            if e not in emails_found:
                                emails_found.append(e)
                    else:
                        errors.append(f"hunter http {resp.status_code}")
                except Exception as exc:
                    errors.append(f"hunter: {str(exc)[:100]}")

        data: dict = {"site_analysis": {"emails_found": emails_found}}

        # EC6: Only set primary email if lead doesn't have one.
        # Never populate `email` in result.data when the lead already has an email —
        # the orchestrator's data-precedence logic also checks this, but belt-and-suspenders.
        existing_email = getattr(lead, "email", None)
        if not existing_email and emails_found:
            # Prefer domain-matching email
            domain = _extract_domain(website or "")
            preferred = next(
                (e for e in emails_found if domain and e.endswith(f"@{domain}")),
                emails_found[0],
            )
            data["email"] = preferred

        return ProviderResult(
            success=True,
            data=data,
            errors=errors,
            source=self.name,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd backend && pytest tests/enrichment/test_email_discoverer.py -v
```

Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/enrichment/providers/email_discoverer.py \
        backend/tests/enrichment/test_email_discoverer.py
git commit -m "feat(enrichment): add EmailDiscovererProvider with Hunter.io support"
```

---

## Task 10: Apollo Enricher Provider

**Files:**
- Create: `backend/app/pipeline/enrichment/providers/apollo_enricher.py`
- Create: `backend/tests/enrichment/test_apollo_enricher.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/enrichment/test_apollo_enricher.py`:

```python
"""Tests for ApolloProvider."""
from unittest.mock import patch, MagicMock

from app.pipeline.enrichment.base_provider import EnrichmentContext
from app.pipeline.enrichment.providers.apollo_enricher import ApolloProvider


class FakeLead:
    def __init__(self, website=None, email=None):
        self.website = website
        self.email = email


@patch("app.pipeline.enrichment.providers.apollo_enricher.settings")
def test_cannot_run_without_api_key(mock_settings):
    mock_settings.apollo_api_key = ""
    provider = ApolloProvider()
    assert provider.can_run(FakeLead(website="https://x.com")) is False


@patch("app.pipeline.enrichment.providers.apollo_enricher.settings")
def test_cannot_run_without_website_or_email(mock_settings):
    mock_settings.apollo_api_key = "fake"
    provider = ApolloProvider()
    assert provider.can_run(FakeLead()) is False


@patch("app.pipeline.enrichment.providers.apollo_enricher.settings")
def test_can_run_with_key_and_website(mock_settings):
    mock_settings.apollo_api_key = "fake"
    provider = ApolloProvider()
    assert provider.can_run(FakeLead(website="https://x.com")) is True


@patch("app.pipeline.enrichment.providers.apollo_enricher.settings")
@patch("app.pipeline.enrichment.providers.apollo_enricher.requests.get")
def test_enrich_organization(mock_get, mock_settings):
    mock_settings.apollo_api_key = "fake_key"
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "organization": {
            "name": "Clinica X",
            "short_description": "Odonto",
            "industry": "Healthcare",
            "estimated_num_employees": 25,
            "linkedin_url": "https://linkedin.com/company/x",
        }
    }
    mock_get.return_value = mock_resp

    provider = ApolloProvider()
    lead = FakeLead(website="https://clinicax.com")
    ctx = EnrichmentContext()
    result = provider.run(lead, ctx)

    assert result.success is True
    apollo_data = result.data["site_analysis"]["apollo_data"]
    assert apollo_data["name"] == "Clinica X"
    assert apollo_data["estimated_num_employees"] == 25


# --- EC17: Apollo 200 with null organization ---

@patch("app.pipeline.enrichment.providers.apollo_enricher.settings")
@patch("app.pipeline.enrichment.providers.apollo_enricher.requests.get")
def test_handles_null_organization(mock_get, mock_settings):
    mock_settings.apollo_api_key = "fake"
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"organization": None}
    mock_get.return_value = mock_resp

    provider = ApolloProvider()
    result = provider.run(FakeLead(website="https://x.com"), EnrichmentContext())
    # Not an error, just nothing to merge
    assert result.success is True
    apollo_data = result.data["site_analysis"].get("apollo_data", {})
    assert not apollo_data.get("name")


@patch("app.pipeline.enrichment.providers.apollo_enricher.settings")
@patch("app.pipeline.enrichment.providers.apollo_enricher.requests.get")
def test_handles_rate_limit(mock_get, mock_settings):
    mock_settings.apollo_api_key = "fake_key"
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_get.return_value = mock_resp

    provider = ApolloProvider()
    lead = FakeLead(website="https://x.com")
    ctx = EnrichmentContext()
    result = provider.run(lead, ctx)
    assert result.success is False
    assert any("429" in e or "rate" in e.lower() for e in result.errors)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd backend && pytest tests/enrichment/test_apollo_enricher.py -v
```

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement ApolloProvider**

Create `backend/app/pipeline/enrichment/providers/apollo_enricher.py`:

```python
"""Apollo Enricher — calls Apollo.io Organization Enrichment API.

Requires APOLLO_API_KEY. Free tier has generous monthly credits.
"""
from __future__ import annotations

import logging
import re
import requests

from app.pipeline.enrichment.base_provider import (
    BaseProvider,
    EnrichmentContext,
    ProviderResult,
)
from app.config import settings

logger = logging.getLogger(__name__)

APOLLO_ORG_ENRICH_URL = "https://api.apollo.io/v1/organizations/enrich"


def _extract_domain(website: str) -> str:
    match = re.search(r"https?://(?:www\.)?([^/]+)", website or "")
    return match.group(1).lower() if match else ""


class ApolloProvider(BaseProvider):
    name = "apollo"
    display_name = "Apollo.io"
    required_fields = ["website"]  # also accepts email
    cost = "freemium"

    def can_run(self, lead, context: EnrichmentContext | None = None) -> bool:
        if not settings.apollo_api_key:
            return False
        website = getattr(lead, "website", None) or (context.discovered_website if context else None)
        email = getattr(lead, "email", None)
        return bool(website or email)

    def run(self, lead, context: EnrichmentContext) -> ProviderResult:
        website = getattr(lead, "website", None) or (context.discovered_website if context else None)
        domain = _extract_domain(website or "")
        if not domain:
            email = getattr(lead, "email", None) or ""
            if "@" in email:
                domain = email.split("@", 1)[1].strip().lower()

        if not domain:
            return ProviderResult(
                success=False, data={}, errors=["no domain"], source=self.name
            )

        try:
            resp = requests.get(
                APOLLO_ORG_ENRICH_URL,
                params={"api_key": settings.apollo_api_key, "domain": domain},
                timeout=20,
            )
        except Exception as exc:
            return ProviderResult(
                success=False, data={}, errors=[f"http: {str(exc)[:80]}"], source=self.name
            )

        if resp.status_code == 429:
            return ProviderResult(
                success=False, data={}, errors=["http 429 rate limit"], source=self.name
            )
        if resp.status_code != 200:
            return ProviderResult(
                success=False, data={}, errors=[f"http {resp.status_code}"], source=self.name
            )

        try:
            body = resp.json() or {}
        except Exception as exc:
            return ProviderResult(
                success=False, data={}, errors=[f"json: {str(exc)[:80]}"], source=self.name
            )

        org = body.get("organization") or {}
        apollo_data = {
            "name": org.get("name", ""),
            "description": (org.get("short_description") or "")[:500],
            "industry": org.get("industry", ""),
            "estimated_num_employees": org.get("estimated_num_employees"),
            "linkedin_url": org.get("linkedin_url", ""),
            "founded_year": org.get("founded_year"),
            "logo_url": org.get("logo_url", ""),
        }

        return ProviderResult(
            success=True,
            data={"site_analysis": {"apollo_data": apollo_data}},
            errors=[],
            source=self.name,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd backend && pytest tests/enrichment/test_apollo_enricher.py -v
```

Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/enrichment/providers/apollo_enricher.py \
        backend/tests/enrichment/test_apollo_enricher.py
git commit -m "feat(enrichment): add ApolloProvider"
```

---

## Task 11: Enrichment Orchestrator

**Files:**
- Create: `backend/app/pipeline/enrichment/orchestrator.py`
- Create: `backend/tests/enrichment/test_orchestrator.py`
- Modify: `backend/app/pipeline/enrichment/__init__.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/enrichment/test_orchestrator.py`:

```python
"""Tests for EnrichmentOrchestrator — planning + execution."""
from unittest.mock import patch, MagicMock

from app.pipeline.enrichment.base_provider import (
    BaseProvider,
    EnrichmentContext,
    ProviderResult,
)
from app.pipeline.enrichment.orchestrator import (
    EnrichmentOrchestrator,
    EnrichmentPlan,
)


class FakeLead:
    def __init__(self, **kwargs):
        self.website = kwargs.get("website")
        self.email = kwargs.get("email")
        self.cnpj = kwargs.get("cnpj")
        self.nome = kwargs.get("nome", "Test")
        self.cidade = kwargs.get("cidade")
        self.telefone = kwargs.get("telefone")
        self.nicho = kwargs.get("nicho")
        self.categoria = kwargs.get("categoria")
        self.rating = kwargs.get("rating")
        self.reviews_count = kwargs.get("reviews_count", 0)
        self.top_reviews = kwargs.get("top_reviews", [])


class StubProvider(BaseProvider):
    """Provider that records invocations and returns a preset ProviderResult."""
    def __init__(self, name: str, cost="free", result=None, can_run_result=True):
        self.name = name
        self.display_name = name
        self.required_fields = []
        self.cost = cost
        self._result = result or ProviderResult(
            success=True, data={}, errors=[], source=name
        )
        self._can_run = can_run_result
        self.calls = 0

    def can_run(self, lead, context=None):
        return self._can_run

    def run(self, lead, context):
        self.calls += 1
        return self._result


def test_plan_with_website_runs_crawler_chain():
    lead = FakeLead(website="https://example.com")
    orch = EnrichmentOrchestrator()
    plan = orch.plan(lead)
    names = [p.name for p in plan.providers]
    # Expect crawler, schema, tech, email, apollo in the plan
    assert "website_crawler" in names
    assert "schema_extractor" in names
    assert "tech_stack" in names


def test_plan_without_website_but_with_cnpj_discovers_first():
    # HP2: CNPJ is first in the plan, and crawl chain is included optimistically
    lead = FakeLead(cnpj="12345678000190")
    orch = EnrichmentOrchestrator()
    plan = orch.plan(lead)
    names = [p.name for p in plan.providers]
    assert names[0] == "cnpj_enricher"
    # Crawl chain is optimistically included for post-discovery execution
    assert "website_crawler" in names
    assert "schema_extractor" in names
    assert "tech_stack" in names


def test_plan_with_only_nome_and_phone_is_mostly_empty():
    # HP5: lead with minimal data — plan skips providers that can't run
    lead = FakeLead(nome="Nada", telefone="+554999")
    orch = EnrichmentOrchestrator()
    plan = orch.plan(lead)
    names = [p.name for p in plan.providers]
    # No website, no cnpj, no email → crawl chain and contact providers are all skipped
    assert "website_crawler" not in names
    assert "cnpj_enricher" not in names
    assert "apollo" not in names


def test_skip_providers_honored():
    lead = FakeLead(website="https://example.com")
    orch = EnrichmentOrchestrator()
    plan = orch.plan(lead, skip_providers=["apollo", "email_discoverer"])
    names = [p.name for p in plan.providers]
    assert "apollo" not in names
    assert "email_discoverer" not in names
    assert "website_crawler" in names


def test_force_providers_bypasses_can_run():
    lead = FakeLead()  # no website, no cnpj
    orch = EnrichmentOrchestrator()
    plan = orch.plan(lead, force_providers=["apollo"])
    names = [p.name for p in plan.providers]
    assert "apollo" in names


def test_execute_merges_provider_data():
    lead = FakeLead(website="https://example.com")
    orch = EnrichmentOrchestrator()
    # Inject stub providers
    stub_crawler = StubProvider(
        "website_crawler",
        result=ProviderResult(
            success=True,
            data={"site_analysis": {"has_ssl": True, "status": "ok"}},
            errors=[],
            source="website_crawler",
        ),
    )
    stub_cnpj = StubProvider(
        "cnpj_enricher",
        result=ProviderResult(
            success=True,
            data={"razao_social": "TEST LTDA", "porte": "ME"},
            errors=[],
            source="cnpj_enricher",
        ),
    )
    orch._providers_by_name = {
        "website_crawler": stub_crawler,
        "cnpj_enricher": stub_cnpj,
    }
    plan = EnrichmentPlan(providers=[stub_crawler, stub_cnpj])
    result = orch.execute(lead, plan)

    assert result["opportunity_score"] is not None
    assert result["site_analysis"]["has_ssl"] is True
    assert result["razao_social"] == "TEST LTDA"
    sources = [s["provider"] for s in result["enrichment_sources"]]
    assert "website_crawler" in sources
    assert "cnpj_enricher" in sources


# --- HP4 / EC6 / EC7 / EC8: existing lead fields are preserved ---

def test_existing_email_preserved_over_discovered():
    lead = FakeLead(website="https://x.com", email="existing@x.com")
    orch = EnrichmentOrchestrator()
    stub = StubProvider(
        "email_discoverer",
        result=ProviderResult(
            success=True,
            data={"email": "discovered@x.com"},
            errors=[],
            source="email_discoverer",
        ),
    )
    plan = EnrichmentPlan(providers=[stub])
    result = orch.execute(lead, plan)
    # The orchestrator MUST NOT return `email` key (lead already has one).
    # Consumer (pipeline router) only sets lead.email from result if key is present.
    assert "email" not in result or result["email"] == "existing@x.com"


def test_existing_website_preserved_over_discovered():
    lead = FakeLead(website="https://existing.com")
    orch = EnrichmentOrchestrator()
    stub = StubProvider(
        "cnpj_enricher",
        result=ProviderResult(
            success=True,
            data={"website": "https://discovered.com", "razao_social": "X LTDA"},
            errors=[],
            source="cnpj_enricher",
        ),
    )
    plan = EnrichmentPlan(providers=[stub])
    result = orch.execute(lead, plan)
    assert "website" not in result or result["website"] == "https://existing.com"
    # Other fields still merged
    assert result["razao_social"] == "X LTDA"


def test_existing_cnpj_preserved():
    lead = FakeLead()
    lead.cnpj = "99999999000100"
    orch = EnrichmentOrchestrator()
    stub = StubProvider(
        "cnpj_enricher",
        result=ProviderResult(
            success=True,
            data={"cnpj": "11111111000100", "razao_social": "Y LTDA"},
            errors=[],
            source="cnpj_enricher",
        ),
    )
    plan = EnrichmentPlan(providers=[stub])
    result = orch.execute(lead, plan)
    assert "cnpj" not in result or result["cnpj"] == "99999999000100"


# --- HP5 / EC19: empty plan returns valid result ---

def test_empty_plan_returns_valid_result():
    lead = FakeLead(nome="Only Name Lead", telefone="+554999")
    orch = EnrichmentOrchestrator()
    plan = EnrichmentPlan(providers=[])
    result = orch.execute(lead, plan)
    assert result["opportunity_score"] is not None
    assert result["opportunity_reasons"] is not None
    assert result["enrichment_sources"] == []
    assert result["site_analysis"] == {}
    assert result["tech_stack"] == []


# --- EC9 / EC10: idempotency — a fresh run returns a fresh list (not appended) ---

def test_run_returns_fresh_lists_not_appended():
    lead = FakeLead(website="https://x.com")
    # Simulate lead already having enrichment_sources from a prior run
    lead.enrichment_sources = [{"provider": "old", "status": "ok"}]
    lead.tech_stack = [{"name": "OldTech", "category": "x"}]

    orch = EnrichmentOrchestrator()
    stub = StubProvider(
        "website_crawler",
        result=ProviderResult(
            success=True,
            data={
                "site_analysis": {"status": "ok", "has_ssl": True},
                "tech_stack": [{"name": "NewTech", "category": "y"}],
            },
            errors=[],
            source="website_crawler",
        ),
    )
    plan = EnrichmentPlan(providers=[stub])
    result = orch.execute(lead, plan)

    # enrichment_sources from this run only (not merged with old)
    sources = result["enrichment_sources"]
    assert all(s["provider"] != "old" for s in sources)
    assert any(s["provider"] == "website_crawler" for s in sources)

    # tech_stack replaced (not appended)
    names = [t["name"] for t in result["tech_stack"]]
    assert "OldTech" not in names


# --- EC20: provider returns a non-ProviderResult ---

def test_provider_returns_invalid_type_recorded_as_error():
    lead = FakeLead(website="https://x.com")
    orch = EnrichmentOrchestrator()

    class BadProvider(BaseProvider):
        name = "bad"
        display_name = "bad"
        required_fields = []
        cost = "free"
        def can_run(self, lead, context=None): return True
        def run(self, lead, context):
            return {"not": "a ProviderResult"}  # wrong type

    plan = EnrichmentPlan(providers=[BadProvider()])
    result = orch.execute(lead, plan)
    entry = next((s for s in result["enrichment_sources"] if s["provider"] == "bad"), None)
    assert entry is not None
    assert entry["status"] == "error"


# --- EC21: skip beats force when both are specified ---

def test_skip_overrides_force_when_both_specified():
    lead = FakeLead(website="https://x.com")
    orch = EnrichmentOrchestrator()
    plan = orch.plan(
        lead,
        skip_providers=["apollo"],
        force_providers=["apollo"],
    )
    names = [p.name for p in plan.providers]
    assert "apollo" not in names


def test_execute_continues_on_provider_exception():
    lead = FakeLead(website="https://example.com")
    orch = EnrichmentOrchestrator()

    class FailingProvider(BaseProvider):
        name = "failing"
        display_name = "failing"
        required_fields = []
        cost = "free"
        def can_run(self, lead, context=None): return True
        def run(self, lead, context):
            raise RuntimeError("boom")

    good_provider = StubProvider(
        "website_crawler",
        result=ProviderResult(
            success=True,
            data={"site_analysis": {"status": "ok", "has_ssl": True}},
            errors=[],
            source="website_crawler",
        ),
    )

    plan = EnrichmentPlan(providers=[FailingProvider(), good_provider])
    result = orch.execute(lead, plan)

    sources = result["enrichment_sources"]
    failing_entry = next((s for s in sources if s["provider"] == "failing"), None)
    assert failing_entry is not None
    assert failing_entry["status"] == "error"
    # Good provider still ran
    assert good_provider.calls == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd backend && pytest tests/enrichment/test_orchestrator.py -v
```

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement orchestrator.py**

Create `backend/app/pipeline/enrichment/orchestrator.py`:

```python
"""Enrichment Orchestrator — decides which providers to run and executes them.

Phases:
  1. Discovery — CNPJ (can discover website)
  2. Crawl — WebsiteCrawler, Schema.org, TechStack (chain via context.html_content)
  3. Contact — EmailDiscoverer, Apollo
  4. Scoring — recalculate opportunity_score

Supports `skip_providers` and `force_providers` to override the auto-plan.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, date

from app.pipeline.enrichment.base_provider import (
    BaseProvider,
    EnrichmentContext,
    ProviderResult,
)
from app.pipeline.enrichment.providers.website_crawler import WebsiteCrawlerProvider
from app.pipeline.enrichment.providers.schema_extractor import SchemaOrgProvider
from app.pipeline.enrichment.providers.tech_stack import TechStackProvider
from app.pipeline.enrichment.providers.cnpj_enricher import CnpjProvider
from app.pipeline.enrichment.providers.email_discoverer import EmailDiscovererProvider
from app.pipeline.enrichment.providers.apollo_enricher import ApolloProvider
from app.pipeline.enrichment.scoring import calculate_score

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentPlan:
    providers: list[BaseProvider] = field(default_factory=list)


def _default_providers() -> list[BaseProvider]:
    return [
        CnpjProvider(),
        WebsiteCrawlerProvider(),
        SchemaOrgProvider(),
        TechStackProvider(),
        EmailDiscovererProvider(),
        ApolloProvider(),
    ]


# Default execution order by phase
_PHASE_ORDER = [
    "cnpj_enricher",       # discovery
    "website_crawler",     # crawl (populates context)
    "schema_extractor",    # crawl (consumes context)
    "tech_stack",          # crawl (consumes context)
    "email_discoverer",    # contact
    "apollo",              # contact
]


class EnrichmentOrchestrator:
    def __init__(self, providers: list[BaseProvider] | None = None):
        providers = providers or _default_providers()
        self._providers_by_name: dict[str, BaseProvider] = {
            p.name: p for p in providers
        }

    def plan(
        self,
        lead,
        skip_providers: list[str] | None = None,
        force_providers: list[str] | None = None,
    ) -> EnrichmentPlan:
        """Build the list of providers to run for this lead.

        EC21: explicit skip wins over force. If a name is in both lists, it's skipped.

        HP2: If the lead has no website but has a CNPJ, the CNPJ provider may
        discover a website at runtime. In that case we optimistically include the
        crawl-chain providers (website_crawler, schema_extractor, tech_stack, email)
        in the plan — `execute` passes the live context to their `can_run`, so
        they're still skipped gracefully if nothing was actually discovered.
        """
        skip = set(skip_providers or [])
        force = set(force_providers or [])
        selected: list[BaseProvider] = []

        # The crawl chain (website_crawler → schema_extractor → tech_stack) only
        # runs when there's HTML in the context, which depends on website_crawler
        # running first. So we include them in the plan whenever website_crawler
        # is likely to run — either the lead already has a website, or CNPJ might
        # discover one at runtime. The per-provider can_run check is re-run
        # inside execute() with the live context to skip gracefully if not.
        has_website = bool(getattr(lead, "website", None))
        might_discover_website = (
            bool(getattr(lead, "cnpj", None))
            and not has_website
            and "cnpj_enricher" not in skip
        )
        include_crawl_chain = has_website or might_discover_website
        optimistic_names = {
            "website_crawler", "schema_extractor", "tech_stack",
            "email_discoverer", "apollo",
        } if include_crawl_chain else set()

        for name in _PHASE_ORDER:
            provider = self._providers_by_name.get(name)
            if not provider:
                continue
            if name in skip:
                continue
            if name in force:
                selected.append(provider)
                continue
            if name in optimistic_names:
                selected.append(provider)
                continue
            try:
                if _accepts_context(provider.can_run):
                    runnable = provider.can_run(lead, context=None)
                else:
                    runnable = provider.can_run(lead)
                if runnable:
                    selected.append(provider)
            except Exception as exc:
                logger.warning("can_run failed for %s: %s", name, exc)

        return EnrichmentPlan(providers=selected)

    def execute(self, lead, plan: EnrichmentPlan) -> dict:
        """Run providers in plan order, merge results, compute score.

        Returns a fresh dict of fields to apply to the Lead. Lists (tech_stack,
        socios, enrichment_sources) are REPLACED, not appended — this makes
        re-running enrichment idempotent (EC9, EC10).

        Flat fields (email, cnpj, razao_social, porte, cnae, data_fundacao,
        website) are only emitted if the lead does NOT already have a value for
        that field — this preserves manually-entered or previously-enriched
        data (EC6, EC7, EC8). The consumer (pipeline router) should only apply
        a field when the key is present in the returned dict.
        """
        context = EnrichmentContext()
        merged_site_analysis: dict = {}
        merged_social_profiles: dict = {}
        merged_tech_stack: list = []
        merged_socios: list = []
        enrichment_sources: list = []
        flat: dict = {}  # direct Lead column values (email, cnpj, ...)

        # Snapshot existing lead values — used for data-precedence checks
        existing_flat = {
            key: getattr(lead, key, None)
            for key in ("email", "cnpj", "razao_social", "porte", "cnae",
                        "data_fundacao", "website")
        }

        for provider in plan.providers:
            source_entry = {
                "provider": provider.name,
                "status": "ok",
                "timestamp": datetime.utcnow().isoformat(),
            }
            try:
                # Re-check can_run with the live context — providers that were
                # included optimistically (e.g. after a CNPJ discovery) may now
                # have the data they need, and vice-versa.
                if _accepts_context(provider.can_run):
                    runnable = provider.can_run(lead, context=context)
                else:
                    runnable = provider.can_run(lead)
                if not runnable:
                    source_entry["status"] = "skipped"
                    source_entry["error"] = "preconditions not met"
                    enrichment_sources.append(source_entry)
                    continue

                result = provider.run(lead, context)
                if not isinstance(result, ProviderResult):
                    source_entry["status"] = "error"
                    source_entry["error"] = "invalid result type"
                    enrichment_sources.append(source_entry)
                    continue

                if not result.success:
                    source_entry["status"] = "skipped"
                    if result.errors:
                        source_entry["error"] = "; ".join(result.errors)[:200]
                    enrichment_sources.append(source_entry)
                    continue

                data = result.data or {}
                # Merge nested site_analysis
                sa = data.get("site_analysis") or {}
                if sa:
                    merged_site_analysis.update(sa)
                sp = data.get("social_profiles") or {}
                if sp:
                    merged_social_profiles.update(sp)
                ts = data.get("tech_stack") or []
                if ts:
                    merged_tech_stack = ts
                sc = data.get("socios") or []
                if sc:
                    merged_socios = sc

                # Flat fields — respect existing lead data (EC6/EC7/EC8)
                for key in ("email", "cnpj", "razao_social", "porte", "cnae",
                            "data_fundacao", "website"):
                    if key not in data or not data[key]:
                        continue
                    if existing_flat.get(key):
                        # Lead already has a value for this field — don't overwrite
                        continue
                    if flat.get(key):
                        # An earlier provider in this run already set it — keep first
                        continue
                    flat[key] = data[key]

                if result.errors:
                    source_entry["error"] = "; ".join(result.errors)[:200]

            except Exception as exc:
                logger.exception("provider %s crashed", provider.name)
                source_entry["status"] = "error"
                source_entry["error"] = str(exc)[:200]

            enrichment_sources.append(source_entry)

        # Score calculation
        lead_view = {
            "website": flat.get("website") or getattr(lead, "website", None),
            "email": flat.get("email") or getattr(lead, "email", None),
        }
        data_fundacao_val = flat.get("data_fundacao")
        data_fundacao_date: date | None = None
        if isinstance(data_fundacao_val, str):
            try:
                data_fundacao_date = datetime.fromisoformat(data_fundacao_val).date()
            except ValueError:
                data_fundacao_date = None

        score, reasons = calculate_score(
            lead_view,
            merged_site_analysis,
            tech_stack=merged_tech_stack,
            data_fundacao=data_fundacao_date,
        )

        return {
            "opportunity_score": score,
            "opportunity_reasons": reasons,
            "site_analysis": merged_site_analysis,
            "social_profiles": merged_social_profiles,
            "tech_stack": merged_tech_stack,
            "socios": merged_socios,
            "enrichment_sources": enrichment_sources,
            **flat,
        }

    def run(
        self,
        lead,
        skip_providers: list[str] | None = None,
        force_providers: list[str] | None = None,
    ) -> dict:
        """Convenience: plan + execute."""
        plan = self.plan(lead, skip_providers=skip_providers, force_providers=force_providers)
        return self.execute(lead, plan)


def _accepts_context(func) -> bool:
    """Check if a `can_run` method accepts a `context` kwarg."""
    import inspect
    try:
        sig = inspect.signature(func)
        return "context" in sig.parameters
    except (TypeError, ValueError):
        return False
```

- [ ] **Step 4: Update package __init__.py**

Replace `backend/app/pipeline/enrichment/__init__.py` with:

```python
"""Smart enrichment pipeline package."""
from app.pipeline.enrichment.base_provider import (
    BaseProvider,
    EnrichmentContext,
    ProviderResult,
)
from app.pipeline.enrichment.orchestrator import (
    EnrichmentOrchestrator,
    EnrichmentPlan,
)
from app.pipeline.enrichment.scoring import calculate_score

__all__ = [
    "BaseProvider",
    "EnrichmentContext",
    "ProviderResult",
    "EnrichmentOrchestrator",
    "EnrichmentPlan",
    "calculate_score",
]
```

- [ ] **Step 5: Run tests to verify they pass**

Run:
```bash
cd backend && pytest tests/enrichment/test_orchestrator.py -v
```

Expected: PASS (6 tests).

- [ ] **Step 6: Run the full enrichment test suite**

Run:
```bash
cd backend && pytest tests/enrichment/ -v
```

Expected: PASS for all tests across the enrichment package.

- [ ] **Step 7: Commit**

```bash
git add backend/app/pipeline/enrichment/orchestrator.py \
        backend/app/pipeline/enrichment/__init__.py \
        backend/tests/enrichment/test_orchestrator.py
git commit -m "feat(enrichment): add EnrichmentOrchestrator with smart planning"
```

---

## Task 12: Refactor Legacy enricher.py Into Thin Wrapper

**Files:**
- Modify: `backend/app/pipeline/enricher.py`
- Modify: `backend/tests/test_enricher.py`

**Goal:** Keep the existing function `enrich_lead_data(website, lead_info, skip_pagespeed)` as the public entry point for backward compatibility with the pipeline router, but route it through the new orchestrator. This avoids breaking `_run_enrich` until Task 13 updates it.

- [ ] **Step 1: Add new wrapper function (keep existing helpers)**

Edit `backend/app/pipeline/enricher.py` — add an import for the orchestrator at the top (after existing imports):

```python
from app.pipeline.enrichment.orchestrator import EnrichmentOrchestrator
```

At the bottom of the file, add (do NOT remove existing helper functions — they're still used by `WebsiteCrawlerProvider`):

```python
def enrich_lead_via_orchestrator(
    lead,
    skip_providers: list[str] | None = None,
    force_providers: list[str] | None = None,
) -> dict:
    """New entry point — uses the orchestrator.

    Takes a Lead-like object directly (not the legacy website+lead_info dict).
    Returns a dict compatible with what _run_enrich applies to the Lead row.
    """
    orch = EnrichmentOrchestrator()
    return orch.run(lead, skip_providers=skip_providers, force_providers=force_providers)
```

- [ ] **Step 2: Update test_enricher.py to not break**

The existing tests import several helpers. The new wrapper doesn't replace them — helpers stay. Just verify the old tests still pass:

Run:
```bash
cd backend && pytest tests/test_enricher.py -v
```

Expected: PASS. If any test breaks, it's because `enrich_lead_data` signature changed — DO NOT change its signature. The legacy function stays intact.

- [ ] **Step 3: Commit**

```bash
git add backend/app/pipeline/enricher.py
git commit -m "feat(enrichment): add orchestrator entry point alongside legacy enricher"
```

---

## Task 13: Update Pipeline Router to Use Orchestrator

**Files:**
- Modify: `backend/app/routers/pipeline.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/tests/test_pipeline_api.py`

- [ ] **Step 1: Update EnrichRequest schema**

Edit `backend/app/schemas.py` — replace the `EnrichRequest` class with:

```python
class EnrichRequest(BaseModel):
    lead_ids: list[int] = []
    skip_providers: list[str] = []
    force_providers: list[str] = []
```

- [ ] **Step 2: Write a failing test for the override params**

Edit `backend/tests/test_pipeline_api.py` — add a new test:

```python
def test_enrich_accepts_skip_providers(client, sample_lead):
    response = client.post(
        "/api/pipeline/enrich",
        json={"lead_ids": [sample_lead.id], "skip_providers": ["apollo"]},
    )
    assert response.status_code in (200, 202)
    data = response.json()
    assert "id" in data or "job_id" in data
```

Run:
```bash
cd backend && pytest tests/test_pipeline_api.py::test_enrich_accepts_skip_providers -v
```

Expected: may PASS already if the route just stores `params` as dict. Inspect — if the test passes, move to Step 3. If it fails due to 422, the schema wasn't applied correctly.

- [ ] **Step 3: Update `_run_enrich` to call the orchestrator**

Edit `backend/app/routers/pipeline.py` — replace the body of `_run_enrich` from the line `from app.pipeline.enricher import enrich_lead_data` down to the end of the per-lead loop. Full replacement:

```python
def _run_enrich(job_id: int, params: dict):
    from app.pipeline.enricher import enrich_lead_via_orchestrator

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()

        _emit(job_id, {"type": "started", "job_id": job_id})

        lead_ids = params.get("lead_ids", [])
        skip_providers = params.get("skip_providers", []) or []
        force_providers = params.get("force_providers", []) or []

        if lead_ids:
            leads = db.query(Lead).filter(Lead.id.in_(lead_ids)).all()
        else:
            leads = db.query(Lead).filter(Lead.status == "scraped").all()

        enriched = 0
        errors: list[str] = []
        for idx, lead in enumerate(leads):
            try:
                result = enrich_lead_via_orchestrator(
                    lead,
                    skip_providers=skip_providers,
                    force_providers=force_providers,
                )
                lead.opportunity_score = result.get("opportunity_score")
                lead.opportunity_reasons = result.get("opportunity_reasons") or []
                lead.site_analysis = result.get("site_analysis") or {}
                social = result.get("social_profiles") or {}
                lead.social_profiles = social if isinstance(social, dict) else {}
                lead.tech_stack = result.get("tech_stack") or []
                lead.enrichment_sources = result.get("enrichment_sources") or []
                if result.get("email"):
                    lead.email = result["email"]
                if result.get("cnpj"):
                    lead.cnpj = result["cnpj"]
                if result.get("razao_social"):
                    lead.razao_social = result["razao_social"]
                if result.get("porte"):
                    lead.porte = result["porte"]
                if result.get("cnae"):
                    lead.cnae = result["cnae"]
                if result.get("data_fundacao"):
                    try:
                        lead.data_fundacao = datetime.fromisoformat(result["data_fundacao"]).date()
                    except (ValueError, TypeError):
                        pass
                if result.get("socios"):
                    lead.socios = result["socios"]
                if result.get("website") and not lead.website:
                    lead.website = result["website"]
                lead.status = "enriched"
                enriched += 1
                db.commit()
                _emit(job_id, {"type": "progress", "current": idx + 1, "total": len(leads)})
            except Exception as exc:
                db.rollback()
                lead.status = "enrich_failed"
                db.commit()
                errors.append(f"Lead {lead.id} ({lead.nome}): {str(exc)[:120]}")

        job.status = "done_with_errors" if errors else "done"
        job.result_summary = {"enriched": enriched, "total": len(leads), "errors": errors}
        job.finished_at = datetime.utcnow()
        db.commit()
        _emit(job_id, {"type": "done", "summary": job.result_summary})

    except Exception as exc:
        db.rollback()
        job = db.get(Job, job_id)
        if job:
            job.status = "failed"
            job.error_message = str(exc)[:500]
            job.finished_at = datetime.utcnow()
            db.commit()
        _emit(job_id, {"type": "error", "message": str(exc)[:500]})
    finally:
        db.close()
```

**Note:** This drops the "disqualified" branch because the new scoring doesn't use `qualified`. The legacy diagnostic-based disqualification is orthogonal to this refactor and can be re-added later as a separate provider if needed.

- [ ] **Step 4: Update the enrich endpoint to pass override fields into job params**

Find the existing enrich endpoint (something like `@router.post("/pipeline/enrich")`). It should accept `EnrichRequest`. Ensure the job's `params` dict stores `skip_providers` and `force_providers`:

```python
@router.post("/pipeline/enrich", response_model=JobOut)
def create_enrich_job(
    req: EnrichRequest,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
):
    job = Job(
        type="enrich",
        status="pending",
        params={
            "lead_ids": req.lead_ids,
            "skip_providers": req.skip_providers,
            "force_providers": req.force_providers,
        },
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    bg.add_task(_run_enrich, job.id, job.params)
    return job
```

If the existing endpoint already exists with a similar shape, only update the `params={...}` dict construction. Do not duplicate routes.

- [ ] **Step 5: Run test_pipeline_api.py**

Run:
```bash
cd backend && pytest tests/test_pipeline_api.py -v
```

Expected: PASS — all tests including the new `test_enrich_accepts_skip_providers`.

- [ ] **Step 6: Run all backend tests**

Run:
```bash
cd backend && pytest
```

Expected: PASS. If any legacy test in `test_enricher.py` breaks because it was asserting on the old disqualification flow, update just those assertions to reflect the new behavior (status = "enriched" always).

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas.py backend/app/routers/pipeline.py backend/tests/test_pipeline_api.py
git commit -m "feat(enrichment): route pipeline enrich job through orchestrator"
```

---

## Task 14: Frontend Types and API Client

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Update Lead type**

Edit `frontend/src/lib/types.ts` — add to the `Lead` interface:

```typescript
export interface Lead {
  id: number;
  public_id: string;
  nome: string;
  telefone: string | null;
  email: string | null;                       // NEW
  website: string | null;
  endereco: string | null;
  cidade: string | null;
  nicho: string | null;
  categoria: string | null;
  rating: number | null;
  reviews_count: number;
  google_maps_url: string | null;
  top_reviews: string[];
  status: string;
  opportunity_score: number | null;
  opportunity_reasons: string[];
  site_analysis: Record<string, unknown>;
  social_profiles: Record<string, unknown>;
  cnpj: string | null;                        // NEW
  razao_social: string | null;                // NEW
  porte: string | null;                       // NEW
  cnae: string | null;                        // NEW
  data_fundacao: string | null;               // NEW
  socios: Array<{ nome: string }>;            // NEW
  tech_stack: Array<{ name: string; category: string }>;  // NEW
  enrichment_sources: Array<{
    provider: string;
    status: string;
    timestamp: string;
    error?: string;
  }>;                                         // NEW
  lp_html: string | null;
  job_id: number | null;
  created_at: string;
  updated_at: string;
}
```

Add a new type for provider metadata (used by the UI toggles):

```typescript
export interface EnrichProvider {
  name: string;
  display_name: string;
  cost: "free" | "freemium";
}

export const ENRICH_PROVIDERS: EnrichProvider[] = [
  { name: "website_crawler", display_name: "Website Crawler", cost: "free" },
  { name: "schema_extractor", display_name: "Schema.org Extractor", cost: "free" },
  { name: "tech_stack", display_name: "Tech Stack Detector", cost: "free" },
  { name: "cnpj_enricher", display_name: "CNPJ (BrasilAPI)", cost: "free" },
  { name: "email_discoverer", display_name: "Email Discoverer", cost: "freemium" },
  { name: "apollo", display_name: "Apollo.io", cost: "freemium" },
];
```

Find the existing `EnrichRequest` type (or create one) and update to:

```typescript
export interface EnrichRequest {
  lead_ids?: number[];
  skip_providers?: string[];
  force_providers?: string[];
}
```

- [ ] **Step 2: Update runEnrich in api.ts**

Edit `frontend/src/lib/api.ts` — find `runEnrich`. Change its signature to:

```typescript
export const runEnrich = (params: EnrichRequest) =>
  apiFetch<Job>("/api/pipeline/enrich", {
    method: "POST",
    body: JSON.stringify(params),
  });
```

(Adjust to match the existing style of `apiFetch` — the key change is accepting `skip_providers` and `force_providers` in the body.)

- [ ] **Step 3: Run frontend lint to catch type errors**

Run:
```bash
cd frontend && npm run lint
```

Expected: No type errors. If any component references old Lead fields that no longer exist, fix them. (No old fields were removed — only added.)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts
git commit -m "feat(frontend): add enrichment fields and provider override types"
```

---

## Task 15: Frontend — Provider Toggles in Enrich Panel

**Files:**
- Modify: `frontend/src/components/pipeline-controls.tsx` (or wherever the enrich trigger UI is)
- Modify: `frontend/src/components/lead-sheet.tsx` (single-lead enrich trigger)

- [ ] **Step 1: Locate the enrich trigger**

Find where `runEnrich` is called. Use:

```bash
cd frontend && grep -rn "runEnrich" src/
```

Expected: hits in `pipeline-controls.tsx` (batch enrich) and `lead-sheet.tsx` (single-lead enrich).

- [ ] **Step 2: Add provider selection state and UI to pipeline-controls.tsx**

Open `frontend/src/components/pipeline-controls.tsx`. Near the top of the component, add:

```typescript
import { ENRICH_PROVIDERS } from "@/lib/types";

// Inside the component:
const [enabledProviders, setEnabledProviders] = useState<Set<string>>(
  new Set(ENRICH_PROVIDERS.map((p) => p.name))
);
const [showProviders, setShowProviders] = useState(false);

const toggleProvider = (name: string) => {
  setEnabledProviders((prev) => {
    const next = new Set(prev);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    return next;
  });
};
```

In the JSX, add a collapsible section near the enrich button:

```tsx
<div className="mt-2">
  <button
    type="button"
    onClick={() => setShowProviders((v) => !v)}
    className="text-xs text-neutral-400 hover:text-neutral-200"
  >
    {showProviders ? "▾" : "▸"} Fontes de enriquecimento ({enabledProviders.size}/{ENRICH_PROVIDERS.length})
  </button>
  {showProviders && (
    <div className="mt-2 space-y-1 rounded border border-neutral-800 p-2">
      {ENRICH_PROVIDERS.map((p) => (
        <label key={p.name} className="flex items-center gap-2 text-xs">
          <input
            type="checkbox"
            checked={enabledProviders.has(p.name)}
            onChange={() => toggleProvider(p.name)}
          />
          <span>{p.display_name}</span>
          {p.cost === "freemium" && (
            <span className="rounded bg-amber-900/40 px-1 text-[10px] text-amber-300">
              freemium
            </span>
          )}
        </label>
      ))}
    </div>
  )}
</div>
```

Update the enrich trigger function (wherever `runEnrich` is called) to pass `skip_providers`:

```typescript
const handleEnrich = async () => {
  const skip = ENRICH_PROVIDERS
    .filter((p) => !enabledProviders.has(p.name))
    .map((p) => p.name);
  await runEnrich({ lead_ids: selectedLeadIds, skip_providers: skip });
  // ...existing post-enrich logic
};
```

- [ ] **Step 3: Apply the same pattern to lead-sheet.tsx (single lead)**

Open `frontend/src/components/lead-sheet.tsx`. For the single-lead enrich button, you can either reuse the full checkbox UI or keep it simple — recommendation: keep it simple for lead-sheet (no toggles, uses default — all providers). This avoids duplicating the UI. If you want consistency, copy the pattern from Step 2.

For MVP, leave `lead-sheet.tsx` unchanged — it calls `runEnrich({ lead_ids: [lead.id] })` with all providers.

- [ ] **Step 4: Display enrichment_sources in lead detail**

In `frontend/src/components/lead-detail.tsx` (or `lead-sheet.tsx`), add a small section showing which providers ran:

```tsx
{lead.enrichment_sources && lead.enrichment_sources.length > 0 && (
  <div className="mt-4">
    <h3 className="text-xs font-semibold uppercase text-neutral-400">
      Fontes de enriquecimento
    </h3>
    <ul className="mt-1 space-y-0.5">
      {lead.enrichment_sources.map((s, i) => (
        <li key={i} className="flex items-center gap-2 text-xs">
          <span
            className={
              s.status === "ok"
                ? "text-emerald-400"
                : s.status === "skipped"
                ? "text-neutral-500"
                : "text-red-400"
            }
          >
            ●
          </span>
          <span className="text-neutral-200">{s.provider}</span>
          {s.error && (
            <span className="truncate text-neutral-500">— {s.error}</span>
          )}
        </li>
      ))}
    </ul>
  </div>
)}
```

- [ ] **Step 5: Run lint**

Run:
```bash
cd frontend && npm run lint
```

Expected: No errors.

- [ ] **Step 6: Manual smoke test**

Start the frontend:
```bash
cd frontend && npm run dev
```

In the browser:
1. Open the Kanban page
2. Verify "Fontes de enriquecimento" toggle appears near the enrich button
3. Toggle providers on/off
4. Open a lead detail — verify `enrichment_sources` section renders (empty for existing leads)

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/pipeline-controls.tsx \
        frontend/src/components/lead-detail.tsx \
        frontend/src/components/lead-sheet.tsx
git commit -m "feat(frontend): add provider toggles and enrichment sources display"
```

---

## Task 16: End-to-End Integration Test

**Files:**
- Create: `backend/tests/enrichment/test_integration.py`

- [ ] **Step 1: Write integration test**

Create `backend/tests/enrichment/test_integration.py`:

```python
"""End-to-end integration test: orchestrator runs over a fake lead with mocks."""
from unittest.mock import patch, MagicMock

from app.pipeline.enrichment.orchestrator import EnrichmentOrchestrator


class FakeLead:
    def __init__(self, **kwargs):
        self.website = kwargs.get("website")
        self.email = kwargs.get("email")
        self.cnpj = kwargs.get("cnpj")
        self.nome = kwargs.get("nome", "Clinica X")
        self.cidade = kwargs.get("cidade", "Chapeco SC")
        self.telefone = kwargs.get("telefone")
        self.nicho = kwargs.get("nicho")
        self.categoria = kwargs.get("categoria")
        self.rating = kwargs.get("rating")
        self.reviews_count = kwargs.get("reviews_count", 0)
        self.top_reviews = kwargs.get("top_reviews", [])


@patch("app.pipeline.enrichment.providers.apollo_enricher.settings")
@patch("app.pipeline.enrichment.providers.email_discoverer.settings")
@patch("app.pipeline.enrichment.providers.website_crawler.check_pagespeed")
@patch("app.pipeline.enrichment.providers.website_crawler.requests.get")
def test_full_pipeline_on_website_lead(
    mock_crawler_get, mock_pagespeed, mock_email_settings, mock_apollo_settings
):
    mock_email_settings.hunter_api_key = ""
    mock_apollo_settings.apollo_api_key = ""

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.url = "https://clinicax.com"
    mock_resp.text = """
    <html>
    <head>
      <meta name="viewport" content="width=device-width">
      <meta name="generator" content="WordPress">
    </head>
    <body>
      <a href="mailto:contato@clinicax.com">email</a>
      <script src="/wp-content/themes/foo/bar.js"></script>
      <a href="https://instagram.com/clinicax">ig</a>
      <button>Agende sua consulta</button>
    </body>
    </html>
    """
    mock_resp.headers = {"Server": "nginx"}
    mock_crawler_get.return_value = mock_resp
    mock_pagespeed.return_value = {"performance_score": 75}

    lead = FakeLead(website="https://clinicax.com")
    orch = EnrichmentOrchestrator()

    with patch(
        "app.pipeline.enrichment.providers.website_crawler.settings"
    ) as mock_crawler_settings:
        mock_crawler_settings.apify_token = ""
        mock_crawler_settings.skip_social_scraping = True
        result = orch.run(lead)

    # Assertions
    assert result["opportunity_score"] is not None
    assert result["site_analysis"]["has_ssl"] is True
    assert result["site_analysis"]["has_responsive_meta"] is True
    # Tech stack detected WordPress
    names = [t["name"] for t in result["tech_stack"]]
    assert "WordPress" in names
    # Email extracted
    assert result.get("email") == "contato@clinicax.com"
    # Enrichment sources recorded
    source_names = [s["provider"] for s in result["enrichment_sources"]]
    assert "website_crawler" in source_names
    assert "schema_extractor" in source_names
    assert "tech_stack" in source_names
    assert "email_discoverer" in source_names


def test_full_pipeline_skips_providers_via_override():
    lead = FakeLead(website="https://example.com")
    orch = EnrichmentOrchestrator()
    plan = orch.plan(lead, skip_providers=["apollo", "email_discoverer", "website_crawler",
                                             "schema_extractor", "tech_stack", "cnpj_enricher"])
    assert plan.providers == []
```

- [ ] **Step 2: Run tests**

Run:
```bash
cd backend && pytest tests/enrichment/test_integration.py -v
```

Expected: PASS (2 tests).

- [ ] **Step 3: Run the full test suite**

Run:
```bash
cd backend && pytest
```

Expected: PASS — all tests including legacy `test_enricher.py`, `test_pipeline_api.py`, and the new `tests/enrichment/` package.

- [ ] **Step 4: Run frontend lint one more time**

Run:
```bash
cd frontend && npm run lint
```

Expected: Clean.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/enrichment/test_integration.py
git commit -m "test(enrichment): add end-to-end orchestrator integration test"
```

---

## Self-Review Notes (author use)

- Every task has concrete file paths, concrete code, concrete test assertions.
- Types used in later tasks (`EnrichmentContext`, `ProviderResult`, `BaseProvider`) are defined in Task 3 before any consumer.
- `calculate_score` signature (Task 4) is consistent with how `orchestrator.execute` calls it (Task 11).
- `WebsiteCrawlerProvider` reuses `analyze_html`, `check_pagespeed`, `scrape_social_profiles` from legacy `enricher.py` — intentional, these helpers stay.
- `CnpjProvider.can_run` returns False for name+cidade case because BrasilAPI doesn't support name search — documented explicitly, not a bug.
- Removed the legacy "disqualified" flow in `_run_enrich` — documented in Task 13 Step 3 as orthogonal to this refactor.
- `skip_providers` / `force_providers` parameters are propagated: schema (Task 13) → route handler (Task 13) → job params dict (Task 13) → `_run_enrich` (Task 13) → `orchestrator.run` (Task 11).
- Migration (Task 1) uses `down_revision = "h01_better_auth_tables"` with explicit instruction to verify it matches `alembic heads`.
- Frontend types (Task 14) and UI (Task 15) match the backend `enrichment_sources` shape.
- No placeholders — all code blocks are complete and runnable.
- Every item in the "Happy Paths & Edge Cases Catalog" is covered by at least one test:
  - HP1: Task 16 integration test
  - HP2: Task 11 `test_plan_without_website_but_with_cnpj_discovers_first`
  - HP3: Task 9 `test_extracts_email_from_html`
  - HP4: Task 11 `test_existing_*_preserved_*` + `test_run_returns_fresh_lists_not_appended`
  - HP5: Task 11 `test_plan_with_only_nome_and_phone_is_mostly_empty` + `test_empty_plan_returns_valid_result`
  - EC1/EC2/EC3: Task 5 URL normalization tests
  - EC4: Task 8 `test_accepts_masked_cnpj`
  - EC5: Task 9 `test_normalizes_mixed_case_emails`
  - EC6: Task 11 `test_existing_email_preserved_over_discovered` + Task 9 `test_skips_if_lead_already_has_email`
  - EC7: Task 11 `test_existing_website_preserved_over_discovered`
  - EC8: Task 11 `test_existing_cnpj_preserved`
  - EC9/EC10: Task 11 `test_run_returns_fresh_lists_not_appended`
  - EC11/EC12/EC13: Task 6 `@graph` / array / empty-string tests + Task 7 empty-string test
  - EC14: Task 9 `test_ignores_image_filename_false_positives`
  - EC15: Task 8 `test_handles_empty_body`
  - EC16: Task 9 `test_hunter_402_recorded_as_error_not_crash`
  - EC17: Task 10 `test_handles_null_organization`
  - EC18: Task 5 `test_run_handles_timeout` + Task 8 `test_handles_timeout`
  - EC19: Task 11 `test_empty_plan_returns_valid_result`
  - EC20: Task 11 `test_provider_returns_invalid_type_recorded_as_error`
  - EC21: Task 11 `test_skip_overrides_force_when_both_specified`
- Data-precedence logic is implemented in `orchestrator.execute` (flat-field loop checks `existing_flat`), not in each provider. Providers still do a best-effort check (e.g. email_discoverer skips if lead already has email) as belt-and-suspenders.
- Idempotency: `execute` builds all lists (`enrichment_sources`, `tech_stack`, `socios`) from scratch each run — they are NEVER merged with pre-existing lead values. Task 13's consumer applies them with simple assignment, so re-running enrichment replaces these fields entirely.
- Crawl chain inclusion in the plan: uses "optimistic inclusion" when lead has website OR might discover one via CNPJ. The per-provider `can_run` is re-checked inside `execute` with the live context to skip gracefully if the discovery didn't actually happen.
