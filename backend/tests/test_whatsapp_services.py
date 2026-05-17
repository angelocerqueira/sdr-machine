from datetime import datetime, timezone

import pytest

from app.models import Conversation, ConversationMessage, Lead
from app.whatsapp.services import (
    append_message,
    find_lead_by_phone,
    get_or_create_conversation,
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
