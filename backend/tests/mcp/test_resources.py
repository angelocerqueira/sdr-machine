"""Smoke tests pros resources MCP."""
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
    conversations_list_resource,
    conversation_detail_resource,
    lead_landing_pages_resource,
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
    assert isinstance(data, str)
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


def test_conversations_list_resource(db):
    data = asyncio.run(conversations_list_resource(_ctx()))
    assert isinstance(data, str)
