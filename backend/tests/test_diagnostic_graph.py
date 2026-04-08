"""Tests for the diagnostic LangGraph graph (end-to-end with mocked LLM)."""

from unittest.mock import patch, MagicMock

from app.pipeline.diagnostic.graph import run_diagnostic
from app.pipeline.diagnostic.state import NivelScore, ServiceLevelAnalysis


SAMPLE_LEAD_INFO = {
    "nome": "Odonto Sorriso",
    "nicho": "dentista",
    "categoria": "Dentista",
    "cidade": "Chapecó SC",
    "rating": 4.7,
    "reviews_count": 123,
    "top_reviews": ["Excelente atendimento!"],
}


def _mock_nivel(score: int) -> NivelScore:
    return NivelScore(
        score=score,
        sinais=["sinal mock"],
        oportunidades=["opp mock"],
        justificativa="justificativa mock",
    )


class TestRunDiagnostic:
    @patch("app.pipeline.diagnostic.nodes.analyzers._run_analyzer")
    def test_returns_service_level_analysis(self, mock_analyzer):
        mock_analyzer.side_effect = [
            {"lp_result": _mock_nivel(80)},
            {"automacao_result": _mock_nivel(60)},
            {"advanced_result": _mock_nivel(40)},
            {"os_result": _mock_nivel(15)},
        ]

        result = run_diagnostic(
            lead_info=SAMPLE_LEAD_INFO,
            site_data={"status": "ok", "html": "<html></html>", "has_ssl": True},
            html_analysis={"has_responsive_meta": True},
            pagespeed={"performance_score": 70},
            html="<html></html>",
            social_profiles={},
        )

        assert isinstance(result, ServiceLevelAnalysis)
        assert result.lp.score == 80
        assert result.automacao_basica.score == 60
        assert result.qualificado is True
        assert result.nivel_recomendado in ("lp", "automacao_basica", "mapa_automacoes", "vertical_os")

    @patch("app.pipeline.diagnostic.graph.settings")
    def test_returns_none_when_no_api_key(self, mock_settings):
        mock_settings.llm_api_key = ""
        mock_settings.skip_service_level_analysis = False
        mock_settings.langsmith_tracing = False
        mock_settings.langsmith_api_key = ""
        mock_settings.langsmith_project = "sdr-machine"

        result = run_diagnostic(
            lead_info=SAMPLE_LEAD_INFO,
            site_data={"status": "ok"},
            html_analysis={},
            pagespeed={},
            html="",
            social_profiles={},
        )

        assert result is None

    @patch("app.pipeline.diagnostic.graph.settings")
    def test_returns_none_when_disabled(self, mock_settings):
        mock_settings.skip_service_level_analysis = True
        mock_settings.langsmith_tracing = False
        mock_settings.langsmith_api_key = ""
        mock_settings.langsmith_project = "sdr-machine"

        result = run_diagnostic(
            lead_info=SAMPLE_LEAD_INFO,
            site_data={},
            html_analysis={},
            pagespeed={},
            html="",
            social_profiles={},
        )

        assert result is None
