"""ABC do contrato WhatsApp provider — Evolution / Z-API / Cloud / etc.

Cada adapter implementa os 5 métodos. Webhook normalization fica dentro
do adapter (cada provider tem formato próprio); helpers compartilhados
moram em `app.whatsapp.normalizer`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from app.whatsapp.types import (
    InboundMessage,
    ProviderHealth,
    SentMessage,
    StatusUpdate,
)


class WhatsAppProvider(ABC):
    name: ClassVar[str]

    @abstractmethod
    def send_text(
        self, to_phone: str, body: str, *, idempotency_key: str
    ) -> SentMessage: ...

    @abstractmethod
    def send_media(
        self, to_phone: str, media_url: str, caption: str | None = None
    ) -> SentMessage: ...

    @abstractmethod
    def fetch_history(
        self, phone: str, *, limit: int = 50
    ) -> list[InboundMessage]: ...

    @abstractmethod
    def parse_webhook(
        self, raw: dict
    ) -> list[InboundMessage | StatusUpdate]: ...

    @abstractmethod
    def health_check(self) -> ProviderHealth: ...
