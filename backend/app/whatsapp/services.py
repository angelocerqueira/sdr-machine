"""DB services pro webhook handler: upsert idempotente + correlação lead/outreach.

Camada pura sobre SQLAlchemy. Sem HTTP, sem httpx. Cada função recebe
`db: Session` injetada pelo caller (handler ou router).
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Conversation, ConversationMessage, Lead
from app.whatsapp.normalizer import normalize_phone_br

logger = logging.getLogger(__name__)


def find_lead_by_phone(
    db: Session, workspace_id: int, normalized_phone: str
) -> Lead | None:
    """Acha lead cujo `telefone` (possivelmente mascarado no DB) normaliza
    pro mesmo valor de `normalized_phone`.

    Telefones no DB chegam em formatos heterogêneos ("(44) 99999-0000",
    "+55 44 9...", "44999990000"). LIKE em substring não bate em strings
    mascaradas, então iteramos leads não-nulos e normalizamos em Python.
    Single-tenant (workspace_id=1) hoje; em escala maior, adicionar
    coluna `telefone_normalizado` indexada.
    """
    if not normalized_phone or len(normalized_phone) < 9:
        return None
    candidates = (
        db.query(Lead)
        .filter(Lead.telefone.isnot(None))
        .filter(Lead.telefone != "")
        .order_by(Lead.id.asc())
        .all()
    )
    for lead in candidates:
        try:
            if normalize_phone_br(lead.telefone) == normalized_phone:
                return lead
        except ValueError:
            continue
    return None


def get_or_create_conversation(
    db: Session, *, workspace_id: int, lead_id: int, provider: str,
    provider_chat_id: str, phone: str,
) -> Conversation:
    """Idempotent: retorna conversation existente ou cria nova.

    Unique constraint `uq_conversations_workspace_provider_chat` garante
    que duas POSTs concorrentes do mesmo chat não duplicam. Trata
    IntegrityError como race e re-busca.
    """
    conv = (
        db.query(Conversation)
        .filter_by(
            workspace_id=workspace_id, provider=provider,
            provider_chat_id=provider_chat_id,
        )
        .first()
    )
    if conv is not None:
        return conv
    conv = Conversation(
        workspace_id=workspace_id, lead_id=lead_id, provider=provider,
        provider_chat_id=provider_chat_id, phone=phone,
    )
    db.add(conv)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        conv = (
            db.query(Conversation)
            .filter_by(
                workspace_id=workspace_id, provider=provider,
                provider_chat_id=provider_chat_id,
            )
            .first()
        )
        if conv is None:
            raise
        return conv
    db.refresh(conv)
    return conv


def append_message(
    db: Session, *, conversation_id: int, direction: str,
    provider_message_id: str, body: str | None,
    timestamp: datetime, media_url: str | None = None,
    outreach_message_id: int | None = None,
) -> ConversationMessage:
    """Idempotent por `provider_message_id`. Retorna row existente se já
    foi gravada (webhook retry). Incrementa `unread_count` apenas em
    inbound NOVO (não em retry).
    """
    existing = (
        db.query(ConversationMessage)
        .filter_by(provider_message_id=provider_message_id)
        .first()
    )
    if existing is not None:
        return existing

    msg = ConversationMessage(
        conversation_id=conversation_id,
        direction=direction,
        provider_message_id=provider_message_id,
        body=body,
        media_url=media_url,
        outreach_message_id=outreach_message_id,
        status="received" if direction == "in" else "sent",
        received_at=timestamp if direction == "in" else None,
        sent_at=timestamp if direction == "out" else None,
    )
    db.add(msg)

    conv = db.query(Conversation).filter_by(id=conversation_id).first()
    if conv is not None:
        conv.last_message_at = timestamp
        if direction == "in":
            conv.unread_count = (conv.unread_count or 0) + 1

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return (
            db.query(ConversationMessage)
            .filter_by(provider_message_id=provider_message_id)
            .first()
        )
    db.refresh(msg)
    return msg
