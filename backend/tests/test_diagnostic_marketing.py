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


def test_marketing_node_extracts_json_with_prose_around():
    """LLM frequentemente adiciona texto antes/depois do JSON sem fence — extrair mesmo assim."""
    mock_response = MagicMock()
    mock_response.content = (
        "Aqui vai o diagnóstico do negócio:\n\n"
        f"{json.dumps(VALID_JSON)}\n\n"
        "Espero que ajude!"
    )

    with patch("app.pipeline.diagnostic.nodes.marketing._get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        result = analyze_marketing(_base_state())

    md = result["marketing_result"]
    assert isinstance(md, MarketingDiagnostic)
    assert md.momento_funil == "descoberta"


def test_marketing_node_handles_braces_inside_string_values():
    """O extrator de JSON balanceado precisa respeitar strings (chaves dentro de aspas não contam)."""
    payload = dict(VALID_JSON)
    payload["resumo_executivo"] = "Negócio com {chaves} dentro do texto e } solto."
    mock_response = MagicMock()
    mock_response.content = f"Resposta:\n{json.dumps(payload)}\nFim."

    with patch("app.pipeline.diagnostic.nodes.marketing._get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        result = analyze_marketing(_base_state())

    md = result["marketing_result"]
    assert isinstance(md, MarketingDiagnostic)
    assert "{chaves}" in md.resumo_executivo


def test_marketing_node_logs_response_preview_on_failure(caplog):
    """Quando JSON é irrecuperável, log deve incluir tamanho da resposta + head/tail
    pra permitir diagnóstico sem precisar reproduzir o lead."""
    mock_response = MagicMock()
    mock_response.content = "ABCDEFGH" * 200 + "{ broken json here"  # 1600+ chars, no closing

    with patch("app.pipeline.diagnostic.nodes.marketing._get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        with caplog.at_level("ERROR", logger="app.pipeline.diagnostic.nodes.marketing"):
            result = analyze_marketing(_base_state())

    assert result == {"marketing_result": None}
    log_text = caplog.text
    assert "resp_len=" in log_text
    # Should mention the actual size
    assert str(len(mock_response.content)) in log_text


def test_marketing_node_redacts_phone_like_digits_in_log(caplog):
    """LGPD: telefone/CPF não devem vazar em log de diagnóstico, mesmo que o
    LLM ecoe esses campos do prompt na resposta."""
    mock_response = MagicMock()
    # Resposta truncada com um telefone visível
    mock_response.content = (
        '{"resumo_executivo": "Negócio em Porto Alegre, contato 5133110406, '
        'cnpj 12345678000190 — site fraco, broken'
    )

    with patch("app.pipeline.diagnostic.nodes.marketing._get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        with caplog.at_level("ERROR", logger="app.pipeline.diagnostic.nodes.marketing"):
            result = analyze_marketing(_base_state())

    assert result == {"marketing_result": None}
    # Os digitos longos devem estar mascarados
    assert "5133110406" not in caplog.text
    assert "12345678000190" not in caplog.text
    # Mas o resto do contexto (texto curto, palavras) ainda aparece
    assert "Porto Alegre" in caplog.text


def test_marketing_node_short_response_logged_inline(caplog):
    """Quando resp_len ≤ 400, head/tail se sobrepõem — logar inteiro pra
    evitar duplicação."""
    mock_response = MagicMock()
    mock_response.content = "resposta curta e quebrada"  # < 400

    with patch("app.pipeline.diagnostic.nodes.marketing._get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        with caplog.at_level("ERROR", logger="app.pipeline.diagnostic.nodes.marketing"):
            result = analyze_marketing(_base_state())

    assert result == {"marketing_result": None}
    log_text = caplog.text
    # No "head=" nem "tail=" para resposta curta — só "resp="
    assert "resp_len=" in log_text
    assert "head=" not in log_text
    assert "tail=" not in log_text
    assert "resp=" in log_text
