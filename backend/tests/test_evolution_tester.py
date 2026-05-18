from unittest.mock import patch, Mock

from app.integrations.testers import check_evolution


def test_check_evolution_ok():
    fake_response = Mock(status_code=200, text='{"instance":{"state":"open"}}')
    fake_response.json.return_value = {"instance": {"state": "open"}}
    with patch("httpx.get", return_value=fake_response) as mock_get:
        result = check_evolution({
            "base_url": "https://evo.example.com",
            "instance": "sdr",
            "api_key": "X",
        })
    assert result.ok is True
    assert result.error is None
    mock_get.assert_called_once()
    called_url = mock_get.call_args[0][0]
    assert "/instance/connectionState/sdr" in called_url
    headers = mock_get.call_args.kwargs["headers"]
    assert headers["apikey"] == "X"


def test_check_evolution_connecting_state():
    fake_response = Mock(status_code=200)
    fake_response.json.return_value = {"instance": {"state": "connecting"}}
    with patch("httpx.get", return_value=fake_response):
        result = check_evolution({
            "base_url": "https://evo.example.com",
            "instance": "sdr", "api_key": "X",
        })
    assert result.ok is False
    assert "connecting" in (result.error or "")


def test_check_evolution_http_error():
    fake_response = Mock(status_code=401, text="unauthorized")
    with patch("httpx.get", return_value=fake_response):
        result = check_evolution({
            "base_url": "https://evo.example.com",
            "instance": "sdr", "api_key": "X",
        })
    assert result.ok is False
