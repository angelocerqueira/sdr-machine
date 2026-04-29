"""Tests for landing page generator — focus on LLM call resilience."""
from unittest.mock import patch, MagicMock

import requests

from app.pipeline.generator import _generate_html


_MIN_LEAD = {
    "nome": "Test Lead",
    "categoria": "Advocacia",
    "telefone": "11999998888",
    "rating": 4.5,
    "reviews_count": 100,
}

_MIN_BRIEF = {
    "palette": {"accent": "#000", "bg": "#fff"},
    "typography": {"heading": "Bricolage Grotesque", "body": "Inter Tight"},
    "tone": "consultivo",
}


def _ok_response(html: str = "<!DOCTYPE html><html><body>x</body></html>") -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "choices": [{"message": {"content": html}, "finish_reason": "stop"}],
    }
    resp.raise_for_status = lambda: None
    return resp


def test_pass2_includes_max_tokens_in_request_body():
    """B: HTML generation must cap output via max_tokens to avoid runaway LLM."""
    with patch("app.pipeline.generator.requests.post", return_value=_ok_response()) as mock_post:
        _generate_html(_MIN_LEAD, "Advocacia", _MIN_BRIEF, "11999998888", "")

    body = mock_post.call_args.kwargs["json"]
    assert "max_tokens" in body
    # 8000 is enough for a rich LP HTML, well below the runaway scenarios we hit in prod
    assert body["max_tokens"] == 8000


def test_pass2_retries_once_on_read_timeout():
    """C: ReadTimeout is transient (slow provider) — retry once before giving up."""
    timeout_exc = requests.exceptions.ReadTimeout("read timed out")
    ok = _ok_response()
    with patch(
        "app.pipeline.generator.requests.post",
        side_effect=[timeout_exc, ok],
    ) as mock_post:
        result = _generate_html(_MIN_LEAD, "Advocacia", _MIN_BRIEF, "11999998888", "")

    assert mock_post.call_count == 2
    assert result.lower().startswith("<!doctype")


def test_pass2_retries_once_on_connection_error():
    """C: ConnectionError (TCP reset, DNS hiccup) is transient — retry."""
    conn_exc = requests.exceptions.ConnectionError("conn reset")
    ok = _ok_response()
    with patch(
        "app.pipeline.generator.requests.post",
        side_effect=[conn_exc, ok],
    ) as mock_post:
        result = _generate_html(_MIN_LEAD, "Advocacia", _MIN_BRIEF, "11999998888", "")

    assert mock_post.call_count == 2
    assert result != ""


def test_pass2_returns_empty_after_two_timeouts():
    """C: After 1 retry that also times out, give up gracefully (caller marks lead failed)."""
    timeout_exc = requests.exceptions.ReadTimeout("read timed out")
    with patch(
        "app.pipeline.generator.requests.post",
        side_effect=[timeout_exc, timeout_exc],
    ) as mock_post:
        result = _generate_html(_MIN_LEAD, "Advocacia", _MIN_BRIEF, "11999998888", "")

    assert mock_post.call_count == 2
    assert result == ""


def test_pass2_does_not_retry_on_4xx():
    """C: 4xx is not transient (auth, bad payload) — don't waste a 2nd call."""
    resp_400 = MagicMock()
    resp_400.status_code = 400
    resp_400.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "400 Bad Request", response=resp_400,
    )
    with patch(
        "app.pipeline.generator.requests.post",
        return_value=resp_400,
    ) as mock_post:
        result = _generate_html(_MIN_LEAD, "Advocacia", _MIN_BRIEF, "11999998888", "")

    assert mock_post.call_count == 1
    assert result == ""


def test_pass2_does_not_retry_on_5xx():
    """C: 5xx propagates without retry too — by design (same whitelist as 4xx).

    Regression guard: protects against someone adding HTTPError to the transient
    list under the assumption "5xx is provider flake". If we ever do want 5xx
    retries, that decision should be explicit and tested separately.
    """
    resp_503 = MagicMock()
    resp_503.status_code = 503
    resp_503.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "503 Service Unavailable", response=resp_503,
    )
    with patch(
        "app.pipeline.generator.requests.post",
        return_value=resp_503,
    ) as mock_post:
        result = _generate_html(_MIN_LEAD, "Advocacia", _MIN_BRIEF, "11999998888", "")

    assert mock_post.call_count == 1
    assert result == ""


def test_pass1_includes_max_tokens_in_request_body():
    """B (Pass 1, defensive): brief generation also caps output."""
    from app.pipeline.generator import _generate_creative_brief

    brief_json = (
        '{"palette":{"accent":"#000"},"typography":{"heading":"x","body":"y"},'
        '"tone":"x","layout":"x","headline":"x","subheadline":"x"}'
    )
    guide = {
        "copy_framework": "PAS",
        "mood": "autoridade",
        "color_direction": "azuis profundos",
        "typography_direction": "serif",
        "visual_metaphors": "escudo",
        "icon_suggestions": ["shield-check"],
    }
    with patch(
        "app.pipeline.generator.requests.post",
        return_value=_ok_response(brief_json),
    ) as mock_post:
        _generate_creative_brief(
            lead_data=_MIN_LEAD, niche="Advocacia", guide=guide,
            reviews_text="", gaps_text="", diagnostic_context="",
        )

    body = mock_post.call_args.kwargs["json"]
    assert "max_tokens" in body
