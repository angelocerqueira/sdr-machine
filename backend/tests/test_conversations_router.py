import pytest
from datetime import datetime, timedelta, timezone

from app.models import Conversation, ConversationMessage, Lead


def _seed_conversation(db, *, lead_nome="Lead Test", lead_telefone="5544999990000",
                       unread=0, last_msg_minutes_ago=10, msgs=None):
    lead = Lead(nome=lead_nome, telefone=lead_telefone, status="outreach_sent")
    db.add(lead)
    db.commit()
    db.refresh(lead)

    conv = Conversation(
        workspace_id=1, lead_id=lead.id, provider="evolution",
        provider_chat_id=f"{lead_telefone}@s.whatsapp.net",
        phone=lead_telefone,
        last_message_at=datetime.now(timezone.utc) - timedelta(minutes=last_msg_minutes_ago),
        unread_count=unread,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    for i, (direction, body) in enumerate(msgs or []):
        m = ConversationMessage(
            conversation_id=conv.id, direction=direction,
            provider_message_id=f"MSG-{conv.id}-{i}", body=body,
            status="received" if direction == "in" else "sent",
            received_at=datetime.now(timezone.utc) if direction == "in" else None,
            sent_at=datetime.now(timezone.utc) if direction == "out" else None,
        )
        db.add(m)
    db.commit()
    return lead, conv


def test_list_conversations_empty(client, db):
    r = client.get("/api/conversations")
    assert r.status_code == 200
    assert r.json() == []


def test_list_conversations_returns_all(client, db):
    _seed_conversation(db, lead_nome="A", lead_telefone="5544111111111",
                       msgs=[("in", "oi A"), ("out", "olá A")])
    _seed_conversation(db, lead_nome="B", lead_telefone="5544222222222",
                       msgs=[("in", "oi B")])

    r = client.get("/api/conversations")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2
    assert {row["lead_nome"] for row in rows} == {"A", "B"}
    assert all("last_message_preview" in row for row in rows)


def test_list_conversations_orders_by_last_message_desc(client, db):
    _seed_conversation(db, lead_nome="Old", last_msg_minutes_ago=120,
                       lead_telefone="5544111111111", msgs=[("in", "antigo")])
    _seed_conversation(db, lead_nome="New", last_msg_minutes_ago=5,
                       lead_telefone="5544222222222", msgs=[("in", "recente")])

    r = client.get("/api/conversations")
    rows = r.json()
    assert rows[0]["lead_nome"] == "New"
    assert rows[1]["lead_nome"] == "Old"


def test_list_conversations_filter_unread(client, db):
    _seed_conversation(db, lead_nome="Read", unread=0,
                       lead_telefone="5544111111111", msgs=[("in", "x")])
    _seed_conversation(db, lead_nome="Unread", unread=3,
                       lead_telefone="5544222222222", msgs=[("in", "y")])

    r = client.get("/api/conversations?filter=unread")
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["lead_nome"] == "Unread"


def test_list_conversations_search_by_name(client, db):
    _seed_conversation(db, lead_nome="Padaria do João",
                       lead_telefone="5544111111111", msgs=[("in", "x")])
    _seed_conversation(db, lead_nome="Mercearia da Maria",
                       lead_telefone="5544222222222", msgs=[("in", "x")])

    r = client.get("/api/conversations?search=joão")
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["lead_nome"] == "Padaria do João"


def test_list_conversations_search_by_phone(client, db):
    _seed_conversation(db, lead_telefone="5544999990000", msgs=[("in", "x")])
    _seed_conversation(db, lead_telefone="5544888888888", msgs=[("in", "x")])

    r = client.get("/api/conversations?search=999990000")
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["phone"] == "5544999990000"


def test_list_conversations_last_message_preview(client, db):
    long_body = "a" * 200
    _seed_conversation(db, msgs=[("in", "primeira"), ("in", long_body)])
    r = client.get("/api/conversations")
    preview = r.json()[0]["last_message_preview"]
    assert preview is not None
    assert len(preview) <= 80
    assert preview.startswith("aaa")
