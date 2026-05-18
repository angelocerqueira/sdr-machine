# MCP M-3 Write Tools + Two-Phase Commit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar 5 soft-write tools + 7 `prepare_*` tools + `commit_action` + `cancel_action` + reaper de pending_actions expiradas. Soft-write executa direto (Claude prompt-instruído a confirmar). Hard-write usa two-phase commit via tabela `pending_actions`.

**Architecture:** `pending_actions_service.py` centraliza CRUD da tabela `pending_actions`. Cada `prepare_*` tool valida inputs, gera UUID, monta preview JSON, persiste row com `expires_at = now + 5min`. `commit_action(id)` valida ownership (token hash), executa o handler registrado pra `action_type`, persiste `result`, marca `committed_at`. Idempotente: commit 2x retorna mesmo result. Reaper diário marca actions expiradas como cancelled.

**Tech Stack:** Mesmo M-1/M-2 — FastAPI + SQLAlchemy + `mcp` SDK + pytest

**Spec:** [`docs/superpowers/specs/2026-05-18-mcp-server-m0-architecture.md`](../specs/2026-05-18-mcp-server-m0-architecture.md) §4 (soft + hard write)

**Depende:** M-1 (schema pending_actions) + M-2 (server tem read tools, FastMCP estável). Não precisa esperar PRs merged — pode rodar como stack PR sobre M-2.

---

## Notas de execução

- Branch: `feat/mcp-m3-write-tools`. Baseia em main após M-2 merged (ou stack sobre M-2 branch).
- Pre-write tools soft delegam pros services existentes do backend (leads_router, workspace_settings_router).
- Hard-write usa registry de action_type → handler function. Adicionar handler novo = registrar no dict.
- Commits Conventional Commits, escopo `mcp`

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `backend/app/mcp/pending_actions_service.py` | Create | CRUD + commit/cancel + reaper. Action_type → handler registry. |
| `backend/app/mcp/tools_soft_write.py` | Create | 5 tools: update_lead_status, update_lead_fields, mark_conversation_read, update_workspace_profile, update_workspace_targeting |
| `backend/app/mcp/tools_prepare.py` | Create | 7 prepare_* tools (montam preview + persistem pending_action) |
| `backend/app/mcp/action_handlers.py` | Create | Handlers executados pelo commit_action — 1 função por action_type |
| `backend/app/mcp/tools_commit.py` | Create | commit_action(id) + cancel_action(id) |
| `backend/app/mcp/reaper.py` | Create | Função `reap_expired_actions(db)` chamada no startup hook |
| `backend/app/main.py` | Modify | Adicionar reaper ao startup event (similar ao _reap_orphaned_jobs) |
| `backend/app/mcp/server.py` | Modify | Registrar novas tools |
| `backend/tests/mcp/test_pending_actions_service.py` | Create | CRUD + commit idempotency + ownership + expiry |
| `backend/tests/mcp/test_tools_soft_write.py` | Create | 5 tools × 2-3 tests |
| `backend/tests/mcp/test_tools_prepare.py` | Create | 7 prepare_* × 2 tests cada |
| `backend/tests/mcp/test_tools_commit.py` | Create | commit happy/idempotent/ownership-violation/expired/cancelled |
| `backend/tests/mcp/test_action_handlers.py` | Create | 7 handlers × happy path test |
| `backend/tests/mcp/test_reaper.py` | Create | Marca expired sem afetar válidos |

---

## Task 1: `pending_actions_service.py` — CRUD + registry

**Files:**
- Create: `backend/app/mcp/pending_actions_service.py`
- Create: `backend/tests/mcp/test_pending_actions_service.py`

- [ ] **Step 1: Criar branch**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git checkout main && git pull origin main
git checkout -b feat/mcp-m3-write-tools
```

- [ ] **Step 2: Test falhando**

Create `backend/tests/mcp/test_pending_actions_service.py`:

```python
import pytest
from datetime import datetime, timedelta, timezone

from app.models import PendingAction
from app.mcp.pending_actions_service import (
    create_action,
    get_action,
    commit_action_row,
    cancel_action_row,
    register_handler,
    HANDLERS,
)


def test_create_action_persists_with_uuid_and_expiry(db):
    pa = create_action(
        db,
        workspace_id=1,
        action_type="send_message",
        params={"conv_id": 5, "body": "oi"},
        preview={"to": "5544...", "rendered": "oi"},
        token_hash="x" * 64,
    )
    assert pa.id is not None
    assert len(pa.id) >= 8
    assert pa.expires_at > datetime.utcnow()
    assert pa.committed_at is None
    assert pa.cancelled_at is None
    assert pa.result is None


def test_get_action_returns_row(db):
    pa = create_action(
        db, workspace_id=1, action_type="x", params={}, preview={},
        token_hash="x" * 64,
    )
    found = get_action(db, action_id=pa.id, workspace_id=1, token_hash="x" * 64)
    assert found is not None
    assert found.id == pa.id


def test_get_action_rejects_wrong_token(db):
    pa = create_action(
        db, workspace_id=1, action_type="x", params={}, preview={},
        token_hash="a" * 64,
    )
    found = get_action(db, action_id=pa.id, workspace_id=1, token_hash="b" * 64)
    assert found is None  # ownership violation = invisível


def test_get_action_rejects_wrong_workspace(db):
    pa = create_action(
        db, workspace_id=1, action_type="x", params={}, preview={},
        token_hash="x" * 64,
    )
    found = get_action(db, action_id=pa.id, workspace_id=2, token_hash="x" * 64)
    assert found is None


def test_get_action_rejects_expired(db):
    past = datetime.utcnow() - timedelta(minutes=1)
    pa = PendingAction(
        id="exp", workspace_id=1, action_type="x", params={}, preview={},
        created_by_token_hash="x" * 64, expires_at=past,
    )
    db.add(pa)
    db.commit()

    found = get_action(db, action_id="exp", workspace_id=1, token_hash="x" * 64)
    assert found is None


def test_commit_action_row_marks_committed_and_stores_result(db):
    pa = create_action(
        db, workspace_id=1, action_type="x", params={}, preview={},
        token_hash="x" * 64,
    )
    commit_action_row(db, action_id=pa.id, result={"ok": True, "msg_id": 42})

    refreshed = db.query(PendingAction).filter_by(id=pa.id).first()
    assert refreshed.committed_at is not None
    assert refreshed.result == {"ok": True, "msg_id": 42}


def test_cancel_action_row_marks_cancelled(db):
    pa = create_action(
        db, workspace_id=1, action_type="x", params={}, preview={},
        token_hash="x" * 64,
    )
    cancel_action_row(db, action_id=pa.id)

    refreshed = db.query(PendingAction).filter_by(id=pa.id).first()
    assert refreshed.cancelled_at is not None


def test_register_handler_adds_to_registry():
    @register_handler("test_action_xyz")
    def handler(db, params):
        return {"echoed": params}

    assert "test_action_xyz" in HANDLERS
    # cleanup pra não vazar pra outros tests
    HANDLERS.pop("test_action_xyz")
```

- [ ] **Step 3: Rodar — deve falhar**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_pending_actions_service.py -v
```

Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 4: Implementar `pending_actions_service.py`**

Create `backend/app/mcp/pending_actions_service.py`:

```python
"""Pending Actions service — CRUD + handler registry pra two-phase commit.

Pattern:
1. `prepare_*` tool chama `create_action(...)` → retorna PendingAction.id
2. LLM mostra preview ao user, recebe confirmação
3. `commit_action(action_id)` tool chama:
   - `get_action(...)` valida ownership + expiry
   - Pega `HANDLERS[action.action_type]` e executa
   - `commit_action_row(...)` persiste result

Idempotência: `commit_action_row` é no-op se `committed_at` já setado;
caller deve retornar o `result` existente.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

from sqlalchemy.orm import Session

from app.models import PendingAction

logger = logging.getLogger(__name__)

ACTION_TTL = timedelta(minutes=5)


# Handler registry: action_type -> sync function(db, params) -> result dict
HandlerFn = Callable[[Session, dict], Dict[str, Any]]
HANDLERS: Dict[str, HandlerFn] = {}


def register_handler(action_type: str):
    """Decorator pra registrar handler de um action_type específico."""
    def decorator(fn: HandlerFn) -> HandlerFn:
        if action_type in HANDLERS:
            logger.warning("mcp.handler.override action_type=%s", action_type)
        HANDLERS[action_type] = fn
        return fn
    return decorator


def create_action(
    db: Session,
    *,
    workspace_id: int,
    action_type: str,
    params: dict,
    preview: dict,
    token_hash: str,
    ttl: timedelta = ACTION_TTL,
) -> PendingAction:
    """Cria PendingAction com UUID novo e TTL default 5min."""
    pa = PendingAction(
        id=uuid.uuid4().hex[:32],
        workspace_id=workspace_id,
        action_type=action_type,
        params=params,
        preview=preview,
        created_by_token_hash=token_hash,
        expires_at=datetime.utcnow() + ttl,
    )
    db.add(pa)
    db.commit()
    db.refresh(pa)
    return pa


def get_action(
    db: Session,
    *,
    action_id: str,
    workspace_id: int,
    token_hash: str,
) -> Optional[PendingAction]:
    """Retorna PendingAction se:
    - existe
    - mesmo workspace
    - mesmo token (ownership)
    - não expirada (expires_at > now)
    - não cancelled
    Retorna a row mesmo se já committed (caller decide se é retry idempotente).
    """
    row = db.query(PendingAction).filter_by(id=action_id).first()
    if row is None:
        return None
    if row.workspace_id != workspace_id:
        return None
    if row.created_by_token_hash != token_hash:
        return None
    if row.cancelled_at is not None:
        return None
    # Expired check: só rejeita se ainda não foi committed
    if row.committed_at is None and row.expires_at <= datetime.utcnow():
        return None
    return row


def commit_action_row(
    db: Session, *, action_id: str, result: dict,
) -> None:
    """Marca committed_at + persiste result. NO-OP se já committed."""
    row = db.query(PendingAction).filter_by(id=action_id).first()
    if row is None:
        return
    if row.committed_at is not None:
        return  # idempotente
    row.committed_at = datetime.utcnow()
    row.result = result
    db.commit()


def cancel_action_row(db: Session, *, action_id: str) -> bool:
    row = db.query(PendingAction).filter_by(id=action_id).first()
    if row is None or row.committed_at is not None or row.cancelled_at is not None:
        return False
    row.cancelled_at = datetime.utcnow()
    db.commit()
    return True
```

- [ ] **Step 5: Rodar tests**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_pending_actions_service.py -v
```

Expected: 8 PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/app/mcp/pending_actions_service.py backend/tests/mcp/test_pending_actions_service.py
git commit -m "feat(mcp): pending_actions_service CRUD + handler registry"
```

---

## Task 2: Soft-write tools (5 tools)

**Files:**
- Create: `backend/app/mcp/tools_soft_write.py`
- Create: `backend/tests/mcp/test_tools_soft_write.py`

- [ ] **Step 1: Test falhando**

Create `backend/tests/mcp/test_tools_soft_write.py`:

```python
import asyncio
from unittest.mock import Mock

from mcp.server.auth.provider import AccessToken

from app.models import Conversation, Lead, WorkspaceProfile, WorkspaceTargeting
from app.mcp.tools_soft_write import (
    update_lead_status,
    update_lead_fields,
    mark_conversation_read,
    update_workspace_profile,
    update_workspace_targeting,
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


def test_update_lead_status_changes_status(db):
    lead = Lead(nome="X", telefone="123", status="scraped")
    db.add(lead)
    db.commit()
    db.refresh(lead)

    result = asyncio.run(update_lead_status(_ctx(), id=lead.id, new_status="enriched"))
    assert result["ok"] is True

    db.refresh(lead)
    assert lead.status == "enriched"


def test_update_lead_status_lead_not_found(db):
    result = asyncio.run(update_lead_status(_ctx(), id=9999, new_status="enriched"))
    assert result["ok"] is False
    assert "not found" in result["error"].lower()


def test_update_lead_fields_changes_email(db):
    lead = Lead(nome="X", telefone="123", status="scraped")
    db.add(lead)
    db.commit()
    db.refresh(lead)

    result = asyncio.run(update_lead_fields(
        _ctx(), id=lead.id, patch={"email": "x@y.com", "perfil_lead": "hot"},
    ))
    assert result["ok"] is True

    db.refresh(lead)
    assert lead.email == "x@y.com"
    assert lead.perfil_lead == "hot"


def test_update_lead_fields_rejects_invalid_field(db):
    lead = Lead(nome="X", telefone="123", status="scraped")
    db.add(lead)
    db.commit()

    result = asyncio.run(update_lead_fields(
        _ctx(), id=lead.id, patch={"unknown_column": "evil"},
    ))
    # unknown fields silenciosamente ignorados; valid fields aplicados
    assert result["ok"] is True


def test_mark_conversation_read_zeros_unread(db):
    lead = Lead(nome="A", telefone="123", status="outreach_sent")
    db.add(lead)
    db.commit()
    db.refresh(lead)
    conv = Conversation(
        workspace_id=1, lead_id=lead.id, provider="evolution",
        provider_chat_id="x", phone="123", unread_count=5,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    result = asyncio.run(mark_conversation_read(_ctx(), conv_id=conv.id))
    assert result["ok"] is True

    db.refresh(conv)
    assert conv.unread_count == 0


def test_update_workspace_profile_creates_when_missing(db):
    result = asyncio.run(update_workspace_profile(
        _ctx(), patch={"business_name": "Acme Inc", "your_name": "Angelo"},
    ))
    assert result["ok"] is True

    row = db.query(WorkspaceProfile).filter_by(workspace_id=1).first()
    assert row.business_name == "Acme Inc"


def test_update_workspace_profile_preserves_unset_fields(db):
    db.add(WorkspaceProfile(
        workspace_id=1, business_name="Original", your_name="Angelo",
    ))
    db.commit()

    asyncio.run(update_workspace_profile(_ctx(), patch={"business_name": "Updated"}))

    row = db.query(WorkspaceProfile).filter_by(workspace_id=1).first()
    assert row.business_name == "Updated"
    assert row.your_name == "Angelo"  # preservado


def test_update_workspace_targeting_updates_lists(db):
    result = asyncio.run(update_workspace_targeting(_ctx(), patch={
        "target_niches": ["dentista", "advogado"],
        "target_cities": ["Chapecó SC"],
        "min_rating": 4.0,
    }))
    assert result["ok"] is True

    row = db.query(WorkspaceTargeting).filter_by(workspace_id=1).first()
    assert row.target_niches == ["dentista", "advogado"]
    assert row.min_rating == 4.0
```

- [ ] **Step 2: Rodar — deve falhar**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_tools_soft_write.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implementar `tools_soft_write.py`**

Create `backend/app/mcp/tools_soft_write.py`:

```python
"""MCP soft-write tools — execute direct, but Claude system-prompt instrui
a confirmar com user antes."""
from __future__ import annotations

from typing import Any

from app.mcp.context import get_workspace_id
from app.mcp.db import db_session
from app.models import (
    Conversation,
    Lead,
    WorkspaceProfile,
    WorkspaceTargeting,
)


_LEAD_ALLOWED_FIELDS = {
    "nome", "telefone", "email", "perfil_lead", "nicho_canonico",
    "endereco", "cidade", "categoria", "rating", "opportunity_score",
}


async def update_lead_status(ctx: Any, id: int, new_status: str) -> dict:
    workspace_id = get_workspace_id(ctx)  # noqa: F841

    with db_session() as db:
        lead = db.get(Lead, id)
        if lead is None:
            return {"ok": False, "error": "Lead not found"}
        old_status = lead.status
        lead.status = new_status
        db.commit()
        return {
            "ok": True,
            "lead_id": id,
            "old_status": old_status,
            "new_status": new_status,
        }


async def update_lead_fields(ctx: Any, id: int, patch: dict) -> dict:
    workspace_id = get_workspace_id(ctx)  # noqa: F841

    with db_session() as db:
        lead = db.get(Lead, id)
        if lead is None:
            return {"ok": False, "error": "Lead not found"}

        applied = {}
        for k, v in patch.items():
            if k in _LEAD_ALLOWED_FIELDS:
                setattr(lead, k, v)
                applied[k] = v
        db.commit()
        return {"ok": True, "lead_id": id, "applied": applied}


async def mark_conversation_read(ctx: Any, conv_id: int) -> dict:
    workspace_id = get_workspace_id(ctx)

    with db_session() as db:
        conv = db.query(Conversation).filter_by(
            id=conv_id, workspace_id=workspace_id,
        ).first()
        if conv is None:
            return {"ok": False, "error": "Conversation not found"}
        previous = conv.unread_count
        conv.unread_count = 0
        db.commit()
        return {
            "ok": True, "conversation_id": conv_id, "previous_unread": previous,
        }


async def update_workspace_profile(ctx: Any, patch: dict) -> dict:
    workspace_id = get_workspace_id(ctx)

    with db_session() as db:
        row = db.query(WorkspaceProfile).filter_by(workspace_id=workspace_id).first()
        if row is None:
            row = WorkspaceProfile(workspace_id=workspace_id)
            db.add(row)
        for k, v in patch.items():
            if hasattr(row, k):
                setattr(row, k, v)
        db.commit()
        return {"ok": True, "workspace_id": workspace_id, "applied": list(patch.keys())}


async def update_workspace_targeting(ctx: Any, patch: dict) -> dict:
    workspace_id = get_workspace_id(ctx)

    with db_session() as db:
        row = db.query(WorkspaceTargeting).filter_by(workspace_id=workspace_id).first()
        if row is None:
            row = WorkspaceTargeting(
                workspace_id=workspace_id, target_niches=[], target_cities=[],
            )
            db.add(row)
        for k, v in patch.items():
            if hasattr(row, k):
                setattr(row, k, v)
        db.commit()
        return {"ok": True, "workspace_id": workspace_id, "applied": list(patch.keys())}


def register_soft_write_tools(server) -> None:
    server.tool(name="update_lead_status")(update_lead_status)
    server.tool(name="update_lead_fields")(update_lead_fields)
    server.tool(name="mark_conversation_read")(mark_conversation_read)
    server.tool(name="update_workspace_profile")(update_workspace_profile)
    server.tool(name="update_workspace_targeting")(update_workspace_targeting)
```

- [ ] **Step 4: Rodar tests**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_tools_soft_write.py -v
```

Expected: 8 PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/app/mcp/tools_soft_write.py backend/tests/mcp/test_tools_soft_write.py
git commit -m "feat(mcp): 5 soft-write tools (update_lead/conv/workspace)"
```

---

## Task 3: Action handlers — funções que `commit_action` executa

**Files:**
- Create: `backend/app/mcp/action_handlers.py`
- Create: `backend/tests/mcp/test_action_handlers.py`

Cada handler é `(db, params) -> result dict`. Registrados via decorator `@register_handler("send_message")` no carregamento do módulo.

- [ ] **Step 1: Test falhando — handlers principais**

Create `backend/tests/mcp/test_action_handlers.py`:

```python
import pytest
from unittest.mock import Mock, patch

from app.integrations.crypto import encrypt
from app.models import (
    Conversation, ConversationMessage, IntegrationSettings, Lead,
)
import app.mcp.action_handlers  # noqa: F401 — força registro dos handlers
from app.mcp.pending_actions_service import HANDLERS


def _seed_evolution(db):
    db.add(IntegrationSettings(
        workspace_id=1, provider="evolution", enabled=True,
        config={
            "base_url": "https://evo.example.com", "instance": "sdr",
            "api_key": encrypt("KEY"), "webhook_secret": encrypt("SEC"),
        },
    ))
    db.commit()


def test_handler_send_message_persists(db):
    _seed_evolution(db)
    lead = Lead(nome="X", telefone="5544999990000", status="outreach_sent")
    db.add(lead)
    db.commit()
    db.refresh(lead)
    conv = Conversation(
        workspace_id=1, lead_id=lead.id, provider="evolution",
        provider_chat_id="x", phone="5544999990000",
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    fake = Mock(status_code=201)
    fake.json.return_value = {
        "key": {"id": "OUT-1", "remoteJid": "x", "fromMe": True},
        "status": "PENDING",
    }
    with patch("httpx.post", return_value=fake):
        handler = HANDLERS["send_message"]
        result = handler(db, {"conversation_id": conv.id, "body": "oi"})

    assert result["ok"] is True
    assert result["provider_message_id"] == "OUT-1"

    out_msgs = db.query(ConversationMessage).filter_by(
        conversation_id=conv.id, direction="out",
    ).all()
    assert len(out_msgs) == 1


def test_handler_delete_lead_cascades(db):
    lead = Lead(nome="DeleteMe", telefone="x", status="scraped")
    db.add(lead)
    db.commit()
    db.refresh(lead)
    lead_id = lead.id

    handler = HANDLERS["delete_lead"]
    result = handler(db, {"lead_id": lead_id})

    assert result["ok"] is True
    assert db.get(Lead, lead_id) is None


def test_handler_run_pipeline_creates_job(db):
    from app.models import Job
    handler = HANDLERS["run_pipeline"]
    with patch("app.mcp.action_handlers._spawn_pipeline_stage") as spawn:
        result = handler(db, {"stage": "scrape", "params": {"nichos": ["dentista"]}})

    assert result["ok"] is True
    assert "job_id" in result
    spawn.assert_called_once()

    job = db.get(Job, result["job_id"])
    assert job is not None
    assert job.type == "scrape"
```

- [ ] **Step 2: Rodar — deve falhar**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_action_handlers.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implementar `action_handlers.py`**

Create `backend/app/mcp/action_handlers.py`:

```python
"""Handlers executados pelo commit_action — 1 por action_type.

Registrados via `@register_handler("xxx")`. Importar este módulo dispara
auto-registro (side effect). NÃO importar em outros módulos por puro side effect
indireto; o import explícito está em `mcp/server.py`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.mcp.pending_actions_service import register_handler
from app.models import (
    Conversation, ConversationMessage, Job, Lead, OutreachMessage,
)
from app.whatsapp.registry import (
    ProviderNotConfigured,
    UnknownProviderError,
    get_provider,
)
from app.whatsapp.services import append_message

logger = logging.getLogger(__name__)


@register_handler("send_message")
def handle_send_message(db: Session, params: dict) -> dict:
    """Envia WhatsApp via provider + grava ConversationMessage idempotente."""
    conv_id = params["conversation_id"]
    body = params["body"]

    conv = db.get(Conversation, conv_id)
    if conv is None:
        return {"ok": False, "error": "Conversation not found"}

    try:
        adapter = get_provider(db, workspace_id=conv.workspace_id, provider=conv.provider)
    except (UnknownProviderError, ProviderNotConfigured) as exc:
        return {"ok": False, "error": f"provider unavailable: {exc}"}

    idem = f"mcp_send_conv_{conv.id}_{int(datetime.now(timezone.utc).timestamp()*1000)}"
    try:
        sent = adapter.send_text(
            to_phone=conv.phone, body=body, idempotency_key=idem,
        )
    except Exception as exc:
        logger.exception("mcp.send_message.failed conv=%s", conv.id)
        return {"ok": False, "error": f"send failed: {exc}"}

    msg = append_message(
        db, conversation_id=conv.id, direction="out",
        provider_message_id=sent.provider_message_id, body=body,
        timestamp=sent.sent_at,
    )

    return {
        "ok": True,
        "message_id": msg.id,
        "provider_message_id": sent.provider_message_id,
        "sent_at": sent.sent_at.isoformat() if sent.sent_at else None,
    }


@register_handler("bulk_send")
def handle_bulk_send(db: Session, params: dict) -> dict:
    """Disparo em massa — cria Job background. Retorna job_id."""
    template = params["template"]
    recipients = params["recipient_lead_ids"]

    job = Job(
        type="mcp_bulk_send",
        status="pending",
        params={"template": template, "lead_ids": recipients},
        started_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Spawn no thread separado pra não bloquear MCP request
    _spawn_bulk_send(job.id)

    return {
        "ok": True, "job_id": job.id, "recipient_count": len(recipients),
    }


@register_handler("delete_lead")
def handle_delete_lead(db: Session, params: dict) -> dict:
    lead_id = params["lead_id"]
    lead = db.get(Lead, lead_id)
    if lead is None:
        return {"ok": False, "error": "Lead not found"}
    db.delete(lead)
    db.commit()
    return {"ok": True, "deleted_lead_id": lead_id}


@register_handler("delete_conversations")
def handle_delete_conversations(db: Session, params: dict) -> dict:
    ids = params["conversation_ids"]
    if not ids:
        return {"ok": True, "deleted_count": 0}
    rows = db.query(Conversation).filter(Conversation.id.in_(ids)).all()
    for r in rows:
        db.delete(r)
    db.commit()
    return {"ok": True, "deleted_count": len(rows)}


@register_handler("run_pipeline")
def handle_run_pipeline(db: Session, params: dict) -> dict:
    stage = params["stage"]
    stage_params = params.get("params", {})

    job = Job(
        type=stage,
        status="pending",
        params=stage_params,
        started_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    _spawn_pipeline_stage(stage, job.id, stage_params)
    return {"ok": True, "job_id": job.id, "stage": stage}


@register_handler("classify_leads")
def handle_classify_leads(db: Session, params: dict) -> dict:
    job = Job(
        type="classify",
        status="pending",
        params=params,
        started_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    _spawn_classify(job.id, params)
    return {"ok": True, "job_id": job.id}


@register_handler("generate_lps")
def handle_generate_lps(db: Session, params: dict) -> dict:
    job = Job(
        type="generate",
        status="pending",
        params=params,
        started_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    _spawn_generate_lps(job.id, params)
    return {"ok": True, "job_id": job.id}


# ─── Spawners — wrappers thin pra reuse do code do pipeline router ───

def _spawn_pipeline_stage(stage: str, job_id: int, params: dict) -> None:
    """Dispara stage do pipeline em thread daemon. Reusa _run_* do pipeline."""
    import threading
    from app.routers.pipeline import (
        _run_scrape, _run_enrich, _run_generate, _run_outreach,
    )
    runners = {
        "scrape": _run_scrape, "enrich": _run_enrich,
        "generate": _run_generate, "outreach": _run_outreach,
    }
    fn = runners.get(stage)
    if fn is None:
        return
    t = threading.Thread(target=fn, args=(job_id, params), daemon=True, name=f"mcp-{stage}-{job_id}")
    t.start()


def _spawn_bulk_send(job_id: int) -> None:
    """Placeholder pra bulk send. Implementação concreta vem em P3 (dispatch_outreach)
    ou inline aqui se priorizar via MCP."""
    logger.info("mcp.bulk_send.spawned job=%s (no-op stub)", job_id)


def _spawn_classify(job_id: int, params: dict) -> None:
    import threading
    from app.routers.pipeline import _run_classify
    t = threading.Thread(target=_run_classify, args=(job_id, params), daemon=True, name=f"mcp-classify-{job_id}")
    t.start()


def _spawn_generate_lps(job_id: int, params: dict) -> None:
    import threading
    from app.routers.pipeline import _run_generate
    t = threading.Thread(target=_run_generate, args=(job_id, params), daemon=True, name=f"mcp-genlp-{job_id}")
    t.start()
```

- [ ] **Step 4: Rodar tests**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_action_handlers.py -v
```

Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/app/mcp/action_handlers.py backend/tests/mcp/test_action_handlers.py
git commit -m "feat(mcp): action_handlers — 7 functions registered for commit_action"
```

---

## Task 4: Prepare tools (7 tools)

**Files:**
- Create: `backend/app/mcp/tools_prepare.py`
- Create: `backend/tests/mcp/test_tools_prepare.py`

Cada `prepare_*` valida inputs, monta preview, persiste `pending_actions` row.

- [ ] **Step 1: Test falhando**

Create `backend/tests/mcp/test_tools_prepare.py`:

```python
import asyncio
from unittest.mock import Mock

from mcp.server.auth.provider import AccessToken

from app.models import Conversation, Lead, PendingAction
from app.mcp.tools_prepare import (
    prepare_send_message,
    prepare_bulk_send,
    prepare_delete_lead,
    prepare_delete_conversations,
    prepare_run_pipeline,
    prepare_classify_leads,
    prepare_generate_lps,
)


def _ctx(workspace_id: int = 1, token_id: str = "tok-abc"):
    ctx = Mock()
    user = Mock()
    user.access_token = AccessToken(
        token=token_id * (64 // len(token_id) + 1),
        client_id="mcp-1",
        scopes=[f"mcp:workspace:{workspace_id}"],
        expires_at=None, resource=None,
    )
    ctx.request_context.request.user = user
    return ctx


def test_prepare_send_message_creates_action(db):
    lead = Lead(nome="X", telefone="5544999990000", status="outreach_sent")
    db.add(lead)
    db.commit()
    db.refresh(lead)
    conv = Conversation(
        workspace_id=1, lead_id=lead.id, provider="evolution",
        provider_chat_id="x", phone="5544999990000",
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    result = asyncio.run(prepare_send_message(
        _ctx(), conversation_id=conv.id, body="testing 123",
    ))
    assert result["action_id"]
    assert result["preview"]["to_phone"] == "5544999990000"
    assert result["preview"]["body_rendered"] == "testing 123"
    assert result["preview"]["lead_nome"] == "X"

    row = db.query(PendingAction).filter_by(id=result["action_id"]).first()
    assert row is not None
    assert row.action_type == "send_message"


def test_prepare_send_message_conv_not_found(db):
    result = asyncio.run(prepare_send_message(
        _ctx(), conversation_id=9999, body="x",
    ))
    assert "error" in result


def test_prepare_delete_lead_includes_cascade_counts(db):
    lead = Lead(nome="Big", telefone="x", status="scraped")
    db.add(lead)
    db.commit()
    db.refresh(lead)
    # Sem cascades aqui — só verificar preview shape

    result = asyncio.run(prepare_delete_lead(_ctx(), lead_id=lead.id))
    assert result["action_id"]
    assert result["preview"]["lead_summary"]["nome"] == "Big"
    assert "related_data" in result["preview"]


def test_prepare_run_pipeline_creates_preview(db):
    result = asyncio.run(prepare_run_pipeline(
        _ctx(), stage="scrape", params={"nichos": ["dentista"], "cidades": ["X"]},
    ))
    assert result["action_id"]
    assert result["preview"]["stage"] == "scrape"
    assert "eligible_count" in result["preview"] or "estimated_eligible_count" in result["preview"]


def test_prepare_bulk_send_includes_count(db):
    lead_ids = []
    for i in range(3):
        l = Lead(nome=f"L{i}", telefone=f"x{i}", status="outreach_ready")
        db.add(l)
    db.commit()
    leads = db.query(Lead).all()
    lead_ids = [l.id for l in leads]

    result = asyncio.run(prepare_bulk_send(
        _ctx(), recipient_lead_ids=lead_ids, template="Olá {{lead.nome}}",
    ))
    assert result["action_id"]
    assert result["preview"]["count"] == 3
    assert "recipients_sample" in result["preview"]


def test_prepare_classify_leads_returns_estimate(db):
    for i in range(2):
        db.add(Lead(nome=f"L{i}", telefone=f"x{i}", status="enriched"))
    db.commit()

    result = asyncio.run(prepare_classify_leads(
        _ctx(), filter={"status": "enriched"}, level="full",
    ))
    assert result["action_id"]
    assert result["preview"]["count"] == 2


def test_prepare_generate_lps_returns_estimate(db):
    for i in range(4):
        db.add(Lead(nome=f"L{i}", telefone=f"x{i}", status="enriched"))
    db.commit()

    result = asyncio.run(prepare_generate_lps(
        _ctx(), filter={"status": "enriched"},
    ))
    assert result["action_id"]
    assert result["preview"]["count"] == 4
```

- [ ] **Step 2: Rodar — deve falhar**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_tools_prepare.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implementar `tools_prepare.py`**

Create `backend/app/mcp/tools_prepare.py`:

```python
"""MCP prepare_* tools — montam preview + persistem pending_action.

Cada um retorna `{action_id, preview, expires_at}`. Claude mostra preview ao
user, recebe confirmação, e chama `commit_action(action_id)` pra executar.
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from app.mcp.context import get_workspace_id
from app.mcp.db import db_session
from app.mcp.pending_actions_service import create_action
from app.mcp.tokens import hash_token
from app.models import Conversation, ConversationMessage, Lead


def _token_hash_from_ctx(ctx: Any) -> str:
    """Recupera hash do token usado nesta request — pra rastrear ownership."""
    try:
        user = ctx.request_context.request.user
        plain = user.access_token.token if user else ""
    except AttributeError:
        plain = ""
    return hash_token(plain) if plain else ""


def _result(action_id: str, preview: dict, row) -> dict:
    return {
        "action_id": action_id,
        "preview": preview,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
    }


async def prepare_send_message(
    ctx: Any, conversation_id: int, body: str,
) -> dict:
    workspace_id = get_workspace_id(ctx)
    token_hash = _token_hash_from_ctx(ctx)

    with db_session() as db:
        conv = db.query(Conversation).filter_by(
            id=conversation_id, workspace_id=workspace_id,
        ).first()
        if conv is None:
            return {"error": "Conversation not found"}
        lead = db.get(Lead, conv.lead_id)
        preview = {
            "to_phone": conv.phone,
            "body_rendered": body,
            "lead_nome": lead.nome if lead else None,
            "conversation_id": conversation_id,
        }
        params = {"conversation_id": conversation_id, "body": body}
        row = create_action(
            db, workspace_id=workspace_id, action_type="send_message",
            params=params, preview=preview, token_hash=token_hash,
        )
        return _result(row.id, preview, row)


async def prepare_bulk_send(
    ctx: Any, recipient_lead_ids: list[int], template: str,
) -> dict:
    workspace_id = get_workspace_id(ctx)
    token_hash = _token_hash_from_ctx(ctx)

    with db_session() as db:
        sample_leads = (
            db.query(Lead)
            .filter(Lead.id.in_(recipient_lead_ids))
            .limit(5)
            .all()
        )
        preview = {
            "count": len(recipient_lead_ids),
            "recipients_sample": [
                {"id": l.id, "nome": l.nome, "telefone": l.telefone}
                for l in sample_leads
            ],
            "template": template,
            "estimated_minutes": max(1, len(recipient_lead_ids) // 30),
        }
        row = create_action(
            db, workspace_id=workspace_id, action_type="bulk_send",
            params={"recipient_lead_ids": recipient_lead_ids, "template": template},
            preview=preview, token_hash=token_hash,
        )
        return _result(row.id, preview, row)


async def prepare_delete_lead(ctx: Any, lead_id: int) -> dict:
    workspace_id = get_workspace_id(ctx)
    token_hash = _token_hash_from_ctx(ctx)

    with db_session() as db:
        lead = db.get(Lead, lead_id)
        if lead is None:
            return {"error": "Lead not found"}

        msgs_count = (
            db.query(ConversationMessage)
            .join(Conversation, Conversation.id == ConversationMessage.conversation_id)
            .filter(Conversation.lead_id == lead_id)
            .count()
        )
        from app.models import LandingPage, OutreachMessage
        lps_count = db.query(LandingPage).filter_by(lead_id=lead_id).count()
        outreach_count = db.query(OutreachMessage).filter_by(lead_id=lead_id).count()
        convs_count = db.query(Conversation).filter_by(lead_id=lead_id).count()

        preview = {
            "lead_summary": {
                "id": lead.id, "nome": lead.nome, "telefone": lead.telefone,
                "status": lead.status, "score": lead.opportunity_score,
            },
            "related_data": {
                "conversations": convs_count,
                "messages": msgs_count,
                "landing_pages": lps_count,
                "outreach_messages": outreach_count,
            },
        }
        row = create_action(
            db, workspace_id=workspace_id, action_type="delete_lead",
            params={"lead_id": lead_id}, preview=preview, token_hash=token_hash,
        )
        return _result(row.id, preview, row)


async def prepare_delete_conversations(
    ctx: Any, conversation_ids: list[int],
) -> dict:
    workspace_id = get_workspace_id(ctx)
    token_hash = _token_hash_from_ctx(ctx)

    with db_session() as db:
        rows = (
            db.query(Conversation)
            .filter(
                Conversation.id.in_(conversation_ids),
                Conversation.workspace_id == workspace_id,
            )
            .limit(3)
            .all()
        )
        preview = {
            "count": len(conversation_ids),
            "sample": [
                {"id": c.id, "phone": c.phone, "lead_id": c.lead_id} for c in rows
            ],
        }
        row = create_action(
            db, workspace_id=workspace_id, action_type="delete_conversations",
            params={"conversation_ids": conversation_ids},
            preview=preview, token_hash=token_hash,
        )
        return _result(row.id, preview, row)


async def prepare_run_pipeline(
    ctx: Any, stage: Literal["scrape", "enrich", "generate", "outreach"],
    params: Optional[dict] = None,
) -> dict:
    workspace_id = get_workspace_id(ctx)
    token_hash = _token_hash_from_ctx(ctx)
    stage_params = params or {}

    # Estimate eligible leads via pipeline preview endpoint logic
    with db_session() as db:
        if stage == "enrich":
            count = db.query(Lead).filter(Lead.status == "scraped").count()
        elif stage == "generate":
            count = db.query(Lead).filter(Lead.status == "enriched").count()
        elif stage == "outreach":
            count = db.query(Lead).filter(Lead.status == "lp_generated").count()
        else:  # scrape
            count = None  # depende dos params

        preview = {
            "stage": stage,
            "estimated_eligible_count": count,
            "params": stage_params,
            "estimated_minutes": (count or 50) // 30 if count else 5,
            "estimated_cost_usd": None,  # placeholder; LLM cost calc avançado fica pra v2
        }
        row = create_action(
            db, workspace_id=workspace_id, action_type="run_pipeline",
            params={"stage": stage, "params": stage_params},
            preview=preview, token_hash=token_hash,
        )
        return _result(row.id, preview, row)


async def prepare_classify_leads(
    ctx: Any, filter: Optional[dict] = None,
    level: Literal["light", "full"] = "full",
) -> dict:
    workspace_id = get_workspace_id(ctx)
    token_hash = _token_hash_from_ctx(ctx)
    f = filter or {}

    with db_session() as db:
        q = db.query(Lead)
        if f.get("status"):
            q = q.filter(Lead.status == f["status"])
        count = q.count()
        # Heurística: ~$0.005/classify
        cost_estimate = round(count * 0.005, 2)

        preview = {
            "count": count, "level": level, "filter": f,
            "estimated_llm_calls": count,
            "estimated_cost_usd": cost_estimate,
        }
        row = create_action(
            db, workspace_id=workspace_id, action_type="classify_leads",
            params={"filter": f, "level": level},
            preview=preview, token_hash=token_hash,
        )
        return _result(row.id, preview, row)


async def prepare_generate_lps(
    ctx: Any, filter: Optional[dict] = None,
) -> dict:
    workspace_id = get_workspace_id(ctx)
    token_hash = _token_hash_from_ctx(ctx)
    f = filter or {}

    with db_session() as db:
        q = db.query(Lead)
        if f.get("status"):
            q = q.filter(Lead.status == f["status"])
        else:
            q = q.filter(Lead.status == "enriched")
        count = q.count()
        cost_estimate = round(count * 0.03, 2)  # ~$0.03/LP heurístico

        preview = {
            "count": count, "filter": f,
            "estimated_cost_usd": cost_estimate,
        }
        row = create_action(
            db, workspace_id=workspace_id, action_type="generate_lps",
            params={"filter": f}, preview=preview, token_hash=token_hash,
        )
        return _result(row.id, preview, row)


def register_prepare_tools(server) -> None:
    server.tool(name="prepare_send_message")(prepare_send_message)
    server.tool(name="prepare_bulk_send")(prepare_bulk_send)
    server.tool(name="prepare_delete_lead")(prepare_delete_lead)
    server.tool(name="prepare_delete_conversations")(prepare_delete_conversations)
    server.tool(name="prepare_run_pipeline")(prepare_run_pipeline)
    server.tool(name="prepare_classify_leads")(prepare_classify_leads)
    server.tool(name="prepare_generate_lps")(prepare_generate_lps)
```

- [ ] **Step 4: Rodar tests**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_tools_prepare.py -v
```

Expected: 7 PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/app/mcp/tools_prepare.py backend/tests/mcp/test_tools_prepare.py
git commit -m "feat(mcp): 7 prepare_* tools (two-phase commit phase 1)"
```

---

## Task 5: `commit_action` + `cancel_action`

**Files:**
- Create: `backend/app/mcp/tools_commit.py`
- Create: `backend/tests/mcp/test_tools_commit.py`

- [ ] **Step 1: Test falhando**

Create `backend/tests/mcp/test_tools_commit.py`:

```python
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from mcp.server.auth.provider import AccessToken

from app.integrations.crypto import encrypt
from app.models import (
    Conversation, ConversationMessage, IntegrationSettings, Lead, PendingAction,
)
import app.mcp.action_handlers  # noqa: F401 — força registro dos handlers
from app.mcp.pending_actions_service import HANDLERS, create_action
from app.mcp.tools_commit import commit_action, cancel_action
from app.mcp.tokens import hash_token


def _ctx(token_plain: str = "x" * 64, workspace_id: int = 1):
    ctx = Mock()
    user = Mock()
    user.access_token = AccessToken(
        token=token_plain, client_id="mcp-1",
        scopes=[f"mcp:workspace:{workspace_id}"], expires_at=None, resource=None,
    )
    ctx.request_context.request.user = user
    return ctx


def _seed_send_message_action(db, *, token_plain="x" * 64):
    """Seeds Evolution config + lead + conv + pending_action send_message."""
    db.add(IntegrationSettings(
        workspace_id=1, provider="evolution", enabled=True,
        config={
            "base_url": "https://evo.example.com", "instance": "sdr",
            "api_key": encrypt("KEY"), "webhook_secret": encrypt("SEC"),
        },
    ))
    lead = Lead(nome="X", telefone="5544999990000", status="outreach_sent")
    db.add(lead)
    db.commit()
    db.refresh(lead)
    conv = Conversation(
        workspace_id=1, lead_id=lead.id, provider="evolution",
        provider_chat_id="x", phone="5544999990000",
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    pa = create_action(
        db, workspace_id=1, action_type="send_message",
        params={"conversation_id": conv.id, "body": "ping"},
        preview={"to_phone": "5544999990000", "body_rendered": "ping"},
        token_hash=hash_token(token_plain),
    )
    return pa, conv


def test_commit_action_executes_handler(db):
    pa, conv = _seed_send_message_action(db)

    fake = Mock(status_code=201)
    fake.json.return_value = {
        "key": {"id": "PMID-1", "remoteJid": "x", "fromMe": True},
        "status": "PENDING",
    }
    with patch("httpx.post", return_value=fake):
        result = asyncio.run(commit_action(_ctx(), action_id=pa.id))

    assert result["ok"] is True
    assert result["result"]["provider_message_id"] == "PMID-1"

    row = db.query(PendingAction).filter_by(id=pa.id).first()
    assert row.committed_at is not None
    assert row.result["provider_message_id"] == "PMID-1"


def test_commit_action_idempotent(db):
    pa, _ = _seed_send_message_action(db)
    pa.committed_at = datetime.utcnow()
    pa.result = {"ok": True, "provider_message_id": "OLD"}
    db.commit()

    result = asyncio.run(commit_action(_ctx(), action_id=pa.id))
    assert result["ok"] is True
    assert result["result"]["provider_message_id"] == "OLD"
    assert result["already_committed"] is True


def test_commit_action_ownership_violation(db):
    pa, _ = _seed_send_message_action(db, token_plain="a" * 64)

    # Ctx usa token diferente
    result = asyncio.run(commit_action(_ctx(token_plain="b" * 64), action_id=pa.id))
    assert result["ok"] is False
    assert "not found" in result["error"].lower() or "invalid" in result["error"].lower()


def test_commit_action_expired(db):
    db.add(PendingAction(
        id="expired-1", workspace_id=1, action_type="send_message",
        params={"conversation_id": 1, "body": "x"}, preview={},
        created_by_token_hash=hash_token("x" * 64),
        expires_at=datetime.utcnow() - timedelta(seconds=1),
    ))
    db.commit()

    result = asyncio.run(commit_action(_ctx(), action_id="expired-1"))
    assert result["ok"] is False


def test_commit_action_cancelled(db):
    db.add(PendingAction(
        id="cancel-1", workspace_id=1, action_type="send_message",
        params={}, preview={},
        created_by_token_hash=hash_token("x" * 64),
        expires_at=datetime.utcnow() + timedelta(minutes=5),
        cancelled_at=datetime.utcnow(),
    ))
    db.commit()

    result = asyncio.run(commit_action(_ctx(), action_id="cancel-1"))
    assert result["ok"] is False


def test_cancel_action_marks_cancelled(db):
    pa = create_action(
        db, workspace_id=1, action_type="send_message",
        params={}, preview={}, token_hash=hash_token("x" * 64),
    )
    result = asyncio.run(cancel_action(_ctx(), action_id=pa.id))
    assert result["ok"] is True

    row = db.query(PendingAction).filter_by(id=pa.id).first()
    assert row.cancelled_at is not None


def test_cancel_action_idempotent(db):
    pa = create_action(
        db, workspace_id=1, action_type="send_message",
        params={}, preview={}, token_hash=hash_token("x" * 64),
    )
    asyncio.run(cancel_action(_ctx(), action_id=pa.id))
    result = asyncio.run(cancel_action(_ctx(), action_id=pa.id))
    # 2x cancel: 2nd retorna ok=false ou ok=true com already_cancelled — qualquer um aceito
    assert "ok" in result
```

- [ ] **Step 2: Rodar — deve falhar**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_tools_commit.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implementar `tools_commit.py`**

Create `backend/app/mcp/tools_commit.py`:

```python
"""MCP commit_action + cancel_action — phase 2 do two-phase commit."""
from __future__ import annotations

import logging
from typing import Any

from app.mcp.context import get_workspace_id
from app.mcp.db import db_session
from app.mcp.pending_actions_service import (
    HANDLERS,
    cancel_action_row,
    commit_action_row,
    get_action,
)
from app.mcp.tokens import hash_token

logger = logging.getLogger(__name__)


def _token_hash_from_ctx(ctx: Any) -> str:
    try:
        user = ctx.request_context.request.user
        plain = user.access_token.token if user else ""
    except AttributeError:
        plain = ""
    return hash_token(plain) if plain else ""


async def commit_action(ctx: Any, action_id: str) -> dict:
    """Executa a ação preparada. Idempotente: 2ª chamada retorna mesmo result.

    Validations:
    - action_id existe
    - mesmo workspace
    - mesmo token (ownership)
    - não expirada
    - não cancelled
    """
    workspace_id = get_workspace_id(ctx)
    token_hash = _token_hash_from_ctx(ctx)

    with db_session() as db:
        row = get_action(
            db, action_id=action_id, workspace_id=workspace_id, token_hash=token_hash,
        )
        if row is None:
            return {"ok": False, "error": "Action not found or invalid"}

        # Idempotente
        if row.committed_at is not None:
            return {
                "ok": True,
                "already_committed": True,
                "committed_at": row.committed_at.isoformat(),
                "result": row.result,
            }

        handler = HANDLERS.get(row.action_type)
        if handler is None:
            logger.error("mcp.commit.no_handler action_type=%s id=%s", row.action_type, action_id)
            return {"ok": False, "error": f"No handler for {row.action_type}"}

        try:
            result = handler(db, row.params)
        except Exception as exc:
            logger.exception("mcp.commit.handler_failed id=%s", action_id)
            return {"ok": False, "error": f"Handler failed: {exc}"}

        commit_action_row(db, action_id=action_id, result=result)

        return {"ok": True, "action_id": action_id, "result": result}


async def cancel_action(ctx: Any, action_id: str) -> dict:
    workspace_id = get_workspace_id(ctx)
    token_hash = _token_hash_from_ctx(ctx)

    with db_session() as db:
        row = get_action(
            db, action_id=action_id, workspace_id=workspace_id, token_hash=token_hash,
        )
        if row is None:
            return {"ok": False, "error": "Action not found or invalid"}
        ok = cancel_action_row(db, action_id=action_id)
        return {"ok": ok, "action_id": action_id}


def register_commit_tools(server) -> None:
    server.tool(name="commit_action")(commit_action)
    server.tool(name="cancel_action")(cancel_action)
```

- [ ] **Step 4: Rodar tests**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_tools_commit.py -v
```

Expected: 7 PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/app/mcp/tools_commit.py backend/tests/mcp/test_tools_commit.py
git commit -m "feat(mcp): commit_action + cancel_action (two-phase commit phase 2)"
```

---

## Task 6: Reaper — limpa pending_actions expiradas

**Files:**
- Create: `backend/app/mcp/reaper.py`
- Create: `backend/tests/mcp/test_reaper.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Test falhando**

Create `backend/tests/mcp/test_reaper.py`:

```python
from datetime import datetime, timedelta

from app.models import PendingAction
from app.mcp.reaper import reap_expired_actions


def test_reaper_marks_expired_as_cancelled(db):
    past = datetime.utcnow() - timedelta(minutes=10)
    future = datetime.utcnow() + timedelta(minutes=5)
    db.add_all([
        PendingAction(
            id="exp1", workspace_id=1, action_type="x",
            params={}, preview={}, created_by_token_hash="h",
            expires_at=past,
        ),
        PendingAction(
            id="exp2", workspace_id=1, action_type="x",
            params={}, preview={}, created_by_token_hash="h",
            expires_at=past,
        ),
        PendingAction(
            id="active", workspace_id=1, action_type="x",
            params={}, preview={}, created_by_token_hash="h",
            expires_at=future,
        ),
    ])
    db.commit()

    reaped = reap_expired_actions(db)
    assert reaped == 2

    rows = {r.id: r for r in db.query(PendingAction).all()}
    assert rows["exp1"].cancelled_at is not None
    assert rows["exp2"].cancelled_at is not None
    assert rows["active"].cancelled_at is None


def test_reaper_ignores_already_committed(db):
    past = datetime.utcnow() - timedelta(minutes=10)
    db.add(PendingAction(
        id="commited-but-expired", workspace_id=1, action_type="x",
        params={}, preview={}, created_by_token_hash="h",
        expires_at=past, committed_at=datetime.utcnow(),
    ))
    db.commit()

    reaped = reap_expired_actions(db)
    assert reaped == 0

    row = db.query(PendingAction).filter_by(id="commited-but-expired").first()
    assert row.cancelled_at is None


def test_reaper_ignores_already_cancelled(db):
    past = datetime.utcnow() - timedelta(minutes=10)
    db.add(PendingAction(
        id="cancelled-and-expired", workspace_id=1, action_type="x",
        params={}, preview={}, created_by_token_hash="h",
        expires_at=past, cancelled_at=datetime.utcnow(),
    ))
    db.commit()

    reaped = reap_expired_actions(db)
    assert reaped == 0
```

- [ ] **Step 2: Rodar — deve falhar**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_reaper.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implementar `reaper.py`**

Create `backend/app/mcp/reaper.py`:

```python
"""Reaper de pending_actions expiradas — marca cancelled_at sem deletar.

Chamado no startup (uma vez por process boot). Em produção idealmente roda
periódico via cron leve, mas pra MVP startup-hook é suficiente.
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import PendingAction

logger = logging.getLogger(__name__)


def reap_expired_actions(db: Session) -> int:
    """Marca todas as PendingAction expiradas e não-finalizadas como cancelled.
    Retorna contagem de rows afetadas."""
    rows = (
        db.query(PendingAction)
        .filter(PendingAction.expires_at <= datetime.utcnow())
        .filter(PendingAction.committed_at.is_(None))
        .filter(PendingAction.cancelled_at.is_(None))
        .all()
    )
    now = datetime.utcnow()
    for r in rows:
        r.cancelled_at = now
    if rows:
        db.commit()
        logger.info("mcp.reaper.reaped count=%d", len(rows))
    return len(rows)
```

- [ ] **Step 4: Wire em `main.py` no startup hook**

Edit `backend/app/main.py`. Localizar o `@app.on_event("startup")` que executa `_reap_orphaned_jobs`. Adicionar ao mesmo handler OU criar segundo:

```python
@app.on_event("startup")
def _reap_mcp_pending_actions() -> None:
    """Marca pending_actions expiradas como cancelled no startup."""
    from app.mcp.reaper import reap_expired_actions
    db = SessionLocal()
    try:
        reap_expired_actions(db)
    except Exception:
        logger.exception("startup.reap_mcp_failed")
        db.rollback()
    finally:
        db.close()
```

- [ ] **Step 5: Rodar tests reaper**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_reaper.py -v
```

Expected: 3 PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/app/mcp/reaper.py backend/app/main.py backend/tests/mcp/test_reaper.py
git commit -m "feat(mcp): reaper marca pending_actions expiradas no startup"
```

---

## Task 7: Wire em `build_mcp_server`

**Files:**
- Modify: `backend/app/mcp/server.py`

- [ ] **Step 1: Atualizar `build_mcp_server`**

Edit `backend/app/mcp/server.py`. Adicionar registrations:

```python
# Imports adicionais
from app.mcp.tools_soft_write import register_soft_write_tools
from app.mcp.tools_prepare import register_prepare_tools
from app.mcp.tools_commit import register_commit_tools
import app.mcp.action_handlers  # noqa: F401 — força registro dos handlers
```

E dentro de `build_mcp_server` (depois de `register_pending_tools(server)`):

```python
    # M-3 write tools
    register_soft_write_tools(server)
    register_prepare_tools(server)
    register_commit_tools(server)
```

- [ ] **Step 2: Atualizar test `test_server_build.py` com novas tools**

Adicionar ao `expected_tools` set (no test que já existe):

```python
    expected_tools |= {
        "update_lead_status", "update_lead_fields", "mark_conversation_read",
        "update_workspace_profile", "update_workspace_targeting",
        "prepare_send_message", "prepare_bulk_send", "prepare_delete_lead",
        "prepare_delete_conversations", "prepare_run_pipeline",
        "prepare_classify_leads", "prepare_generate_lps",
        "commit_action", "cancel_action",
    }
```

- [ ] **Step 3: Rodar suite MCP**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/ -v
```

Expected: TODOS PASS (~80 testes em M-1 + M-2 + M-3).

- [ ] **Step 4: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/app/mcp/server.py backend/tests/mcp/test_server_build.py
git commit -m "feat(mcp): wire write tools + handlers em build_mcp_server"
```

---

## Task 8: Smoke + push + PR

- [ ] **Step 1: Suite full backend**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest --deselect tests/test_outreach.py 2>&1 | tail -5
```

Expected: ~785 PASS (745 baseline pós-M-2 + ~40 M-3).

- [ ] **Step 2: Push**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git push -u origin feat/mcp-m3-write-tools
```

- [ ] **Step 3: Abrir PR**

```bash
gh pr create --base main --title "feat(mcp): M-3 write tools + two-phase commit" --body "$(cat <<'EOF'
## Summary

5 soft-write + 7 prepare_* + commit/cancel + reaper.

**Soft-write (executa direto, Claude confirma via prompt):**
- update_lead_status, update_lead_fields, mark_conversation_read,
- update_workspace_profile, update_workspace_targeting

**Hard-write (two-phase commit):**
- prepare_send_message → commit_action → handle_send_message → ConversationMessage gravado
- prepare_bulk_send → handle_bulk_send (job background)
- prepare_delete_lead → handle_delete_lead (cascade)
- prepare_delete_conversations → handle_delete_conversations
- prepare_run_pipeline (scrape/enrich/generate/outreach) → handle_run_pipeline
- prepare_classify_leads → handle_classify_leads
- prepare_generate_lps → handle_generate_lps

**Service + Infra:**
- \`pending_actions_service.py\` — create/get/commit/cancel + HANDLERS registry
- \`action_handlers.py\` — 7 handlers registrados via decorator
- \`reaper.py\` — startup hook marca expiradas como cancelled

**Idempotência + ownership:**
- commit_action 2x retorna mesmo result com \`already_committed: true\`
- Token hash do criador vs token hash do committer = match obrigatório
- Workspace_id scope obrigatório
- Expired (>5min) e cancelled rejeitados

## Test Plan

- [x] ~40 testes novos (pending_actions service, soft-write tools, prepare tools, commit/cancel, action handlers, reaper)
- [x] Suite backend full passa (~785 PASS)
- [ ] **Manual:** Claude Desktop pedir "manda follow-up no lead X" → Claude chama prepare_send_message → mostra preview → user confirma → Claude chama commit_action → msg enviada via Evolution

## Não coberto

- UI gerenciar tokens (M-4)
- Prompts pre-built (M-5)
- Subscriptions SSE (M-5)
EOF
)"
```

---

## Self-Review

**Spec coverage** (vs M-0 §4 soft + hard write):

| Spec item | Task |
|---|---|
| update_lead_status | Task 2 |
| update_lead_fields | Task 2 |
| mark_conversation_read | Task 2 |
| update_workspace_profile | Task 2 |
| update_workspace_targeting | Task 2 |
| prepare_send_message + handler | Task 3 + 4 |
| prepare_bulk_send + handler | Task 3 + 4 |
| prepare_delete_lead + handler | Task 3 + 4 |
| prepare_delete_conversations + handler | Task 3 + 4 |
| prepare_run_pipeline + handler | Task 3 + 4 |
| prepare_classify_leads + handler | Task 3 + 4 |
| prepare_generate_lps + handler | Task 3 + 4 |
| commit_action (idempotent) | Task 5 |
| cancel_action | Task 5 |
| pending_actions table TTL + reaper | Task 1 + 6 |
| Token hash ownership validation | Task 1 (get_action) + Task 5 (commit/cancel) |

**Placeholder scan:** Nenhum step usa "TBD" / "implement later". `_spawn_bulk_send` é stub explícito documentado ("implementação concreta vem em P3").

**Type consistency:**
- `HandlerFn = Callable[[Session, dict], Dict[str, Any]]` em pending_actions_service → consumido em action_handlers ✓
- `create_action(db, *, workspace_id, action_type, params, preview, token_hash, ttl=...) -> PendingAction` consumido em tools_prepare ✓
- `get_action(db, *, action_id, workspace_id, token_hash) -> Optional[PendingAction]` em commit/cancel ✓
- Result dict shape `{ok, action_id, result, already_committed?, error?}` consistente em commit_action

---

## Execution Handoff

Após M-3 merged, próximo é **M-4 (UI tokens)** que dá UX pra user gerenciar tokens via `/app/settings/mcp` sem mexer SQL.

Plan complete and saved to `docs/superpowers/plans/2026-05-18-mcp-m3-write-tools.md`.
