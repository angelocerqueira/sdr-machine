"""
Integration tests for the outreach generator pipeline (PR1.4 + PR2.3).

Verifies that ``generate_messages`` correctly wires:
- ``validators.validate_hard`` (post-LLM gate)
- ``validators.fix_capitalization`` / ``fix_punctuation_spacing`` (fixers)
- Taxonomy parser + validators (ÂNGULO / CTA, no-repeat per cadence)
- ``status`` + ``validation_errors`` + ``angulo_usado`` + ``cta_usado`` on each
  emitted message dict.
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


# Long body — passes ALL min_length thresholds (initial=180 is the strictest).
_BODY_TEXT = (
    "Oi! Vi a Odonto Sorriso no Google com 4.7 estrelas e 123 avaliacoes, "
    "presença local clara. olhei o site e o gap principal tá na captação "
    "de lead pelo mobile e em sinais de credibilidade no topo da página. "
    "faz sentido a gente trocar 10 min pra eu te mostrar dois ajustes "
    "rápidos? abraço, João."
)


def _wrap(angulo: str, cta: str, body: str = _BODY_TEXT) -> str:
    """Build a structured LLM response with ÂNGULO/CTA/TEXTO headers."""
    return f"ÂNGULO: {angulo}\nCTA: {cta}\nTEXTO:\n{body}"


# Valid response — distinct keys per toque so the cadence doesn't trip
# `taxonomy:angulo_repetido`. Order matches CADENCE_ORDER.
# CTAs from ctas.json:
#   initial:     pergunta_aberta_diagnostica, convite_10min, diagnostico_link, validacao_aberta
#   bump_d2:     chegou_a_ver, pergunta_nova_curta
#   insight_d5:  sem_cta, valeria_compartilhar
#   angle_d9:    reuniao_curta, diagnostico_link, pergunta_pivot, piloto_curto
#   breakup_d14: porta_aberta, sem_pressao, diagnostico_gratuito
_CADENCE_RESPONSES = [
    _wrap("seo",                 "convite_10min"),       # initial
    _wrap("reputacao",            "chegou_a_ver"),        # bump_d2
    _wrap("conversao",            "valeria_compartilhar"),# insight_d5
    _wrap("operacao",             "pergunta_pivot"),      # angle_d9
    _wrap("posicionamento",       "porta_aberta"),        # breakup_d14
]


# Same shape as _CADENCE_RESPONSES but body contains an XXXX placeholder —
# triggers placeholder hard-block in `validate_hard`.
_PLACEHOLDER_BODY = (
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


def _mock_sequence(texts: list[str]) -> list[MagicMock]:
    """Build a list of mock responses for `requests.post.side_effect`."""
    return [_build_mock_response(t) for t in texts]


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
    """LLM returns a body with XXXX placeholder for EVERY toque → all
    hard-blocked, fallback used, validation_errors persisted."""
    placeholder_resp = _wrap("seo", "convite_10min", body=_PLACEHOLDER_BODY)
    mock_post.return_value = _build_mock_response(placeholder_resp)

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
    # Taxonomy fields stay None on validation failure.
    assert initial["angulo_usado"] is None
    assert initial["cta_usado"] is None


# ---------------------------------------------------------------------------
# Scenario 2: valid LLM output → pronta, no errors, text comes from LLM
# ---------------------------------------------------------------------------


@patch("app.pipeline.outreach.generator.requests.post")
def test_valid_llm_output_is_persisted_with_status_pronta(mock_post):
    """LLM returns clean, long, well-punctuated text wrapped in the taxonomy
    headers → passes validators, fixers applied, status=pronta,
    validation_errors=None."""
    mock_post.side_effect = _mock_sequence(_CADENCE_RESPONSES)

    with patch.object(settings, "llm_api_key", "fake-key"):
        messages = generate_messages("pub-2", LEAD_WITH_DIAG, has_lp=False)

    assert len(messages) == 5

    initial = next(m for m in messages if m["type"] == "initial")
    assert initial["status"] == "pronta"
    assert initial["validation_errors"] is None
    # Came from the LLM (a distinctive substring of the body)
    assert "presença local clara" in initial["message_text"]
    # Fixers applied: first letter capitalized (already was)
    assert initial["message_text"].lstrip()[0].isupper()
    # LLM text had lowercase "olhei" after ". " — fix_capitalization must uppercase it
    assert ". Olhei" in initial["message_text"]
    assert ". olhei" not in initial["message_text"]
    # Taxonomy persisted.
    assert initial["angulo_usado"] == "seo"
    assert initial["cta_usado"] == "convite_10min"


# ---------------------------------------------------------------------------
# Scenario 3: no API key → fallback for all, no LLM call, no errors
# ---------------------------------------------------------------------------


@patch("app.pipeline.outreach.generator.requests.post")
def test_no_api_key_uses_fallback_with_no_errors(mock_post):
    """When llm_api_key is empty, no LLM call is attempted; all messages
    are fallback with status=pronta, validation_errors=None, and no taxonomy."""
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
        assert msg["angulo_usado"] is None
        assert msg["cta_usado"] is None


# ---------------------------------------------------------------------------
# Scenario 4 (PR2.3): cadence uses distinct ângulos for all 5 toques
# ---------------------------------------------------------------------------


@patch("app.pipeline.outreach.generator.requests.post")
def test_cadence_uses_distinct_angulos(mock_post):
    """All 5 toques succeed with distinct ângulo / cta keys."""
    mock_post.side_effect = _mock_sequence(_CADENCE_RESPONSES)

    with patch.object(settings, "llm_api_key", "fake-key"):
        messages = generate_messages("pub-4", LEAD_WITH_DIAG, has_lp=False)

    assert len(messages) == 5

    angulos = [m["angulo_usado"] for m in messages]
    statuses = [m["status"] for m in messages]

    # All ângulos present and distinct.
    assert all(a is not None for a in angulos), f"every message should have angulo_usado, got {angulos}"
    assert len(set(angulos)) == 5, f"all 5 ângulos should be distinct, got {angulos}"
    # All succeeded.
    assert statuses == ["pronta"] * 5, f"expected all pronta, got {statuses}"


# ---------------------------------------------------------------------------
# Scenario 5 (PR2.3): repeated ângulo across cadence → fallback on repeats
# ---------------------------------------------------------------------------


@patch("app.pipeline.outreach.generator.requests.post")
def test_repeated_angulo_triggers_fallback(mock_post):
    """If the LLM returns the same ângulo on every toque, message[0] succeeds
    and messages[1..4] fall back with `taxonomy:angulo_repetido:seo`."""
    # All 5 responses use ÂNGULO: seo (with distinct CTAs to avoid cta_repetido
    # interfering — we want to isolate the ângulo-repeat signal).
    distinct_ctas = [
        "convite_10min",          # initial
        "chegou_a_ver",           # bump_d2
        "valeria_compartilhar",   # insight_d5
        "pergunta_pivot",         # angle_d9
        "porta_aberta",           # breakup_d14
    ]
    repeats = [_wrap("seo", cta) for cta in distinct_ctas]
    mock_post.side_effect = _mock_sequence(repeats)

    with patch.object(settings, "llm_api_key", "fake-key"):
        messages = generate_messages("pub-5", LEAD_WITH_DIAG, has_lp=False)

    assert len(messages) == 5

    # First message accepts seo and records it.
    assert messages[0]["status"] == "pronta"
    assert messages[0]["angulo_usado"] == "seo"
    assert messages[0]["validation_errors"] is None

    # Remaining 4 are rejected for repeating seo → fallback.
    from app.pipeline.outreach.generator import _fallback, _build_context
    ctx = _build_context(LEAD_WITH_DIAG, has_lp=False, lp_url=None)

    for i in range(1, 5):
        msg = messages[i]
        assert msg["status"] == "erro_geracao", (
            f"toque {i} ({msg['type']}) should be erro_geracao, got {msg['status']}"
        )
        assert msg["validation_errors"], f"toque {i} should have errors"
        assert "taxonomy:angulo_repetido:seo" in msg["validation_errors"], (
            f"toque {i} errors should include taxonomy:angulo_repetido:seo, got {msg['validation_errors']}"
        )
        # Body comes from fallback templates (not the LLM body).
        expected_fallback = _fallback(ctx, msg["type"])
        assert msg["message_text"] == expected_fallback, (
            f"toque {i} body should match the deterministic fallback"
        )
        assert msg["angulo_usado"] is None
        assert msg["cta_usado"] is None


# ---------------------------------------------------------------------------
# Scenario 6 (PR2.3): missing ÂNGULO header → fallback with taxonomy:angulo_ausente
# ---------------------------------------------------------------------------


@patch("app.pipeline.outreach.generator.requests.post")
def test_missing_angulo_header_triggers_fallback(mock_post):
    """LLM returns text without the ÂNGULO: line → taxonomy:angulo_ausente."""
    bad_response = f"CTA: convite_10min\nTEXTO:\n{_BODY_TEXT}"
    mock_post.return_value = _build_mock_response(bad_response)

    with patch.object(settings, "llm_api_key", "fake-key"):
        messages = generate_messages("pub-6", LEAD_WITH_DIAG, has_lp=False)

    initial = next(m for m in messages if m["type"] == "initial")
    assert initial["status"] == "erro_geracao"
    assert initial["validation_errors"], "expected non-empty validation_errors"
    assert "taxonomy:angulo_ausente" in initial["validation_errors"]
    assert initial["angulo_usado"] is None


# ---------------------------------------------------------------------------
# Scenario 7 (PR2.3): invalid ângulo key → fallback with taxonomy:angulo_invalido
# ---------------------------------------------------------------------------


@patch("app.pipeline.outreach.generator.requests.post")
def test_invalid_angulo_key_triggers_fallback(mock_post):
    """LLM returns ÂNGULO: bogus → taxonomy:angulo_invalido:bogus error."""
    bad_response = _wrap("bogus", "convite_10min")
    mock_post.return_value = _build_mock_response(bad_response)

    with patch.object(settings, "llm_api_key", "fake-key"):
        messages = generate_messages("pub-7", LEAD_WITH_DIAG, has_lp=False)

    initial = next(m for m in messages if m["type"] == "initial")
    assert initial["status"] == "erro_geracao"
    assert initial["validation_errors"], "expected non-empty validation_errors"
    assert "taxonomy:angulo_invalido:bogus" in initial["validation_errors"]
    assert initial["angulo_usado"] is None
