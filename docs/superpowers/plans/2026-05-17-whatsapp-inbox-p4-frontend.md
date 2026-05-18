# WhatsApp Inbox — P4 Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar `/app/inbox` (lista + conversa + rail) consumindo conversas que já chegam via webhook P2, incluindo os endpoints backend que ainda não existem (GET conversations, GET messages, POST send outbound, PATCH mark read).

**Architecture:** Backend ganha router `conversations.py` com 4 endpoints CRUD/read. Frontend monta 3-coluna mobile-first em Next.js App Router, reusando padrão visual do Lead App. Polling SWR 5s. Send outbound chama `provider.send_text` via registry P1 e grava `ConversationMessage` direction="out".

**Tech Stack:** FastAPI 0.115 · SQLAlchemy 2.0 · pytest · Next.js 16 App Router · React 19 · TypeScript · SWR · Tailwind CSS 4 · DS Instrumento

**Spec:** `docs/superpowers/specs/2026-05-16-whatsapp-inbox-design.md` (§5)

---

## Notas de execução

- Branch: `feat/whatsapp-inbox-p4-frontend`. Baseia em `main` (P0-P2 já merged).
- Backend tests: `cd backend && venv/bin/pytest`
- Frontend lint: `cd frontend && npm run lint`
- Frontend dev: `cd frontend && npm run dev` (http://localhost:3000)
- Sem testes frontend automatizados configurados — validação manual via dev server. Lint passa, screenshots quando relevante.
- Commits Conventional Commits. Escopo `inbox` ou `conversations`.

---

## File Structure

### Backend

| File | Action | Responsibility |
|---|---|---|
| `backend/app/routers/conversations.py` | Create | 4 endpoints HTTP `/api/conversations*` |
| `backend/app/schemas.py` | Modify | Adicionar Pydantic schemas `ConversationOut`, `ConversationListItem`, `MessageOut`, `SendMessageIn` |
| `backend/app/main.py:13,84-89` | Modify | Import + register router |
| `backend/tests/test_conversations_router.py` | Create | 12 testes E2E HTTP |

### Frontend

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/lib/api-inbox.ts` | Create | Fetch wrappers + types `Conversation`, `ConversationDetail`, `Message` |
| `frontend/src/app/app/inbox/page.tsx` | Create | Rota raiz `/app/inbox` — lista + empty state |
| `frontend/src/app/app/inbox/[id]/page.tsx` | Create | Rota detail `/app/inbox/[id]` — 3 colunas |
| `frontend/src/components/inbox/InboxList.tsx` | Create | Lista de conversas, search, group por status, virtualized |
| `frontend/src/components/inbox/InboxFilters.tsx` | Create | Chips: Todas / Não lidas / Respondidas / Ganho |
| `frontend/src/components/inbox/ConversationView.tsx` | Create | Bubbles in/out, scroll auto-bottom |
| `frontend/src/components/inbox/MessageBubble.tsx` | Create | 1 msg: corpo + timestamp + status pills |
| `frontend/src/components/inbox/Composer.tsx` | Create | Textarea + send button, Enter sends |
| `frontend/src/components/inbox/ConversationRail.tsx` | Create | Lead context — reusa LaRail + atalho "Ir pro Lead" |
| `frontend/src/components/inbox/inbox.css` | Create | Estilos containers + bubbles |
| `frontend/src/components/app-sidebar.tsx:12-18` | Modify | Adicionar item "Inbox" entre Pipeline e Leads, com badge unread |

---

## Task 1: Backend — Pydantic schemas

**Files:**
- Modify: `backend/app/schemas.py`

- [ ] **Step 1: Adicionar schemas ao final do `schemas.py`**

```python
class MessageOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    conversation_id: int
    direction: str  # "in" | "out"
    provider_message_id: str | None
    body: str | None
    media_url: str | None
    status: str
    sent_at: datetime | None
    delivered_at: datetime | None
    read_at: datetime | None
    received_at: datetime | None
    error: str | None
    created_at: datetime


class ConversationListItem(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    lead_id: int
    lead_nome: str | None  # join
    lead_telefone: str | None  # join
    lead_status: str | None  # join
    provider: str
    phone: str
    last_message_at: datetime | None
    last_message_preview: str | None  # snippet dos últimos 80 chars body
    unread_count: int
    status: str


class ConversationOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    workspace_id: int
    lead_id: int
    provider: str
    provider_chat_id: str
    phone: str
    last_message_at: datetime | None
    unread_count: int
    status: str
    created_at: datetime
    messages: list[MessageOut]


class SendMessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
```

- [ ] **Step 2: Verificar imports no topo de schemas.py**

Run: `head -10 backend/app/schemas.py`
Expected: `from datetime import datetime` e `from pydantic import BaseModel, Field` já presentes. Se não, adicionar.

- [ ] **Step 3: Commit**

```bash
git checkout -b feat/whatsapp-inbox-p4-frontend
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/app/schemas.py
git commit -m "feat(inbox): pydantic schemas pra conversations + messages"
```

---

## Task 2: Backend — GET /api/conversations (list)

**Files:**
- Create: `backend/app/routers/conversations.py`
- Create: `backend/tests/test_conversations_router.py`

- [ ] **Step 1: Test falhando — list endpoint**

Create `backend/tests/test_conversations_router.py`:

```python
import pytest
from datetime import datetime, timedelta, timezone

from app.models import Conversation, ConversationMessage, Lead


def _seed_conversation(db, *, lead_nome="Lead Test", lead_telefone="5544999990000",
                       unread=0, last_msg_minutes_ago=10, msgs=None):
    lead = Lead(nome=lead_nome, telefone=lead_telefone, status="outreach_sent")
    db.add(lead)
    db.commit()
    db.refresh(lead)

    conv = Conversation(
        workspace_id=1, lead_id=lead.id, provider="evolution",
        provider_chat_id=f"{lead_telefone}@s.whatsapp.net",
        phone=lead_telefone,
        last_message_at=datetime.now(timezone.utc) - timedelta(minutes=last_msg_minutes_ago),
        unread_count=unread,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    for i, (direction, body) in enumerate(msgs or []):
        m = ConversationMessage(
            conversation_id=conv.id, direction=direction,
            provider_message_id=f"MSG-{conv.id}-{i}", body=body,
            status="received" if direction == "in" else "sent",
            received_at=datetime.now(timezone.utc) if direction == "in" else None,
            sent_at=datetime.now(timezone.utc) if direction == "out" else None,
        )
        db.add(m)
    db.commit()
    return lead, conv


def test_list_conversations_empty(client, db):
    r = client.get("/api/conversations")
    assert r.status_code == 200
    assert r.json() == []


def test_list_conversations_returns_all(client, db):
    _seed_conversation(db, lead_nome="A", lead_telefone="5544111111111",
                       msgs=[("in", "oi A"), ("out", "olá A")])
    _seed_conversation(db, lead_nome="B", lead_telefone="5544222222222",
                       msgs=[("in", "oi B")])

    r = client.get("/api/conversations")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2
    # Cada row tem lead_nome, lead_telefone, lead_status (joinado)
    assert {row["lead_nome"] for row in rows} == {"A", "B"}
    assert all("last_message_preview" in row for row in rows)


def test_list_conversations_orders_by_last_message_desc(client, db):
    _seed_conversation(db, lead_nome="Old", last_msg_minutes_ago=120,
                       msgs=[("in", "antigo")])
    _seed_conversation(db, lead_nome="New", last_msg_minutes_ago=5,
                       msgs=[("in", "recente")])

    r = client.get("/api/conversations")
    rows = r.json()
    assert rows[0]["lead_nome"] == "New"
    assert rows[1]["lead_nome"] == "Old"


def test_list_conversations_filter_unread(client, db):
    _seed_conversation(db, lead_nome="Read", unread=0,
                       lead_telefone="5544111111111", msgs=[("in", "x")])
    _seed_conversation(db, lead_nome="Unread", unread=3,
                       lead_telefone="5544222222222", msgs=[("in", "y")])

    r = client.get("/api/conversations?filter=unread")
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["lead_nome"] == "Unread"


def test_list_conversations_search_by_name(client, db):
    _seed_conversation(db, lead_nome="Padaria do João",
                       lead_telefone="5544111111111", msgs=[("in", "x")])
    _seed_conversation(db, lead_nome="Mercearia da Maria",
                       lead_telefone="5544222222222", msgs=[("in", "x")])

    r = client.get("/api/conversations?search=joão")
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["lead_nome"] == "Padaria do João"


def test_list_conversations_search_by_phone(client, db):
    _seed_conversation(db, lead_telefone="5544999990000", msgs=[("in", "x")])
    _seed_conversation(db, lead_telefone="5544888888888", msgs=[("in", "x")])

    r = client.get("/api/conversations?search=999990000")
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["phone"] == "5544999990000"


def test_list_conversations_last_message_preview(client, db):
    long_body = "a" * 200
    _seed_conversation(db, msgs=[("in", "primeira"), ("in", long_body)])
    r = client.get("/api/conversations")
    preview = r.json()[0]["last_message_preview"]
    assert preview is not None
    assert len(preview) <= 80
    assert preview.startswith("aaa")
```

- [ ] **Step 2: Rodar — deve falhar (router não existe)**

```bash
cd backend && venv/bin/pytest tests/test_conversations_router.py::test_list_conversations_empty -v
```

Expected: FAIL (404 ou ModuleNotFoundError).

- [ ] **Step 3: Implementar router list**

Create `backend/app/routers/conversations.py`:

```python
"""Conversations API — lista + detalhe + send outbound + mark-read.

Backend pra o Inbox UI (P4). Reusa adapters do P1 e schemas do P0.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Conversation, ConversationMessage, Lead
from app.schemas import (
    ConversationListItem,
    ConversationOut,
    MessageOut,
    SendMessageIn,
)
from app.whatsapp.normalizer import to_chat_id
from app.whatsapp.registry import (
    ProviderNotConfigured,
    UnknownProviderError,
    get_provider,
)
from app.whatsapp.services import append_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

WORKSPACE_ID = 1  # single-tenant scaffold

_PREVIEW_LEN = 80


def _build_preview(conv: Conversation, db: Session) -> str | None:
    last = (
        db.query(ConversationMessage)
        .filter_by(conversation_id=conv.id)
        .order_by(desc(ConversationMessage.created_at))
        .first()
    )
    if not last or not last.body:
        return None
    return last.body[:_PREVIEW_LEN]


@router.get("", response_model=list[ConversationListItem])
def list_conversations(
    filter: Literal["all", "unread", "responded", "won"] | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    q = (
        db.query(Conversation, Lead)
        .join(Lead, Conversation.lead_id == Lead.id)
        .filter(Conversation.workspace_id == WORKSPACE_ID)
    )

    if filter == "unread":
        q = q.filter(Conversation.unread_count > 0)
    elif filter == "responded":
        q = q.filter(Lead.status == "responded")
    elif filter == "won":
        q = q.filter(Lead.status.in_(["closed", "won", "delivered"]))

    if search:
        pattern = f"%{search.lower()}%"
        q = q.filter(
            or_(
                Lead.nome.ilike(pattern),
                Lead.telefone.ilike(pattern),
                Conversation.phone.ilike(pattern),
            )
        )

    rows = q.order_by(desc(Conversation.last_message_at)).all()

    out: list[ConversationListItem] = []
    for conv, lead in rows:
        out.append(ConversationListItem(
            id=conv.id, lead_id=lead.id,
            lead_nome=lead.nome, lead_telefone=lead.telefone,
            lead_status=lead.status,
            provider=conv.provider, phone=conv.phone,
            last_message_at=conv.last_message_at,
            last_message_preview=_build_preview(conv, db),
            unread_count=conv.unread_count, status=conv.status,
        ))
    return out
```

- [ ] **Step 4: Registrar router em `main.py`**

Edit `backend/app/main.py`:

Linha 13, adicionar `conversations`:
```python
from app.routers import conversations, dashboard, leads, pipeline, settings, webhooks, workspace_settings
```

Após linha `app.include_router(webhooks.router)`, adicionar:
```python
app.include_router(conversations.router)
```

- [ ] **Step 5: Rodar tests da list — devem passar**

```bash
cd backend && venv/bin/pytest tests/test_conversations_router.py -v -k "list"
```

Expected: 7 PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/conversations.py backend/app/main.py backend/tests/test_conversations_router.py
git commit -m "feat(inbox): GET /api/conversations com filtros + search + preview"
```

---

## Task 3: Backend — GET /api/conversations/{id} (detail + messages)

**Files:**
- Modify: `backend/app/routers/conversations.py`
- Modify: `backend/tests/test_conversations_router.py`

- [ ] **Step 1: Adicionar testes detail**

Edit `backend/tests/test_conversations_router.py`. Adicionar:

```python
def test_get_conversation_detail(client, db):
    lead, conv = _seed_conversation(
        db, lead_nome="X", lead_telefone="5544999990000",
        msgs=[("in", "oi"), ("out", "olá"), ("in", "tudo bem?")],
    )

    r = client.get(f"/api/conversations/{conv.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == conv.id
    assert body["lead_id"] == lead.id
    assert len(body["messages"]) == 3
    # ordem cronológica
    assert body["messages"][0]["body"] == "oi"
    assert body["messages"][-1]["body"] == "tudo bem?"


def test_get_conversation_not_found(client, db):
    r = client.get("/api/conversations/9999")
    assert r.status_code == 404
```

- [ ] **Step 2: Rodar — deve falhar (sem endpoint detail)**

```bash
cd backend && venv/bin/pytest tests/test_conversations_router.py::test_get_conversation_detail -v
```

Expected: FAIL (404 do FastAPI por rota não definida).

- [ ] **Step 3: Implementar endpoint detail**

Edit `backend/app/routers/conversations.py`. Adicionar depois de `list_conversations`:

```python
@router.get("/{conversation_id}", response_model=ConversationOut)
def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    conv = (
        db.query(Conversation)
        .options(joinedload(Conversation.messages))
        .filter_by(id=conversation_id, workspace_id=WORKSPACE_ID)
        .first()
    )
    if not conv:
        raise HTTPException(status_code=404, detail="conversation not found")

    # Ordem cronológica das messages
    messages = sorted(conv.messages, key=lambda m: m.created_at)

    return ConversationOut(
        id=conv.id, workspace_id=conv.workspace_id, lead_id=conv.lead_id,
        provider=conv.provider, provider_chat_id=conv.provider_chat_id,
        phone=conv.phone, last_message_at=conv.last_message_at,
        unread_count=conv.unread_count, status=conv.status,
        created_at=conv.created_at,
        messages=[MessageOut.model_validate(m) for m in messages],
    )
```

- [ ] **Step 4: Rodar — devem passar**

```bash
cd backend && venv/bin/pytest tests/test_conversations_router.py -v -k "detail or not_found"
```

Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/conversations.py backend/tests/test_conversations_router.py
git commit -m "feat(inbox): GET /api/conversations/{id} com messages"
```

---

## Task 4: Backend — POST /api/conversations/{id}/messages (send outbound)

**Files:**
- Modify: `backend/app/routers/conversations.py`
- Modify: `backend/tests/test_conversations_router.py`

- [ ] **Step 1: Adicionar testes**

Edit `backend/tests/test_conversations_router.py`. Adicionar:

```python
from unittest.mock import Mock, patch
from app.integrations.crypto import encrypt
from app.models import IntegrationSettings


def _seed_evolution(db):
    db.add(IntegrationSettings(
        workspace_id=1, provider="evolution", enabled=True,
        config={
            "base_url": "https://evo.example.com", "instance": "sdr",
            "api_key": encrypt("X"), "webhook_secret": encrypt("Y"),
        },
    ))
    db.commit()


def test_send_message_outbound_ok(client, db):
    _seed_evolution(db)
    lead, conv = _seed_conversation(db, lead_telefone="5544999990000")

    fake_response = Mock(status_code=201)
    fake_response.json.return_value = {
        "key": {"id": "SEND-1", "remoteJid": "5544999990000@s.whatsapp.net", "fromMe": True},
        "status": "PENDING",
    }
    with patch("httpx.post", return_value=fake_response):
        r = client.post(
            f"/api/conversations/{conv.id}/messages",
            json={"body": "oi do operador"},
        )

    assert r.status_code == 201, r.text
    body = r.json()
    assert body["direction"] == "out"
    assert body["body"] == "oi do operador"
    assert body["provider_message_id"] == "SEND-1"


def test_send_message_persists_conversation_message(client, db):
    _seed_evolution(db)
    lead, conv = _seed_conversation(db, lead_telefone="5544999990000")

    fake_response = Mock(status_code=201)
    fake_response.json.return_value = {
        "key": {"id": "SEND-2", "remoteJid": "x@s.whatsapp.net", "fromMe": True},
        "status": "PENDING",
    }
    with patch("httpx.post", return_value=fake_response):
        client.post(
            f"/api/conversations/{conv.id}/messages",
            json={"body": "msg X"},
        )

    from app.models import ConversationMessage
    out_msgs = db.query(ConversationMessage).filter_by(
        conversation_id=conv.id, direction="out"
    ).all()
    assert len(out_msgs) == 1
    assert out_msgs[0].body == "msg X"
    assert out_msgs[0].provider_message_id == "SEND-2"


def test_send_message_conversation_not_found(client, db):
    _seed_evolution(db)
    r = client.post("/api/conversations/9999/messages", json={"body": "x"})
    assert r.status_code == 404


def test_send_message_empty_body_rejected(client, db):
    _seed_evolution(db)
    lead, conv = _seed_conversation(db, lead_telefone="5544999990000")
    r = client.post(f"/api/conversations/{conv.id}/messages", json={"body": ""})
    assert r.status_code == 422
```

- [ ] **Step 2: Rodar — deve falhar**

```bash
cd backend && venv/bin/pytest tests/test_conversations_router.py -v -k "send"
```

Expected: FAIL (rota não existe).

- [ ] **Step 3: Implementar endpoint send**

Edit `backend/app/routers/conversations.py`. Adicionar:

```python
@router.post("/{conversation_id}/messages", response_model=MessageOut, status_code=201)
def send_message(
    conversation_id: int, payload: SendMessageIn,
    db: Session = Depends(get_db),
):
    conv = (
        db.query(Conversation)
        .filter_by(id=conversation_id, workspace_id=WORKSPACE_ID)
        .first()
    )
    if not conv:
        raise HTTPException(status_code=404, detail="conversation not found")

    try:
        adapter = get_provider(db, workspace_id=WORKSPACE_ID, provider=conv.provider)
    except (UnknownProviderError, ProviderNotConfigured) as exc:
        logger.warning(
            "conversations.send.provider_unavailable conv=%s reason=%s",
            conv.id, exc,
        )
        raise HTTPException(status_code=503, detail=f"provider unavailable: {exc}")

    idempotency_key = f"manual_send_conv_{conv.id}_{int(datetime.utcnow().timestamp()*1000)}"

    try:
        sent = adapter.send_text(
            to_phone=conv.phone, body=payload.body,
            idempotency_key=idempotency_key,
        )
    except Exception as exc:
        logger.exception("conversations.send.failed conv=%s", conv.id)
        raise HTTPException(status_code=502, detail=f"send failed: {exc}")

    msg = append_message(
        db, conversation_id=conv.id, direction="out",
        provider_message_id=sent.provider_message_id, body=payload.body,
        timestamp=sent.sent_at,
    )

    return MessageOut.model_validate(msg)
```

- [ ] **Step 4: Rodar — devem passar**

```bash
cd backend && venv/bin/pytest tests/test_conversations_router.py -v -k "send"
```

Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/conversations.py backend/tests/test_conversations_router.py
git commit -m "feat(inbox): POST /api/conversations/{id}/messages — send outbound via provider"
```

---

## Task 5: Backend — PATCH /api/conversations/{id}/read (mark all as read)

**Files:**
- Modify: `backend/app/routers/conversations.py`
- Modify: `backend/tests/test_conversations_router.py`

- [ ] **Step 1: Adicionar testes**

```python
def test_mark_read_zeros_unread(client, db):
    lead, conv = _seed_conversation(db, unread=5, msgs=[("in", "x")])
    r = client.patch(f"/api/conversations/{conv.id}/read")
    assert r.status_code == 200
    body = r.json()
    assert body["unread_count"] == 0

    db.refresh(conv)
    assert conv.unread_count == 0


def test_mark_read_not_found(client, db):
    r = client.patch("/api/conversations/9999/read")
    assert r.status_code == 404
```

- [ ] **Step 2: Rodar — deve falhar**

```bash
cd backend && venv/bin/pytest tests/test_conversations_router.py -v -k "mark_read"
```

Expected: FAIL.

- [ ] **Step 3: Implementar endpoint**

Edit `backend/app/routers/conversations.py`. Adicionar:

```python
@router.patch("/{conversation_id}/read", response_model=ConversationListItem)
def mark_read(conversation_id: int, db: Session = Depends(get_db)):
    conv = (
        db.query(Conversation)
        .filter_by(id=conversation_id, workspace_id=WORKSPACE_ID)
        .first()
    )
    if not conv:
        raise HTTPException(status_code=404, detail="conversation not found")
    conv.unread_count = 0
    db.commit()
    db.refresh(conv)

    lead = db.query(Lead).filter_by(id=conv.lead_id).first()
    return ConversationListItem(
        id=conv.id, lead_id=conv.lead_id,
        lead_nome=lead.nome if lead else None,
        lead_telefone=lead.telefone if lead else None,
        lead_status=lead.status if lead else None,
        provider=conv.provider, phone=conv.phone,
        last_message_at=conv.last_message_at,
        last_message_preview=_build_preview(conv, db),
        unread_count=conv.unread_count, status=conv.status,
    )
```

- [ ] **Step 4: Rodar — devem passar**

```bash
cd backend && venv/bin/pytest tests/test_conversations_router.py -v
```

Expected: TODOS PASS (~14 testes).

- [ ] **Step 5: Rodar suite completa do backend**

```bash
cd backend && venv/bin/pytest --deselect tests/test_outreach.py
```

Expected: 684 + 14 = ~698 PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/conversations.py backend/tests/test_conversations_router.py
git commit -m "feat(inbox): PATCH /api/conversations/{id}/read — zera unread"
```

---

## Task 6: Frontend — api wrapper + types

**Files:**
- Create: `frontend/src/lib/api-inbox.ts`

- [ ] **Step 1: Criar arquivo**

Create `frontend/src/lib/api-inbox.ts`:

```typescript
export type ConversationFilter = "all" | "unread" | "responded" | "won";

export interface Message {
  id: number;
  conversation_id: number;
  direction: "in" | "out";
  provider_message_id: string | null;
  body: string | null;
  media_url: string | null;
  status: string;
  sent_at: string | null;
  delivered_at: string | null;
  read_at: string | null;
  received_at: string | null;
  error: string | null;
  created_at: string;
}

export interface ConversationListItem {
  id: number;
  lead_id: number;
  lead_nome: string | null;
  lead_telefone: string | null;
  lead_status: string | null;
  provider: string;
  phone: string;
  last_message_at: string | null;
  last_message_preview: string | null;
  unread_count: number;
  status: string;
}

export interface ConversationDetail {
  id: number;
  workspace_id: number;
  lead_id: number;
  provider: string;
  provider_chat_id: string;
  phone: string;
  last_message_at: string | null;
  unread_count: number;
  status: string;
  created_at: string;
  messages: Message[];
}

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getSessionToken(): string | null {
  const cookies = document.cookie.split("; ");
  for (const c of cookies) {
    if (
      c.startsWith("__Secure-better-auth.session_data=") ||
      c.startsWith("better-auth.session_data=")
    ) {
      try {
        const val = decodeURIComponent(c.split("=").slice(1).join("="));
        const data = JSON.parse(atob(val));
        return data?.session?.session?.token || null;
      } catch {
        /* ignore */
      }
    }
  }
  return null;
}

async function fetchInbox<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getSessionToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API}${path}`, { ...init, headers, credentials: "include" });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`${res.status}: ${txt}`);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const listConversations = (params: { filter?: ConversationFilter; search?: string } = {}) => {
  const qs = new URLSearchParams();
  if (params.filter && params.filter !== "all") qs.set("filter", params.filter);
  if (params.search) qs.set("search", params.search);
  const tail = qs.toString() ? `?${qs.toString()}` : "";
  return fetchInbox<ConversationListItem[]>(`/api/conversations${tail}`);
};

export const getConversation = (id: number) =>
  fetchInbox<ConversationDetail>(`/api/conversations/${id}`);

export const sendMessage = (id: number, body: string) =>
  fetchInbox<Message>(`/api/conversations/${id}/messages`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });

export const markRead = (id: number) =>
  fetchInbox<ConversationListItem>(`/api/conversations/${id}/read`, {
    method: "PATCH",
  });
```

- [ ] **Step 2: Lint pra confirmar sem erros**

```bash
cd frontend && npm run lint -- --max-warnings=0
```

Expected: PASS (sem warnings novos).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/api-inbox.ts
git commit -m "feat(inbox): api wrappers pra conversations"
```

---

## Task 7: Frontend — MessageBubble + Composer (componentes base)

**Files:**
- Create: `frontend/src/components/inbox/MessageBubble.tsx`
- Create: `frontend/src/components/inbox/Composer.tsx`
- Create: `frontend/src/components/inbox/inbox.css`

- [ ] **Step 1: Criar `inbox.css`**

```css
/* Inbox layout */
.inbox-root {
  display: grid;
  grid-template-columns: 320px 1fr 320px;
  height: calc(100vh - 56px);
  gap: 0;
  background: var(--surface);
}

.inbox-list-col {
  border-right: 1px solid var(--border);
  overflow-y: auto;
}

.inbox-conv-col {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.inbox-rail-col {
  border-left: 1px solid var(--border);
  overflow-y: auto;
}

.inbox-conv-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Bubbles */
.msg-bubble {
  max-width: 70%;
  padding: 8px 12px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.4;
  word-wrap: break-word;
  position: relative;
}

.msg-bubble-in {
  background: var(--surface-2);
  align-self: flex-start;
  border-bottom-left-radius: 4px;
}

.msg-bubble-out {
  background: var(--accent);
  color: white;
  align-self: flex-end;
  border-bottom-right-radius: 4px;
}

.msg-bubble-meta {
  font-size: 11px;
  opacity: 0.7;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
  justify-content: flex-end;
}

.msg-status-failed { color: var(--terra); }
.msg-status-read { color: #88c0fb; }  /* azul leitura */

/* Composer */
.composer {
  border-top: 1px solid var(--border);
  padding: 12px 16px;
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.composer-textarea {
  flex: 1;
  min-height: 40px;
  max-height: 120px;
  resize: none;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text);
  font-family: inherit;
  font-size: 14px;
  line-height: 1.4;
  outline: none;
}

.composer-textarea:focus {
  border-color: var(--accent);
}

.composer-send {
  padding: 8px 16px;
  border-radius: 8px;
  border: none;
  background: var(--accent);
  color: white;
  font-weight: 600;
  cursor: pointer;
}

.composer-send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Empty state */
.inbox-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-muted);
  font-size: 14px;
}

/* Mobile */
@media (max-width: 768px) {
  .inbox-root {
    grid-template-columns: 1fr;
  }
  .inbox-list-col, .inbox-rail-col {
    display: none;
  }
  .inbox-root.show-list .inbox-list-col,
  .inbox-root.show-rail .inbox-rail-col {
    display: block;
    position: absolute;
    inset: 56px 0 0 0;
    background: var(--surface);
    z-index: 10;
  }
}
```

- [ ] **Step 2: Criar `MessageBubble.tsx`**

```tsx
import type { Message } from "@/lib/api-inbox";

interface Props {
  message: Message;
}

function fmtTime(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString("pt-BR", {
    hour: "2-digit", minute: "2-digit",
  });
}

function statusGlyph(message: Message): string {
  if (message.direction !== "out") return "";
  if (message.error) return "❌";
  if (message.read_at) return "✓✓";
  if (message.delivered_at) return "✓✓";
  if (message.sent_at) return "✓";
  return "…";
}

export function MessageBubble({ message }: Props) {
  const cls = `msg-bubble msg-bubble-${message.direction}`;
  const time = fmtTime(
    message.direction === "in" ? message.received_at : message.sent_at,
  );
  const glyph = statusGlyph(message);
  const isRead = !!message.read_at;
  const isFailed = !!message.error;

  return (
    <div className={cls}>
      <div>{message.body}</div>
      <div className="msg-bubble-meta">
        <span>{time}</span>
        {glyph && (
          <span
            className={
              isFailed
                ? "msg-status-failed"
                : isRead
                  ? "msg-status-read"
                  : ""
            }
            aria-label={
              isFailed
                ? "falha no envio"
                : isRead
                  ? "lida"
                  : "enviada"
            }
          >
            {glyph}
          </span>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Criar `Composer.tsx`**

```tsx
"use client";

import { useState, useRef, type KeyboardEvent } from "react";

interface Props {
  onSend: (body: string) => Promise<void>;
  disabled?: boolean;
}

export function Composer({ onSend, disabled }: Props) {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const ref = useRef<HTMLTextAreaElement>(null);

  async function handleSend() {
    const trimmed = text.trim();
    if (!trimmed || sending || disabled) return;
    setSending(true);
    try {
      await onSend(trimmed);
      setText("");
      ref.current?.focus();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Erro ao enviar");
    } finally {
      setSending(false);
    }
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="composer">
      <textarea
        ref={ref}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Mensagem..."
        className="composer-textarea"
        disabled={disabled || sending}
        rows={1}
      />
      <button
        type="button"
        className="composer-send"
        onClick={handleSend}
        disabled={disabled || sending || !text.trim()}
      >
        {sending ? "Enviando…" : "Enviar"}
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Lint**

```bash
cd frontend && npm run lint -- --max-warnings=0
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/inbox/
git commit -m "feat(inbox): MessageBubble + Composer + estilos"
```

---

## Task 8: Frontend — InboxList + InboxFilters

**Files:**
- Create: `frontend/src/components/inbox/InboxList.tsx`
- Create: `frontend/src/components/inbox/InboxFilters.tsx`

- [ ] **Step 1: Criar `InboxFilters.tsx`**

```tsx
"use client";

import type { ConversationFilter } from "@/lib/api-inbox";

interface Props {
  value: ConversationFilter;
  onChange: (next: ConversationFilter) => void;
  search: string;
  onSearchChange: (next: string) => void;
}

const FILTERS: { key: ConversationFilter; label: string }[] = [
  { key: "all", label: "Todas" },
  { key: "unread", label: "Não lidas" },
  { key: "responded", label: "Respondidas" },
  { key: "won", label: "Ganho" },
];

export function InboxFilters({ value, onChange, search, onSearchChange }: Props) {
  return (
    <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
      <input
        type="search"
        placeholder="Buscar nome ou telefone..."
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        style={{
          width: "100%", padding: "8px 12px", border: "1px solid var(--border)",
          borderRadius: 8, background: "var(--surface)", color: "var(--text)",
          fontSize: 14, outline: "none",
        }}
      />
      <div style={{ display: "flex", gap: 6, marginTop: 12, flexWrap: "wrap" }}>
        {FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            onClick={() => onChange(f.key)}
            style={{
              padding: "4px 10px", borderRadius: 12,
              border: "1px solid var(--border)",
              background: value === f.key ? "var(--accent)" : "var(--surface)",
              color: value === f.key ? "white" : "var(--text)",
              fontSize: 12, cursor: "pointer",
            }}
          >
            {f.label}
          </button>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Criar `InboxList.tsx`**

```tsx
"use client";

import Link from "next/link";
import type { ConversationListItem } from "@/lib/api-inbox";

interface Props {
  items: ConversationListItem[];
  selectedId: number | null;
}

function fmtRelative(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  const diff = Date.now() - date.getTime();
  const min = Math.floor(diff / 60000);
  if (min < 1) return "agora";
  if (min < 60) return `${min}min`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h}h`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${d}d`;
  return date.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

export function InboxList({ items, selectedId }: Props) {
  if (items.length === 0) {
    return (
      <div className="inbox-empty" style={{ padding: 24 }}>
        Nenhuma conversa ainda.
      </div>
    );
  }
  return (
    <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
      {items.map((c) => {
        const active = c.id === selectedId;
        return (
          <li key={c.id}>
            <Link
              href={`/app/inbox/${c.id}`}
              style={{
                display: "block",
                padding: "12px 16px",
                borderBottom: "1px solid var(--border)",
                background: active ? "var(--surface-2)" : "transparent",
                textDecoration: "none",
                color: "inherit",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <strong style={{ fontSize: 14 }}>
                  {c.lead_nome || c.phone}
                </strong>
                <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  {fmtRelative(c.last_message_at)}
                </span>
              </div>
              <div style={{
                fontSize: 13, color: "var(--text-muted)",
                overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
              }}>
                {c.last_message_preview || "—"}
              </div>
              {c.unread_count > 0 && (
                <span style={{
                  display: "inline-block", marginTop: 4,
                  background: "var(--accent)", color: "white",
                  padding: "1px 8px", borderRadius: 12, fontSize: 11, fontWeight: 600,
                }}>
                  {c.unread_count}
                </span>
              )}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
```

- [ ] **Step 3: Lint**

```bash
cd frontend && npm run lint -- --max-warnings=0
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/inbox/InboxList.tsx frontend/src/components/inbox/InboxFilters.tsx
git commit -m "feat(inbox): InboxList + InboxFilters"
```

---

## Task 9: Frontend — ConversationView + ConversationRail

**Files:**
- Create: `frontend/src/components/inbox/ConversationView.tsx`
- Create: `frontend/src/components/inbox/ConversationRail.tsx`

- [ ] **Step 1: Criar `ConversationView.tsx`**

```tsx
"use client";

import { useEffect, useRef } from "react";
import { MessageBubble } from "./MessageBubble";
import { Composer } from "./Composer";
import type { ConversationDetail } from "@/lib/api-inbox";

interface Props {
  conversation: ConversationDetail;
  onSend: (body: string) => Promise<void>;
}

export function ConversationView({ conversation, onSend }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [conversation.messages.length]);

  return (
    <>
      <header style={{
        padding: "12px 16px", borderBottom: "1px solid var(--border)",
        display: "flex", justifyContent: "space-between", alignItems: "center",
      }}>
        <div>
          <strong>{conversation.phone}</strong>
          <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
            {conversation.provider} · {conversation.status}
          </div>
        </div>
      </header>
      <div className="inbox-conv-messages" ref={scrollRef}>
        {conversation.messages.length === 0 ? (
          <div className="inbox-empty">Nenhuma mensagem ainda.</div>
        ) : (
          conversation.messages.map((m) => (
            <MessageBubble key={m.id} message={m} />
          ))
        )}
      </div>
      <Composer onSend={onSend} />
    </>
  );
}
```

- [ ] **Step 2: Criar `ConversationRail.tsx`**

```tsx
"use client";

import Link from "next/link";
import type { ConversationDetail } from "@/lib/api-inbox";

interface Props {
  conversation: ConversationDetail;
}

export function ConversationRail({ conversation }: Props) {
  return (
    <div style={{ padding: 16 }}>
      <section style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: 12, color: "var(--text-muted)", textTransform: "uppercase",
                     letterSpacing: 0.5, marginBottom: 8 }}>
          Lead
        </h3>
        <div style={{ fontSize: 14 }}>
          Telefone: <strong>{conversation.phone}</strong>
        </div>
        <Link
          href={`/app/leads?selected=${conversation.lead_id}`}
          style={{
            display: "inline-block", marginTop: 12,
            padding: "6px 12px", borderRadius: 8,
            background: "var(--accent)", color: "white",
            textDecoration: "none", fontSize: 13,
          }}
        >
          Abrir Lead →
        </Link>
      </section>
      <section>
        <h3 style={{ fontSize: 12, color: "var(--text-muted)", textTransform: "uppercase",
                     letterSpacing: 0.5, marginBottom: 8 }}>
          Conversa
        </h3>
        <div style={{ fontSize: 13, color: "var(--text-muted)" }}>
          {conversation.messages.length} mensagens<br />
          Criada em {new Date(conversation.created_at).toLocaleString("pt-BR")}
        </div>
      </section>
    </div>
  );
}
```

- [ ] **Step 3: Lint**

```bash
cd frontend && npm run lint -- --max-warnings=0
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/inbox/ConversationView.tsx frontend/src/components/inbox/ConversationRail.tsx
git commit -m "feat(inbox): ConversationView + ConversationRail"
```

---

## Task 10: Frontend — páginas `/app/inbox` e `/app/inbox/[id]`

**Files:**
- Create: `frontend/src/app/app/inbox/page.tsx`
- Create: `frontend/src/app/app/inbox/[id]/page.tsx`

- [ ] **Step 1: Criar `/app/inbox/page.tsx`**

```tsx
"use client";

import { useState, useEffect } from "react";
import useSWR from "swr";
import { listConversations, type ConversationFilter } from "@/lib/api-inbox";
import { InboxList } from "@/components/inbox/InboxList";
import { InboxFilters } from "@/components/inbox/InboxFilters";
import "@/components/inbox/inbox.css";

export default function InboxPage() {
  const [filter, setFilter] = useState<ConversationFilter>("all");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  const { data, error } = useSWR(
    ["conversations-list", filter, debouncedSearch],
    () => listConversations({ filter, search: debouncedSearch }),
    { refreshInterval: 5000 },
  );

  return (
    <div className="inbox-root">
      <div className="inbox-list-col">
        <InboxFilters
          value={filter} onChange={setFilter}
          search={search} onSearchChange={setSearch}
        />
        {error && <div style={{ padding: 16, color: "var(--terra)" }}>Erro: {String(error)}</div>}
        {data && <InboxList items={data} selectedId={null} />}
      </div>
      <div className="inbox-conv-col">
        <div className="inbox-empty">
          Selecione uma conversa pra ver mensagens.
        </div>
      </div>
      <div className="inbox-rail-col" />
    </div>
  );
}
```

- [ ] **Step 2: Criar `/app/inbox/[id]/page.tsx`**

```tsx
"use client";

import { useState, useEffect, use } from "react";
import { useRouter } from "next/navigation";
import useSWR, { mutate } from "swr";
import {
  listConversations, getConversation, sendMessage, markRead,
  type ConversationFilter,
} from "@/lib/api-inbox";
import { InboxList } from "@/components/inbox/InboxList";
import { InboxFilters } from "@/components/inbox/InboxFilters";
import { ConversationView } from "@/components/inbox/ConversationView";
import { ConversationRail } from "@/components/inbox/ConversationRail";
import "@/components/inbox/inbox.css";

export default function InboxDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const conversationId = Number(id);
  const router = useRouter();

  const [filter, setFilter] = useState<ConversationFilter>("all");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  const { data: list } = useSWR(
    ["conversations-list", filter, debouncedSearch],
    () => listConversations({ filter, search: debouncedSearch }),
    { refreshInterval: 5000 },
  );

  const { data: conv, error: convError } = useSWR(
    conversationId ? ["conversation", conversationId] : null,
    () => getConversation(conversationId),
    { refreshInterval: 5000 },
  );

  // Auto-mark-read on open + unread badge present
  useEffect(() => {
    if (conv && conv.unread_count > 0) {
      markRead(conversationId).then(() => {
        mutate(["conversations-list", filter, debouncedSearch]);
      });
    }
  }, [conv?.id, conv?.unread_count, conversationId, filter, debouncedSearch]);

  async function handleSend(body: string) {
    await sendMessage(conversationId, body);
    mutate(["conversation", conversationId]);
    mutate(["conversations-list", filter, debouncedSearch]);
  }

  if (convError) {
    if (String(convError).includes("404")) {
      router.replace("/app/inbox");
      return null;
    }
  }

  return (
    <div className="inbox-root">
      <div className="inbox-list-col">
        <InboxFilters
          value={filter} onChange={setFilter}
          search={search} onSearchChange={setSearch}
        />
        {list && <InboxList items={list} selectedId={conversationId} />}
      </div>
      <div className="inbox-conv-col">
        {conv ? (
          <ConversationView conversation={conv} onSend={handleSend} />
        ) : (
          <div className="inbox-empty">Carregando…</div>
        )}
      </div>
      <div className="inbox-rail-col">
        {conv && <ConversationRail conversation={conv} />}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Lint**

```bash
cd frontend && npm run lint -- --max-warnings=0
```

Expected: PASS.

- [ ] **Step 4: Validar manualmente no browser**

```bash
cd frontend && npm run dev
```

Em http://localhost:3000/app/inbox:
- Lista carrega (vazia se sem conversas)
- Filtros mudam URL params (não muda — só state)
- Search filtra após 300ms debounce
- Clicar conversa → /app/inbox/[id] com 3 colunas
- Composer envia → mock provider responde (Evolution real apontando pra dev)

Documentar limitações encontradas em comentário no PR.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/app/inbox/
git commit -m "feat(inbox): páginas /app/inbox + /app/inbox/[id]"
```

---

## Task 11: Frontend — sidebar nav badge unread

**Files:**
- Modify: `frontend/src/components/app-sidebar.tsx`

- [ ] **Step 1: Adicionar "Inbox" ao NAV_ITEMS**

Edit `frontend/src/components/app-sidebar.tsx`, linha 12-18.

Antes:
```typescript
const NAV_ITEMS: { key: string; icon: IconName; label: string; href: string }[] = [
  { key: "home", icon: "home", label: "Dashboard", href: "/app" },
  { key: "board", icon: "board", label: "Pipeline", href: "/app/pipeline" },
  { key: "leads", icon: "lead", label: "Leads", href: "/app/leads" },
  { key: "job", icon: "job", label: "Jobs", href: "/app/jobs" },
];
```

Depois (adicionar item inbox entre board e leads):
```typescript
const NAV_ITEMS: { key: string; icon: IconName; label: string; href: string }[] = [
  { key: "home", icon: "home", label: "Dashboard", href: "/app" },
  { key: "board", icon: "board", label: "Pipeline", href: "/app/pipeline" },
  { key: "inbox", icon: "message", label: "Inbox", href: "/app/inbox" },
  { key: "leads", icon: "lead", label: "Leads", href: "/app/leads" },
  { key: "job", icon: "job", label: "Jobs", href: "/app/jobs" },
];
```

> Se `IconName` não tem `"message"`: usar `"chat"` ou outro existente. Verificar arquivos `frontend/src/components/ui/Icon.tsx` pra confirmar.

- [ ] **Step 2: Verificar Icon disponível**

```bash
grep -n "message\|chat\|inbox" frontend/src/components/ui/Icon.tsx
```

Se nenhum desses: usar `"job"` temporariamente e fazer issue futura pra adicionar ícone proper.

- [ ] **Step 3: Adicionar badge de total unread**

Edit `app-sidebar.tsx`. Após a função `RunningJobsBadge` (linha ~58), adicionar:

```typescript
function InboxUnreadBadge() {
  const [count, setCount] = useState(0);
  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const { listConversations } = await import("@/lib/api-inbox");
        const items = await listConversations({ filter: "unread" });
        if (!cancelled) {
          const total = items.reduce((sum, c) => sum + (c.unread_count || 0), 0);
          setCount(total);
        }
      } catch {
        // ignore
      }
    }
    poll();
    const id = setInterval(poll, 10000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);
  if (count === 0) return null;
  return <span className="app-sidebar-btn-badge">{count > 99 ? "99+" : count}</span>;
}
```

Wire na render do nav item `inbox` (procurar o `.map` que renderiza `NAV_ITEMS`):

```tsx
{NAV_ITEMS.map((it) => (
  <Link
    key={it.key}
    href={it.href}
    className={`app-sidebar-btn ${isActive(it.href) ? "active" : ""}`}
    aria-label={it.label}
  >
    <Icon name={it.icon} />
    <span className="app-sidebar-btn-label">{it.label}</span>
    {it.key === "job" && <RunningJobsBadge />}
    {it.key === "inbox" && <InboxUnreadBadge />}
  </Link>
))}
```

- [ ] **Step 4: Lint + dev verify**

```bash
cd frontend && npm run lint -- --max-warnings=0
```

Expected: PASS.

Validar manualmente: badge aparece na sidebar quando há conversation com `unread_count > 0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/app-sidebar.tsx
git commit -m "feat(inbox): item nav Inbox + badge unread polling"
```

---

## Task 12: Suite final + push

- [ ] **Step 1: Rodar backend suite completa**

```bash
cd backend && venv/bin/pytest --deselect tests/test_outreach.py
```

Expected: ~698 PASS.

- [ ] **Step 2: Lint frontend**

```bash
cd frontend && npm run lint -- --max-warnings=0
```

Expected: PASS.

- [ ] **Step 3: Smoke manual no browser**

- `/app/inbox` carrega
- Sidebar nav mostra Inbox
- Conversa sem msgs renderiza empty
- Conversa com msgs: bubbles + composer
- Send manda msg (com Evolution configurada — depende de P5 mas funciona via SQL direto)
- Filtros mudam lista
- Search debounce 300ms

- [ ] **Step 4: Push da branch**

```bash
git push -u origin feat/whatsapp-inbox-p4-frontend
```

- [ ] **Step 5: Abrir PR**

```bash
gh pr create --base main --title "feat(inbox): P4 — UI /app/inbox + endpoints conversations" --body "$(cat <<'EOF'
## Summary

**Backend** (4 endpoints novos em `/api/conversations`):
- `GET /api/conversations` — list com filter (all/unread/responded/won) + search nome/telefone + preview last msg
- `GET /api/conversations/{id}` — detail com messages ordenadas cronologicamente
- `POST /api/conversations/{id}/messages` — send outbound via provider P1 + grava ConversationMessage idempotente
- `PATCH /api/conversations/{id}/read` — zera unread_count

**Frontend** (`/app/inbox`):
- 3 colunas: lista + conversation view + rail
- Polling SWR 5s lista + 5s detail
- Composer com Enter envia, Shift+Enter quebra
- Auto-mark-read ao abrir conversa
- Sidebar nav novo item "Inbox" com badge total unread (polling 10s)

## Test Plan

- [x] 14 testes backend novos (list filter/search/preview, detail, send mocked Evolution, mark-read)
- [x] Suite full backend: 698 PASS
- [x] Frontend lint: 0 warnings
- [ ] **Manual:** Evolution real apontando dev, enviar inbound, abrir UI, ver msg aparecer, responder via Composer
EOF
)"
```

- [ ] **Step 6: Verificar mergeability**

```bash
gh pr view --json mergeable,mergeStateStatus
```

Expected: `MERGEABLE`, `CLEAN`.

---

## Self-Review

**Spec coverage** (vs `2026-05-16-whatsapp-inbox-design.md` §5):
- ✅ Layout 3 colunas → Task 10
- ✅ InboxList virtualized — **parcial**: implementação base sem virtualization (lista pequena no MVP). Adicionar `react-window` se passar de 200 conversas
- ✅ ConversationView bubbles in/out + status ✓✓ — Task 7, 9
- ✅ Composer Enter envia/Shift quebra — Task 7
- ✅ ConversationRail reusa partes do Lead App — **simplificado**: rail próprio sem reuso direto do LaRail (Lead App tem dependências do hook `useLeadApp`). Mostra Lead nome/phone/link.
- ✅ InboxFilters chips — Task 8
- ✅ Polling SWR 5s — Task 10
- ✅ Sidebar nav com badge — Task 11

**Não coberto neste plan** (próximos PRs/v2):
- Virtualization (`react-window`) — adicionar quando lista > 200
- Reuso LaRail completo com score/diagnóstico — depende de refactor do hook useLeadApp pra aceitar lead_id direto
- Server-sent events em vez de polling
- Upload de mídia no composer
- Threading de respostas (visual indicator de qual outbound foi respondida)

**Placeholder scan:** nenhum step usa "TBD" / "appropriate error handling". Todos têm código completo.

**Type consistency:**
- `Message`, `ConversationListItem`, `ConversationDetail` definidos Task 6, usados Tasks 7-11
- `sendMessage`, `markRead`, `listConversations`, `getConversation` — assinaturas idênticas em api wrapper e components
- Backend `ConversationOut`, `ConversationListItem`, `MessageOut` consistentes entre router e schemas
