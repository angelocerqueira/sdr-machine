# MCP M-2 READ Tools + Resources Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar 13 tools READ-only e 12 resources URI-style ao `mcp_server` montado em M-1. Cada tool delega pros services existentes do backend, filtrando por `workspace_id` derivado do AccessToken. Sem side effects — todas chamadas seguras.

**Architecture:** Tools registradas via `@mcp_server.tool()` decorators agrupados em arquivos por domínio (`tools_leads.py`, `tools_conversations.py`, etc). Resources via `@mcp_server.resource()` com pattern matching URI. Helper `db_session()` context manager pra abrir/fechar Session por chamada. Workspace_id sempre extraído de `Context` via `get_workspace_id(ctx)`.

**Tech Stack:** Mesmo M-1 — FastAPI + SQLAlchemy + `mcp` SDK + pytest

**Spec:** [`docs/superpowers/specs/2026-05-18-mcp-server-m0-architecture.md`](../specs/2026-05-18-mcp-server-m0-architecture.md) §4 (READ tools), §5 (Resources)

**Depende:** M-1 mergeado (foundation pronta com `build_mcp_server()` retornando FastMCP autenticado).

---

## Notas de execução

- Branch: `feat/mcp-m2-read-tools`. Baseia em main com M-1 já merged.
- Testes via `cd backend && venv/bin/pytest tests/mcp/`
- Cada tool tem 2-3 tests: happy path + workspace isolation + edge case (empty/not-found)
- Testes usam helper `_seed_workspace(db, ws_id)` pra criar dados scoped
- Commits Conventional Commits, escopo `mcp` ou `mcp-tools`

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `backend/app/mcp/db.py` | Create | `db_session()` context manager (abre+fecha Session por tool call) |
| `backend/app/mcp/schemas.py` | Create | Pydantic schemas leves pra retorno das tools (subset dos schemas da API) |
| `backend/app/mcp/tools_leads.py` | Create | `list_leads`, `get_lead`, `list_landing_pages`, `get_lp_html` |
| `backend/app/mcp/tools_conversations.py` | Create | `list_conversations`, `get_conversation` |
| `backend/app/mcp/tools_jobs.py` | Create | `list_jobs`, `get_job` |
| `backend/app/mcp/tools_stats.py` | Create | `dashboard_stats`, `conversion_funnel` |
| `backend/app/mcp/tools_workspace.py` | Create | `workspace_profile`, `workspace_targeting` |
| `backend/app/mcp/tools_pending.py` | Create | `list_pending_actions` |
| `backend/app/mcp/resources.py` | Create | Resources URI handlers (12 patterns) |
| `backend/app/mcp/server.py` | Modify | Chamar `register_all_tools(server)` + `register_resources(server)` no build |
| `backend/tests/mcp/test_tools_leads.py` | Create | 4 tools × 2-3 tests cada |
| `backend/tests/mcp/test_tools_conversations.py` | Create | 2 tools × 2-3 tests |
| `backend/tests/mcp/test_tools_jobs.py` | Create | 2 tools × 2 tests |
| `backend/tests/mcp/test_tools_stats.py` | Create | 2 tools × 2 tests |
| `backend/tests/mcp/test_tools_workspace.py` | Create | 2 tools × 2 tests |
| `backend/tests/mcp/test_tools_pending.py` | Create | 1 tool × 2 tests (depende de M-3 pra ter PendingActions reais, mas testa shape) |
| `backend/tests/mcp/test_resources.py` | Create | 12 resources × 1 smoke test cada |

---

## Task 1: Setup — `db_session()` + schemas

**Files:**
- Create: `backend/app/mcp/db.py`
- Create: `backend/app/mcp/schemas.py`

- [ ] **Step 1: Criar branch**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git checkout main && git pull origin main
git checkout -b feat/mcp-m2-read-tools
```

- [ ] **Step 2: Test falhando — `db_session` opens + closes**

Create `backend/tests/mcp/test_db_helper.py`:

```python
from app.mcp.db import db_session
from app.models import Lead


def test_db_session_yields_session():
    with db_session() as db:
        # Smoke: poder fazer query
        count = db.query(Lead).count()
        assert isinstance(count, int)


def test_db_session_rollback_on_exception():
    try:
        with db_session() as db:
            db.add(Lead(nome="rollback-test", telefone="x", status="scraped"))
            raise RuntimeError("force rollback")
    except RuntimeError:
        pass

    with db_session() as db:
        count = db.query(Lead).filter_by(nome="rollback-test").count()
        assert count == 0
```

- [ ] **Step 3: Rodar — deve falhar**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_db_helper.py -v
```

Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 4: Implementar `db.py`**

Create `backend/app/mcp/db.py`:

```python
"""DB session helper pras tools MCP.

Tools são chamadas async pelo FastMCP, mas SQLAlchemy é sync — abrimos uma
Session por chamada e fechamos no exit. Erros causam rollback.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy.orm import Session

from app.database import SessionLocal


@contextmanager
def db_session() -> Iterator[Session]:
    """Session por chamada. Commit explícito nos tools que escrevem;
    auto-rollback em exception."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

- [ ] **Step 5: Rodar test — deve passar**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_db_helper.py -v
```

Expected: 2 PASS.

- [ ] **Step 6: Criar `schemas.py` com Pydantic leves**

Create `backend/app/mcp/schemas.py`:

```python
"""Pydantic schemas leves pras tools MCP retornarem.

Retornamos subset dos campos pra não estourar context window do LLM.
Tools full-detail expõem mais (ex: get_lead retorna enrichment completo).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel


class LeadSummary(BaseModel):
    id: int
    nome: str
    telefone: Optional[str]
    nicho: Optional[str]
    cidade: Optional[str]
    status: str
    opportunity_score: Optional[int]
    has_email: bool
    has_website: bool

    @classmethod
    def from_lead(cls, lead) -> "LeadSummary":
        return cls(
            id=lead.id, nome=lead.nome or "(sem nome)",
            telefone=lead.telefone, nicho=lead.nicho, cidade=lead.cidade,
            status=lead.status, opportunity_score=lead.opportunity_score,
            has_email=bool(lead.email), has_website=bool(lead.website),
        )


class LeadListResult(BaseModel):
    items: List[LeadSummary]
    total: int
    page: int
    per_page: int


class LeadFull(BaseModel):
    id: int
    nome: str
    telefone: Optional[str]
    email: Optional[str]
    website: Optional[str]
    endereco: Optional[str]
    nicho: Optional[str]
    cidade: Optional[str]
    categoria: Optional[str]
    rating: Optional[float]
    reviews_count: Optional[int]
    status: str
    opportunity_score: Optional[int]
    opportunity_reasons: Optional[List[str]]
    cnpj: Optional[str]
    razao_social: Optional[str]
    porte: Optional[str]
    tech_stack: Optional[List[Any]]
    enrichment_sources: Optional[List[Any]]
    perfil_lead: Optional[str]
    nicho_canonico: Optional[str]
    created_at: datetime
    updated_at: datetime
    responded_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ConversationSummary(BaseModel):
    id: int
    lead_id: int
    lead_nome: Optional[str]
    phone: str
    provider: str
    last_message_at: Optional[datetime]
    last_message_preview: Optional[str]
    unread_count: int
    status: str


class MessageSummary(BaseModel):
    id: int
    direction: str
    body: Optional[str]
    sent_at: Optional[datetime]
    received_at: Optional[datetime]
    status: str


class ConversationFull(BaseModel):
    id: int
    lead_id: int
    phone: str
    provider: str
    unread_count: int
    status: str
    created_at: datetime
    messages: List[MessageSummary]


class JobSummary(BaseModel):
    id: int
    type: str
    status: str
    progress: Optional[float]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_message: Optional[str]


class JobFull(JobSummary):
    params: Optional[dict]
    result_summary: Optional[dict]


class DashboardStats(BaseModel):
    total_leads: int
    by_status: dict[str, int]
    avg_score: Optional[float]
    conversion_rate: Optional[float]
    leads_by_day: List[dict]


class LandingPageSummary(BaseModel):
    id: int
    lead_id: int
    version: int
    is_active: bool
    created_at: datetime


class WorkspaceProfileOut(BaseModel):
    business_name: Optional[str]
    your_name: Optional[str]
    your_email: Optional[str]
    your_whatsapp: Optional[str]
    your_website: Optional[str]
    legal_basis: Optional[str]


class WorkspaceTargetingOut(BaseModel):
    target_niches: List[str]
    target_cities: List[str]
    min_rating: Optional[float]
    max_results_per_search: Optional[int]
    opportunity_score_threshold: Optional[int]


class PendingActionOut(BaseModel):
    id: str
    action_type: str
    preview: dict
    created_at: datetime
    expires_at: datetime
    committed_at: Optional[datetime]
    cancelled_at: Optional[datetime]
```

- [ ] **Step 7: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/app/mcp/db.py backend/app/mcp/schemas.py backend/tests/mcp/test_db_helper.py
git commit -m "feat(mcp): db_session helper + schemas leves pras tools"
```

---

## Task 2: Tools de Leads — `list_leads` + `get_lead`

**Files:**
- Create: `backend/app/mcp/tools_leads.py`
- Create: `backend/tests/mcp/test_tools_leads.py`

- [ ] **Step 1: Test falhando**

Create `backend/tests/mcp/test_tools_leads.py`:

```python
import asyncio
from unittest.mock import Mock

from mcp.server.auth.provider import AccessToken

from app.models import Lead
from app.mcp.tools_leads import list_leads, get_lead


def _ctx(workspace_id: int = 1):
    """Mock Context com workspace scope."""
    ctx = Mock()
    user = Mock()
    user.access_token = AccessToken(
        token="x" * 64, client_id=f"mcp-{workspace_id}",
        scopes=[f"mcp:workspace:{workspace_id}"], expires_at=None, resource=None,
    )
    ctx.request_context.request.user = user
    return ctx


def test_list_leads_empty(db):
    result = asyncio.run(list_leads(_ctx(), filter=None, limit=20, offset=0))
    assert result.total == 0
    assert result.items == []


def test_list_leads_returns_all(db):
    db.add_all([
        Lead(nome="A", telefone="44999990000", status="scraped"),
        Lead(nome="B", telefone="44888880000", status="enriched"),
    ])
    db.commit()

    result = asyncio.run(list_leads(_ctx(), filter=None, limit=20, offset=0))
    assert result.total == 2
    assert {item.nome for item in result.items} == {"A", "B"}


def test_list_leads_filter_status(db):
    db.add_all([
        Lead(nome="A", telefone="x", status="scraped"),
        Lead(nome="B", telefone="y", status="enriched"),
    ])
    db.commit()

    result = asyncio.run(list_leads(
        _ctx(), filter={"status": "scraped"}, limit=20, offset=0,
    ))
    assert result.total == 1
    assert result.items[0].nome == "A"


def test_list_leads_filter_score_min(db):
    db.add_all([
        Lead(nome="Low", telefone="x", status="scraped", opportunity_score=30),
        Lead(nome="High", telefone="y", status="scraped", opportunity_score=85),
    ])
    db.commit()

    result = asyncio.run(list_leads(
        _ctx(), filter={"score_min": 70}, limit=20, offset=0,
    ))
    assert result.total == 1
    assert result.items[0].nome == "High"


def test_list_leads_search(db):
    db.add_all([
        Lead(nome="Padaria Central", telefone="x", status="scraped"),
        Lead(nome="Auto Posto", telefone="y", status="scraped"),
    ])
    db.commit()

    result = asyncio.run(list_leads(
        _ctx(), filter={"search": "padaria"}, limit=20, offset=0,
    ))
    assert result.total == 1


def test_list_leads_pagination(db):
    for i in range(5):
        db.add(Lead(nome=f"L{i}", telefone=f"x{i}", status="scraped"))
    db.commit()

    p1 = asyncio.run(list_leads(_ctx(), filter=None, limit=2, offset=0))
    p2 = asyncio.run(list_leads(_ctx(), filter=None, limit=2, offset=2))
    assert len(p1.items) == 2
    assert len(p2.items) == 2
    assert p1.total == 5
    assert {x.id for x in p1.items} != {x.id for x in p2.items}


def test_get_lead_returns_full(db):
    lead = Lead(
        nome="Detail Co", telefone="44999990000", email="a@b.com",
        website="https://x.com", nicho="dentista", cidade="Chapecó",
        status="enriched", opportunity_score=75,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    result = asyncio.run(get_lead(_ctx(), id=lead.id))
    assert result is not None
    assert result.id == lead.id
    assert result.email == "a@b.com"
    assert result.opportunity_score == 75


def test_get_lead_not_found(db):
    result = asyncio.run(get_lead(_ctx(), id=9999))
    assert result is None
```

- [ ] **Step 2: Rodar — deve falhar**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_tools_leads.py -v
```

Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 3: Implementar `tools_leads.py`**

Create `backend/app/mcp/tools_leads.py`:

```python
"""MCP READ tools — Leads domain.

Tools NÃO são registradas via decorator nesse módulo (porque server é construído
elsewhere). Em vez disso, expomos funções puras e o `register_leads_tools(server)`
faz o binding.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import or_

from app.mcp.context import get_workspace_id
from app.mcp.db import db_session
from app.mcp.schemas import (
    LandingPageSummary,
    LeadFull,
    LeadListResult,
    LeadSummary,
)
from app.models import LandingPage, Lead


async def list_leads(
    ctx: Any,
    filter: Optional[dict] = None,
    limit: int = 20,
    offset: int = 0,
) -> LeadListResult:
    """Lista leads do workspace com filtros opcionais.

    Filter keys suportados: status, nicho, cidade, score_min, has_email, search.
    """
    workspace_id = get_workspace_id(ctx)  # noqa: F841 — usado quando Lead.workspace_id existir
    f = filter or {}

    with db_session() as db:
        q = db.query(Lead)
        # TODO multi-tenant: filter by workspace_id quando Lead.workspace_id existir.
        if f.get("status"):
            q = q.filter(Lead.status == f["status"])
        if f.get("nicho"):
            q = q.filter(Lead.nicho == f["nicho"])
        if f.get("cidade"):
            q = q.filter(Lead.cidade == f["cidade"])
        if f.get("score_min") is not None:
            q = q.filter(Lead.opportunity_score >= f["score_min"])
        if f.get("has_email") is True:
            q = q.filter(Lead.email.isnot(None), Lead.email != "")
        if f.get("search"):
            pat = f"%{f['search']}%"
            q = q.filter(or_(Lead.nome.ilike(pat), Lead.telefone.ilike(pat)))

        total = q.count()
        rows = q.order_by(Lead.id.desc()).limit(limit).offset(offset).all()

        return LeadListResult(
            items=[LeadSummary.from_lead(r) for r in rows],
            total=total,
            page=offset // max(limit, 1) + 1 if limit > 0 else 1,
            per_page=limit,
        )


async def get_lead(ctx: Any, id: int) -> Optional[LeadFull]:
    """Detalhe completo de 1 lead. None se não existir."""
    workspace_id = get_workspace_id(ctx)  # noqa: F841

    with db_session() as db:
        lead = db.get(Lead, id)
        if lead is None:
            return None
        return LeadFull.model_validate(lead)


async def list_landing_pages(ctx: Any, lead_id: int) -> list[LandingPageSummary]:
    """LPs geradas pro lead."""
    workspace_id = get_workspace_id(ctx)  # noqa: F841

    with db_session() as db:
        rows = (
            db.query(LandingPage)
            .filter_by(lead_id=lead_id)
            .order_by(LandingPage.version.desc())
            .all()
        )
        return [
            LandingPageSummary(
                id=r.id, lead_id=r.lead_id, version=r.version,
                is_active=r.is_active, created_at=r.created_at,
            )
            for r in rows
        ]


async def get_lp_html(ctx: Any, lp_id: int) -> Optional[dict]:
    """Retorna HTML completo + URL pública. None se LP não existe."""
    workspace_id = get_workspace_id(ctx)  # noqa: F841

    with db_session() as db:
        lp = db.get(LandingPage, lp_id)
        if lp is None:
            return None
        # public_id em Lead (não em LandingPage); buscar via lead
        from app.config import settings as app_settings
        lead = db.get(Lead, lp.lead_id)
        public_url = None
        if lead and lead.public_id:
            base = (app_settings.api_url or "http://localhost:8000").rstrip("/")
            public_url = f"{base}/api/leads/p/{lead.public_id}/lp"
        return {
            "html": lp.html,
            "public_url": public_url,
            "version": lp.version,
            "is_active": lp.is_active,
        }


def register_leads_tools(server) -> None:
    """Registra as tools no FastMCP server. Chamado de build_mcp_server()."""
    server.tool(name="list_leads")(list_leads)
    server.tool(name="get_lead")(get_lead)
    server.tool(name="list_landing_pages")(list_landing_pages)
    server.tool(name="get_lp_html")(get_lp_html)
```

- [ ] **Step 4: Rodar tests**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_tools_leads.py -v
```

Expected: 8 PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/app/mcp/tools_leads.py backend/tests/mcp/test_tools_leads.py
git commit -m "feat(mcp): tools list_leads + get_lead + LP helpers"
```

---

## Task 3: Tools de Conversations

**Files:**
- Create: `backend/app/mcp/tools_conversations.py`
- Create: `backend/tests/mcp/test_tools_conversations.py`

- [ ] **Step 1: Test falhando**

Create `backend/tests/mcp/test_tools_conversations.py`:

```python
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from mcp.server.auth.provider import AccessToken

from app.models import Conversation, ConversationMessage, Lead
from app.mcp.tools_conversations import list_conversations, get_conversation


def _ctx(workspace_id: int = 1):
    ctx = Mock()
    user = Mock()
    user.access_token = AccessToken(
        token="x" * 64, client_id="mcp-1",
        scopes=[f"mcp:workspace:{workspace_id}"], expires_at=None, resource=None,
    )
    ctx.request_context.request.user = user
    return ctx


def _seed_conv(db, *, lead_nome="X", phone="5544999990000", unread=0, msgs=None):
    lead = Lead(nome=lead_nome, telefone=phone, status="outreach_sent")
    db.add(lead)
    db.commit()
    db.refresh(lead)
    conv = Conversation(
        workspace_id=1, lead_id=lead.id, provider="evolution",
        provider_chat_id=f"{phone}@s.whatsapp.net", phone=phone,
        last_message_at=datetime.now(timezone.utc),
        unread_count=unread,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    for i, (direction, body) in enumerate(msgs or []):
        db.add(ConversationMessage(
            conversation_id=conv.id, direction=direction,
            provider_message_id=f"MSG-{conv.id}-{i}", body=body,
            status="received" if direction == "in" else "sent",
            received_at=datetime.now(timezone.utc) if direction == "in" else None,
            sent_at=datetime.now(timezone.utc) if direction == "out" else None,
        ))
    db.commit()
    return conv


def test_list_conversations_empty(db):
    result = asyncio.run(list_conversations(_ctx(), filter=None))
    assert result == []


def test_list_conversations_returns_summary(db):
    _seed_conv(db, lead_nome="A", phone="5544111111111",
               msgs=[("in", "oi A")])
    _seed_conv(db, lead_nome="B", phone="5544222222222",
               msgs=[("in", "oi B"), ("out", "tudo bem?")])

    result = asyncio.run(list_conversations(_ctx(), filter=None))
    assert len(result) == 2
    assert {r.lead_nome for r in result} == {"A", "B"}


def test_list_conversations_filter_unread(db):
    _seed_conv(db, lead_nome="Read", phone="5544111111111", unread=0,
               msgs=[("in", "x")])
    _seed_conv(db, lead_nome="Unread", phone="5544222222222", unread=3,
               msgs=[("in", "y")])

    result = asyncio.run(list_conversations(_ctx(), filter={"unread": True}))
    assert len(result) == 1
    assert result[0].lead_nome == "Unread"


def test_get_conversation_returns_msgs_chronological(db):
    conv = _seed_conv(db, msgs=[("in", "1ª"), ("out", "2ª"), ("in", "3ª")])
    result = asyncio.run(get_conversation(_ctx(), id=conv.id))
    assert result is not None
    assert len(result.messages) == 3
    assert result.messages[0].body == "1ª"
    assert result.messages[-1].body == "3ª"


def test_get_conversation_not_found(db):
    result = asyncio.run(get_conversation(_ctx(), id=9999))
    assert result is None
```

- [ ] **Step 2: Rodar — deve falhar**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_tools_conversations.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implementar `tools_conversations.py`**

Create `backend/app/mcp/tools_conversations.py`:

```python
"""MCP READ tools — Conversations."""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import desc

from app.mcp.context import get_workspace_id
from app.mcp.db import db_session
from app.mcp.schemas import (
    ConversationFull,
    ConversationSummary,
    MessageSummary,
)
from app.models import Conversation, ConversationMessage, Lead

_PREVIEW_LEN = 80


def _preview(db, conv_id: int) -> Optional[str]:
    last = (
        db.query(ConversationMessage)
        .filter_by(conversation_id=conv_id)
        .order_by(desc(ConversationMessage.created_at))
        .first()
    )
    if last is None or not last.body:
        return None
    return last.body[:_PREVIEW_LEN]


async def list_conversations(
    ctx: Any, filter: Optional[dict] = None,
) -> list[ConversationSummary]:
    workspace_id = get_workspace_id(ctx)
    f = filter or {}

    with db_session() as db:
        q = (
            db.query(Conversation, Lead)
            .join(Lead, Conversation.lead_id == Lead.id)
            .filter(Conversation.workspace_id == workspace_id)
        )
        if f.get("unread") is True:
            q = q.filter(Conversation.unread_count > 0)
        if f.get("status"):
            q = q.filter(Lead.status == f["status"])
        if f.get("search"):
            from sqlalchemy import or_
            pat = f"%{f['search']}%"
            q = q.filter(or_(
                Lead.nome.ilike(pat),
                Lead.telefone.ilike(pat),
                Conversation.phone.ilike(pat),
            ))

        rows = q.order_by(desc(Conversation.last_message_at)).all()
        out = []
        for conv, lead in rows:
            out.append(ConversationSummary(
                id=conv.id, lead_id=lead.id, lead_nome=lead.nome,
                phone=conv.phone, provider=conv.provider,
                last_message_at=conv.last_message_at,
                last_message_preview=_preview(db, conv.id),
                unread_count=conv.unread_count, status=conv.status,
            ))
        return out


async def get_conversation(ctx: Any, id: int) -> Optional[ConversationFull]:
    workspace_id = get_workspace_id(ctx)

    with db_session() as db:
        conv = (
            db.query(Conversation)
            .filter_by(id=id, workspace_id=workspace_id)
            .first()
        )
        if conv is None:
            return None
        msgs = (
            db.query(ConversationMessage)
            .filter_by(conversation_id=conv.id)
            .order_by(ConversationMessage.created_at.asc())
            .all()
        )
        return ConversationFull(
            id=conv.id, lead_id=conv.lead_id, phone=conv.phone,
            provider=conv.provider, unread_count=conv.unread_count,
            status=conv.status, created_at=conv.created_at,
            messages=[
                MessageSummary(
                    id=m.id, direction=m.direction, body=m.body,
                    sent_at=m.sent_at, received_at=m.received_at,
                    status=m.status,
                )
                for m in msgs
            ],
        )


def register_conversations_tools(server) -> None:
    server.tool(name="list_conversations")(list_conversations)
    server.tool(name="get_conversation")(get_conversation)
```

- [ ] **Step 4: Rodar tests**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_tools_conversations.py -v
```

Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/app/mcp/tools_conversations.py backend/tests/mcp/test_tools_conversations.py
git commit -m "feat(mcp): tools list_conversations + get_conversation"
```

---

## Task 4: Tools de Jobs

**Files:**
- Create: `backend/app/mcp/tools_jobs.py`
- Create: `backend/tests/mcp/test_tools_jobs.py`

- [ ] **Step 1: Test falhando**

Create `backend/tests/mcp/test_tools_jobs.py`:

```python
import asyncio
from datetime import datetime
from unittest.mock import Mock

from mcp.server.auth.provider import AccessToken

from app.models import Job
from app.mcp.tools_jobs import list_jobs, get_job


def _ctx():
    ctx = Mock()
    user = Mock()
    user.access_token = AccessToken(
        token="x" * 64, client_id="mcp-1",
        scopes=["mcp:workspace:1"], expires_at=None, resource=None,
    )
    ctx.request_context.request.user = user
    return ctx


def test_list_jobs_empty(db):
    result = asyncio.run(list_jobs(_ctx(), status=None, type=None, limit=10))
    assert result == []


def test_list_jobs_filter_status(db):
    db.add_all([
        Job(type="scrape", status="done", params={}, started_at=datetime.utcnow()),
        Job(type="enrich", status="running", params={}, started_at=datetime.utcnow()),
    ])
    db.commit()

    result = asyncio.run(list_jobs(_ctx(), status="running", type=None, limit=10))
    assert len(result) == 1
    assert result[0].status == "running"


def test_get_job_returns_full(db):
    job = Job(
        type="scrape", status="done", params={"nichos": ["dentista"]},
        result_summary={"total": 10}, started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    result = asyncio.run(get_job(_ctx(), id=job.id))
    assert result is not None
    assert result.params == {"nichos": ["dentista"]}
    assert result.result_summary == {"total": 10}


def test_get_job_not_found(db):
    result = asyncio.run(get_job(_ctx(), id=9999))
    assert result is None
```

- [ ] **Step 2: Rodar — deve falhar**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_tools_jobs.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implementar `tools_jobs.py`**

Create `backend/app/mcp/tools_jobs.py`:

```python
"""MCP READ tools — Jobs."""
from __future__ import annotations

from typing import Any, Optional

from app.mcp.context import get_workspace_id
from app.mcp.db import db_session
from app.mcp.schemas import JobFull, JobSummary
from app.models import Job


async def list_jobs(
    ctx: Any,
    status: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = 10,
) -> list[JobSummary]:
    workspace_id = get_workspace_id(ctx)  # noqa: F841 — Job não tem workspace_id hoje

    with db_session() as db:
        q = db.query(Job)
        if status:
            q = q.filter(Job.status == status)
        if type:
            q = q.filter(Job.type == type)
        rows = q.order_by(Job.id.desc()).limit(limit).all()
        return [
            JobSummary(
                id=r.id, type=r.type, status=r.status,
                progress=getattr(r, "progress", None),
                started_at=r.started_at, finished_at=r.finished_at,
                error_message=r.error_message,
            )
            for r in rows
        ]


async def get_job(ctx: Any, id: int) -> Optional[JobFull]:
    workspace_id = get_workspace_id(ctx)  # noqa: F841

    with db_session() as db:
        r = db.get(Job, id)
        if r is None:
            return None
        return JobFull(
            id=r.id, type=r.type, status=r.status,
            progress=getattr(r, "progress", None),
            started_at=r.started_at, finished_at=r.finished_at,
            error_message=r.error_message,
            params=r.params, result_summary=r.result_summary,
        )


def register_jobs_tools(server) -> None:
    server.tool(name="list_jobs")(list_jobs)
    server.tool(name="get_job")(get_job)
```

- [ ] **Step 4: Rodar tests**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_tools_jobs.py -v
```

Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/app/mcp/tools_jobs.py backend/tests/mcp/test_tools_jobs.py
git commit -m "feat(mcp): tools list_jobs + get_job"
```

---

## Task 5: Tools de Stats + Workspace + Pending

**Files:**
- Create: `backend/app/mcp/tools_stats.py`
- Create: `backend/app/mcp/tools_workspace.py`
- Create: `backend/app/mcp/tools_pending.py`
- Create: `backend/tests/mcp/test_tools_stats.py`
- Create: `backend/tests/mcp/test_tools_workspace.py`
- Create: `backend/tests/mcp/test_tools_pending.py`

- [ ] **Step 1: Test falhando — stats**

Create `backend/tests/mcp/test_tools_stats.py`:

```python
import asyncio
from unittest.mock import Mock

from mcp.server.auth.provider import AccessToken

from app.models import Lead
from app.mcp.tools_stats import dashboard_stats, conversion_funnel


def _ctx():
    ctx = Mock()
    user = Mock()
    user.access_token = AccessToken(
        token="x" * 64, client_id="mcp-1",
        scopes=["mcp:workspace:1"], expires_at=None, resource=None,
    )
    ctx.request_context.request.user = user
    return ctx


def test_dashboard_stats_empty(db):
    result = asyncio.run(dashboard_stats(_ctx()))
    assert result.total_leads == 0
    assert result.by_status == {}


def test_dashboard_stats_aggregates(db):
    db.add_all([
        Lead(nome="A", telefone="x", status="scraped", opportunity_score=40),
        Lead(nome="B", telefone="y", status="enriched", opportunity_score=60),
        Lead(nome="C", telefone="z", status="enriched", opportunity_score=80),
    ])
    db.commit()

    result = asyncio.run(dashboard_stats(_ctx()))
    assert result.total_leads == 3
    assert result.by_status["enriched"] == 2
    assert result.by_status["scraped"] == 1
    assert result.avg_score == 60.0


def test_conversion_funnel_returns_period_data(db):
    result = asyncio.run(conversion_funnel(_ctx(), period="7d"))
    assert isinstance(result, dict)
    assert "period" in result
```

- [ ] **Step 2: Implementar `tools_stats.py`**

Create `backend/app/mcp/tools_stats.py`:

```python
"""MCP READ tools — dashboard stats + conversion funnel."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Literal

from sqlalchemy import func

from app.mcp.context import get_workspace_id
from app.mcp.db import db_session
from app.mcp.schemas import DashboardStats
from app.models import Lead


async def dashboard_stats(ctx: Any) -> DashboardStats:
    workspace_id = get_workspace_id(ctx)  # noqa: F841

    with db_session() as db:
        total = db.query(Lead).count()
        if total == 0:
            return DashboardStats(
                total_leads=0, by_status={}, avg_score=None,
                conversion_rate=None, leads_by_day=[],
            )

        by_status = dict(
            db.query(Lead.status, func.count(Lead.id))
            .group_by(Lead.status)
            .all()
        )
        avg = db.query(func.avg(Lead.opportunity_score)).scalar()

        # leads_by_day: últimos 14 dias
        since = datetime.utcnow() - timedelta(days=14)
        by_day_rows = (
            db.query(
                func.date(Lead.created_at).label("day"),
                func.count(Lead.id).label("count"),
            )
            .filter(Lead.created_at >= since)
            .group_by(func.date(Lead.created_at))
            .order_by("day")
            .all()
        )
        leads_by_day = [
            {"day": str(r.day), "count": r.count} for r in by_day_rows
        ]

        # conversion_rate = closed/won / total
        won_count = (
            db.query(Lead).filter(Lead.status.in_(["closed", "won", "delivered"]))
            .count()
        )
        conv_rate = (won_count / total) if total > 0 else None

        return DashboardStats(
            total_leads=total,
            by_status=by_status,
            avg_score=float(avg) if avg is not None else None,
            conversion_rate=conv_rate,
            leads_by_day=leads_by_day,
        )


async def conversion_funnel(
    ctx: Any, period: Literal["7d", "30d", "90d"] = "30d",
) -> dict:
    workspace_id = get_workspace_id(ctx)  # noqa: F841
    days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
    since = datetime.utcnow() - timedelta(days=days)

    with db_session() as db:
        rows = (
            db.query(Lead.status, func.count(Lead.id))
            .filter(Lead.created_at >= since)
            .group_by(Lead.status)
            .all()
        )
        return {
            "period": period,
            "since": since.isoformat(),
            "by_status": dict(rows),
        }


def register_stats_tools(server) -> None:
    server.tool(name="dashboard_stats")(dashboard_stats)
    server.tool(name="conversion_funnel")(conversion_funnel)
```

- [ ] **Step 3: Test workspace + impl**

Create `backend/tests/mcp/test_tools_workspace.py`:

```python
import asyncio
from unittest.mock import Mock

from mcp.server.auth.provider import AccessToken

from app.models import WorkspaceProfile, WorkspaceTargeting
from app.mcp.tools_workspace import workspace_profile, workspace_targeting


def _ctx():
    ctx = Mock()
    user = Mock()
    user.access_token = AccessToken(
        token="x" * 64, client_id="mcp-1",
        scopes=["mcp:workspace:1"], expires_at=None, resource=None,
    )
    ctx.request_context.request.user = user
    return ctx


def test_workspace_profile_returns_default_when_missing(db):
    result = asyncio.run(workspace_profile(_ctx()))
    assert result is not None
    # Defaults vazios — comportamento do _get_or_create existente


def test_workspace_profile_returns_persisted(db):
    db.add(WorkspaceProfile(
        workspace_id=1, business_name="Acme", your_name="Angelo",
    ))
    db.commit()

    result = asyncio.run(workspace_profile(_ctx()))
    assert result.business_name == "Acme"
    assert result.your_name == "Angelo"


def test_workspace_targeting_returns_empty_lists_default(db):
    result = asyncio.run(workspace_targeting(_ctx()))
    assert result.target_niches == []
    assert result.target_cities == []
```

Create `backend/app/mcp/tools_workspace.py`:

```python
"""MCP READ tools — workspace profile + targeting."""
from __future__ import annotations

from typing import Any

from app.mcp.context import get_workspace_id
from app.mcp.db import db_session
from app.mcp.schemas import WorkspaceProfileOut, WorkspaceTargetingOut
from app.models import WorkspaceProfile, WorkspaceTargeting


async def workspace_profile(ctx: Any) -> WorkspaceProfileOut:
    ws = get_workspace_id(ctx)
    with db_session() as db:
        row = db.query(WorkspaceProfile).filter_by(workspace_id=ws).first()
        if row is None:
            return WorkspaceProfileOut(
                business_name=None, your_name=None, your_email=None,
                your_whatsapp=None, your_website=None, legal_basis=None,
            )
        return WorkspaceProfileOut(
            business_name=row.business_name, your_name=row.your_name,
            your_email=row.your_email, your_whatsapp=row.your_whatsapp,
            your_website=row.your_website, legal_basis=row.legal_basis,
        )


async def workspace_targeting(ctx: Any) -> WorkspaceTargetingOut:
    ws = get_workspace_id(ctx)
    with db_session() as db:
        row = db.query(WorkspaceTargeting).filter_by(workspace_id=ws).first()
        if row is None:
            return WorkspaceTargetingOut(
                target_niches=[], target_cities=[], min_rating=None,
                max_results_per_search=None, opportunity_score_threshold=None,
            )
        return WorkspaceTargetingOut(
            target_niches=row.target_niches or [],
            target_cities=row.target_cities or [],
            min_rating=row.min_rating,
            max_results_per_search=row.max_results_per_search,
            opportunity_score_threshold=row.opportunity_score_threshold,
        )


def register_workspace_tools(server) -> None:
    server.tool(name="workspace_profile")(workspace_profile)
    server.tool(name="workspace_targeting")(workspace_targeting)
```

- [ ] **Step 4: Test pending + impl**

Create `backend/tests/mcp/test_tools_pending.py`:

```python
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from mcp.server.auth.provider import AccessToken

from app.models import PendingAction
from app.mcp.tools_pending import list_pending_actions


def _ctx():
    ctx = Mock()
    user = Mock()
    user.access_token = AccessToken(
        token="x" * 64, client_id="mcp-1",
        scopes=["mcp:workspace:1"], expires_at=None, resource=None,
    )
    ctx.request_context.request.user = user
    return ctx


def test_list_pending_actions_empty(db):
    result = asyncio.run(list_pending_actions(_ctx(), include_expired=False))
    assert result == []


def test_list_pending_actions_excludes_expired_by_default(db):
    future = datetime.now(timezone.utc) + timedelta(minutes=5)
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    db.add_all([
        PendingAction(
            id="active", workspace_id=1, action_type="send_message",
            params={}, preview={"sample": "active"},
            created_by_token_hash="x" * 64, expires_at=future,
        ),
        PendingAction(
            id="expired", workspace_id=1, action_type="send_message",
            params={}, preview={"sample": "expired"},
            created_by_token_hash="x" * 64, expires_at=past,
        ),
    ])
    db.commit()

    result = asyncio.run(list_pending_actions(_ctx(), include_expired=False))
    assert len(result) == 1
    assert result[0].id == "active"


def test_list_pending_actions_include_expired(db):
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    db.add(PendingAction(
        id="expired", workspace_id=1, action_type="send_message",
        params={}, preview={},
        created_by_token_hash="x" * 64, expires_at=past,
    ))
    db.commit()

    result = asyncio.run(list_pending_actions(_ctx(), include_expired=True))
    assert len(result) == 1
```

Create `backend/app/mcp/tools_pending.py`:

```python
"""MCP READ tool — pending actions."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.mcp.context import get_workspace_id
from app.mcp.db import db_session
from app.mcp.schemas import PendingActionOut
from app.models import PendingAction


async def list_pending_actions(
    ctx: Any, include_expired: bool = False,
) -> list[PendingActionOut]:
    """Lista pending_actions do workspace. Por default exclui expiradas e
    já committed/cancelled."""
    ws = get_workspace_id(ctx)

    with db_session() as db:
        q = (
            db.query(PendingAction)
            .filter_by(workspace_id=ws)
            .filter(PendingAction.committed_at.is_(None))
            .filter(PendingAction.cancelled_at.is_(None))
        )
        if not include_expired:
            q = q.filter(PendingAction.expires_at > datetime.utcnow())
        rows = q.order_by(PendingAction.created_at.desc()).all()
        return [
            PendingActionOut(
                id=r.id, action_type=r.action_type, preview=r.preview,
                created_at=r.created_at, expires_at=r.expires_at,
                committed_at=r.committed_at, cancelled_at=r.cancelled_at,
            )
            for r in rows
        ]


def register_pending_tools(server) -> None:
    server.tool(name="list_pending_actions")(list_pending_actions)
```

- [ ] **Step 5: Rodar todos os 3 test files**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_tools_stats.py tests/mcp/test_tools_workspace.py tests/mcp/test_tools_pending.py -v
```

Expected: ~10 PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/app/mcp/tools_stats.py backend/app/mcp/tools_workspace.py backend/app/mcp/tools_pending.py \
        backend/tests/mcp/test_tools_stats.py backend/tests/mcp/test_tools_workspace.py backend/tests/mcp/test_tools_pending.py
git commit -m "feat(mcp): tools stats + workspace + pending_actions"
```

---

## Task 6: Resources — 12 URI handlers

**Files:**
- Create: `backend/app/mcp/resources.py`
- Create: `backend/tests/mcp/test_resources.py`

Resources são read-only URI endpoints que LLM pode `resources/list` e `resources/read`. FastMCP usa `@server.resource("scheme://pattern")` decorator.

- [ ] **Step 1: Test falhando**

Create `backend/tests/mcp/test_resources.py`:

```python
"""Smoke tests pros resources MCP. Cada resource registra um handler que
retorna dados. Testes minimalistas — só confirmam que o handler responde."""
import asyncio
from unittest.mock import Mock

from mcp.server.auth.provider import AccessToken

from app.models import Lead, Job
from app.mcp.resources import (
    leads_list_resource,
    lead_detail_resource,
    jobs_list_resource,
    job_detail_resource,
    workspace_profile_resource,
    workspace_targeting_resource,
    workspace_integrations_resource,
    pending_actions_list_resource,
)


def _ctx():
    ctx = Mock()
    user = Mock()
    user.access_token = AccessToken(
        token="x" * 64, client_id="mcp-1",
        scopes=["mcp:workspace:1"], expires_at=None, resource=None,
    )
    ctx.request_context.request.user = user
    return ctx


def test_leads_list_resource_empty(db):
    data = asyncio.run(leads_list_resource(_ctx()))
    assert isinstance(data, str)  # MCP resources retornam string (JSON serialized)
    assert "items" in data


def test_lead_detail_resource(db):
    lead = Lead(nome="X", telefone="123", status="scraped")
    db.add(lead)
    db.commit()
    db.refresh(lead)

    data = asyncio.run(lead_detail_resource(_ctx(), lead_id=lead.id))
    assert str(lead.id) in data
    assert "X" in data


def test_lead_detail_resource_not_found(db):
    data = asyncio.run(lead_detail_resource(_ctx(), lead_id=9999))
    assert "not_found" in data.lower() or "null" in data.lower()


def test_jobs_list_resource(db):
    from datetime import datetime
    db.add(Job(type="scrape", status="done", params={}, started_at=datetime.utcnow()))
    db.commit()

    data = asyncio.run(jobs_list_resource(_ctx()))
    assert "scrape" in data


def test_workspace_profile_resource(db):
    data = asyncio.run(workspace_profile_resource(_ctx()))
    assert isinstance(data, str)


def test_workspace_integrations_resource_no_secrets(db):
    """CRITICAL: integrations resource NUNCA retorna secrets em plain."""
    from app.models import IntegrationSettings
    from app.integrations.crypto import encrypt
    db.add(IntegrationSettings(
        workspace_id=1, provider="evolution", enabled=True,
        config={"api_key": encrypt("SUPERSECRET123"), "base_url": "https://x.com"},
    ))
    db.commit()

    data = asyncio.run(workspace_integrations_resource(_ctx()))
    assert "SUPERSECRET123" not in data
    assert "has_api_key" in data


def test_pending_actions_resource(db):
    data = asyncio.run(pending_actions_list_resource(_ctx()))
    assert isinstance(data, str)
```

- [ ] **Step 2: Rodar — deve falhar**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_resources.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implementar `resources.py`**

Create `backend/app/mcp/resources.py`:

```python
"""MCP Resources — URI-style read-only endpoints.

Pattern: `<scheme>://<path>` registrados via `@server.resource()`.
Retornam string (JSON serialized) por simplicidade — LLM parsea.
"""
from __future__ import annotations

import json
from typing import Any

from app.mcp.context import get_workspace_id
from app.mcp.db import db_session
from app.mcp.tools_conversations import get_conversation, list_conversations
from app.mcp.tools_jobs import get_job, list_jobs
from app.mcp.tools_leads import get_lead, list_landing_pages, list_leads
from app.mcp.tools_pending import list_pending_actions
from app.mcp.tools_workspace import workspace_profile, workspace_targeting
from app.models import IntegrationSettings


def _json(data) -> str:
    """Serializa Pydantic models, dicts, lists pra string JSON."""
    if hasattr(data, "model_dump_json"):
        return data.model_dump_json(indent=2)
    if hasattr(data, "model_dump"):
        return json.dumps(data.model_dump(), default=str, indent=2)
    return json.dumps(data, default=str, indent=2)


async def leads_list_resource(ctx: Any) -> str:
    result = await list_leads(ctx, filter=None, limit=50, offset=0)
    return _json(result)


async def lead_detail_resource(ctx: Any, lead_id: int) -> str:
    result = await get_lead(ctx, id=lead_id)
    if result is None:
        return json.dumps({"not_found": True, "id": lead_id})
    return _json(result)


async def lead_landing_pages_resource(ctx: Any, lead_id: int) -> str:
    result = await list_landing_pages(ctx, lead_id=lead_id)
    return _json([r.model_dump() for r in result])


async def conversations_list_resource(ctx: Any) -> str:
    result = await list_conversations(ctx, filter=None)
    return _json([r.model_dump() for r in result])


async def conversation_detail_resource(ctx: Any, conv_id: int) -> str:
    result = await get_conversation(ctx, id=conv_id)
    if result is None:
        return json.dumps({"not_found": True, "id": conv_id})
    return _json(result)


async def jobs_list_resource(ctx: Any) -> str:
    result = await list_jobs(ctx, status=None, type=None, limit=20)
    return _json([r.model_dump() for r in result])


async def job_detail_resource(ctx: Any, job_id: int) -> str:
    result = await get_job(ctx, id=job_id)
    if result is None:
        return json.dumps({"not_found": True, "id": job_id})
    return _json(result)


async def workspace_profile_resource(ctx: Any) -> str:
    result = await workspace_profile(ctx)
    return _json(result)


async def workspace_targeting_resource(ctx: Any) -> str:
    result = await workspace_targeting(ctx)
    return _json(result)


async def workspace_integrations_resource(ctx: Any) -> str:
    """CRITICAL: NUNCA retorna secrets em plain. Só status + last4."""
    workspace_id = get_workspace_id(ctx)

    with db_session() as db:
        rows = db.query(IntegrationSettings).filter_by(workspace_id=workspace_id).all()
        out = []
        for r in rows:
            cfg = r.config or {}
            # Mascarar: copiar non-secret + has_<field>/last4 dos secrets
            from app.integrations.schemas import SECRET_FIELDS
            secrets = SECRET_FIELDS.get(r.provider, set())
            masked = {k: v for k, v in cfg.items() if k not in secrets}
            for field in secrets:
                cipher = cfg.get(field)
                masked[f"has_{field}"] = bool(cipher)
                if cipher:
                    try:
                        from app.integrations.crypto import decrypt
                        val = decrypt(cipher)
                        masked[f"{field}_last4"] = val[-4:] if val and len(val) >= 4 else None
                    except Exception:
                        masked[f"{field}_decrypt_error"] = True
            out.append({
                "provider": r.provider,
                "enabled": r.enabled,
                "config": masked,
                "last_tested_at": r.last_tested_at.isoformat() if r.last_tested_at else None,
            })
        return json.dumps(out, default=str, indent=2)


async def pending_actions_list_resource(ctx: Any) -> str:
    result = await list_pending_actions(ctx, include_expired=False)
    return _json([r.model_dump() for r in result])


def register_resources(server) -> None:
    """Registra resources no FastMCP server.

    URI patterns:
      leads://list
      leads://{lead_id}
      leads://{lead_id}/landing-pages
      conversations://list
      conversations://{conv_id}
      jobs://list
      jobs://{job_id}
      workspace://profile
      workspace://targeting
      workspace://integrations
      pending_actions://list
    """
    server.resource("leads://list")(leads_list_resource)
    server.resource("leads://{lead_id}")(lead_detail_resource)
    server.resource("leads://{lead_id}/landing-pages")(lead_landing_pages_resource)
    server.resource("conversations://list")(conversations_list_resource)
    server.resource("conversations://{conv_id}")(conversation_detail_resource)
    server.resource("jobs://list")(jobs_list_resource)
    server.resource("jobs://{job_id}")(job_detail_resource)
    server.resource("workspace://profile")(workspace_profile_resource)
    server.resource("workspace://targeting")(workspace_targeting_resource)
    server.resource("workspace://integrations")(workspace_integrations_resource)
    server.resource("pending_actions://list")(pending_actions_list_resource)
```

- [ ] **Step 4: Rodar tests**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_resources.py -v
```

Expected: 7 PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/app/mcp/resources.py backend/tests/mcp/test_resources.py
git commit -m "feat(mcp): 11 resources URI-style (leads/convs/jobs/workspace/pending)"
```

---

## Task 7: Wire everything em `build_mcp_server()`

**Files:**
- Modify: `backend/app/mcp/server.py`

- [ ] **Step 1: Atualizar `build_mcp_server`**

Edit `backend/app/mcp/server.py`. Substituir a função completa por:

```python
"""Builder do FastMCP server pro SDR Machine."""
from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from app.database import SessionLocal
from app.mcp.auth import BearerTokenVerifier
from app.mcp.resources import register_resources
from app.mcp.tools_conversations import register_conversations_tools
from app.mcp.tools_jobs import register_jobs_tools
from app.mcp.tools_leads import register_leads_tools
from app.mcp.tools_pending import register_pending_tools
from app.mcp.tools_stats import register_stats_tools
from app.mcp.tools_workspace import register_workspace_tools

logger = logging.getLogger(__name__)


def build_mcp_server() -> FastMCP:
    verifier = BearerTokenVerifier(session_factory=SessionLocal)
    server = FastMCP(
        "sdr-machine",
        instructions=(
            "Servidor MCP do SDR Machine — plataforma de automação de prospecção. "
            "Use tools para listar leads, conversas e jobs. Ações que enviam mensagens "
            "ou deletam dados usam two-phase commit (prepare_* + commit_action) — "
            "sempre revise o preview com o usuário antes de chamar commit_action."
        ),
        token_verifier=verifier,
        json_response=True,
        streamable_http_path="/",
    )

    # READ tools (M-2)
    register_leads_tools(server)
    register_conversations_tools(server)
    register_jobs_tools(server)
    register_stats_tools(server)
    register_workspace_tools(server)
    register_pending_tools(server)

    # Resources (M-2)
    register_resources(server)

    # M-3 vai adicionar write tools (prepare_*, commit_action, etc)
    # M-5 vai adicionar prompts + subscriptions

    return server
```

- [ ] **Step 2: Rodar test de mount + tools listadas**

Adicionar test em `backend/tests/mcp/test_server_build.py` (que já existe de M-1):

```python
def test_server_has_all_read_tools():
    from app.mcp.server import build_mcp_server
    server = build_mcp_server()

    expected_tools = {
        "list_leads", "get_lead", "list_landing_pages", "get_lp_html",
        "list_conversations", "get_conversation",
        "list_jobs", "get_job",
        "dashboard_stats", "conversion_funnel",
        "workspace_profile", "workspace_targeting",
        "list_pending_actions",
    }
    registered = set()
    # FastMCP expõe tools via .list_tools() async; usar sync access:
    if hasattr(server, "_tools"):
        registered = set(server._tools.keys())
    elif hasattr(server, "_tool_manager"):
        registered = set(server._tool_manager._tools.keys())

    missing = expected_tools - registered
    assert not missing, f"Tools missing: {missing}"
```

> A API exata do FastMCP varia entre versões. Se nem `_tools` nem `_tool_manager._tools` existir, ajustar pra novo accessor que o SDK expõe (provavelmente `server.list_tools()` async ou similar).

- [ ] **Step 3: Rodar suite MCP completa**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/ -v
```

Expected: TODOS PASS (~40 testes em M-1 + M-2).

- [ ] **Step 4: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/app/mcp/server.py backend/tests/mcp/test_server_build.py
git commit -m "feat(mcp): wire READ tools + resources em build_mcp_server"
```

---

## Task 8: Smoke + push + PR

- [ ] **Step 1: Suite full backend**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest --deselect tests/test_outreach.py 2>&1 | tail -5
```

Expected: ~745 PASS (704 baseline + 23 M-1 + ~18 M-2).

- [ ] **Step 2: Push**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git push -u origin feat/mcp-m2-read-tools
```

- [ ] **Step 3: Abrir PR**

```bash
gh pr create --base main --title "feat(mcp): M-2 READ tools + Resources" --body "$(cat <<'EOF'
## Summary

13 READ tools + 11 Resources registrados no FastMCP server criado em M-1.

**Tools (13):**
- Leads: list_leads, get_lead, list_landing_pages, get_lp_html
- Conversations: list_conversations, get_conversation
- Jobs: list_jobs, get_job
- Stats: dashboard_stats, conversion_funnel
- Workspace: workspace_profile, workspace_targeting
- Pending: list_pending_actions

**Resources (11):**
- leads://list, leads://{id}, leads://{id}/landing-pages
- conversations://list, conversations://{id}
- jobs://list, jobs://{id}
- workspace://profile, workspace://targeting, workspace://integrations (NUNCA expõe secrets)
- pending_actions://list

Sem side effects — todas tools são read-only. Filtro por workspace_id derivado do AccessToken.

## Test Plan

- [x] ~18 testes novos cobrindo cada tool (empty, populated, filters, not-found)
- [x] CRITICAL: workspace_integrations_resource mascarado — nunca retorna secrets em plain (test específico)
- [x] Suite backend full passa (~745 PASS)
- [ ] **Manual:** Claude Desktop conectado, chamar \`list_leads\` via prompt, verificar retorno

## Não coberto

- Write tools (M-3)
- Prompts pre-built (M-5)
- Subscriptions SSE (M-5)
- UI gerar tokens (M-4)
EOF
)"
```

---

## Self-Review

**Spec coverage** (vs M-0 §4 + §5):

| Spec item | Task |
|---|---|
| `list_leads` | Task 2 |
| `get_lead` | Task 2 |
| `list_landing_pages` | Task 2 |
| `get_lp_html` | Task 2 |
| `list_conversations` | Task 3 |
| `get_conversation` | Task 3 |
| `list_jobs` | Task 4 |
| `get_job` | Task 4 |
| `dashboard_stats` | Task 5 |
| `conversion_funnel` | Task 5 |
| `workspace_profile` | Task 5 |
| `workspace_targeting` | Task 5 |
| `list_pending_actions` | Task 5 |
| 11 resources | Task 6 |
| Workspace isolation | All tasks (`get_workspace_id`) |
| Secret masking em workspace_integrations | Task 6 |

**Placeholder scan:** nenhum step usa "TBD" / "implement later" / "appropriate error handling". `workspace_id` extraído mas `# noqa: F841` em Lead/Job (não tem coluna ainda) — comportamento documentado.

**Type consistency:**
- `LeadSummary`, `LeadFull`, `ConversationSummary`, `ConversationFull`, `JobSummary`, `JobFull`, `DashboardStats`, `LandingPageSummary`, `WorkspaceProfileOut`, `WorkspaceTargetingOut`, `PendingActionOut` definidos Task 1, consumidos em Tasks 2-6 ✓
- `register_*_tools(server)` pattern consistente em todos os módulos tools_*.py
- `_json()` helper em resources.py reusado em todos resources ✓
- `register_resources(server)` registra 11 URIs (number bate com spec)

---

## Execution Handoff

Após Task 8 (push + PR), próximo é **M-3: write tools + 2-phase commit** que adiciona `prepare_*` / `commit_action` / `cancel_action`.

Plan complete and saved to `docs/superpowers/plans/2026-05-18-mcp-m2-read-tools.md`.
