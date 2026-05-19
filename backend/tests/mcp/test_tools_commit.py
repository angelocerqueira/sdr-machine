import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from mcp.server.auth.provider import AccessToken

from app.integrations.crypto import encrypt
from app.models import (
    Conversation, ConversationMessage, IntegrationSettings, Lead, PendingAction,
)
import app.mcp.action_handlers  # noqa: F401 — força registro
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

    db.expire_all()
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
    result = asyncio.run(commit_action(_ctx(token_plain="b" * 64), action_id=pa.id))
    assert result["ok"] is False


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
    db.expire_all()
    row = db.query(PendingAction).filter_by(id=pa.id).first()
    assert row.cancelled_at is not None


def test_cancel_action_unknown_returns_error(db):
    result = asyncio.run(cancel_action(_ctx(), action_id="ghost"))
    assert result["ok"] is False
