from datetime import datetime, timedelta

import pytest

from app.models import PendingAction
from app.mcp.pending_actions_service import (
    HANDLERS,
    cancel_action_row,
    commit_action_row,
    create_action,
    get_action,
    register_handler,
)


def test_create_action_persists_with_uuid_and_expiry(db):
    pa = create_action(
        db, workspace_id=1, action_type="send_message",
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
    assert found is None


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
    def handler(db, params, action_id):
        return {"echoed": params, "action_id": action_id}

    assert "test_action_xyz" in HANDLERS
    HANDLERS.pop("test_action_xyz")
