import asyncio
from datetime import datetime, timedelta
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
    future = datetime.utcnow() + timedelta(minutes=5)
    past = datetime.utcnow() - timedelta(minutes=5)
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
    past = datetime.utcnow() - timedelta(minutes=5)
    db.add(PendingAction(
        id="expired", workspace_id=1, action_type="send_message",
        params={}, preview={}, created_by_token_hash="x" * 64,
        expires_at=past,
    ))
    db.commit()
    result = asyncio.run(list_pending_actions(_ctx(), include_expired=True))
    assert len(result) == 1
