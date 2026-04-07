"""Tests para o módulo de outreach (outreach.py)."""

import json
from unittest.mock import patch, MagicMock

import pytest

from app.pipeline.outreach import (
    _clean_phone,
    _generate_ai_message,
    _get_diagnostic,
    generate_messages,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_LEAD_DATA = {
    "nome": "Odonto Sorriso",
    "telefone": "49999887766",
    "website": "https://odontosorriso.com.br",
    "nicho": "dentista",
    "rating": 4.7,
    "reviews_count": 123,
    "opportunity_reasons": ["Sem HTTPS/SSL", "Sem chatbot"],
    "site_analysis": {
        "status": "ok",
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

SAMPLE_LEAD_DATA_NO_DIAG = {
    "nome": "Pet Shop Feliz",
    "telefone": "(49) 99988-7766",
    "website": None,
    "nicho": "pet shop",
    "rating": 4.2,
    "reviews_count": 45,
    "opportunity_reasons": [],
    "site_analysis": {"status": "no_website"},
}

SAMPLE_LEAD_DATA_MINIMAL = {
    "telefone": "49999887766",
    "site_analysis": {},
}


# ---------------------------------------------------------------------------
# Tests: _clean_phone
# ---------------------------------------------------------------------------

class TestCleanPhone:
    def test_simple_number(self):
        assert _clean_phone("49999887766") == "5549999887766"

    def test_with_country_code(self):
        assert _clean_phone("+5549999887766") == "5549999887766"

    def test_with_formatting(self):
        assert _clean_phone("(49) 99988-7766") == "5549999887766"

    def test_empty_phone(self):
        assert _clean_phone("") == ""

    def test_none_phone(self):
        assert _clean_phone(None) == ""


# ---------------------------------------------------------------------------
# Tests: _get_diagnostic
# ---------------------------------------------------------------------------

class TestGetDiagnostic:
    def test_with_diagnostic(self):
        diag = _get_diagnostic(SAMPLE_LEAD_DATA)
        assert diag is not None
        assert diag["momento_funil"] == "descoberta"

    def test_without_diagnostic(self):
        assert _get_diagnostic(SAMPLE_LEAD_DATA_NO_DIAG) is None

    def test_empty_site_analysis(self):
        assert _get_diagnostic({"site_analysis": {}}) is None

    def test_missing_site_analysis(self):
        assert _get_diagnostic({}) is None


# ---------------------------------------------------------------------------
# Tests: _generate_ai_message
# ---------------------------------------------------------------------------

class TestGenerateAiMessage:
    @patch("app.pipeline.outreach.settings")
    def test_returns_none_without_api_key(self, mock_settings):
        mock_settings.llm_api_key = ""
        result = _generate_ai_message(SAMPLE_LEAD_DATA, "http://lp.url", "initial")
        assert result is None

    @patch("app.pipeline.outreach.settings")
    def test_returns_none_without_diagnostic(self, mock_settings):
        mock_settings.llm_api_key = "test-key"
        result = _generate_ai_message(SAMPLE_LEAD_DATA_NO_DIAG, "http://lp.url", "initial")
        assert result is None

    @patch("app.pipeline.outreach.settings")
    def test_returns_none_for_unknown_type(self, mock_settings):
        mock_settings.llm_api_key = "test-key"
        result = _generate_ai_message(SAMPLE_LEAD_DATA, "http://lp.url", "unknown_type")
        assert result is None

    @patch("app.pipeline.outreach.settings")
    @patch("app.pipeline.outreach.requests.post")
    def test_success_initial(self, mock_post, mock_settings):
        mock_settings.llm_api_key = "test-key"
        mock_settings.llm_base_url = "https://api.minimax.io/v1"
        mock_settings.your_name = "João"
        mock_settings.business_name = "Studio Digital"
        mock_settings.your_website = "https://studio.com"
        mock_settings.diagnostic_model = ""
        mock_settings.llm_model = "MiniMax-M2.7"

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Oi! Tudo bem? Vi a Odonto Sorriso no Google Maps..."}}]
        }
        mock_post.return_value = mock_resp

        result = _generate_ai_message(SAMPLE_LEAD_DATA, "http://lp.url", "initial")
        assert result is not None
        assert "Odonto Sorriso" in result
        mock_post.assert_called_once()

    @patch("app.pipeline.outreach.settings")
    @patch("app.pipeline.outreach.requests.post")
    def test_strips_quotes_from_response(self, mock_post, mock_settings):
        mock_settings.llm_api_key = "test-key"
        mock_settings.llm_base_url = "https://api.minimax.io/v1"
        mock_settings.your_name = "João"
        mock_settings.business_name = "Studio"
        mock_settings.your_website = "https://studio.com"
        mock_settings.diagnostic_model = ""
        mock_settings.llm_model = "MiniMax-M2.7"

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": '"Oi! Mensagem com aspas"'}}]
        }
        mock_post.return_value = mock_resp

        result = _generate_ai_message(SAMPLE_LEAD_DATA, "http://lp.url", "initial")
        assert not result.startswith('"')
        assert not result.endswith('"')

    @patch("app.pipeline.outreach.settings")
    @patch("app.pipeline.outreach.requests.post")
    def test_api_failure_returns_none(self, mock_post, mock_settings):
        mock_settings.llm_api_key = "test-key"
        mock_settings.llm_base_url = "https://api.minimax.io/v1"
        mock_settings.diagnostic_model = ""
        mock_settings.llm_model = "MiniMax-M2.7"
        mock_post.side_effect = Exception("API timeout")

        result = _generate_ai_message(SAMPLE_LEAD_DATA, "http://lp.url", "initial")
        assert result is None

    @patch("app.pipeline.outreach.settings")
    @patch("app.pipeline.outreach.requests.post")
    def test_handles_missing_nome_gracefully(self, mock_post, mock_settings):
        """lead_data without 'nome' key should not crash."""
        mock_settings.llm_api_key = "test-key"
        mock_settings.llm_base_url = "https://api.minimax.io/v1"
        mock_settings.your_name = "João"
        mock_settings.business_name = "Studio"
        mock_settings.your_website = "https://studio.com"
        mock_settings.diagnostic_model = ""
        mock_settings.llm_model = "MiniMax-M2.7"

        lead_data = {
            "site_analysis": SAMPLE_LEAD_DATA["site_analysis"],
        }

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Oi! Tudo bem?"}}]
        }
        mock_post.return_value = mock_resp

        # Should not raise KeyError
        result = _generate_ai_message(lead_data, "http://lp.url", "initial")
        assert result is not None


# ---------------------------------------------------------------------------
# Tests: generate_messages
# ---------------------------------------------------------------------------

class TestGenerateMessages:
    @patch("app.pipeline.outreach._generate_ai_message")
    def test_with_diagnostic_uses_ai(self, mock_ai):
        mock_ai.return_value = "AI generated message"

        messages = generate_messages(1, SAMPLE_LEAD_DATA)

        assert len(messages) == 3
        assert messages[0]["type"] == "initial"
        assert messages[1]["type"] == "followup_48h"
        assert messages[2]["type"] == "followup_final"
        # AI was called for all 3 types
        assert mock_ai.call_count == 3
        assert messages[0]["message_text"] == "AI generated message"

    def test_without_diagnostic_uses_templates(self):
        messages = generate_messages(1, SAMPLE_LEAD_DATA_NO_DIAG)

        assert len(messages) == 3
        assert messages[0]["type"] == "initial"
        # Should use sem_site fallback (no website)
        assert "site" in messages[0]["message_text"].lower() or "Maps" in messages[0]["message_text"]

    @patch("app.pipeline.outreach._generate_ai_message")
    def test_ai_failure_falls_back(self, mock_ai):
        """When AI returns None, should fall back to templates."""
        mock_ai.return_value = None

        messages = generate_messages(1, SAMPLE_LEAD_DATA)

        assert len(messages) == 3
        # Template-based messages should exist
        assert len(messages[0]["message_text"]) > 0

    def test_whatsapp_links_generated(self):
        messages = generate_messages(1, SAMPLE_LEAD_DATA)

        for msg in messages:
            assert msg["whatsapp_link"].startswith("https://wa.me/5549999887766")

    def test_empty_phone_no_whatsapp_link(self):
        data = {**SAMPLE_LEAD_DATA, "telefone": ""}
        messages = generate_messages(1, data)

        for msg in messages:
            assert msg["whatsapp_link"] == ""

    def test_minimal_lead_data_doesnt_crash(self):
        """generate_messages should handle minimal lead data without crashing."""
        messages = generate_messages(1, SAMPLE_LEAD_DATA_MINIMAL)

        assert len(messages) == 3
        for msg in messages:
            assert msg["message_text"]
