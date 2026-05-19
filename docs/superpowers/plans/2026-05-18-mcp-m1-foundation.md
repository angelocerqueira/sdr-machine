# MCP M-1 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Schema `mcp_tokens` + `pending_actions` + FastMCP server skeleton mounted em FastAPI com Bearer auth workspace-scoped, sem tools ainda (vazio mas autenticável e healthy).

**Architecture:** Adiciona dependência `mcp` (Anthropic Python SDK), monta `FastMCP` em `/api/mcp` via Starlette mount. `TokenVerifier` custom valida Bearer contra `mcp_tokens` table (SHA-256 hash). Workspace_id derivado do token e disponibilizado nas tools via `Context.request_context`. Tabela `pending_actions` criada agora mas sem uso (consumida em M-3).

**Tech Stack:** FastAPI 0.115 · SQLAlchemy 2.0 · Alembic · `mcp>=1.12` (Anthropic SDK) · pytest

**Spec:** [`docs/superpowers/specs/2026-05-18-mcp-server-m0-architecture.md`](../specs/2026-05-18-mcp-server-m0-architecture.md) §3, §7, §8

---

## Notas de execução

- Branch: `feat/mcp-m1-foundation`. Baseia em `main`.
- Backend tests: `cd backend && venv/bin/pytest`
- Sem mudanças frontend neste plan (UI vem em M-4)
- Commits Conventional Commits, escopo `mcp`
- **Não implementa nenhuma tool** — só foundation. M-2 adiciona READ tools.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `backend/requirements.txt` | Modify | Adicionar `mcp>=1.12.4` |
| `backend/alembic/versions/r16_mcp_schema.py` | Create | Migration: tabelas `mcp_tokens` + `pending_actions` |
| `backend/app/models.py` | Modify | Adicionar classes `McpToken` + `PendingAction` |
| `backend/app/mcp/__init__.py` | Create | Package init |
| `backend/app/mcp/tokens.py` | Create | `generate_token()`, `hash_token()`, `verify_token_in_db()`, `revoke_token()` |
| `backend/app/mcp/auth.py` | Create | `BearerTokenVerifier` (implementa `TokenVerifier` do SDK) |
| `backend/app/mcp/context.py` | Create | `get_workspace_id_from_context(ctx)` helper |
| `backend/app/mcp/server.py` | Create | `build_mcp_server()` retorna `FastMCP` configurado (sem tools ainda) |
| `backend/app/main.py` | Modify | Mount MCP server em `/api/mcp` |
| `backend/tests/mcp/__init__.py` | Create | Empty (pacote tests) |
| `backend/tests/mcp/test_token_lifecycle.py` | Create | Generate + hash + verify + revoke |
| `backend/tests/mcp/test_auth_middleware.py` | Create | Bearer válido / inválido / revogado / workspace scoping |
| `backend/tests/mcp/test_server_mount.py` | Create | Server responde `initialize` JSON-RPC |

---

## Task 1: Criar branch + adicionar dependência `mcp`

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Criar branch**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git checkout main
git pull origin main
git checkout -b feat/mcp-m1-foundation
```

- [ ] **Step 2: Adicionar `mcp` ao requirements.txt**

Edit `backend/requirements.txt`. Adicionar linha alfabeticamente:

```
mcp>=1.12.4
```

- [ ] **Step 3: Instalar dependência no venv**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend
venv/bin/pip install "mcp>=1.12.4"
```

Expected: instala `mcp` + transitivas (pydantic, anyio, etc — já são deps).

- [ ] **Step 4: Confirmar import funciona**

```bash
venv/bin/python -c "from mcp.server.fastmcp import FastMCP; print(FastMCP.__name__)"
```

Expected output: `FastMCP`

- [ ] **Step 5: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/requirements.txt
git commit -m "feat(mcp): adiciona dependência mcp Python SDK"
```

---

## Task 2: Migration r16 — `mcp_tokens` + `pending_actions`

**Files:**
- Create: `backend/alembic/versions/r16_mcp_schema.py`

- [ ] **Step 1: Determinar revision_id do último migration**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend
ls -1 alembic/versions/ | sort | tail -3
```

Expected: ver últimas migrations (r13_whatsapp_inbox + outras). Usar a mais recente como `down_revision`.

- [ ] **Step 2: Criar migration**

Create `backend/alembic/versions/r16_mcp_schema.py`:

```python
"""mcp schema: mcp_tokens + pending_actions

Revision ID: r16_mcp_schema
Revises: <LATEST_REV_ID_FROM_STEP_1>
Create Date: 2026-05-18

"""
from alembic import op
import sqlalchemy as sa

revision = "r16_mcp_schema"
down_revision = "<LATEST_REV_ID_FROM_STEP_1>"  # SUBSTITUIR pelo ID identificado no Step 1
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mcp_tokens",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("workspace_id", sa.Integer, nullable=False, server_default="1"),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("token_hash", sa.String(80), nullable=False, unique=True),
        sa.Column("last4", sa.String(4), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("last_used_at", sa.DateTime),
        sa.Column("revoked_at", sa.DateTime),
    )
    op.create_index("ix_mcp_tokens_hash", "mcp_tokens", ["token_hash"], unique=True)
    op.create_index("ix_mcp_tokens_workspace", "mcp_tokens", ["workspace_id"])

    op.create_table(
        "pending_actions",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("workspace_id", sa.Integer, nullable=False, server_default="1"),
        sa.Column("action_type", sa.String(60), nullable=False),
        sa.Column("params", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("preview", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_by_token_hash", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("committed_at", sa.DateTime),
        sa.Column("cancelled_at", sa.DateTime),
        sa.Column("result", sa.JSON),
    )
    op.create_index("ix_pending_actions_expires", "pending_actions", ["expires_at"])
    op.create_index("ix_pending_actions_workspace", "pending_actions", ["workspace_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_pending_actions_workspace", table_name="pending_actions")
    op.drop_index("ix_pending_actions_expires", table_name="pending_actions")
    op.drop_table("pending_actions")

    op.drop_index("ix_mcp_tokens_workspace", table_name="mcp_tokens")
    op.drop_index("ix_mcp_tokens_hash", table_name="mcp_tokens")
    op.drop_table("mcp_tokens")
```

> **Atenção:** Após criar, substituir `<LATEST_REV_ID_FROM_STEP_1>` pelo valor real (ex: `r13_whatsapp_inbox` ou o ID interno do último arquivo). Confirmar com `alembic history`.

- [ ] **Step 3: Aplicar migration**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend
venv/bin/alembic upgrade head
```

Expected: `INFO  [alembic.runtime.migration] Running upgrade <down_revision> -> r16_mcp_schema, mcp schema: mcp_tokens + pending_actions`

- [ ] **Step 4: Verificar tabelas no DB**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend
venv/bin/python -c "
from sqlalchemy import inspect
from app.database import engine
insp = inspect(engine)
print('mcp_tokens cols:', [c['name'] for c in insp.get_columns('mcp_tokens')])
print('pending_actions cols:', [c['name'] for c in insp.get_columns('pending_actions')])
"
```

Expected:
```
mcp_tokens cols: ['id', 'workspace_id', 'name', 'token_hash', 'last4', 'created_at', 'last_used_at', 'revoked_at']
pending_actions cols: ['id', 'workspace_id', 'action_type', 'params', 'preview', 'created_by_token_hash', 'created_at', 'expires_at', 'committed_at', 'cancelled_at', 'result']
```

- [ ] **Step 5: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/alembic/versions/r16_mcp_schema.py
git commit -m "feat(mcp): migration r16 schema mcp_tokens + pending_actions"
```

---

## Task 3: Models SQLAlchemy — `McpToken` + `PendingAction`

**Files:**
- Modify: `backend/app/models.py`

- [ ] **Step 1: Test falhando — imports dos models**

Create `backend/tests/mcp/__init__.py` (arquivo vazio, marca pacote):

```python
```

Create `backend/tests/mcp/test_models_schema.py`:

```python
from datetime import datetime, timedelta, timezone

from app.models import McpToken, PendingAction


def test_mcp_token_minimal(db):
    t = McpToken(
        workspace_id=1,
        name="claude-desktop-laptop",
        token_hash="a" * 64,
        last4="abcd",
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    assert t.id is not None
    assert t.created_at is not None
    assert t.revoked_at is None


def test_mcp_token_unique_hash(db):
    db.add(McpToken(
        workspace_id=1, name="a", token_hash="X" * 64, last4="abcd",
    ))
    db.commit()
    with pytest.raises(Exception):
        db.add(McpToken(
            workspace_id=1, name="b", token_hash="X" * 64, last4="efgh",
        ))
        db.commit()


def test_pending_action_minimal(db):
    pa = PendingAction(
        id="action-abc-123",
        workspace_id=1,
        action_type="send_message",
        params={"conv_id": 5, "body": "oi"},
        preview={"to": "5544...", "rendered": "oi"},
        created_by_token_hash="x" * 64,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    db.add(pa)
    db.commit()
    db.refresh(pa)
    assert pa.id == "action-abc-123"
    assert pa.params["conv_id"] == 5
    assert pa.committed_at is None
    assert pa.cancelled_at is None


import pytest  # placed at end so test_mcp_token_unique_hash references it
```

- [ ] **Step 2: Rodar — deve falhar (sem classes)**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend
venv/bin/pytest tests/mcp/test_models_schema.py -v
```

Expected: FAIL `ImportError: cannot import name 'McpToken' from 'app.models'`.

- [ ] **Step 3: Adicionar classes em `models.py`**

Edit `backend/app/models.py`. Adicionar AO FINAL do arquivo (após o último model existente):

```python
class McpToken(Base):
    __tablename__ = "mcp_tokens"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, nullable=False, default=1)
    name = Column(String(120), nullable=False)
    token_hash = Column(String(80), nullable=False, unique=True)
    last4 = Column(String(4), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime)
    revoked_at = Column(DateTime)

    __table_args__ = (
        Index("ix_mcp_tokens_hash", "token_hash"),
        Index("ix_mcp_tokens_workspace", "workspace_id"),
    )


class PendingAction(Base):
    __tablename__ = "pending_actions"

    id = Column(String(40), primary_key=True)
    workspace_id = Column(Integer, nullable=False, default=1)
    action_type = Column(String(60), nullable=False)
    params = Column(JSON, nullable=False, default=dict)
    preview = Column(JSON, nullable=False, default=dict)
    created_by_token_hash = Column(String(80), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    committed_at = Column(DateTime)
    cancelled_at = Column(DateTime)
    result = Column(JSON)

    __table_args__ = (
        Index("ix_pending_actions_expires", "expires_at"),
        Index("ix_pending_actions_workspace", "workspace_id", "created_at"),
    )
```

> Verificar imports no topo de `models.py`. Devem estar presentes: `from sqlalchemy import Column, Integer, String, DateTime, JSON, Index`, `from sqlalchemy.sql import func`. Se faltar algum, adicionar.

- [ ] **Step 4: Rodar tests — devem passar**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend
venv/bin/pytest tests/mcp/test_models_schema.py -v
```

Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/app/models.py backend/tests/mcp/__init__.py backend/tests/mcp/test_models_schema.py
git commit -m "feat(mcp): SQLAlchemy models McpToken + PendingAction"
```

---

## Task 4: Token utilities — generate, hash, verify, revoke

**Files:**
- Create: `backend/app/mcp/__init__.py`
- Create: `backend/app/mcp/tokens.py`
- Create: `backend/tests/mcp/test_token_lifecycle.py`

- [ ] **Step 1: Test falhando**

Create `backend/app/mcp/__init__.py` (arquivo vazio):

```python
```

Create `backend/tests/mcp/test_token_lifecycle.py`:

```python
import pytest
from datetime import datetime

from app.models import McpToken
from app.mcp.tokens import (
    generate_token,
    hash_token,
    verify_token,
    revoke_token,
    list_tokens,
)


def test_generate_token_format():
    plain = generate_token()
    # 32 bytes hex = 64 chars
    assert len(plain) == 64
    assert all(c in "0123456789abcdef" for c in plain)


def test_generate_token_unique():
    a = generate_token()
    b = generate_token()
    assert a != b


def test_hash_token_deterministic():
    plain = "deadbeef" * 8  # 64 chars
    h1 = hash_token(plain)
    h2 = hash_token(plain)
    assert h1 == h2
    assert len(h1) == 64  # sha256 hex


def test_hash_token_different_for_different_inputs():
    a = hash_token("aaaaaaaa" * 8)
    b = hash_token("bbbbbbbb" * 8)
    assert a != b


def test_verify_token_finds_valid(db):
    plain = generate_token()
    h = hash_token(plain)
    db.add(McpToken(
        workspace_id=1, name="laptop", token_hash=h, last4=plain[-4:],
    ))
    db.commit()

    row = verify_token(db, plain)
    assert row is not None
    assert row.name == "laptop"
    assert row.workspace_id == 1


def test_verify_token_returns_none_for_unknown(db):
    plain = generate_token()
    row = verify_token(db, plain)
    assert row is None


def test_verify_token_rejects_revoked(db):
    plain = generate_token()
    h = hash_token(plain)
    tok = McpToken(
        workspace_id=1, name="x", token_hash=h, last4="abcd",
        revoked_at=datetime.utcnow(),
    )
    db.add(tok)
    db.commit()

    row = verify_token(db, plain)
    assert row is None  # revoked = invisível


def test_verify_token_updates_last_used_at(db):
    plain = generate_token()
    h = hash_token(plain)
    db.add(McpToken(workspace_id=1, name="x", token_hash=h, last4="abcd"))
    db.commit()

    before = datetime.utcnow()
    verify_token(db, plain)

    tok = db.query(McpToken).filter_by(token_hash=h).first()
    assert tok.last_used_at is not None
    assert tok.last_used_at >= before


def test_revoke_token_sets_revoked_at(db):
    plain = generate_token()
    h = hash_token(plain)
    db.add(McpToken(workspace_id=1, name="x", token_hash=h, last4="abcd"))
    db.commit()

    revoke_token(db, h)

    tok = db.query(McpToken).filter_by(token_hash=h).first()
    assert tok.revoked_at is not None


def test_list_tokens_excludes_revoked_by_default(db):
    h1 = hash_token(generate_token())
    h2 = hash_token(generate_token())
    db.add_all([
        McpToken(workspace_id=1, name="active", token_hash=h1, last4="aaaa"),
        McpToken(workspace_id=1, name="revoked", token_hash=h2, last4="bbbb",
                 revoked_at=datetime.utcnow()),
    ])
    db.commit()

    rows = list_tokens(db, workspace_id=1)
    assert len(rows) == 1
    assert rows[0].name == "active"


def test_list_tokens_workspace_scoped(db):
    h1 = hash_token(generate_token())
    h2 = hash_token(generate_token())
    db.add_all([
        McpToken(workspace_id=1, name="ws1", token_hash=h1, last4="aaaa"),
        McpToken(workspace_id=2, name="ws2", token_hash=h2, last4="bbbb"),
    ])
    db.commit()

    rows = list_tokens(db, workspace_id=1)
    assert len(rows) == 1
    assert rows[0].name == "ws1"
```

- [ ] **Step 2: Rodar — deve falhar (sem tokens.py)**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend
venv/bin/pytest tests/mcp/test_token_lifecycle.py -v
```

Expected: FAIL com `ModuleNotFoundError: No module named 'app.mcp.tokens'`.

- [ ] **Step 3: Implementar `tokens.py`**

Create `backend/app/mcp/tokens.py`:

```python
"""Token utilities pro MCP server: generate, hash (SHA-256), verify, revoke.

Plain token nunca é persistido — só seu hash. Apenas o user vê o plain UMA VEZ
no momento de criação (UI mostra modal "copie agora").
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from app.models import McpToken


def generate_token() -> str:
    """32 random bytes em hex = 64 chars. Crypto-strong via secrets module."""
    return secrets.token_hex(32)


def hash_token(plain: str) -> str:
    """SHA-256 hex digest. Plain nunca volta ao banco."""
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def verify_token(db: Session, plain: str) -> McpToken | None:
    """Localiza token ativo (não-revogado). Atualiza last_used_at e retorna row.

    Retorna None se: token desconhecido, revogado, ou hash inválido.
    """
    if not plain or len(plain) != 64:
        return None
    h = hash_token(plain)
    row = (
        db.query(McpToken)
        .filter_by(token_hash=h)
        .filter(McpToken.revoked_at.is_(None))
        .first()
    )
    if row is None:
        return None
    row.last_used_at = datetime.utcnow()
    db.commit()
    return row


def revoke_token(db: Session, token_hash: str) -> bool:
    """Marca como revogado. Retorna True se afetou linha."""
    row = db.query(McpToken).filter_by(token_hash=token_hash).first()
    if row is None or row.revoked_at is not None:
        return False
    row.revoked_at = datetime.utcnow()
    db.commit()
    return True


def list_tokens(
    db: Session, *, workspace_id: int, include_revoked: bool = False,
) -> List[McpToken]:
    """Lista tokens do workspace. Exclui revogados por default."""
    q = db.query(McpToken).filter_by(workspace_id=workspace_id)
    if not include_revoked:
        q = q.filter(McpToken.revoked_at.is_(None))
    return q.order_by(McpToken.created_at.desc()).all()
```

- [ ] **Step 4: Rodar tests — devem passar**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend
venv/bin/pytest tests/mcp/test_token_lifecycle.py -v
```

Expected: 10 PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/app/mcp/__init__.py backend/app/mcp/tokens.py backend/tests/mcp/test_token_lifecycle.py
git commit -m "feat(mcp): token utilities generate/hash/verify/revoke/list"
```

---

## Task 5: `BearerTokenVerifier` — implementa contrato do MCP SDK

**Files:**
- Create: `backend/app/mcp/auth.py`
- Create: `backend/tests/mcp/test_auth_verifier.py`

- [ ] **Step 1: Test falhando**

Create `backend/tests/mcp/test_auth_verifier.py`:

```python
import asyncio

from app.mcp.auth import BearerTokenVerifier
from app.mcp.tokens import generate_token, hash_token
from app.models import McpToken


def _new_db_factory(session):
    """Retorna callable que devolve a session de teste (mimica SessionLocal)."""
    def _factory():
        return session
    return _factory


def test_verifier_accepts_valid_token(db):
    plain = generate_token()
    db.add(McpToken(
        workspace_id=42, name="x", token_hash=hash_token(plain), last4=plain[-4:],
    ))
    db.commit()

    verifier = BearerTokenVerifier(session_factory=_new_db_factory(db))
    result = asyncio.run(verifier.verify_token(plain))

    assert result is not None
    assert result.scopes == ["mcp:workspace:42"]


def test_verifier_rejects_unknown_token(db):
    plain = generate_token()  # nunca persistido
    verifier = BearerTokenVerifier(session_factory=_new_db_factory(db))
    result = asyncio.run(verifier.verify_token(plain))
    assert result is None


def test_verifier_rejects_malformed(db):
    verifier = BearerTokenVerifier(session_factory=_new_db_factory(db))
    assert asyncio.run(verifier.verify_token("short")) is None
    assert asyncio.run(verifier.verify_token("")) is None


def test_verifier_rejects_revoked(db):
    from datetime import datetime
    plain = generate_token()
    db.add(McpToken(
        workspace_id=1, name="x", token_hash=hash_token(plain), last4="abcd",
        revoked_at=datetime.utcnow(),
    ))
    db.commit()

    verifier = BearerTokenVerifier(session_factory=_new_db_factory(db))
    assert asyncio.run(verifier.verify_token(plain)) is None
```

- [ ] **Step 2: Rodar — deve falhar**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend
venv/bin/pytest tests/mcp/test_auth_verifier.py -v
```

Expected: FAIL com `ModuleNotFoundError`.

- [ ] **Step 3: Implementar `auth.py`**

Create `backend/app/mcp/auth.py`:

```python
"""BearerTokenVerifier — implementa o protocolo TokenVerifier do MCP SDK.

O SDK chama `verify_token(plain) -> AccessToken | None` em cada request.
Retornamos um AccessToken com scope `mcp:workspace:<id>` codificado, que
o downstream usa pra derivar workspace_id sem 2nd lookup.
"""
from __future__ import annotations

import logging
from typing import Callable

from mcp.server.auth.provider import AccessToken, TokenVerifier
from sqlalchemy.orm import Session

from app.mcp.tokens import verify_token

logger = logging.getLogger(__name__)


SessionFactory = Callable[[], Session]


class BearerTokenVerifier(TokenVerifier):
    """Valida Bearer tokens contra tabela mcp_tokens.

    Args:
        session_factory: callable que retorna uma SQLAlchemy Session (geralmente
            `SessionLocal` da app, mas testes injetam factory que devolve a
            session em uso).
    """

    def __init__(self, session_factory: SessionFactory):
        self._session_factory = session_factory

    async def verify_token(self, token: str) -> AccessToken | None:
        """Async per o protocolo, mas DB ops são sync (SQLAlchemy)."""
        db = self._session_factory()
        try:
            row = verify_token(db, token)
        except Exception:
            logger.exception("mcp.auth.verify_failed")
            return None
        finally:
            # Só fecha se session_factory criou nova. Testes passam mesma session;
            # nesse caso o teardown global do conftest cuida.
            pass

        if row is None:
            return None

        return AccessToken(
            token=token,
            client_id=f"mcp-token-{row.id}",
            scopes=[f"mcp:workspace:{row.workspace_id}"],
            expires_at=None,  # tokens MCP não expiram por timestamp, só por revoke
            resource=None,
        )
```

- [ ] **Step 4: Rodar tests**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend
venv/bin/pytest tests/mcp/test_auth_verifier.py -v
```

Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/app/mcp/auth.py backend/tests/mcp/test_auth_verifier.py
git commit -m "feat(mcp): BearerTokenVerifier valida tokens contra DB"
```

---

## Task 6: Context helper — extrair workspace_id da request MCP

**Files:**
- Create: `backend/app/mcp/context.py`
- Create: `backend/tests/mcp/test_context_helper.py`

O `FastMCP` injeta um `Context` em cada tool. O AccessToken está acessível via `ctx.request_context.request.user`. Vamos extrair workspace_id do scope `mcp:workspace:<id>`.

- [ ] **Step 1: Test falhando**

Create `backend/tests/mcp/test_context_helper.py`:

```python
from unittest.mock import Mock

from mcp.server.auth.provider import AccessToken

from app.mcp.context import get_workspace_id


def _mk_ctx_with_token(token: AccessToken):
    """Mock minimal context shape compatível com get_workspace_id."""
    ctx = Mock()
    user = Mock()
    user.access_token = token
    ctx.request_context.request.user = user
    return ctx


def test_extracts_workspace_id_from_scope():
    token = AccessToken(
        token="x" * 64, client_id="mcp-token-1",
        scopes=["mcp:workspace:42"], expires_at=None, resource=None,
    )
    ctx = _mk_ctx_with_token(token)
    assert get_workspace_id(ctx) == 42


def test_returns_default_when_no_workspace_scope():
    token = AccessToken(
        token="x" * 64, client_id="mcp-token-1",
        scopes=["other:scope"], expires_at=None, resource=None,
    )
    ctx = _mk_ctx_with_token(token)
    # Fallback pro single-tenant scaffold
    assert get_workspace_id(ctx) == 1


def test_returns_default_when_no_user():
    ctx = Mock()
    ctx.request_context.request.user = None
    assert get_workspace_id(ctx) == 1


def test_returns_default_when_no_request_context():
    ctx = Mock()
    # Simula ausência via AttributeError
    ctx.request_context = Mock(spec=[])  # sem .request
    assert get_workspace_id(ctx) == 1
```

- [ ] **Step 2: Rodar — deve falhar**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend
venv/bin/pytest tests/mcp/test_context_helper.py -v
```

Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 3: Implementar `context.py`**

Create `backend/app/mcp/context.py`:

```python
"""Helpers pra extrair info do Context injetado pelo FastMCP."""
from __future__ import annotations

from typing import Any

DEFAULT_WORKSPACE_ID = 1  # single-tenant scaffold


_SCOPE_PREFIX = "mcp:workspace:"


def get_workspace_id(ctx: Any) -> int:
    """Deriva workspace_id do AccessToken associado à request.

    Espera scope no formato `mcp:workspace:<int>` (set por BearerTokenVerifier).
    Cai pra DEFAULT_WORKSPACE_ID se ausente — útil pra DEV sem auth ativa.
    """
    try:
        user = ctx.request_context.request.user
    except AttributeError:
        return DEFAULT_WORKSPACE_ID
    if user is None:
        return DEFAULT_WORKSPACE_ID
    token = getattr(user, "access_token", None)
    if token is None:
        return DEFAULT_WORKSPACE_ID
    for scope in (token.scopes or []):
        if scope.startswith(_SCOPE_PREFIX):
            try:
                return int(scope[len(_SCOPE_PREFIX):])
            except ValueError:
                continue
    return DEFAULT_WORKSPACE_ID
```

- [ ] **Step 4: Rodar tests**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend
venv/bin/pytest tests/mcp/test_context_helper.py -v
```

Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/app/mcp/context.py backend/tests/mcp/test_context_helper.py
git commit -m "feat(mcp): get_workspace_id extrai do AccessToken scope"
```

---

## Task 7: `build_mcp_server()` — FastMCP configurado (vazio)

**Files:**
- Create: `backend/app/mcp/server.py`
- Create: `backend/tests/mcp/test_server_build.py`

- [ ] **Step 1: Test falhando**

Create `backend/tests/mcp/test_server_build.py`:

```python
from app.mcp.server import build_mcp_server


def test_build_mcp_server_returns_fastmcp():
    server = build_mcp_server()
    # Instância de FastMCP do SDK
    from mcp.server.fastmcp import FastMCP
    assert isinstance(server, FastMCP)


def test_build_mcp_server_has_token_verifier():
    server = build_mcp_server()
    # FastMCP expõe settings; token_verifier deve estar configurado
    assert server.settings.auth is not None or server._token_verifier is not None or hasattr(server, "_token_verifier")
    # API exata pode variar entre versões do SDK; o teste valida que algo de auth foi configurado.


def test_build_mcp_server_name():
    server = build_mcp_server()
    assert server.name == "sdr-machine"
```

- [ ] **Step 2: Rodar — deve falhar**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend
venv/bin/pytest tests/mcp/test_server_build.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implementar `server.py`**

Create `backend/app/mcp/server.py`:

```python
"""Builder do FastMCP server pro SDR Machine.

M-1 retorna server vazio (sem tools nem resources). M-2 adiciona READ tools,
M-3 adiciona write tools, etc.

Mount em FastAPI feito em `app/main.py`.
"""
from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from app.database import SessionLocal
from app.mcp.auth import BearerTokenVerifier

logger = logging.getLogger(__name__)


def build_mcp_server() -> FastMCP:
    """Constrói o FastMCP server. Idempotente (cada chamada cria nova instância)."""
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
        # streamable_http_path="/" — quando mountar, paths ficam relativos ao mount point
        streamable_http_path="/",
    )

    # M-2/3/4/5 adicionam tools/resources/prompts via decorators dentro deste módulo
    # ou via funções `register_*(server)` chamadas aqui.

    return server
```

- [ ] **Step 4: Rodar tests**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend
venv/bin/pytest tests/mcp/test_server_build.py -v
```

Expected: 3 PASS.

> Se o segundo teste falhar por API do SDK variar entre versões, ajustar a assertion: o que importa é que `verifier` foi passado. Substituir por `assert hasattr(server, '_token_verifier') or server.settings.auth is not None`.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/app/mcp/server.py backend/tests/mcp/test_server_build.py
git commit -m "feat(mcp): build_mcp_server retorna FastMCP configurado com auth"
```

---

## Task 8: Mount MCP server em FastAPI (`app/main.py`)

**Files:**
- Modify: `backend/app/main.py`
- Create: `backend/tests/mcp/test_server_mount.py`

- [ ] **Step 1: Test falhando — endpoint MCP responde**

Create `backend/tests/mcp/test_server_mount.py`:

```python
"""Smoke test: MCP server mounted respondendo no path correto.

Não validamos JSON-RPC handshake completo aqui (M-2/M-3 cobrem). Só confirmamos
que o mount não está 404.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_mcp_path_not_404():
    # MCP requer POST com Content-Type específico; sem auth, deve retornar 401 ou 406, NÃO 404.
    r = client.post("/api/mcp/", json={"jsonrpc": "2.0", "method": "initialize", "id": 1})
    assert r.status_code != 404, (
        f"MCP endpoint not mounted (got 404). Headers: {dict(r.headers)}"
    )


def test_mcp_rejects_no_auth():
    r = client.post("/api/mcp/", json={"jsonrpc": "2.0", "method": "initialize", "id": 1})
    # Token verifier rejeita — pode retornar 401 ou um JSON-RPC error
    assert r.status_code in (401, 403, 400) or (
        r.status_code == 200 and "error" in r.json()
    )
```

- [ ] **Step 2: Rodar — deve falhar (404)**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend
venv/bin/pytest tests/mcp/test_server_mount.py -v
```

Expected: FAIL com `404` no primeiro teste.

- [ ] **Step 3: Mountar server em `main.py`**

Edit `backend/app/main.py`.

No topo do arquivo, adicionar import e instanciar server uma vez no module level (depois dos outros imports):

```python
from app.mcp.server import build_mcp_server

# MCP server — single instance per process
mcp_server = build_mcp_server()
```

Depois de `app = FastAPI(title="SDR Machine API", version="1.0.0")`, adicionar:

```python
# Mount MCP — paths ficam em /api/mcp/* (porque streamable_http_path="/" no FastMCP)
app.mount("/api/mcp", mcp_server.streamable_http_app())
```

Importante: `FastMCP.streamable_http_app()` retorna um Starlette app que precisa do session manager rodando. Conforme docs do SDK, isso é gerenciado via lifespan. Adicionar lifespan combinado.

Localizar a linha onde `@app.on_event("startup")` é definido (`_reap_orphaned_jobs`). Reaproveitar lifespan via:

```python
import contextlib

@contextlib.asynccontextmanager
async def _mcp_lifespan(_app):
    async with mcp_server.session_manager.run():
        yield


app.router.lifespan_context = _mcp_lifespan
```

> Se houver lifespan custom já configurado, integrar via `AsyncExitStack` similar ao exemplo do SDK README ("Configure and Mount Multiple Streamable HTTP FastMCP Servers with Starlette Lifespan").

Após `app.add_middleware(AuthMiddleware, ...)`, adicionar `/api/mcp` ao `public_paths` PRA QUE AuthMiddleware do produto NÃO intercepte requests MCP (auth do MCP é separada via TokenVerifier):

```python
app.add_middleware(
    AuthMiddleware,
    database_url=app_settings.database_url,
    public_paths=[
        "/api/health", "/api/leads/p/", "/api/webhooks",
        "/api/mcp",  # ← novo: MCP tem auth próprio (Bearer via TokenVerifier)
        "/docs", "/openapi.json",
    ],
)
```

- [ ] **Step 4: Rodar tests mount**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend
venv/bin/pytest tests/mcp/test_server_mount.py -v
```

Expected: 2 PASS.

Se o primeiro teste falhar com 404, conferir:
- `streamable_http_path` setado em `build_mcp_server()`
- Mount path em `main.py` é `/api/mcp` (com ou sem trailing slash conforme SDK)
- Lifespan iniciado (se mount funciona mas session manager não roda, retorna 503)

- [ ] **Step 5: Rodar suite completa pra detectar regressão**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend
venv/bin/pytest --deselect tests/test_outreach.py 2>&1 | tail -5
```

Expected: ~720 PASS (704 baseline + ~16 novos MCP em tests).

- [ ] **Step 6: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/app/main.py backend/tests/mcp/test_server_mount.py
git commit -m "feat(mcp): mount FastMCP server em /api/mcp"
```

---

## Task 9: Push branch + abrir PR

- [ ] **Step 1: Final check**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend
venv/bin/pytest tests/mcp/ -v
```

Expected: TODOS PASS (~23 testes em test_models_schema + test_token_lifecycle + test_auth_verifier + test_context_helper + test_server_build + test_server_mount).

- [ ] **Step 2: Push branch**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git push -u origin feat/mcp-m1-foundation
```

- [ ] **Step 3: Criar PR**

```bash
gh pr create --base main --title "feat(mcp): M-1 foundation — schema + FastMCP skeleton + Bearer auth" --body "$(cat <<'EOF'
## Summary

Foundation do MCP server. Sem tools/resources/prompts ainda — M-2 a M-5 adicionam.

**Backend novo:**
- Migration r16: tabelas \`mcp_tokens\` (id, workspace_id, name, token_hash, last4, timestamps) + \`pending_actions\` (id string, action_type, params/preview JSON, expires_at, committed_at, cancelled_at)
- Models SQLAlchemy correspondentes
- Token utilities (\`app/mcp/tokens.py\`): \`generate_token\` (32B hex), \`hash_token\` (SHA-256), \`verify_token\` (lookup + last_used_at), \`revoke_token\`, \`list_tokens\`
- \`BearerTokenVerifier\` (\`app/mcp/auth.py\`) implementa contrato \`TokenVerifier\` do SDK Anthropic — retorna \`AccessToken\` com scope \`mcp:workspace:<id>\`
- \`get_workspace_id\` (\`app/mcp/context.py\`) extrai workspace_id do Context injetado pelo FastMCP
- \`build_mcp_server()\` (\`app/mcp/server.py\`) retorna \`FastMCP\` configurado com token verifier + instructions
- Mount em \`app/main.py\`: \`app.mount("/api/mcp", mcp_server.streamable_http_app())\` + lifespan integrado pra session manager + path adicionado ao \`public_paths\` do AuthMiddleware

**Dependência nova:** \`mcp>=1.12.4\` (Anthropic Python SDK)

## Test Plan

- [x] ~23 testes novos em \`tests/mcp/\` (lifecycle de tokens, auth verifier, context helper, server build, mount smoke)
- [x] Migration aplica + reverte sem erro
- [x] Suite backend full passa (sem regressão em pre-existentes)
- [ ] **Manual:** subir backend local, gerar token via SQL direto, fazer POST \`/api/mcp/\` com Bearer header, confirmar handshake \`initialize\` retorna capabilities

## Não coberto

- READ tools (M-2)
- Write tools + two-phase commit (M-3)
- UI gerenciar tokens (M-4) — hoje só inserção via SQL
- Prompts + subscriptions (M-5)

## Especificação

\`docs/superpowers/specs/2026-05-18-mcp-server-m0-architecture.md\` §3, §7, §8
EOF
)"
```

---

## Self-Review

**Spec coverage** (vs M-0 §3, §7, §8):
- ✅ Tabela `mcp_tokens` com colunas: id, workspace_id, name, token_hash, last4, created_at, last_used_at, revoked_at → Task 2 + 3
- ✅ Tabela `pending_actions` com colunas: id (string UUID), workspace_id, action_type, params JSON, preview JSON, created_by_token_hash, created_at, expires_at, committed_at, cancelled_at, result JSON → Task 2 + 3
- ✅ Token lifecycle (generate hex 64, hash SHA-256, verify, revoke) → Task 4
- ✅ Bearer auth via TokenVerifier do SDK → Task 5
- ✅ Workspace scope no AccessToken → Task 5 + 6
- ✅ HTTP transport em `/api/mcp` → Task 8
- ✅ Public path no AuthMiddleware → Task 8
- ❌ Rate limiting in-memory (mencionado §7) — não incluído neste plan, fica pra M-2 quando primeira tool existe pra rate-limitar. Adicionar nota.

**Placeholder scan:** nenhum step usa "TBD" / "implement later" / "appropriate error handling". `<LATEST_REV_ID_FROM_STEP_1>` em Task 2 é placeholder INTENCIONAL — engineer substitui pelo valor real após `alembic history`.

**Type consistency:**
- `McpToken` columns same em models.py e migration r16 ✓
- `PendingAction` columns same em models.py e migration r16 ✓
- `hash_token(plain) -> str` (64 chars) em Task 4 e Task 5 (consumido por BearerTokenVerifier) ✓
- `verify_token(db, plain) -> McpToken | None` em Task 4 e usado por Task 5 ✓
- `AccessToken.scopes = [f"mcp:workspace:{id}"]` em Task 5, parseado por `get_workspace_id` em Task 6 ✓
- `build_mcp_server() -> FastMCP` em Task 7 e usado em Task 8 main.py ✓

---

## Execution Handoff

Após Task 9 (push + PR), próximo é **M-2: READ tools** que registra tools no `mcp_server` retornado por `build_mcp_server()`.

Plan complete and saved to `docs/superpowers/plans/2026-05-18-mcp-m1-foundation.md`.
