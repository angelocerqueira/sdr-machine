"""Tests for diagnostic graph nodes."""

from app.pipeline.diagnostic.state import NivelScore, GraphState
from app.pipeline.diagnostic.nodes.qualify import qualify


def _make_nivel(score: int) -> NivelScore:
    return NivelScore(
        score=score,
        sinais=["sinal"],
        oportunidades=["opp"],
        justificativa="just",
    )


def _make_state(**overrides) -> GraphState:
    defaults = dict(
        lead_info={"nome": "Test"},
        site_data={"status": "ok"},
        html_analysis={},
        pagespeed={},
        html="",
        social_profiles={},
        lp_result=_make_nivel(80),
        automacao_result=_make_nivel(60),
        advanced_result=_make_nivel(40),
        os_result=_make_nivel(15),
    )
    defaults.update(overrides)
    return GraphState(**defaults)


class TestQualify:
    def test_recommends_highest_viable_level(self):
        state = _make_state(
            lp_result=_make_nivel(50),
            automacao_result=_make_nivel(70),
            advanced_result=_make_nivel(45),
            os_result=_make_nivel(20),
        )
        result = qualify(state)
        final = result["final_result"]
        assert final.nivel_recomendado == "mapa_automacoes"
        assert final.qualificado is True

    def test_recommends_os_when_highest(self):
        state = _make_state(
            lp_result=_make_nivel(50),
            automacao_result=_make_nivel(60),
            advanced_result=_make_nivel(55),
            os_result=_make_nivel(80),
        )
        result = qualify(state)
        assert result["final_result"].nivel_recomendado == "vertical_os"

    def test_disqualifies_when_all_below_threshold(self):
        state = _make_state(
            lp_result=_make_nivel(10),
            automacao_result=_make_nivel(15),
            advanced_result=_make_nivel(5),
            os_result=_make_nivel(20),
        )
        result = qualify(state, disqualify_threshold=25)
        final = result["final_result"]
        assert final.qualificado is False
        assert final.motivo_desqualificacao is not None

    def test_fallback_to_highest_score_when_none_viable(self):
        state = _make_state(
            lp_result=_make_nivel(35),
            automacao_result=_make_nivel(30),
            advanced_result=_make_nivel(25),
            os_result=_make_nivel(10),
        )
        result = qualify(state, disqualify_threshold=25)
        final = result["final_result"]
        assert final.nivel_recomendado == "lp"
        assert final.qualificado is True

    def test_handles_missing_results(self):
        state = _make_state(
            lp_result=_make_nivel(70),
            automacao_result=None,
            advanced_result=None,
            os_result=None,
        )
        result = qualify(state)
        final = result["final_result"]
        assert final.nivel_recomendado == "lp"
        assert final.qualificado is True
        assert final.automacao_basica.score == 0

    def test_resumo_executivo_present(self):
        state = _make_state()
        result = qualify(state)
        assert len(result["final_result"].resumo_executivo) > 0


def test_qualify_includes_marketing_diagnostic():
    """Qualify repassa marketing_result pro final_result."""
    from app.pipeline.diagnostic.state import (
        MarketingDiagnostic, IAPotencial, FunnelStage, FunnelAction,
    )

    md = MarketingDiagnostic(
        resumo_executivo="Resumo.",
        momento_funil="descoberta",
        potencial_ia_automacao=IAPotencial(score=60, oportunidades=["x"], justificativa="y"),
        prioridades_top3=["a", "b", "c"],
        funil={
            "descoberta": FunnelStage(
                diagnostico="d",
                acoes_top2=[FunnelAction(acao="a1", resultado_esperado="r1", kpi="k1")],
            ),
        },
    )

    state = _make_state(marketing_result=md)
    result = qualify(state)

    final = result["final_result"]
    assert final.diagnostico_marketing is not None
    assert final.diagnostico_marketing.momento_funil == "descoberta"


def test_qualify_marketing_none_stays_none():
    """Quando marketing_result=None, diagnostico_marketing fica None."""
    state = _make_state(marketing_result=None)
    result = qualify(state)

    assert result["final_result"].diagnostico_marketing is None
