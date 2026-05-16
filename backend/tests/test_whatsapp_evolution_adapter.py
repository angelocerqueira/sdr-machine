from datetime import datetime
from unittest.mock import patch, Mock

import pytest

from app.whatsapp.evolution_adapter import EvolutionAdapter


@pytest.fixture
def adapter():
    return EvolutionAdapter(
        base_url="https://evo.example.com",
        instance="sdr",
        api_key="SECRET",
    )


def test_send_text_calls_correct_endpoint(adapter):
    fake_response = Mock(status_code=201)
    fake_response.json.return_value = {
        "key": {"id": "EVO-MSG-42", "remoteJid": "5544999990000@s.whatsapp.net", "fromMe": True},
        "status": "PENDING",
        "messageTimestamp": "1715000000",
    }
    with patch("httpx.post", return_value=fake_response) as mock_post:
        result = adapter.send_text(
            to_phone="5544999990000",
            body="Olá, Dr. Marcos",
            idempotency_key="outreach_msg_42",
        )

    # endpoint correto
    url = mock_post.call_args[0][0]
    assert url == "https://evo.example.com/message/sendText/sdr"
    # headers
    headers = mock_post.call_args.kwargs["headers"]
    assert headers["apikey"] == "SECRET"
    # body
    body = mock_post.call_args.kwargs["json"]
    assert body["number"] == "5544999990000"
    assert body["text"] == "Olá, Dr. Marcos"
    # idempotency aplicada como header custom (Evolution ignora; reservado pro app)
    assert headers["X-Idempotency-Key"] == "outreach_msg_42"
    # resultado
    assert result.provider_message_id == "EVO-MSG-42"
    assert result.phone_to == "5544999990000"
    assert result.body == "Olá, Dr. Marcos"
    assert isinstance(result.sent_at, datetime)


def test_send_text_normalizes_phone_with_mask(adapter):
    fake_response = Mock(status_code=201)
    fake_response.json.return_value = {
        "key": {"id": "X", "remoteJid": "5544999990000@s.whatsapp.net", "fromMe": True},
        "status": "PENDING",
    }
    with patch("httpx.post", return_value=fake_response) as mock_post:
        adapter.send_text(
            to_phone="(44) 99999-0000",  # com máscara
            body="oi", idempotency_key="k1",
        )
    body = mock_post.call_args.kwargs["json"]
    assert body["number"] == "5544999990000"


def test_send_text_raises_on_4xx(adapter):
    fake_response = Mock(status_code=400, text="bad number")
    with patch("httpx.post", return_value=fake_response):
        with pytest.raises(RuntimeError, match="Evolution send_text failed"):
            adapter.send_text(
                to_phone="5544999990000", body="oi", idempotency_key="k",
            )
