"""WhatsApp provider abstraction.

Spec: docs/superpowers/specs/2026-05-16-whatsapp-inbox-design.md
"""
from app.whatsapp.types import (
    InboundMessage,
    ProviderHealth,
    SentMessage,
    StatusUpdate,
)

__all__ = ["SentMessage", "InboundMessage", "StatusUpdate", "ProviderHealth"]
