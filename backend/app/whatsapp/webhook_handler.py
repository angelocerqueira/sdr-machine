"""Orquestrador puro: webhook payload → adapter.parse_webhook → services.

Camada chamada pelo router (`routers/webhooks.py`) e testada isoladamente
(sem TestClient).
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.whatsapp.normalizer import to_chat_id
from app.whatsapp.registry import (
    ProviderNotConfigured,
    UnknownProviderError,
    get_provider,
)
from app.whatsapp.services import (
    append_message,
    find_lead_by_phone,
    get_or_create_conversation,
    link_outreach_reply,
    update_outreach_status,
)
from app.whatsapp.types import InboundMessage, StatusUpdate

logger = logging.getLogger(__name__)


class WebhookHandlerError(Exception):
    """Provider desconhecido, payload mal-formado, ou config ausente."""


def handle_webhook(
    db: Session, *, workspace_id: int, provider: str, raw: dict,
) -> dict:
    """Dispatcher: parsea o payload via adapter e roteia pros services.

    Retorna summary dict com contadores pra logging/telemetria.

    Raises:
        WebhookHandlerError: provider name inválido ou não configurado.
    """
    try:
        adapter = get_provider(db, workspace_id=workspace_id, provider=provider)
    except (UnknownProviderError, ProviderNotConfigured) as exc:
        raise WebhookHandlerError(str(exc)) from exc

    parsed = adapter.parse_webhook(raw)

    summary = {
        "inbound_processed": 0,
        "inbound_skipped_no_lead": 0,
        "status_updates_processed": 0,
        "status_updates_no_outreach": 0,
        "lead_id": None,
    }

    for item in parsed:
        if isinstance(item, InboundMessage):
            lead = find_lead_by_phone(
                db, workspace_id=workspace_id, normalized_phone=item.from_phone,
            )
            if lead is None:
                summary["inbound_skipped_no_lead"] += 1
                logger.info(
                    "webhook.inbound_no_lead workspace=%s phone=%s msg_id=%s",
                    workspace_id, item.from_phone, item.provider_message_id,
                )
                continue
            conv = get_or_create_conversation(
                db, workspace_id=workspace_id, lead_id=lead.id, provider=provider,
                provider_chat_id=to_chat_id(item.from_phone), phone=item.from_phone,
            )
            append_message(
                db, conversation_id=conv.id, direction="in",
                provider_message_id=item.provider_message_id,
                body=item.body, timestamp=item.received_at,
                media_url=item.media_url,
            )
            link_outreach_reply(db, lead=lead, reply_timestamp=item.received_at)
            summary["inbound_processed"] += 1
            summary["lead_id"] = lead.id

        elif isinstance(item, StatusUpdate):
            updated = update_outreach_status(
                db, provider_message_id=item.provider_message_id,
                new_status=item.status, timestamp=item.timestamp,
            )
            if updated is None:
                summary["status_updates_no_outreach"] += 1
            else:
                summary["status_updates_processed"] += 1

    return summary
