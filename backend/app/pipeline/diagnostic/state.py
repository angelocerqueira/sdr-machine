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


FALLBACK_NIVEL = NivelScore(
    score=0,
    sinais=["Análise indisponível"],
    oportunidades=[],
    justificativa="Falha na análise — resultado indisponível.",
)


class FunnelAction(BaseModel):
    """Uma ação sugerida pra uma etapa do funil."""
    acao: str
    resultado_esperado: str
    kpi: str


class FunnelStage(BaseModel):
    """Diagnóstico + ações top 2 pra uma etapa do funil."""
    diagnostico: str
    acoes_top2: list[FunnelAction] = Field(default_factory=list, max_length=2)


class IAPotencial(BaseModel):
    """Score e oportunidades de IA/automação."""
    score: int = Field(ge=0, le=100)
    oportunidades: list[str] = Field(default_factory=list)
    justificativa: str

    @field_validator("score")
    @classmethod
    def clamp(cls, v: int) -> int:
        return max(0, min(100, v))


MomentoFunil = Literal["descoberta", "atracao", "consideracao", "acao", "apologia"]


class MarketingDiagnostic(BaseModel):
    """Diagnóstico de marketing completo gerado por LLM."""
    resumo_executivo: str
    momento_funil: MomentoFunil
    potencial_ia_automacao: IAPotencial
    prioridades_top3: list[str] = Field(default_factory=list, max_length=3)
    funil: dict[str, FunnelStage] = Field(default_factory=dict)


class ServiceLevelAnalysis(BaseModel):
    """Consolidated result from all 4 service level analyzers + marketing diagnostic."""

    lp: NivelScore
    automacao_basica: NivelScore
    mapa_automacoes: NivelScore
    vertical_os: NivelScore
    nivel_recomendado: NivelKey
    qualificado: bool
    motivo_desqualificacao: str | None = None
    resumo_executivo: str
    diagnostico_marketing: MarketingDiagnostic | None = None


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
    marketing_result: MarketingDiagnostic | None = None

    # Final result (set by qualify node)
    final_result: ServiceLevelAnalysis | None = None
