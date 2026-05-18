from datetime import datetime, timezone

import pytest

from app.integrations.crypto import encrypt
from app.models import IntegrationSettings, Lead, OutreachMessage
from app.whatsapp.webhook_handler import (
    WebhookHandlerError,
    handle_webhook,
)


@pytest.fixture
def seeded(db):
    db.add(IntegrationSettings(
        workspace_id=1, provider="evolution", enabled=True,
        config={
            "base_url": "https://evo.example.com",
            "instance": "sdr", "api_key": encrypt("X"),
            "webhook_secret": encrypt("hmac-secret"),
        },
    ))
    lead = Lead(nome="Acme", telefone="5544999990000", status="outreach_sent")
    db.add(lead)
    db.commit()
    db.refresh(lead)

    om = OutreachMessage(
        lead_id=lead.id, type="initial", message_text="oi",
        status="enviada", provider_message_id="EVO-OUT-1",
    )
    db.add(om)
    db.commit()
    db.refresh(om)
    return {"lead": lead, "outreach": om}


def test_handle_webhook_inbound_creates_conversation_and_marks_responded(db, seeded):
    raw = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "id": "EVO-IN-1",
                "remoteJid": "5544999990000@s.whatsapp.net",
                "fromMe": False,
            },
            "message": {"conversation": "faz sentido sim"},
            "messageTimestamp": 1715000000,
        },
    }
    summary = handle_webhook(db, workspace_id=1, provider="evolution", raw=raw)

    assert summary["inbound_processed"] == 1
    assert summary["status_updates_processed"] == 0
    assert summary["lead_id"] == seeded["lead"].id

    db.refresh(seeded["lead"])
    assert seeded["lead"].status == "responded"
    assert seeded["lead"].responded_at is not None


def test_handle_webhook_status_update_marks_outreach(db, seeded):
    raw = {
        "event": "messages.update",
        "data": {
            "key": {"id": "EVO-OUT-1", "remoteJid": "5544999990000@s.whatsapp.net"},
            "update": {"status": "READ"},
        },
    }
    summary = handle_webhook(db, workspace_id=1, provider="evolution", raw=raw)

    assert summary["status_updates_processed"] == 1
    db.refresh(seeded["outreach"])
    assert seeded["outreach"].read_at is not None


def test_handle_webhook_idempotent_on_retry(db, seeded):
    raw = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "id": "EVO-IN-1",
                "remoteJid": "5544999990000@s.whatsapp.net",
                "fromMe": False,
            },
            "message": {"conversation": "oi"},
            "messageTimestamp": 1715000000,
        },
    }
    handle_webhook(db, workspace_id=1, provider="evolution", raw=raw)
    handle_webhook(db, workspace_id=1, provider="evolution", raw=raw)

    from app.models import ConversationMessage
    count = db.query(ConversationMessage).filter_by(provider_message_id="EVO-IN-1").count()
    assert count == 1


def test_handle_webhook_lead_not_found_skips_inbound(db, seeded):
    raw = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "id": "EVO-IN-X",
                "remoteJid": "5511000000000@s.whatsapp.net",
                "fromMe": False,
            },
            "message": {"conversation": "alô?"},
            "messageTimestamp": 1715000000,
        },
    }
    summary = handle_webhook(db, workspace_id=1, provider="evolution", raw=raw)
    assert summary["inbound_processed"] == 0
    assert summary["inbound_skipped_no_lead"] == 1


def test_handle_webhook_unknown_provider_raises(db, seeded):
    with pytest.raises(WebhookHandlerError):
        handle_webhook(db, workspace_id=1, provider="bogus", raw={"event": "x"})


def test_handle_webhook_unrecognized_event_returns_empty(db, seeded):
    raw = {"event": "connection.update", "data": {"state": "open"}}
    summary = handle_webhook(db, workspace_id=1, provider="evolution", raw=raw)
    assert summary["inbound_processed"] == 0
    assert summary["status_updates_processed"] == 0
