"""MCP READ tools — Conversations."""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import desc, or_

from app.mcp.context import get_workspace_id
from app.mcp.db import db_session
from app.mcp.schemas import (
    ConversationFull, ConversationSummary, MessageSummary,
)
from app.models import Conversation, ConversationMessage, Lead

_PREVIEW_LEN = 80


def _preview(db, conv_id: int) -> Optional[str]:
    last = (
        db.query(ConversationMessage)
        .filter_by(conversation_id=conv_id)
        .order_by(desc(ConversationMessage.created_at))
        .first()
    )
    if last is None or not last.body:
        return None
    return last.body[:_PREVIEW_LEN]


async def list_conversations(
    ctx: Any,
    filter: Optional[dict] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ConversationSummary]:
    workspace_id = get_workspace_id(ctx)
    f = filter or {}

    with db_session() as db:
        q = (
            db.query(Conversation, Lead)
            .join(Lead, Conversation.lead_id == Lead.id)
            .filter(Conversation.workspace_id == workspace_id)
        )
        if f.get("unread") is True:
            q = q.filter(Conversation.unread_count > 0)
        if f.get("status"):
            q = q.filter(Lead.status == f["status"])
        if f.get("search"):
            pat = f"%{f['search']}%"
            q = q.filter(or_(
                Lead.nome.ilike(pat),
                Lead.telefone.ilike(pat),
                Conversation.phone.ilike(pat),
            ))

        rows = (
            q.order_by(desc(Conversation.last_message_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
        out = []
        for conv, lead in rows:
            out.append(ConversationSummary(
                id=conv.id, lead_id=lead.id, lead_nome=lead.nome,
                phone=conv.phone, provider=conv.provider,
                last_message_at=conv.last_message_at,
                last_message_preview=_preview(db, conv.id),
                unread_count=conv.unread_count, status=conv.status,
            ))
        return out


async def get_conversation(ctx: Any, id: int) -> Optional[ConversationFull]:
    workspace_id = get_workspace_id(ctx)

    with db_session() as db:
        conv = (
            db.query(Conversation)
            .filter_by(id=id, workspace_id=workspace_id)
            .first()
        )
        if conv is None:
            return None
        msgs = (
            db.query(ConversationMessage)
            .filter_by(conversation_id=conv.id)
            .order_by(ConversationMessage.created_at.asc())
            .all()
        )
        return ConversationFull(
            id=conv.id, lead_id=conv.lead_id, phone=conv.phone,
            provider=conv.provider, unread_count=conv.unread_count,
            status=conv.status, created_at=conv.created_at,
            messages=[
                MessageSummary(
                    id=m.id, direction=m.direction, body=m.body,
                    sent_at=m.sent_at, received_at=m.received_at,
                    status=m.status,
                )
                for m in msgs
            ],
        )


def register_conversations_tools(server) -> None:
    server.tool(name="list_conversations")(list_conversations)
    server.tool(name="get_conversation")(get_conversation)
