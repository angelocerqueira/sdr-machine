"""Tests para o módulo de enriquecimento (enricher.py)."""

import json
from unittest.mock import patch, MagicMock

import pytest

from app.pipeline.enricher import (
    analyze_html,
    calculate_score,
    _extract_visible_text,
    _parse_diagnostic_response,
    generate_diagnostic,
    enrich_lead_data,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="description" content="Clínica odontológica">
    <title>Odonto Sorriso</title>
    <script>window.dataLayer=[];</script>
</head>
<body>
    <a href="https://wa.me/5549999887766">WhatsApp</a>
    <a href="https://instagram.com/odontosorriso">Instagram</a>
    <button>Agende sua consulta</button>
    <img src="logo.png"><img src="foto.png"><img src="equipe.png">
    <p>Somos uma clínica odontológica com mais de 10 anos de experiência em Chapecó.</p>
</body>
</html>
"""

SAMPLE_DIAGNOSTIC_JSON = {
    "qualificado": True,
    "motivo_desqualificacao": None,
    "potencial_ia_automacao": {
        "score": 75,
        "oportunidades": ["Chatbot IA para agendamento", "Automação de follow-up"],
        "justificativa": "Clínica odontológica com alto volume de agendamentos.",
    },
    "momento_funil": "descoberta",
    "funil": {
        "descoberta": {
            "diagnostico": "Presença digital limitada.",
            "acoes_top2": [
                {"acao": "Otimizar GMN", "resultado_esperado": "+40% views", "kpi": "Views GMN"},
                {"acao": "Google Ads local", "resultado_esperado": "10 leads/mês", "kpi": "CPL"},
            ],
        },
        "atracao": {"diagnostico": "...", "acoes_top2": [{"acao": "a", "resultado_esperado": "b", "kpi": "c"}, {"acao": "d", "resultado_esperado": "e", "kpi": "f"}]},
        "consideracao": {"diagnostico": "...", "acoes_top2": [{"acao": "a", "resultado_esperado": "b", "kpi": "c"}, {"acao": "d", "resultado_esperado": "e", "kpi": "f"}]},
        "acao": {"diagnostico": "...", "acoes_top2": [{"acao": "a", "resultado_esperado": "b", "kpi": "c"}, {"acao": "d", "resultado_esperado": "e", "kpi": "f"}]},
        "apologia": {"diagnostico": "...", "acoes_top2": [{"acao": "a", "resultado_esperado": "b", "kpi": "c"}, {"acao": "d", "resultado_esperado": "e", "kpi": "f"}]},
    },
    "resumo_executivo": "Clínica com boa reputação mas presença digital fraca.",
    "prioridades_top3": ["Otimizar GMN", "Criar site", "Chatbot WhatsApp"],
}

SAMPLE_LEAD_INFO = {
    "nome": "Odonto Sorriso",
    "nicho": "dentista",
    "categoria": "Dentista",
    "cidade": "Chapecó SC",
    "rating": 4.7,
    "reviews_count": 123,
    "top_reviews": ["Excelente atendimento!", "Muito profissional"],
}


# ---------------------------------------------------------------------------
# Tests: analyze_html
# ---------------------------------------------------------------------------

class TestAnalyzeHtml:
    def test_full_html(self):
        result = analyze_html(SAMPLE_HTML)
        assert result["has_responsive_meta"] is True
        assert result["has_whatsapp_link"] is True
        assert result["has_social_links"] is True
        assert result["has_cta"] is True
        assert result["title"] == "Odonto Sorriso"
        assert result["description"] == "Clínica odontológica"
        assert result["image_count"] == 3
        assert result["word_count"] > 0

    def test_empty_html(self):
        result = analyze_html("")
        assert result["has_responsive_meta"] is False
        assert result["has_whatsapp_link"] is False
        assert result["has_cta"] is False
        assert result["title"] == ""
        assert result["word_count"] == 0


# ---------------------------------------------------------------------------
# Tests: calculate_score
# ---------------------------------------------------------------------------

class TestCalculateScore:
    def test_no_website(self):
        score, reasons = calculate_score(
            {"status": "no_website"}, {}, {}
        )
        assert score == 95
        assert "Sem website" in reasons[0]

    def test_connection_error(self):
        score, reasons = calculate_score(
            {"status": "connection_error"}, {}, {}
        )
        assert score == 85

    def test_good_site(self):
        score, _ = calculate_score(
            {"status": "ok", "has_ssl": True},
            {
                "has_responsive_meta": True,
                "has_whatsapp_link": True,
                "has_analytics": True,
                "has_chatbot": True,
                "has_cta": True,
                "word_count": 500,
                "is_template": False,
                "image_count": 10,
            },
            {"performance_score": 80},
        )
        assert score == 0

    def test_bad_site(self):
        score, reasons = calculate_score(
            {"status": "ok", "has_ssl": False},
            {
                "has_responsive_meta": False,
                "has_whatsapp_link": False,
                "has_analytics": False,
                "has_chatbot": False,
                "has_cta": False,
                "word_count": 50,
                "is_template": True,
                "image_count": 0,
            },
            {"performance_score": 30},
        )
        assert score >= 80
        assert len(reasons) >= 5


# ---------------------------------------------------------------------------
# Tests: _extract_visible_text
# ---------------------------------------------------------------------------

class TestExtractVisibleText:
    def test_extracts_text(self):
        text = _extract_visible_text(SAMPLE_HTML)
        assert "Odonto Sorriso" in text
        assert "clínica odontológica" in text
        assert "<script>" not in text

    def test_empty_html(self):
        assert _extract_visible_text("") == ""

    def test_truncates(self):
        big_html = "<p>" + "x" * 5000 + "</p>"
        assert len(_extract_visible_text(big_html)) <= 2000


# ---------------------------------------------------------------------------
# Tests: _parse_diagnostic_response
# ---------------------------------------------------------------------------

class TestParseDiagnosticResponse:
    def test_valid_json(self):
        result = _parse_diagnostic_response(json.dumps(SAMPLE_DIAGNOSTIC_JSON))
        assert result is not None
        assert result["qualificado"] is True
        assert result["momento_funil"] == "descoberta"
        assert result["potencial_ia_automacao"]["score"] == 75

    def test_json_with_markdown_fences(self):
        text = "```json\n" + json.dumps(SAMPLE_DIAGNOSTIC_JSON) + "\n```"
        result = _parse_diagnostic_response(text)
        assert result is not None
        assert result["qualificado"] is True

    def test_invalid_json(self):
        assert _parse_diagnostic_response("not json at all") is None

    def test_missing_keys(self):
        incomplete = {"qualificado": True}
        assert _parse_diagnostic_response(json.dumps(incomplete)) is None

    def test_invalid_momento_funil(self):
        bad = {**SAMPLE_DIAGNOSTIC_JSON, "momento_funil": "invalid_stage"}
        assert _parse_diagnostic_response(json.dumps(bad)) is None

    def test_invalid_score(self):
        bad = {**SAMPLE_DIAGNOSTIC_JSON}
        bad["potencial_ia_automacao"] = {**bad["potencial_ia_automacao"], "score": 150}
        assert _parse_diagnostic_response(json.dumps(bad)) is None


# ---------------------------------------------------------------------------
# Tests: generate_diagnostic
# ---------------------------------------------------------------------------

class TestGenerateDiagnostic:
    def _mock_claude_response(self, diagnostic_data):
        """Helper pra criar mock response da Claude API."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "content": [{"text": json.dumps(diagnostic_data)}]
        }
        return mock_resp

    @patch("app.pipeline.enricher.settings")
    @patch("app.pipeline.enricher.requests.post")
    def test_success(self, mock_post, mock_settings):
        mock_settings.skip_ai_diagnostic = False
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.diagnostic_model = ""
        mock_settings.claude_model = "claude-sonnet-4-20250514"
        mock_post.return_value = self._mock_claude_response(SAMPLE_DIAGNOSTIC_JSON)

        result = generate_diagnostic(
            lead_info=SAMPLE_LEAD_INFO,
            site_data={"status": "ok", "has_ssl": True},
            html_analysis={"has_responsive_meta": True},
            pagespeed={"performance_score": 70},
            html=SAMPLE_HTML,
        )

        assert result is not None
        assert result["qualificado"] is True
        assert result["potencial_ia_automacao"]["score"] == 75
        mock_post.assert_called_once()

    @patch("app.pipeline.enricher.settings")
    @patch("app.pipeline.enricher.requests.post")
    def test_api_failure_returns_none(self, mock_post, mock_settings):
        mock_settings.skip_ai_diagnostic = False
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.diagnostic_model = ""
        mock_settings.claude_model = "claude-sonnet-4-20250514"
        mock_post.side_effect = Exception("API timeout")

        result = generate_diagnostic(
            lead_info=SAMPLE_LEAD_INFO,
            site_data={"status": "ok"},
            html_analysis={},
            pagespeed={},
            html="",
        )

        assert result is None

    @patch("app.pipeline.enricher.settings")
    def test_skip_when_disabled(self, mock_settings):
        mock_settings.skip_ai_diagnostic = True

        result = generate_diagnostic(
            lead_info=SAMPLE_LEAD_INFO,
            site_data={},
            html_analysis={},
            pagespeed={},
            html="",
        )

        assert result is None

    @patch("app.pipeline.enricher.settings")
    def test_skip_when_no_api_key(self, mock_settings):
        mock_settings.skip_ai_diagnostic = False
        mock_settings.anthropic_api_key = ""

        result = generate_diagnostic(
            lead_info=SAMPLE_LEAD_INFO,
            site_data={},
            html_analysis={},
            pagespeed={},
            html="",
        )

        assert result is None


# ---------------------------------------------------------------------------
# Tests: enrich_lead_data
# ---------------------------------------------------------------------------

class TestEnrichLeadData:
    @patch("app.pipeline.enricher.generate_diagnostic")
    @patch("app.pipeline.enricher.check_pagespeed")
    @patch("app.pipeline.enricher.fetch_website")
    def test_with_diagnostic_qualified(self, mock_fetch, mock_pagespeed, mock_diag):
        mock_fetch.return_value = {"status": "ok", "html": SAMPLE_HTML, "has_ssl": True}
        mock_pagespeed.return_value = {"performance_score": 70}
        mock_diag.return_value = SAMPLE_DIAGNOSTIC_JSON

        result = enrich_lead_data("http://example.com", lead_info=SAMPLE_LEAD_INFO)

        assert result["qualified"] is True
        assert "diagnostico_marketing" in result["site_analysis"]
        assert result["site_analysis"]["diagnostico_marketing"]["momento_funil"] == "descoberta"

    @patch("app.pipeline.enricher.settings")
    @patch("app.pipeline.enricher.generate_diagnostic")
    @patch("app.pipeline.enricher.check_pagespeed")
    @patch("app.pipeline.enricher.fetch_website")
    def test_with_diagnostic_disqualified(self, mock_fetch, mock_pagespeed, mock_diag, mock_settings):
        mock_settings.ai_potential_threshold = 25
        mock_fetch.return_value = {"status": "ok", "html": SAMPLE_HTML, "has_ssl": True}
        mock_pagespeed.return_value = {"performance_score": 70}
        disqualified_diag = {
            **SAMPLE_DIAGNOSTIC_JSON,
            "qualificado": False,
            "motivo_desqualificacao": "Negócio muito informal",
            "potencial_ia_automacao": {**SAMPLE_DIAGNOSTIC_JSON["potencial_ia_automacao"], "score": 10},
        }
        mock_diag.return_value = disqualified_diag

        result = enrich_lead_data("http://example.com", lead_info=SAMPLE_LEAD_INFO)

        assert result["qualified"] is False
        assert "diagnostico_marketing" in result["site_analysis"]

    @patch("app.pipeline.enricher.generate_diagnostic")
    @patch("app.pipeline.enricher.check_pagespeed")
    @patch("app.pipeline.enricher.fetch_website")
    def test_diagnostic_failure_still_enriches(self, mock_fetch, mock_pagespeed, mock_diag):
        mock_fetch.return_value = {"status": "ok", "html": SAMPLE_HTML, "has_ssl": True}
        mock_pagespeed.return_value = {"performance_score": 70}
        mock_diag.return_value = None  # API failure

        result = enrich_lead_data("http://example.com", lead_info=SAMPLE_LEAD_INFO)

        assert result["qualified"] is True  # Default: qualified when no diagnostic
        assert "diagnostico_marketing" not in result["site_analysis"]
        assert result["opportunity_score"] is not None

    @patch("app.pipeline.enricher.fetch_website")
    def test_without_lead_info(self, mock_fetch):
        mock_fetch.return_value = {"status": "no_website", "html": ""}

        result = enrich_lead_data("", lead_info=None, skip_pagespeed=True)

        assert result["qualified"] is True
        assert result["opportunity_score"] == 95
        assert "diagnostico_marketing" not in result["site_analysis"]
