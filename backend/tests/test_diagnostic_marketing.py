"""Tests pro node analyze_marketing."""

import json
from unittest.mock import patch, MagicMock

from app.pipeline.diagnostic.state import GraphState, MarketingDiagnostic
from app.pipeline.diagnostic.nodes.marketing import analyze_marketing


VALID_JSON = {
    "resumo_executivo": "Negócio com boa reputação mas presença digital fraca.",
    "momento_funil": "descoberta",
    "potencial_ia_automacao": {
        "score": 75,
        "oportunidades": ["Chatbot WhatsApp", "Agendamento"],
        "justificativa": "Volume alto de contato manual.",
    },
    "prioridades_top3": ["Criar site", "WhatsApp Business", "Google Meu Negócio"],
    "funil": {
        "descoberta": {
            "diagnostico": "Sem site, só GMN.",
            "acoes_top2": [
                {"acao": "Criar site", "resultado_esperado": "+50% leads", "kpi": "leads/mês"},
                {"acao": "Otimizar GMN", "resultado_esperado": "+30% visualizações", "kpi": "views"},
            ],
        },
        "atracao": {
            "diagnostico": "Sem conteúdo.",
            "acoes_top2": [
                {"acao": "Blog posts", "resultado_esperado": "Tráfego orgânico", "kpi": "sessões"},
                {"acao": "Instagram Reels", "resultado_esperado": "Alcance", "kpi": "views"},
            ],
        },
        "consideracao": {
            "diagnostico": "Sem prova social.",
            "acoes_top2": [
                {"acao": "Testemunhos", "resultado_esperado": "+conversão", "kpi": "taxa"},
                {"acao": "Cases", "resultado_esperado": "Credibilidade", "kpi": "engajamento"},
            ],
        },
        "acao": {
            "diagnostico": "CTA fraco.",
            "acoes_top2": [
                {"acao": "WhatsApp CTA", "resultado_esperado": "+contato", "kpi": "msgs"},
                {"acao": "Formulário", "resultado_esperado": "+leads", "kpi": "leads"},
            ],
        },
        "apologia": {
            "diagnostico": "Sem pós-venda.",
            "acoes_top2": [
                {"acao": "Follow-up", "resultado_esperado": "+avaliações", "kpi": "reviews"},
                {"acao": "Indicações", "resultado_esperado": "+receita", "kpi": "indicações"},
            ],
        },
    },
}


def _base_state() -> GraphState:
    return GraphState(
        lead_info={"nome": "Test", "nicho": "teste", "cidade": "SP"},
        site_data={"status": "ok"},
        html_analysis={},
        pagespeed={},
        html="<html></html>",
        social_profiles={},
    )


def test_marketing_node_parses_valid_json():
    """Node retorna MarketingDiagnostic quando LLM devolve JSON válido."""
    mock_response = MagicMock()
    mock_response.content = json.dumps(VALID_JSON)

    with patch("app.pipeline.diagnostic.nodes.marketing._get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        result = analyze_marketing(_base_state())

    assert "marketing_result" in result
    md = result["marketing_result"]
    assert isinstance(md, MarketingDiagnostic)
    assert md.momento_funil == "descoberta"
    assert md.potencial_ia_automacao.score == 75
    assert len(md.prioridades_top3) == 3
    assert "descoberta" in md.funil


def test_marketing_node_returns_none_on_invalid_json():
    """Node retorna marketing_result=None quando LLM devolve JSON inválido."""
    mock_response = MagicMock()
    mock_response.content = "isso não é JSON"

    with patch("app.pipeline.diagnostic.nodes.marketing._get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        result = analyze_marketing(_base_state())

    assert result == {"marketing_result": None}


def test_marketing_node_strips_markdown_fences():
    """Node extrai JSON de dentro de ```json ... ```."""
    mock_response = MagicMock()
    mock_response.content = f"```json\n{json.dumps(VALID_JSON)}\n```"

    with patch("app.pipeline.diagnostic.nodes.marketing._get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        result = analyze_marketing(_base_state())

    md = result["marketing_result"]
    assert isinstance(md, MarketingDiagnostic)
