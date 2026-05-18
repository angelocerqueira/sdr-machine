"""Conversations API — lista + detalhe + send outbound + mark-read.

Backend pra o Inbox UI (P4). Reusa adapters do P1 e schemas do P0.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Conversation, ConversationMessage, Lead
from app.schemas import (
    ConversationListItem,
    ConversationOut,
    MessageOut,
    SendMessageIn,
)
from app.whatsapp.normalizer import to_chat_id
from app.whatsapp.registry import (
    ProviderNotConfigured,
    UnknownProviderError,
    get_provider,
)
from app.whatsapp.services import append_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

WORKSPACE_ID = 1  # single-tenant scaffold

_PREVIEW_LEN = 80


def _build_preview(conv: Conversation, db: Session) -> str | None:
    last = (
        db.query(ConversationMessage)
        .filter_by(conversation_id=conv.id)
        .order_by(desc(ConversationMessage.created_at))
        .first()
    )
    if not last or not last.body:
        return None
    return last.body[:_PREVIEW_LEN]


@router.get("", response_model=list[ConversationListItem])
def list_conversations(
    filter: Literal["all", "unread", "responded", "won"] | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    q = (
        db.query(Conversation, Lead)
        .join(Lead, Conversation.lead_id == Lead.id)
        .filter(Conversation.workspace_id == WORKSPACE_ID)
    )

    if filter == "unread":
        q = q.filter(Conversation.unread_count > 0)
    elif filter == "responded":
        q = q.filter(Lead.status == "responded")
    elif filter == "won":
        q = q.filter(Lead.status.in_(["closed", "won", "delivered"]))

    if search:
        pattern = f"%{search.lower()}%"
        q = q.filter(
            or_(
                Lead.nome.ilike(pattern),
                Lead.telefone.ilike(pattern),
                Conversation.phone.ilike(pattern),
            )
        )

    rows = q.order_by(desc(Conversation.last_message_at)).all()

    out: list[ConversationListItem] = []
    for conv, lead in rows:
        out.append(ConversationListItem(
            id=conv.id, lead_id=lead.id,
            lead_nome=lead.nome, lead_telefone=lead.telefone,
            lead_status=lead.status,
            provider=conv.provider, phone=conv.phone,
            last_message_at=conv.last_message_at,
            last_message_preview=_build_preview(conv, db),
            unread_count=conv.unread_count, status=conv.status,
        ))
    return out
