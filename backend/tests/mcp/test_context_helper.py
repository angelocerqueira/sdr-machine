from unittest.mock import Mock

from mcp.server.auth.provider import AccessToken

from app.mcp.context import get_workspace_id


def _ctx(token: AccessToken | None):
    ctx = Mock()
    if token is None:
        ctx.request_context.request.user = None
    else:
        user = Mock()
        user.access_token = token
        ctx.request_context.request.user = user
    return ctx


def test_extracts_workspace_id_from_scope():
    token = AccessToken(
        token="x" * 64, client_id="mcp-token-1",
        scopes=["mcp:workspace:42"], expires_at=None, resource=None,
    )
    assert get_workspace_id(_ctx(token)) == 42


def test_returns_default_when_no_workspace_scope():
    token = AccessToken(
        token="x" * 64, client_id="mcp-token-1",
        scopes=["other:scope"], expires_at=None, resource=None,
    )
    assert get_workspace_id(_ctx(token)) == 1


def test_returns_default_when_no_user():
    assert get_workspace_id(_ctx(None)) == 1


def test_returns_default_when_no_request_context():
    ctx = Mock()
    ctx.request_context = Mock(spec=[])
    assert get_workspace_id(ctx) == 1
