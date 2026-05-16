from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from app.whatsapp.types import (
    InboundMessage,
    ProviderHealth,
    SentMessage,
    StatusUpdate,
)


def test_sent_message_frozen():
    m = SentMessage(
        provider_message_id="X",
        sent_at=datetime.now(timezone.utc),
        phone_to="5544999990000",
        body="oi",
    )
    with pytest.raises(FrozenInstanceError):
        m.body = "outro"  # type: ignore


def test_inbound_message_defaults():
    m = InboundMessage(
        provider_message_id="X",
        from_phone="5544999990000",
        body="oi",
        received_at=datetime.now(timezone.utc),
    )
    assert m.direction == "in"
    assert m.media_url is None


def test_provider_health_ok_field():
    h = ProviderHealth(ok=True, state="open", latency_ms=120)
    assert h.ok is True
    assert h.error is None


def test_status_update_minimal():
    u = StatusUpdate(
        provider_message_id="X", status="delivered", timestamp=datetime.now(timezone.utc),
    )
    assert u.status == "delivered"
