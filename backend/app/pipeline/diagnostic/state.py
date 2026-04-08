"""Pydantic models for the diagnostic LangGraph state."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


NIVEL_KEYS = ["lp", "automacao_basica", "mapa_automacoes", "vertical_os"]

NivelKey = Literal["lp", "automacao_basica", "mapa_automacoes", "vertical_os"]


class NivelScore(BaseModel):
    """Score and analysis for a single service level."""

    score: int = Field(description="Score de 0 a 100")
    sinais: list[str] = Field(description="Evidências encontradas")
    oportunidades: list[str] = Field(description="O que pode ser oferecido")
    justificativa: str = Field(description="Por que esse score")

    @field_validator("score")
    @classmethod
    def clamp_score(cls, v: int) -> int:
        return max(0, min(100, v))


class ServiceLevelAnalysis(BaseModel):
    """Consolidated result from all 4 service level analyzers."""

    lp: NivelScore
    automacao_basica: NivelScore
    mapa_automacoes: NivelScore
    vertical_os: NivelScore
    nivel_recomendado: NivelKey
    qualificado: bool
    motivo_desqualificacao: str | None = None
    resumo_executivo: str


class GraphState(BaseModel):
    """LangGraph state that flows through the diagnostic graph."""

    # Input context (set by collect node)
    lead_info: dict
    site_data: dict
    html_analysis: dict
    pagespeed: dict
    html: str
    social_profiles: dict

    # Intermediate results (set by analyzer nodes)
    lp_result: NivelScore | None = None
    automacao_result: NivelScore | None = None
    advanced_result: NivelScore | None = None
    os_result: NivelScore | None = None

    # Final result (set by qualify node)
    final_result: ServiceLevelAnalysis | None = None
