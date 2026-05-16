import pytest

from app.whatsapp.provider import WhatsAppProvider


def test_cannot_instantiate_abc_directly():
    with pytest.raises(TypeError):
        WhatsAppProvider()  # type: ignore


def test_concrete_must_implement_all_methods():
    class HalfBaked(WhatsAppProvider):
        name = "halfbaked"
        # missing send_text etc

    with pytest.raises(TypeError):
        HalfBaked()  # type: ignore


def test_full_impl_instantiates():
    from datetime import datetime, timezone

    from app.whatsapp.types import (
        InboundMessage,
        ProviderHealth,
        SentMessage,
        StatusUpdate,
    )

    class Stub(WhatsAppProvider):
        name = "stub"

        def send_text(self, to_phone, body, *, idempotency_key):
            return SentMessage(
                provider_message_id="X", sent_at=datetime.now(timezone.utc),
                phone_to=to_phone, body=body,
            )

        def send_media(self, to_phone, media_url, caption=None):
            return SentMessage(
                provider_message_id="X", sent_at=datetime.now(timezone.utc),
                phone_to=to_phone, body=caption or "",
            )

        def fetch_history(self, phone, *, limit=50):
            return []

        def parse_webhook(self, raw):
            return []

        def health_check(self):
            return ProviderHealth(ok=True, state="open", latency_ms=10)

    s = Stub()
    assert s.name == "stub"
