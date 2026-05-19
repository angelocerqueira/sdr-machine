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


def test_update_lead_fields_unknown_field_ignored(db):
    lead = Lead(nome="X", telefone="123", status="scraped")
    db.add(lead)
    db.commit()
    result = asyncio.run(update_lead_fields(
        _ctx(), id=lead.id, patch={"unknown_column": "evil"},
    ))
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
    assert row.your_name == "Angelo"


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
