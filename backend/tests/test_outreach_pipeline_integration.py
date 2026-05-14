"""
Integration tests for the outreach generator pipeline (PR1.4).

Verifies that ``generate_messages`` correctly wires:
- ``validators.validate_hard`` (post-LLM gate)
- ``validators.fix_capitalization`` / ``fix_punctuation_spacing`` (fixers)
- ``status`` + ``validation_errors`` on each emitted message dict

Three scenarios:
  1. LLM returns a placeholder-containing message  → ``erro_geracao`` + fallback
  2. LLM returns valid text                         → ``pronta`` + LLM text
  3. ``llm_api_key`` is empty                       → ``pronta`` + fallback (no errors)
"""

from unittest.mock import MagicMock, patch

import pytest

from app.config import settings
from app.pipeline.outreach import generate_messages


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

LEAD_WITH_DIAG: dict = {
    "nome": "Odonto Sorriso",
    "telefone": "49999887766",
    "website": "https://odontosorriso.com.br",
    "nicho": "dentista",
    "cidade": "Chapecó",
    "rating": 4.7,
    "reviews_count": 123,
    "opportunity_reasons": ["Sem HTTPS/SSL", "Sem chatbot"],
    "site_analysis": {
        "status": "ok",
        "qualificado": True,
        "nivel_recomendado": "lp",
        "diagnostico_marketing": {
            "resumo_executivo": "Clínica com boa reputação mas presença digital fraca.",
            "momento_funil": "descoberta",
            "potencial_ia_automacao": {
                "score": 75,
                "oportunidades": ["Chatbot IA para agendamento", "Automação de follow-up"],
                "justificativa": "Alto volume de agendamentos.",
            },
            "prioridades_top3": ["Otimizar GMN", "Criar site", "Chatbot WhatsApp"],
        },
    },
}


# A long, validator-clean message — over 180 chars (initial min_length) and
# stays under min_length for the longer types (insight_d5, angle_d9, breakup_d14)
# only if we make it ~200 chars, so we use ~280 chars to satisfy ALL types.
_VALID_LLM_TEXT = (
    "Oi! Vi a Odonto Sorriso no Google com 4.7 estrelas e 123 avaliacoes, "
    "presença local clara. olhei o site e o gap principal tá na captação "
    "de lead pelo mobile e em sinais de credibilidade no topo da página. "
    "faz sentido a gente trocar 10 min pra eu te mostrar dois ajustes "
    "rápidos? abraço, João."
)


# Contains an "XXXX" placeholder — validators flag as hard-block.
_PLACEHOLDER_LLM_TEXT = (
    "Oi! Vi a Odonto Sorriso no Google. olhei o site e dá pra ajustar "
    "captação de lead pelo mobile. liguei agora, mas chamou no (51) "
    "99606-XXXX. faz sentido a gente trocar 10 min pra eu te mostrar? "
    "abraço, João."
)


def _build_mock_response(text: str) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "choices": [{"message": {"content": text}}]
    }
    return resp


@pytest.fixture(autouse=True)
def _no_sleep():
    """Skip the 1s rate-limit sleep between LLM calls in the test loop."""
    with patch("app.pipeline.outreach.generator.time.sleep"):
        yield


# ---------------------------------------------------------------------------
# Scenario 1: placeholder in LLM output → fallback + erro_geracao
# ---------------------------------------------------------------------------


@patch("app.pipeline.outreach.generator.requests.post")
def test_placeholder_triggers_fallback_with_validation_errors(mock_post):
    """LLM returns text with XXXX placeholder → hard-blocked, fallback used,
    validation_errors persisted on the message dict."""
    mock_post.return_value = _build_mock_response(_PLACEHOLDER_LLM_TEXT)

    with patch.object(settings, "llm_api_key", "fake-key"):
        messages = generate_messages("pub-1", LEAD_WITH_DIAG, has_lp=False)

    assert len(messages) == 5

    initial = next(m for m in messages if m["type"] == "initial")
    assert initial["status"] == "erro_geracao"
    assert initial["validation_errors"], "expected validation_errors to be a non-empty list"
    assert any(err.startswith("placeholder:") for err in initial["validation_errors"]), (
        f"expected a placeholder:* error, got {initial['validation_errors']}"
    )
    # message_text is the deterministic fallback (NOT the LLM placeholder text)
    assert "XXXX" not in initial["message_text"]
    assert "(51) 99606" not in initial["message_text"]


# ---------------------------------------------------------------------------
# Scenario 2: valid LLM output → pronta, no errors, text comes from LLM
# ---------------------------------------------------------------------------


@patch("app.pipeline.outreach.generator.requests.post")
def test_valid_llm_output_is_persisted_with_status_pronta(mock_post):
    """LLM returns clean, long, well-punctuated text → passes validators,
    fixers applied, status=pronta, validation_errors=None."""
    mock_post.return_value = _build_mock_response(_VALID_LLM_TEXT)

    with patch.object(settings, "llm_api_key", "fake-key"):
        messages = generate_messages("pub-2", LEAD_WITH_DIAG, has_lp=False)

    assert len(messages) == 5

    initial = next(m for m in messages if m["type"] == "initial")
    assert initial["status"] == "pronta"
    assert initial["validation_errors"] is None
    # Came from the LLM (a distinctive substring of _VALID_LLM_TEXT)
    assert "presença local clara" in initial["message_text"]
    # Fixers applied: first letter capitalized (already was)
    assert initial["message_text"].lstrip()[0].isupper()
    # No leftover ".lowercase" glue patterns from the LLM (capitalization fixed)
    # "olhei" appeared lowercase in the LLM text after ". " — should now be "Olhei"
    assert ". Olhei" in initial["message_text"] or "Olhei" in initial["message_text"]


# ---------------------------------------------------------------------------
# Scenario 3: no API key → fallback for all, no LLM call, no errors
# ---------------------------------------------------------------------------


@patch("app.pipeline.outreach.generator.requests.post")
def test_no_api_key_uses_fallback_with_no_errors(mock_post):
    """When llm_api_key is empty, no LLM call is attempted; all messages
    are fallback with status=pronta and validation_errors=None."""
    with patch.object(settings, "llm_api_key", ""):
        messages = generate_messages("pub-3", LEAD_WITH_DIAG, has_lp=False)

    assert mock_post.call_count == 0, "no LLM call should have been attempted"
    assert len(messages) == 5

    for msg in messages:
        assert msg["status"] == "pronta", (
            f"expected status=pronta for {msg['type']} (no LLM, no errors), got {msg['status']}"
        )
        assert msg["validation_errors"] is None, (
            f"expected validation_errors=None for {msg['type']}, got {msg['validation_errors']}"
        )
        assert msg["message_text"], "fallback should always produce non-empty text"
