import pytest
from pytest_httpx import HTTPXMock


def test_resend_ok(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.resend.com/domains",
        json={"data": []},
        status_code=200,
    )
    from app.integrations.testers import check_resend
    res = check_resend({"api_key": "re_x"})
    assert res.ok is True
    assert res.error is None
    assert res.latency_ms >= 0


def test_resend_unauthorized(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.resend.com/domains",
        json={"name": "validation_error", "message": "API key is invalid"},
        status_code=401,
    )
    from app.integrations.testers import check_resend
    res = check_resend({"api_key": "re_bad"})
    assert res.ok is False
    assert "invalid" in res.error.lower()


def test_telegram_ok(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.telegram.org/bot123abc/getMe",
        json={"ok": True, "result": {"id": 1, "username": "bot"}},
        status_code=200,
    )
    from app.integrations.testers import check_telegram
    res = check_telegram({"bot_token": "123abc", "chat_id": "-100"})
    assert res.ok is True


def test_apify_ok(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.apify.com/v2/users/me?token=abc",
        json={"data": {"id": "1"}},
        status_code=200,
    )
    from app.integrations.testers import check_apify
    res = check_apify({"token": "abc"})
    assert res.ok is True


def test_dispatch_unknown_provider():
    from app.integrations.testers import run_test
    res = run_test("notarealthing", {})
    assert res.ok is False
    assert "unknown" in res.error.lower()
