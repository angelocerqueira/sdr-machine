import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock

from mcp.server.auth.provider import AccessToken

from app.models import Conversation, ConversationMessage, Lead
from app.mcp.tools_conversations import list_conversations, get_conversation


def _ctx(workspace_id: int = 1):
    ctx = Mock()
    user = Mock()
    user.access_token = AccessToken(
        token="x" * 64, client_id="mcp-1",
        scopes=[f"mcp:workspace:{workspace_id}"], expires_at=None, resource=None,
    )
    ctx.request_context.request.user = user
    return ctx


def _seed_conv(db, *, lead_nome="X", phone="5544999990000", unread=0, msgs=None):
    lead = Lead(nome=lead_nome, telefone=phone, status="outreach_sent")
    db.add(lead)
    db.commit()
    db.refresh(lead)
    conv = Conversation(
        workspace_id=1, lead_id=lead.id, provider="evolution",
        provider_chat_id=f"{phone}@s.whatsapp.net", phone=phone,
        last_message_at=datetime.now(timezone.utc), unread_count=unread,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    for i, (direction, body) in enumerate(msgs or []):
        db.add(ConversationMessage(
            conversation_id=conv.id, direction=direction,
            provider_message_id=f"MSG-{conv.id}-{i}", body=body,
            status="received" if direction == "in" else "sent",
            received_at=datetime.now(timezone.utc) if direction == "in" else None,
            sent_at=datetime.now(timezone.utc) if direction == "out" else None,
        ))
    db.commit()
    return conv


def test_list_conversations_empty(db):
    result = asyncio.run(list_conversations(_ctx(), filter=None))
    assert result == []


def test_list_conversations_returns_summary(db):
    _seed_conv(db, lead_nome="A", phone="5544111111111", msgs=[("in", "oi A")])
    _seed_conv(db, lead_nome="B", phone="5544222222222", msgs=[("in", "oi B"), ("out", "tudo bem?")])

    result = asyncio.run(list_conversations(_ctx(), filter=None))
    assert len(result) == 2
    assert {r.lead_nome for r in result} == {"A", "B"}


def test_list_conversations_filter_unread(db):
    _seed_conv(db, lead_nome="Read", phone="5544111111111", unread=0, msgs=[("in", "x")])
    _seed_conv(db, lead_nome="Unread", phone="5544222222222", unread=3, msgs=[("in", "y")])

    result = asyncio.run(list_conversations(_ctx(), filter={"unread": True}))
    assert len(result) == 1
    assert result[0].lead_nome == "Unread"


def test_get_conversation_returns_msgs_chronological(db):
    conv = _seed_conv(db, msgs=[("in", "1a"), ("out", "2a"), ("in", "3a")])
    result = asyncio.run(get_conversation(_ctx(), id=conv.id))
    assert result is not None
    assert len(result.messages) == 3
    assert result.messages[0].body == "1a"
    assert result.messages[-1].body == "3a"


def test_get_conversation_not_found(db):
    result = asyncio.run(get_conversation(_ctx(), id=9999))
    assert result is None


def test_list_conversations_pagination(db):
    for i in range(5):
        _seed_conv(db, lead_nome=f"L{i}", phone=f"5544000000{i:03d}",
                   msgs=[("in", f"msg {i}")])

    p1 = asyncio.run(list_conversations(_ctx(), filter=None, limit=2, offset=0))
    p2 = asyncio.run(list_conversations(_ctx(), filter=None, limit=2, offset=2))
    assert len(p1) == 2
    assert len(p2) == 2
    assert {c.lead_nome for c in p1} != {c.lead_nome for c in p2}
