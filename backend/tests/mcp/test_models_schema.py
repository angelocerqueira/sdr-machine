from datetime import datetime, timedelta, timezone

import pytest

from app.models import McpToken, PendingAction


def test_mcp_token_minimal(db):
    t = McpToken(
        workspace_id=1, name="claude-desktop-laptop",
        token_hash="a" * 64, last4="abcd",
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    assert t.id is not None
    assert t.created_at is not None
    assert t.revoked_at is None


def test_mcp_token_unique_hash(db):
    db.add(McpToken(workspace_id=1, name="a", token_hash="X" * 64, last4="abcd"))
    db.commit()
    with pytest.raises(Exception):
        db.add(McpToken(workspace_id=1, name="b", token_hash="X" * 64, last4="efgh"))
        db.commit()


def test_pending_action_minimal(db):
    pa = PendingAction(
        id="action-abc-123", workspace_id=1, action_type="send_message",
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
