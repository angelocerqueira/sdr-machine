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


def test_workspace_profile_default_when_missing(db):
    result = asyncio.run(workspace_profile(_ctx()))
    assert result.business_name is None


def test_workspace_profile_returns_persisted(db):
    db.add(WorkspaceProfile(
        workspace_id=1, business_name="Acme", your_name="Angelo",
    ))
    db.commit()
    result = asyncio.run(workspace_profile(_ctx()))
    assert result.business_name == "Acme"
    assert result.your_name == "Angelo"


def test_workspace_targeting_empty_default(db):
    result = asyncio.run(workspace_targeting(_ctx()))
    assert result.target_niches == []
    assert result.target_cities == []
