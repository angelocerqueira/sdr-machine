from unittest.mock import patch

import pytest

from app.integrations.crypto import encrypt
from app.models import IntegrationSettings
from app.whatsapp.evolution_adapter import EvolutionAdapter
from app.whatsapp.registry import (
    UnknownProviderError,
    ProviderNotConfigured,
    get_provider,
)


def _seed_evolution(db, *, enabled=True):
    db.add(IntegrationSettings(
        workspace_id=1, provider="evolution", enabled=enabled,
        config={
            "base_url": "https://evo.example.com",
            "instance": "sdr",
            "api_key": encrypt("SECRET_TOKEN"),
        },
    ))
    db.commit()


def test_get_provider_returns_evolution_adapter(db):
    _seed_evolution(db)
    adapter = get_provider(db, workspace_id=1)
    assert isinstance(adapter, EvolutionAdapter)
    assert adapter.base_url == "https://evo.example.com"
    assert adapter.instance == "sdr"
    assert adapter.api_key == "SECRET_TOKEN"  # já decifrado


def test_get_provider_explicit_name(db):
    _seed_evolution(db)
    adapter = get_provider(db, workspace_id=1, provider="evolution")
    assert isinstance(adapter, EvolutionAdapter)


def test_get_provider_not_configured(db):
    with pytest.raises(ProviderNotConfigured):
        get_provider(db, workspace_id=1)


def test_get_provider_unknown_name(db):
    _seed_evolution(db)
    with pytest.raises(UnknownProviderError):
        get_provider(db, workspace_id=1, provider="zapi")


def test_get_provider_disabled_row_treated_as_not_configured(db):
    _seed_evolution(db, enabled=False)
    with pytest.raises(ProviderNotConfigured):
        get_provider(db, workspace_id=1)


def test_end_to_end_registry_send_text_mocked(db):
    from datetime import datetime
    from unittest.mock import Mock, patch

    _seed_evolution(db)
    adapter = get_provider(db, workspace_id=1)

    fake_response = Mock(status_code=201)
    fake_response.json.return_value = {
        "key": {"id": "SMOKE-1", "remoteJid": "5544999990000@s.whatsapp.net", "fromMe": True},
        "status": "PENDING",
    }
    with patch("httpx.post", return_value=fake_response) as mock_post:
        result = adapter.send_text(
            to_phone="5544999990000",
            body="ping smoke",
            idempotency_key="smoke-1",
        )

    # adapter usou config do DB
    url = mock_post.call_args[0][0]
    assert url == "https://evo.example.com/message/sendText/sdr"
    headers = mock_post.call_args.kwargs["headers"]
    assert headers["apikey"] == "SECRET_TOKEN"  # secret decifrado fluiu até httpx
    assert result.provider_message_id == "SMOKE-1"
    assert isinstance(result.sent_at, datetime)
