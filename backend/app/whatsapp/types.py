"""Dataclasses do contrato provider-agnostic."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

Direction = Literal["in", "out"]
MessageStatus = Literal["queued", "sent", "delivered", "read", "failed", "received"]


@dataclass(frozen=True)
class SentMessage:
    """Resultado de um envio."""
    provider_message_id: str
    sent_at: datetime
    phone_to: str
    body: str
    status: MessageStatus = "sent"


@dataclass(frozen=True)
class InboundMessage:
    """Mensagem recebida (do webhook ou fetch_history)."""
    provider_message_id: str
    from_phone: str
    body: str | None
    received_at: datetime
    media_url: str | None = None
    quoted_message_id: str | None = None
    direction: Direction = "in"
    push_name: str | None = None  # nome exibido pelo remetente (WhatsApp); usado pra auto-criar lead


@dataclass(frozen=True)
class StatusUpdate:
    """Atualização de status de mensagem outbound."""
    provider_message_id: str
    status: MessageStatus
    timestamp: datetime


@dataclass(frozen=True)
class ProviderHealth:
    """Resultado de health check."""
    ok: bool
    state: str  # ex: "open" | "connecting" | "close"
    latency_ms: int
    error: str | None = None
