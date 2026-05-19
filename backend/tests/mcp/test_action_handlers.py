import pytest
from unittest.mock import Mock, patch

from app.integrations.crypto import encrypt
from app.models import (
    Conversation, ConversationMessage, IntegrationSettings, Lead,
)
import app.mcp.action_handlers  # noqa: F401 — força registro
from app.mcp.pending_actions_service import HANDLERS


def _seed_evolution(db):
    db.add(IntegrationSettings(
        workspace_id=1, provider="evolution", enabled=True,
        config={
            "base_url": "https://evo.example.com", "instance": "sdr",
            "api_key": encrypt("KEY"), "webhook_secret": encrypt("SEC"),
        },
    ))
    db.commit()


def test_handler_send_message_persists(db):
    _seed_evolution(db)
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

    fake = Mock(status_code=201)
    fake.json.return_value = {
        "key": {"id": "OUT-1", "remoteJid": "x", "fromMe": True},
        "status": "PENDING",
    }
    with patch("httpx.post", return_value=fake):
        handler = HANDLERS["send_message"]
        result = handler(db, {"conversation_id": conv.id, "body": "oi"})

    assert result["ok"] is True
    assert result["provider_message_id"] == "OUT-1"

    out_msgs = db.query(ConversationMessage).filter_by(
        conversation_id=conv.id, direction="out",
    ).all()
    assert len(out_msgs) == 1


def test_handler_delete_lead_cascades(db):
    lead = Lead(nome="DeleteMe", telefone="x", status="scraped")
    db.add(lead)
    db.commit()
    db.refresh(lead)
    lead_id = lead.id

    handler = HANDLERS["delete_lead"]
    result = handler(db, {"lead_id": lead_id})
    assert result["ok"] is True
    assert db.get(Lead, lead_id) is None


def test_handler_delete_conversations(db):
    lead = Lead(nome="X", telefone="x", status="scraped")
    db.add(lead)
    db.commit()
    db.refresh(lead)
    conv = Conversation(
        workspace_id=1, lead_id=lead.id, provider="evolution",
        provider_chat_id="x", phone="x",
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    handler = HANDLERS["delete_conversations"]
    result = handler(db, {"conversation_ids": [conv.id]})
    assert result["ok"] is True
    assert result["deleted_count"] == 1


def test_handler_run_pipeline_creates_job(db):
    from app.models import Job
    handler = HANDLERS["run_pipeline"]
    with patch("app.mcp.action_handlers._spawn_pipeline_stage") as spawn:
        result = handler(db, {"stage": "scrape", "params": {"nichos": ["dentista"]}})

    assert result["ok"] is True
    assert "job_id" in result
    spawn.assert_called_once()
    job = db.get(Job, result["job_id"])
    assert job is not None
    assert job.type == "scrape"


def test_handler_classify_leads_creates_job(db):
    from app.models import Job
    handler = HANDLERS["classify_leads"]
    with patch("app.mcp.action_handlers._spawn_classify"):
        result = handler(db, {"filter": {}, "level": "full"})
    assert result["ok"] is True
    job = db.get(Job, result["job_id"])
    assert job.type == "classify"


def test_handler_generate_lps_creates_job(db):
    from app.models import Job
    handler = HANDLERS["generate_lps"]
    with patch("app.mcp.action_handlers._spawn_generate_lps"):
        result = handler(db, {"filter": {}})
    assert result["ok"] is True
    job = db.get(Job, result["job_id"])
    assert job.type == "generate"


def test_handler_bulk_send_creates_job(db):
    from app.models import Job
    handler = HANDLERS["bulk_send"]
    with patch("app.mcp.action_handlers._spawn_bulk_send"):
        result = handler(db, {"recipient_lead_ids": [1, 2, 3], "template": "oi"})
    assert result["ok"] is True
    job = db.get(Job, result["job_id"])
    assert job.type == "mcp_bulk_send"
