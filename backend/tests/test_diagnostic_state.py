"""Tests for diagnostic Pydantic state models."""

import pytest
from pydantic import ValidationError

from app.pipeline.diagnostic.state import (
    NivelScore,
    ServiceLevelAnalysis,
    GraphState,
    NIVEL_KEYS,
)


class TestNivelScore:
    def test_valid(self):
        ns = NivelScore(
            score=75,
            sinais=["Sem site"],
            oportunidades=["LP responsiva"],
            justificativa="Negócio sem presença digital.",
        )
        assert ns.score == 75
        assert len(ns.sinais) == 1

    def test_score_clamped_above_100(self):
        ns = NivelScore(
            score=150,
            sinais=[],
            oportunidades=[],
            justificativa="test",
        )
        assert ns.score == 100

    def test_score_clamped_below_0(self):
        ns = NivelScore(
            score=-10,
            sinais=[],
            oportunidades=[],
            justificativa="test",
        )
        assert ns.score == 0


class TestServiceLevelAnalysis:
    def _make_nivel(self, score: int) -> NivelScore:
        return NivelScore(
            score=score,
            sinais=["sinal"],
            oportunidades=["opp"],
            justificativa="just",
        )

    def test_valid(self):
        sla = ServiceLevelAnalysis(
            lp=self._make_nivel(80),
            automacao_basica=self._make_nivel(60),
            mapa_automacoes=self._make_nivel(40),
            vertical_os=self._make_nivel(15),
            nivel_recomendado="lp",
            qualificado=True,
            motivo_desqualificacao=None,
            resumo_executivo="Resumo do lead.",
        )
        assert sla.nivel_recomendado == "lp"
        assert sla.qualificado is True

    def test_invalid_nivel_recomendado(self):
        with pytest.raises(ValidationError):
            ServiceLevelAnalysis(
                lp=self._make_nivel(80),
                automacao_basica=self._make_nivel(60),
                mapa_automacoes=self._make_nivel(40),
                vertical_os=self._make_nivel(15),
                nivel_recomendado="invalid_level",
                qualificado=True,
                motivo_desqualificacao=None,
                resumo_executivo="Resumo.",
            )


class TestNivelKeys:
    def test_order(self):
        assert NIVEL_KEYS == ["lp", "automacao_basica", "mapa_automacoes", "vertical_os"]


class TestGraphState:
    def test_defaults(self):
        state = GraphState(
            lead_info={"nome": "Test"},
            site_data={"status": "ok"},
            html_analysis={},
            pagespeed={},
            html="<html></html>",
            social_profiles={},
        )
        assert state.lp_result is None
        assert state.automacao_result is None
        assert state.advanced_result is None
        assert state.os_result is None
        assert state.final_result is None
