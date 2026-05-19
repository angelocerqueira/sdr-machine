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


def test_send_media_url_image(adapter):
    fake_response = Mock(status_code=201)
    fake_response.json.return_value = {
        "key": {"id": "EVO-MM-1", "remoteJid": "5544999990000@s.whatsapp.net", "fromMe": True},
        "status": "PENDING",
    }
    with patch("httpx.post", return_value=fake_response) as mock_post:
        result = adapter.send_media(
            to_phone="5544999990000",
            media_url="https://cdn.example.com/lp/lead-42.png",
            caption="LP personalizada pra você",
        )
    url = mock_post.call_args[0][0]
    assert url.endswith("/message/sendMedia/sdr")
    body = mock_post.call_args.kwargs["json"]
    assert body["number"] == "5544999990000"
    assert body["media"] == "https://cdn.example.com/lp/lead-42.png"
    assert body["caption"] == "LP personalizada pra você"
    # tipo inferido por extensão
    assert body["mediatype"] == "image"
    assert result.provider_message_id == "EVO-MM-1"


def test_send_media_pdf_infers_document(adapter):
    fake_response = Mock(status_code=201)
    fake_response.json.return_value = {"key": {"id": "X"}, "status": "PENDING"}
    with patch("httpx.post", return_value=fake_response) as mock_post:
        adapter.send_media(to_phone="5544999990000", media_url="https://x.com/relatorio.pdf")
    assert mock_post.call_args.kwargs["json"]["mediatype"] == "document"


def test_fetch_history_returns_normalized_inbound_msgs(adapter):
    fake_response = Mock(status_code=200)
    fake_response.json.return_value = [
        {
            "key": {"id": "M1", "remoteJid": "5544999990000@s.whatsapp.net", "fromMe": False},
            "message": {"conversation": "Bom dia!"},
            "messageTimestamp": 1715000000,
        },
        {
            "key": {"id": "M2", "remoteJid": "5544999990000@s.whatsapp.net", "fromMe": True},
            "message": {"conversation": "Olá, sou do SDR"},
            "messageTimestamp": 1714999900,
        },
        {
            "key": {"id": "M3", "remoteJid": "5544999990000@s.whatsapp.net", "fromMe": False},
            "message": {"extendedTextMessage": {"text": "Quanto custa?"}},
            "messageTimestamp": 1715000100,
        },
    ]
    with patch("httpx.get", return_value=fake_response) as mock_get:
        result = adapter.fetch_history("5544999990000", limit=10)

    # endpoint + filtro
    url = mock_get.call_args[0][0]
    assert url.endswith("/chat/findMessages/sdr")
    params = mock_get.call_args.kwargs["params"]
    assert params["where[key][remoteJid]"] == "5544999990000@s.whatsapp.net"

    # apenas inbound (fromMe=False) retorna como InboundMessage
    assert len(result) == 2
    assert result[0].provider_message_id == "M1"
    assert result[0].body == "Bom dia!"
    assert result[1].body == "Quanto custa?"  # extendedTextMessage suportado


def test_fetch_history_empty_returns_empty_list(adapter):
    fake_response = Mock(status_code=200)
    fake_response.json.return_value = []
    with patch("httpx.get", return_value=fake_response):
        assert adapter.fetch_history("5544999990000") == []


def test_parse_webhook_messages_upsert_inbound(adapter):
    raw = {
        "event": "messages.upsert",
        "instance": "sdr",
        "data": {
            "key": {
                "id": "EVO-IN-99",
                "remoteJid": "5544999990000@s.whatsapp.net",
                "fromMe": False,
            },
            "message": {"conversation": "Faz sentido sim, manda info"},
            "messageTimestamp": 1715000000,
            "pushName": "Marcos",
        },
    }
    out = adapter.parse_webhook(raw)
    assert len(out) == 1
    msg = out[0]
    from app.whatsapp.types import InboundMessage
    assert isinstance(msg, InboundMessage)
    assert msg.provider_message_id == "EVO-IN-99"
    assert msg.from_phone == "5544999990000"
    assert msg.body == "Faz sentido sim, manda info"


def test_parse_webhook_messages_upsert_outbound_ignored(adapter):
    raw = {
        "event": "messages.upsert",
        "data": {
            "key": {"id": "X", "remoteJid": "5544...@s.whatsapp.net", "fromMe": True},
            "message": {"conversation": "..."},
            "messageTimestamp": 1715000000,
        },
    }
    assert adapter.parse_webhook(raw) == []  # outbound não interessa


def test_parse_webhook_messages_update_status(adapter):
    raw = {
        "event": "messages.update",
        "data": {
            "key": {"id": "EVO-MSG-42", "remoteJid": "5544...@s.whatsapp.net"},
            "update": {"status": "READ"},
        },
    }
    out = adapter.parse_webhook(raw)
    from app.whatsapp.types import StatusUpdate
    assert len(out) == 1
    s = out[0]
    assert isinstance(s, StatusUpdate)
    assert s.provider_message_id == "EVO-MSG-42"
    assert s.status == "read"


def test_parse_webhook_unknown_event_returns_empty(adapter):
    raw = {"event": "connection.update", "data": {"state": "open"}}
    assert adapter.parse_webhook(raw) == []


def test_parse_webhook_group_message_ignored(adapter):
    raw = {
        "event": "messages.upsert",
        "data": {
            "key": {"id": "X", "remoteJid": "12345-67890@g.us", "fromMe": False},
            "message": {"conversation": "msg de grupo"},
            "messageTimestamp": 1715000000,
        },
    }
    assert adapter.parse_webhook(raw) == []


def test_health_check_open(adapter):
    fake_response = Mock(status_code=200)
    fake_response.json.return_value = {"instance": {"state": "open"}}
    with patch("httpx.get", return_value=fake_response):
        h = adapter.health_check()
    assert h.ok is True
    assert h.state == "open"
    assert h.error is None


def test_health_check_connecting(adapter):
    fake_response = Mock(status_code=200)
    fake_response.json.return_value = {"instance": {"state": "connecting"}}
    with patch("httpx.get", return_value=fake_response):
        h = adapter.health_check()
    assert h.ok is False
    assert h.state == "connecting"


def test_health_check_http_error(adapter):
    fake_response = Mock(status_code=500, text="server error")
    with patch("httpx.get", return_value=fake_response):
        h = adapter.health_check()
    assert h.ok is False
    assert "server error" in (h.error or "")


def test_connect_instance_returns_qr(adapter):
    fake_response = Mock(status_code=200, text='{"base64":"x"}')
    fake_response.json.return_value = {
        "base64": "data:image/png;base64,QR",
        "code": "2@xyz",
    }
    with patch("httpx.get", return_value=fake_response) as mock_get:
        result = adapter.connect_instance()
    url = mock_get.call_args[0][0]
    assert url == "https://evo.example.com/instance/connect/sdr"
    assert result["ok"] is True
    assert result["qr_base64"] == "data:image/png;base64,QR"
    assert result["code"] == "2@xyz"


def test_connect_instance_alt_shape_qrcode_nested(adapter):
    """Evolution variante: { qrcode: { base64, code } }"""
    fake_response = Mock(status_code=200, text='{"qrcode":{}}')
    fake_response.json.return_value = {
        "qrcode": {"base64": "data:image/png;base64,XX", "code": "2@nested"},
    }
    with patch("httpx.get", return_value=fake_response):
        result = adapter.connect_instance()
    assert result["ok"] is True
    assert result["qr_base64"] == "data:image/png;base64,XX"
    assert result["code"] == "2@nested"


def test_connect_instance_5xx_returns_sanitized(adapter):
    """Evolution 5xx: erro genérico, não vaza body raw."""
    fake_response = Mock(
        status_code=502,
        text="<html>internal server error stack...</html>",
    )
    with patch("httpx.get", return_value=fake_response):
        result = adapter.connect_instance()
    assert result["ok"] is False
    assert "internal server error" not in result["error"].lower()
    assert "502" in result["error"]


def test_connect_instance_timeout_returns_sanitized(adapter):
    """Timeout: erro genérico, sem detalhe interno."""
    import httpx as _httpx

    with patch("httpx.get", side_effect=_httpx.TimeoutException("timed out")):
        result = adapter.connect_instance()
    assert result["ok"] is False
    assert "unreachable" in result["error"].lower()


def test_logout_instance_success(adapter):
    fake_response = Mock(status_code=200, text='{"status":"SUCCESS"}')
    with patch("httpx.delete", return_value=fake_response) as mock_delete:
        result = adapter.logout_instance()
    assert result["ok"] is True
    assert "latency_ms" in result
    url = mock_delete.call_args[0][0]
    assert url == "https://evo.example.com/instance/logout/sdr"


def test_logout_instance_404_treated_as_already_disconnected(adapter):
    fake_response = Mock(status_code=404, text='{"error":"not connected"}')
    with patch("httpx.delete", return_value=fake_response):
        result = adapter.logout_instance()
    assert result["ok"] is True
    assert result["already_disconnected"] is True


def test_logout_instance_5xx_returns_error(adapter):
    fake_response = Mock(status_code=500, text="upstream error")
    with patch("httpx.delete", return_value=fake_response):
        result = adapter.logout_instance()
    assert result["ok"] is False
    assert "upstream error" in (result["error"] or "")


def test_logout_instance_timeout_returns_unreachable(adapter):
    import httpx as _httpx

    with patch("httpx.delete", side_effect=_httpx.TimeoutException("timed out")):
        result = adapter.logout_instance()
    assert result["ok"] is False
    assert "unreachable" in result["error"].lower()


def test_fetch_instance_token_flat_shape(adapter):
    """Evolution v2.x recentes: {"name": "...", "token": "..."}."""
    fake_response = Mock(status_code=200, text='[{"name":"sdr","token":"T"}]')
    fake_response.json.return_value = [
        {"name": "other", "token": "WRONG"},
        {"name": "sdr", "token": "TOKEN-SDR"},
    ]
    with patch("httpx.get", return_value=fake_response):
        token = adapter.fetch_instance_token()
    assert token == "TOKEN-SDR"


def test_fetch_instance_token_legacy_nested_shape(adapter):
    """Evolution legado: {"instance": {"instanceName": "..."}, "hash": {"apikey": "..."}}."""
    fake_response = Mock(status_code=200, text='[{}]')
    fake_response.json.return_value = [
        {"instance": {"instanceName": "sdr"}, "hash": {"apikey": "LEGACY-TOKEN"}},
    ]
    with patch("httpx.get", return_value=fake_response):
        token = adapter.fetch_instance_token()
    assert token == "LEGACY-TOKEN"


def test_fetch_instance_token_returns_none_when_instance_missing(adapter):
    fake_response = Mock(status_code=200, text="[]")
    fake_response.json.return_value = []
    with patch("httpx.get", return_value=fake_response):
        token = adapter.fetch_instance_token()
    assert token is None


def test_fetch_instance_token_returns_none_on_http_error(adapter):
    import httpx as _httpx

    with patch("httpx.get", side_effect=_httpx.TimeoutException("timed out")):
        token = adapter.fetch_instance_token()
    assert token is None


def test_fetch_instance_token_returns_none_on_non_200(adapter):
    fake_response = Mock(status_code=401, text="unauthorized")
    with patch("httpx.get", return_value=fake_response):
        token = adapter.fetch_instance_token()
    assert token is None
