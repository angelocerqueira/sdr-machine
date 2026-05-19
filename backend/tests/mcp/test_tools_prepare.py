import asyncio
from unittest.mock import Mock

from mcp.server.auth.provider import AccessToken

from app.models import Conversation, Lead, PendingAction
from app.mcp.tools_prepare import (
    prepare_send_message,
    prepare_bulk_send,
    prepare_delete_lead,
    prepare_delete_conversations,
    prepare_run_pipeline,
    prepare_classify_leads,
    prepare_generate_lps,
)


def _ctx(workspace_id: int = 1, token: str = "tok-abc"):
    plain = (token * (64 // len(token) + 1))[:64]
    ctx = Mock()
    user = Mock()
    user.access_token = AccessToken(
        token=plain, client_id="mcp-1",
        scopes=[f"mcp:workspace:{workspace_id}"],
        expires_at=None, resource=None,
    )
    ctx.request_context.request.user = user
    return ctx


def test_prepare_send_message_creates_action(db):
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

    result = asyncio.run(prepare_send_message(
        _ctx(), conversation_id=conv.id, body="testing 123",
    ))
    assert result["action_id"]
    assert result["preview"]["to_phone"] == "5544999990000"
    assert result["preview"]["body_rendered"] == "testing 123"
    assert result["preview"]["lead_nome"] == "X"

    row = db.query(PendingAction).filter_by(id=result["action_id"]).first()
    assert row is not None
    assert row.action_type == "send_message"


def test_prepare_send_message_conv_not_found(db):
    result = asyncio.run(prepare_send_message(
        _ctx(), conversation_id=9999, body="x",
    ))
    assert "error" in result


def test_prepare_delete_lead_includes_cascade_counts(db):
    lead = Lead(nome="Big", telefone="x", status="scraped")
    db.add(lead)
    db.commit()
    db.refresh(lead)
    result = asyncio.run(prepare_delete_lead(_ctx(), lead_id=lead.id))
    assert result["action_id"]
    assert result["preview"]["lead_summary"]["nome"] == "Big"
    assert "related_data" in result["preview"]


def test_prepare_run_pipeline_creates_preview(db):
    result = asyncio.run(prepare_run_pipeline(
        _ctx(), stage="scrape", params={"nichos": ["dentista"], "cidades": ["X"]},
    ))
    assert result["action_id"]
    assert result["preview"]["stage"] == "scrape"


def test_prepare_bulk_send_includes_count(db):
    for i in range(3):
        l = Lead(nome=f"L{i}", telefone=f"x{i}", status="outreach_ready")
        db.add(l)
    db.commit()
    leads = db.query(Lead).all()
    lead_ids = [l.id for l in leads]

    result = asyncio.run(prepare_bulk_send(
        _ctx(), recipient_lead_ids=lead_ids, template="Olá {{lead.nome}}",
    ))
    assert result["action_id"]
    assert result["preview"]["count"] == 3
    assert "recipients_sample" in result["preview"]


def test_prepare_classify_leads_returns_estimate(db):
    for i in range(2):
        db.add(Lead(nome=f"L{i}", telefone=f"x{i}", status="enriched"))
    db.commit()
    result = asyncio.run(prepare_classify_leads(
        _ctx(), filter={"status": "enriched"}, level="full",
    ))
    assert result["action_id"]
    assert result["preview"]["count"] == 2


def test_prepare_generate_lps_returns_estimate(db):
    for i in range(4):
        db.add(Lead(nome=f"L{i}", telefone=f"x{i}", status="enriched"))
    db.commit()
    result = asyncio.run(prepare_generate_lps(
        _ctx(), filter={"status": "enriched"},
    ))
    assert result["action_id"]
    assert result["preview"]["count"] == 4
