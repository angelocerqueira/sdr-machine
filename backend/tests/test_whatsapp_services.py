from datetime import datetime, timezone

import pytest

from app.models import Conversation, ConversationMessage, Lead, OutreachMessage
from app.whatsapp.services import (
    append_message,
    find_lead_by_phone,
    get_or_create_conversation,
    link_outreach_reply,
    update_outreach_status,
)


def _make_lead(db, *, telefone, status="outreach_sent", workspace_id=1):
    lead = Lead(nome="x", telefone=telefone, status=status)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def test_find_lead_by_phone_exact_match(db):
    lead = _make_lead(db, telefone="5544999990000")
    found = find_lead_by_phone(db, workspace_id=1, normalized_phone="5544999990000")
    assert found is not None
    assert found.id == lead.id


def test_find_lead_by_phone_with_masked_telefone(db):
    lead = _make_lead(db, telefone="(44) 99999-0000")
    found = find_lead_by_phone(db, workspace_id=1, normalized_phone="5544999990000")
    assert found is not None
    assert found.id == lead.id


def test_find_lead_by_phone_without_ddi_in_db(db):
    lead = _make_lead(db, telefone="44999990000")
    found = find_lead_by_phone(db, workspace_id=1, normalized_phone="5544999990000")
    assert found is not None
    assert found.id == lead.id


def test_find_lead_by_phone_no_match(db):
    _make_lead(db, telefone="5511888880000")
    found = find_lead_by_phone(db, workspace_id=1, normalized_phone="5544999990000")
    assert found is None


def test_find_lead_by_phone_multiple_candidates_returns_first(db):
    lead1 = _make_lead(db, telefone="5544999990000")
    _make_lead(db, telefone="(44)99999-0000")  # mesmo número, formato diferente
    found = find_lead_by_phone(db, workspace_id=1, normalized_phone="5544999990000")
    assert found is not None
    assert found.id == lead1.id


def test_get_or_create_conversation_creates_new(db):
    lead = _make_lead(db, telefone="5544999990000")
    conv = get_or_create_conversation(
        db, workspace_id=1, lead_id=lead.id, provider="evolution",
        provider_chat_id="5544999990000@s.whatsapp.net", phone="5544999990000",
    )
    assert conv.id is not None
    assert conv.lead_id == lead.id
    assert conv.unread_count == 0


def test_get_or_create_conversation_returns_existing(db):
    lead = _make_lead(db, telefone="5544999990000")
    c1 = get_or_create_conversation(
        db, workspace_id=1, lead_id=lead.id, provider="evolution",
        provider_chat_id="5544999990000@s.whatsapp.net", phone="5544999990000",
    )
    c2 = get_or_create_conversation(
        db, workspace_id=1, lead_id=lead.id, provider="evolution",
        provider_chat_id="5544999990000@s.whatsapp.net", phone="5544999990000",
    )
    assert c1.id == c2.id


def test_append_message_inbound_creates_row(db):
    lead = _make_lead(db, telefone="5544999990000")
    conv = get_or_create_conversation(
        db, workspace_id=1, lead_id=lead.id, provider="evolution",
        provider_chat_id="5544999990000@s.whatsapp.net", phone="5544999990000",
    )
    msg = append_message(
        db, conversation_id=conv.id, direction="in",
        provider_message_id="EVO-MSG-1", body="oi",
        timestamp=datetime.now(timezone.utc),
    )
    assert msg is not None
    assert msg.body == "oi"
    assert msg.direction == "in"
    assert msg.received_at is not None

    db.refresh(conv)
    assert conv.unread_count == 1
    assert conv.last_message_at is not None


def test_append_message_idempotent_by_provider_msg_id(db):
    lead = _make_lead(db, telefone="5544999990000")
    conv = get_or_create_conversation(
        db, workspace_id=1, lead_id=lead.id, provider="evolution",
        provider_chat_id="5544999990000@s.whatsapp.net", phone="5544999990000",
    )
    m1 = append_message(
        db, conversation_id=conv.id, direction="in",
        provider_message_id="EVO-MSG-1", body="oi",
        timestamp=datetime.now(timezone.utc),
    )
    m2 = append_message(
        db, conversation_id=conv.id, direction="in",
        provider_message_id="EVO-MSG-1", body="oi",
        timestamp=datetime.now(timezone.utc),
    )
    assert m1.id == m2.id
    db.refresh(conv)
    assert conv.unread_count == 1


def test_append_message_outbound_does_not_increment_unread(db):
    lead = _make_lead(db, telefone="5544999990000")
    conv = get_or_create_conversation(
        db, workspace_id=1, lead_id=lead.id, provider="evolution",
        provider_chat_id="5544999990000@s.whatsapp.net", phone="5544999990000",
    )
    append_message(
        db, conversation_id=conv.id, direction="out",
        provider_message_id="EVO-OUT-1", body="oi",
        timestamp=datetime.now(timezone.utc),
    )
    db.refresh(conv)
    assert conv.unread_count == 0


def _make_outreach(db, *, lead_id, type_="initial",
                   provider_message_id=None, status="enviada"):
    om = OutreachMessage(
        lead_id=lead_id, type=type_, message_text="oi",
        status=status, provider_message_id=provider_message_id,
    )
    db.add(om)
    db.commit()
    db.refresh(om)
    return om


def test_link_outreach_reply_marks_lead_responded(db):
    lead = _make_lead(db, telefone="5544999990000", status="outreach_sent")
    om = _make_outreach(db, lead_id=lead.id)

    result = link_outreach_reply(db, lead=lead, reply_timestamp=datetime.now(timezone.utc))
    assert result is not None
    assert result.id == om.id

    db.refresh(lead)
    assert lead.status == "responded"
    assert lead.responded_at is not None


def test_link_outreach_reply_no_double_advance(db):
    lead = _make_lead(db, telefone="5544999990000", status="closed")
    _make_outreach(db, lead_id=lead.id)

    link_outreach_reply(db, lead=lead, reply_timestamp=datetime.now(timezone.utc))
    db.refresh(lead)
    assert lead.status == "closed"


def test_link_outreach_reply_no_outreach_returns_none(db):
    lead = _make_lead(db, telefone="5544999990000", status="outreach_sent")
    result = link_outreach_reply(db, lead=lead, reply_timestamp=datetime.now(timezone.utc))
    assert result is None
    db.refresh(lead)
    assert lead.status == "responded"
    assert lead.responded_at is not None


def test_update_outreach_status_delivered(db):
    lead = _make_lead(db, telefone="5544999990000")
    om = _make_outreach(db, lead_id=lead.id, provider_message_id="EVO-X-1")
    ts = datetime.now(timezone.utc)

    updated = update_outreach_status(
        db, provider_message_id="EVO-X-1", new_status="delivered", timestamp=ts,
    )
    assert updated is not None
    assert updated.id == om.id
    assert updated.delivered_at is not None
    assert updated.status == "enviada"


def test_update_outreach_status_read(db):
    lead = _make_lead(db, telefone="5544999990000")
    om = _make_outreach(db, lead_id=lead.id, provider_message_id="EVO-Y-1")

    updated = update_outreach_status(
        db, provider_message_id="EVO-Y-1", new_status="read",
        timestamp=datetime.now(timezone.utc),
    )
    assert updated.read_at is not None


def test_update_outreach_status_failed_marks_status_and_reason(db):
    lead = _make_lead(db, telefone="5544999990000")
    om = _make_outreach(db, lead_id=lead.id, provider_message_id="EVO-Z-1")

    updated = update_outreach_status(
        db, provider_message_id="EVO-Z-1", new_status="failed",
        timestamp=datetime.now(timezone.utc), failed_reason="bad number",
    )
    assert updated.status == "erro_envio"
    assert updated.failed_reason == "bad number"


def test_update_outreach_status_unknown_provider_msg_id(db):
    result = update_outreach_status(
        db, provider_message_id="DOESNT-EXIST", new_status="delivered",
        timestamp=datetime.now(timezone.utc),
    )
    assert result is None
