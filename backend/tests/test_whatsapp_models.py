from datetime import datetime, timezone

import pytest

from app.models import Conversation, ConversationMessage, Lead, OutreachMessage


def _make_lead(db) -> Lead:
    lead = Lead(nome="Acme Odonto", telefone="5544999990000", status="scraped")
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def test_conversation_basic_crud(db):
    lead = _make_lead(db)
    conv = Conversation(
        lead_id=lead.id,
        provider="evolution",
        provider_chat_id="5544999990000@s.whatsapp.net",
        phone="5544999990000",
        last_message_at=datetime.now(timezone.utc),
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    assert conv.id is not None
    assert conv.unread_count == 0
    assert conv.status == "active"
    assert conv.workspace_id == 1


def test_conversation_unique_per_workspace_provider_chat(db):
    lead = _make_lead(db)
    c1 = Conversation(
        lead_id=lead.id, provider="evolution",
        provider_chat_id="5544999990000@s.whatsapp.net", phone="5544999990000",
    )
    db.add(c1)
    db.commit()

    c2 = Conversation(
        lead_id=lead.id, provider="evolution",
        provider_chat_id="5544999990000@s.whatsapp.net", phone="5544999990000",
    )
    db.add(c2)
    with pytest.raises(Exception):  # IntegrityError em SQLite/Postgres
        db.commit()
    db.rollback()


def test_conversation_message_relationship(db):
    lead = _make_lead(db)
    conv = Conversation(
        lead_id=lead.id, provider="evolution",
        provider_chat_id="5544999990000@s.whatsapp.net", phone="5544999990000",
    )
    db.add(conv)
    db.commit()

    msg = ConversationMessage(
        conversation_id=conv.id,
        direction="out",
        body="Olá, sou do SDR Machine",
        provider_message_id="EVO-MSG-001",
        status="sent",
        sent_at=datetime.now(timezone.utc),
    )
    db.add(msg)
    db.commit()
    db.refresh(conv)

    assert len(conv.messages) == 1
    assert conv.messages[0].body == "Olá, sou do SDR Machine"


def test_outreach_message_new_columns(db):
    lead = _make_lead(db)
    om = OutreachMessage(
        lead_id=lead.id, type="initial", message_text="oi",
        status="enviada", provider_message_id="EVO-OM-1",
    )
    db.add(om)
    db.commit()
    db.refresh(om)

    assert om.provider_message_id == "EVO-OM-1"
    assert om.delivered_at is None
    assert om.read_at is None
    assert om.failed_reason is None


def test_lead_responded_at(db):
    lead = _make_lead(db)
    assert lead.responded_at is None
    lead.responded_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(lead)
    assert lead.responded_at is not None
