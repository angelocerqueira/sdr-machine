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


@router.get("/{conversation_id}", response_model=ConversationOut)
def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    conv = (
        db.query(Conversation)
        .options(joinedload(Conversation.messages))
        .filter_by(id=conversation_id, workspace_id=WORKSPACE_ID)
        .first()
    )
    if not conv:
        raise HTTPException(status_code=404, detail="conversation not found")

    messages = sorted(conv.messages, key=lambda m: m.created_at)

    return ConversationOut(
        id=conv.id, workspace_id=conv.workspace_id, lead_id=conv.lead_id,
        provider=conv.provider, provider_chat_id=conv.provider_chat_id,
        phone=conv.phone, last_message_at=conv.last_message_at,
        unread_count=conv.unread_count, status=conv.status,
        created_at=conv.created_at,
        messages=[MessageOut.model_validate(m) for m in messages],
    )


@router.post("/{conversation_id}/messages", response_model=MessageOut, status_code=201)
def send_message(
    conversation_id: int, payload: SendMessageIn,
    db: Session = Depends(get_db),
):
    conv = (
        db.query(Conversation)
        .filter_by(id=conversation_id, workspace_id=WORKSPACE_ID)
        .first()
    )
    if not conv:
        raise HTTPException(status_code=404, detail="conversation not found")

    try:
        adapter = get_provider(db, workspace_id=WORKSPACE_ID, provider=conv.provider)
    except (UnknownProviderError, ProviderNotConfigured) as exc:
        logger.warning(
            "conversations.send.provider_unavailable conv=%s reason=%s",
            conv.id, exc,
        )
        raise HTTPException(status_code=503, detail=f"provider unavailable: {exc}")

    idempotency_key = f"manual_send_conv_{conv.id}_{int(datetime.utcnow().timestamp()*1000)}"

    try:
        sent = adapter.send_text(
            to_phone=conv.phone, body=payload.body,
            idempotency_key=idempotency_key,
        )
    except Exception as exc:
        logger.exception("conversations.send.failed conv=%s", conv.id)
        raise HTTPException(status_code=502, detail=f"send failed: {exc}")

    msg = append_message(
        db, conversation_id=conv.id, direction="out",
        provider_message_id=sent.provider_message_id, body=payload.body,
        timestamp=sent.sent_at,
    )

    return MessageOut.model_validate(msg)
