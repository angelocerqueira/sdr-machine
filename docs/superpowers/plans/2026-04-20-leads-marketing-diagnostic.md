# Marketing Diagnostic + Tab Estratégia — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restaurar geração do `diagnostico_marketing` no pipeline diagnostic (novo node LLM) e expor no Lead App via tab nova "Estratégia" (reusa `DiagnosticPanel` existente).

**Architecture:** Novo node `analyze_marketing` roda em paralelo com os 4 analyzers no LangGraph existente. `qualify` consolida no `ServiceLevelAnalysis` que agora inclui `diagnostico_marketing`. Enricher grava em `site_analysis["diagnostico_marketing"]` pra manter compat com generator/outreach que já leem daí. Frontend ganha tab "Estratégia" que wrappa o `DiagnosticPanel` existente. Spec: `docs/superpowers/specs/2026-04-20-leads-marketing-diagnostic-design.md`.

**Tech Stack:** Python 3.12 / LangGraph / LangChain OpenAI / Pydantic 2, Next.js 16 / React 19 / TypeScript.

---

## File Structure

**Backend:**
- `backend/app/pipeline/diagnostic/state.py` — novos modelos Pydantic (`MarketingDiagnostic` etc.)
- `backend/app/pipeline/diagnostic/prompts/marketing.py` — novo, prompt + builder
- `backend/app/pipeline/diagnostic/nodes/marketing.py` — novo, node `analyze_marketing`
- `backend/app/pipeline/diagnostic/graph.py` — adicionar node + edges
- `backend/app/pipeline/diagnostic/nodes/qualify.py` — ler `marketing_result` e popular no final
- `backend/app/pipeline/enricher.py` — gravar `diagnostico_marketing` em `site_analysis`
- `backend/tests/test_diagnostic_marketing.py` — novo, testes do node
- `backend/tests/test_diagnostic_nodes.py` — +1 caso de integração
- `backend/tests/test_enricher.py` — +1 caso

**Frontend:**
- `frontend/src/components/leads/lead-app-types.ts` — expor `diagnostico_marketing` no `LeadAppDetail`
- `frontend/src/components/leads/la-tab-strategy.tsx` — novo, wrapper do DiagnosticPanel
- `frontend/src/components/leads/lead-app-mock.ts` — adicionar tab "strategy" + action
- `frontend/src/app/app/leads/[id]/page.tsx` — mapToDetail + tabContent

---

## Task 1: Modelos Pydantic pro diagnóstico de marketing

**Files:**
- Modify: `backend/app/pipeline/diagnostic/state.py`

- [ ] **Step 1: Adicionar imports necessários**

No topo de `state.py`, se ainda não tiver, garantir:

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator
```

- [ ] **Step 2: Adicionar modelos após `FALLBACK_NIVEL`**

Após a linha `FALLBACK_NIVEL = NivelScore(...)` (linha ~34), adicionar:

```python
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
```

- [ ] **Step 3: Adicionar campo em `ServiceLevelAnalysis`**

Substituir a definição de `ServiceLevelAnalysis` (linhas ~37-47) por:

```python
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
```

- [ ] **Step 4: Adicionar campo em `GraphState`**

No final da classe `GraphState` (linhas ~65-68), após `os_result`, adicionar:

```python
    # Marketing diagnostic result (set by marketing node)
    marketing_result: MarketingDiagnostic | None = None
```

Bloco final da classe fica:

```python
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
```

- [ ] **Step 5: Rodar pytest pra garantir que modelos compilam**

```bash
cd backend && pytest tests/test_diagnostic_state.py -v
```

Expected: PASS (testes existentes ainda passam). Se falhar, tipos estão inconsistentes.

- [ ] **Step 6: Commit**

```bash
git add backend/app/pipeline/diagnostic/state.py
git commit -m "feat(diagnostic): add MarketingDiagnostic model + funnel stages

Introduce FunnelAction, FunnelStage, IAPotencial, MarketingDiagnostic.
GraphState gains marketing_result; ServiceLevelAnalysis gains
diagnostico_marketing (Optional — backward compat).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Prompt do marketing diagnostic

**Files:**
- Create: `backend/app/pipeline/diagnostic/prompts/marketing.py`

- [ ] **Step 1: Criar arquivo com system prompt + builder**

Criar `backend/app/pipeline/diagnostic/prompts/marketing.py`:

```python
"""Prompt pro node de diagnóstico de marketing (funil completo)."""

MARKETING_SYSTEM_PROMPT = """Você é um estrategista de marketing sênior para negócios locais brasileiros.
Analisa o contexto fornecido e produz um diagnóstico de marketing completo, acionável e específico ao negócio.
Evite genérico; use dados concretos da análise. Português do Brasil."""


MARKETING_JSON_INSTRUCTION = """

IMPORTANTE: Responda APENAS com JSON válido no formato exato abaixo, sem texto adicional, sem markdown fences.
{
  "resumo_executivo": "<2-3 frases sobre o estado geral do negócio>",
  "momento_funil": "<descoberta|atracao|consideracao|acao|apologia>",
  "potencial_ia_automacao": {
    "score": <0-100>,
    "oportunidades": ["<oportunidade curta>", ...],
    "justificativa": "<por que esse score>"
  },
  "prioridades_top3": ["<prioridade 1>", "<prioridade 2>", "<prioridade 3>"],
  "funil": {
    "descoberta":   {"diagnostico": "<...>", "acoes_top2": [{"acao":"<...>","resultado_esperado":"<...>","kpi":"<...>"}, {...}]},
    "atracao":      {"diagnostico": "<...>", "acoes_top2": [{...}, {...}]},
    "consideracao": {"diagnostico": "<...>", "acoes_top2": [{...}, {...}]},
    "acao":         {"diagnostico": "<...>", "acoes_top2": [{...}, {...}]},
    "apologia":     {"diagnostico": "<...>", "acoes_top2": [{...}, {...}]}
  }
}"""


def build_marketing_prompt(context: str) -> str:
    """Monta o user prompt com o contexto compartilhado."""
    return f"""{context}

TAREFA:
1. Identifique o momento atual do negócio no funil de marketing (descoberta, atracao, consideracao, acao, apologia). Escolha UMA etapa — a que melhor descreve o estado atual.
2. Avalie o potencial de IA e automação (score 0-100, oportunidades específicas, justificativa).
3. Liste as 3 prioridades de curto prazo (acionáveis, específicas).
4. Para cada uma das 5 etapas do funil, produza:
   - diagnóstico curto da situação atual
   - 2 ações top (com resultado esperado e KPI)
5. Escreva um resumo executivo em 2-3 frases.

Seja específico ao negócio — use o nome, nicho, cidade, dados do site, redes sociais. NÃO seja genérico.{MARKETING_JSON_INSTRUCTION}"""
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/pipeline/diagnostic/prompts/marketing.py
git commit -m "feat(diagnostic): add marketing prompt template

Single-shot prompt that emits MarketingDiagnostic JSON:
resumo, momento_funil, potencial_ia_automacao, prioridades_top3,
funil (5 stages × 2 actions each).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Node `analyze_marketing`

**Files:**
- Create: `backend/app/pipeline/diagnostic/nodes/marketing.py`
- Test: `backend/tests/test_diagnostic_marketing.py`

- [ ] **Step 1: Criar teste failing pra parse de JSON válido**

Criar `backend/tests/test_diagnostic_marketing.py`:

```python
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
```

- [ ] **Step 2: Run — deve falhar (módulo não existe)**

```bash
cd backend && pytest tests/test_diagnostic_marketing.py -v
```

Expected: FAIL com `ModuleNotFoundError: No module named 'app.pipeline.diagnostic.nodes.marketing'`.

- [ ] **Step 3: Implementar node**

Criar `backend/app/pipeline/diagnostic/nodes/marketing.py`:

```python
"""Marketing diagnostic node — produces full funnel analysis via LLM."""

import json
import logging
import re

from langchain_openai import ChatOpenAI

from app.config import settings
from app.pipeline.diagnostic.state import GraphState, MarketingDiagnostic
from app.pipeline.diagnostic.prompts.shared import format_lead_context
from app.pipeline.diagnostic.prompts.marketing import (
    MARKETING_SYSTEM_PROMPT,
    build_marketing_prompt,
)
from app.pipeline.html_utils import _extract_visible_text

logger = logging.getLogger(__name__)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def _get_llm() -> ChatOpenAI:
    """Create a ChatOpenAI instance pointing at the configured LLM provider."""
    model = settings.diagnostic_model or settings.llm_model
    return ChatOpenAI(
        model=model,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        max_tokens=6000,  # prompt é denso — 5 etapas × 2 ações
        timeout=90,
    )


def _parse_response(text: str) -> MarketingDiagnostic:
    """Parse LLM response into MarketingDiagnostic."""
    cleaned = _THINK_RE.sub("", text).strip()
    match = _JSON_BLOCK_RE.search(cleaned)
    if match:
        cleaned = match.group(1).strip()
    return MarketingDiagnostic(**json.loads(cleaned))


def analyze_marketing(state: GraphState) -> dict:
    """Run marketing diagnostic LLM call and parse JSON."""
    try:
        llm = _get_llm()
        visible_text = _extract_visible_text(state.html)
        context = format_lead_context(
            lead_info=state.lead_info,
            site_data=state.site_data,
            html_analysis=state.html_analysis,
            pagespeed=state.pagespeed,
            visible_text=visible_text,
            social_profiles=state.social_profiles,
        )
        user_prompt = build_marketing_prompt(context)
        response = llm.invoke([
            {"role": "system", "content": MARKETING_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ])
        result = _parse_response(response.content)
        return {"marketing_result": result}
    except Exception:
        logger.exception("Marketing analyzer failed")
        return {"marketing_result": None}
```

- [ ] **Step 4: Run — devem passar**

```bash
cd backend && pytest tests/test_diagnostic_marketing.py -v
```

Expected: PASS (3 testes).

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/diagnostic/nodes/marketing.py backend/tests/test_diagnostic_marketing.py
git commit -m "feat(diagnostic): add analyze_marketing LLM node + tests

Calls LLM once with full context, parses JSON into MarketingDiagnostic.
Returns {marketing_result: None} on failure (isolated from other
analyzers). Tested: valid JSON, invalid JSON, markdown-fenced JSON.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Integrar no LangGraph

**Files:**
- Modify: `backend/app/pipeline/diagnostic/graph.py`

- [ ] **Step 1: Adicionar import**

Em `graph.py` linha ~12, após o import dos outros analyzers, adicionar:

```python
from app.pipeline.diagnostic.nodes.marketing import analyze_marketing
```

- [ ] **Step 2: Adicionar node + edges**

Em `_build_graph()` (linhas ~29-55), substituir o bloco inteiro por:

```python
def _build_graph() -> StateGraph:
    """Build the diagnostic StateGraph with parallel analyzer fan-out."""
    graph = StateGraph(GraphState)

    # Add nodes
    graph.add_node("analyze_lp", analyze_lp)
    graph.add_node("analyze_automation", analyze_automation)
    graph.add_node("analyze_advanced", analyze_advanced)
    graph.add_node("analyze_os", analyze_os)
    graph.add_node("analyze_marketing", analyze_marketing)
    graph.add_node("qualify", qualify)

    # Fan-out: START → all 5 analyzers in parallel
    graph.add_edge(START, "analyze_lp")
    graph.add_edge(START, "analyze_automation")
    graph.add_edge(START, "analyze_advanced")
    graph.add_edge(START, "analyze_os")
    graph.add_edge(START, "analyze_marketing")

    # Fan-in: all 5 analyzers → qualify
    graph.add_edge("analyze_lp", "qualify")
    graph.add_edge("analyze_automation", "qualify")
    graph.add_edge("analyze_advanced", "qualify")
    graph.add_edge("analyze_os", "qualify")
    graph.add_edge("analyze_marketing", "qualify")

    # qualify → END
    graph.add_edge("qualify", END)

    return graph.compile()
```

- [ ] **Step 3: Run — testes existentes devem continuar passando**

```bash
cd backend && pytest tests/test_diagnostic_nodes.py tests/test_diagnostic_state.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/pipeline/diagnostic/graph.py
git commit -m "feat(diagnostic): wire analyze_marketing into LangGraph

5th parallel analyzer. Same fan-out/fan-in pattern as the 4
service-level analyzers.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 5: Qualify lê marketing_result e popula no final

**Files:**
- Modify: `backend/app/pipeline/diagnostic/nodes/qualify.py`
- Test: `backend/tests/test_diagnostic_nodes.py`

- [ ] **Step 1: Adicionar teste failing**

Em `backend/tests/test_diagnostic_nodes.py`, adicionar no final:

```python
def test_qualify_includes_marketing_diagnostic(sample_state):
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

    state = sample_state.model_copy(update={"marketing_result": md})
    result = qualify(state)

    final = result["final_result"]
    assert final.diagnostico_marketing is not None
    assert final.diagnostico_marketing.momento_funil == "descoberta"


def test_qualify_marketing_none_stays_none(sample_state):
    """Quando marketing_result=None, diagnostico_marketing fica None."""
    state = sample_state.model_copy(update={"marketing_result": None})
    result = qualify(state)

    assert result["final_result"].diagnostico_marketing is None
```

Se `sample_state` ainda não existe como fixture, verifique o arquivo e use o padrão existente. Caso contrário, construa estado inline:

```python
from app.pipeline.diagnostic.state import GraphState, NivelScore

def _make_state(**overrides):
    base = GraphState(
        lead_info={"nome": "T"}, site_data={}, html_analysis={},
        pagespeed={}, html="", social_profiles={},
        lp_result=NivelScore(score=50, sinais=[], oportunidades=[], justificativa=""),
        automacao_result=NivelScore(score=50, sinais=[], oportunidades=[], justificativa=""),
        advanced_result=NivelScore(score=50, sinais=[], oportunidades=[], justificativa=""),
        os_result=NivelScore(score=50, sinais=[], oportunidades=[], justificativa=""),
    )
    return base.model_copy(update=overrides)
```

E substitua `sample_state` pelos calls `_make_state(marketing_result=md)` etc.

- [ ] **Step 2: Run — deve falhar**

```bash
cd backend && pytest tests/test_diagnostic_nodes.py::test_qualify_includes_marketing_diagnostic -v
```

Expected: FAIL com `AttributeError` ou `AssertionError` sobre `diagnostico_marketing`.

- [ ] **Step 3: Implementar — qualify repassa marketing_result**

Em `backend/app/pipeline/diagnostic/nodes/qualify.py`, substituir a construção de `final` (linhas ~67-76) por:

```python
    final = ServiceLevelAnalysis(
        lp=results["lp"],
        automacao_basica=results["automacao_basica"],
        mapa_automacoes=results["mapa_automacoes"],
        vertical_os=results["vertical_os"],
        nivel_recomendado=nivel_recomendado,
        qualificado=qualificado,
        motivo_desqualificacao=motivo,
        resumo_executivo=resumo,
        diagnostico_marketing=state.marketing_result,
    )
```

- [ ] **Step 4: Run — devem passar**

```bash
cd backend && pytest tests/test_diagnostic_nodes.py -v
```

Expected: PASS (novos + existentes).

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/diagnostic/nodes/qualify.py backend/tests/test_diagnostic_nodes.py
git commit -m "feat(diagnostic): qualify passes marketing_result to final

Qualify node now forwards state.marketing_result to
ServiceLevelAnalysis.diagnostico_marketing. None-safe.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 6: Enricher grava `diagnostico_marketing` em `site_analysis`

**Files:**
- Modify: `backend/app/pipeline/enricher.py:441-443`
- Test: `backend/tests/test_enricher.py`

- [ ] **Step 1: Teste failing pra gravação**

Em `backend/tests/test_enricher.py`, adicionar (encontre o teste `test_with_diagnostic_qualified` similar como referência, e adicione este após):

```python
def test_enrich_writes_diagnostico_marketing_to_site_analysis():
    """Quando service_levels tem diagnostico_marketing, é copiado pra site_analysis."""
    from unittest.mock import patch, MagicMock
    from app.pipeline.enricher import enrich_lead_data
    from app.pipeline.diagnostic.state import (
        ServiceLevelAnalysis, NivelScore, MarketingDiagnostic,
        IAPotencial, FunnelStage, FunnelAction,
    )

    md = MarketingDiagnostic(
        resumo_executivo="r",
        momento_funil="descoberta",
        potencial_ia_automacao=IAPotencial(score=70, oportunidades=[], justificativa="j"),
        prioridades_top3=["a", "b", "c"],
        funil={"descoberta": FunnelStage(
            diagnostico="d",
            acoes_top2=[FunnelAction(acao="a", resultado_esperado="r", kpi="k")],
        )},
    )
    sla = ServiceLevelAnalysis(
        lp=NivelScore(score=60, sinais=[], oportunidades=[], justificativa=""),
        automacao_basica=NivelScore(score=60, sinais=[], oportunidades=[], justificativa=""),
        mapa_automacoes=NivelScore(score=60, sinais=[], oportunidades=[], justificativa=""),
        vertical_os=NivelScore(score=60, sinais=[], oportunidades=[], justificativa=""),
        nivel_recomendado="lp",
        qualificado=True,
        resumo_executivo="r",
        diagnostico_marketing=md,
    )

    with patch("app.pipeline.enricher.run_diagnostic", return_value=sla), \
         patch("app.pipeline.enricher.fetch_website", return_value={"status": "ok", "html": ""}), \
         patch("app.pipeline.enricher.analyze_html", return_value={}), \
         patch("app.pipeline.enricher.fetch_pagespeed", return_value={}):

        result = enrich_lead_data(
            website="http://example.com",
            lead_info={"nome": "T", "nicho": "x", "cidade": "y"},
        )

    assert "diagnostico_marketing" in result["site_analysis"]
    assert result["site_analysis"]["diagnostico_marketing"]["momento_funil"] == "descoberta"
```

Ajuste imports/mocks se a assinatura de `enrich_lead_data` for diferente (leia o arquivo pra confirmar).

- [ ] **Step 2: Run — deve falhar**

```bash
cd backend && pytest tests/test_enricher.py::test_enrich_writes_diagnostico_marketing_to_site_analysis -v
```

Expected: FAIL — `diagnostico_marketing` não está em `site_analysis`.

- [ ] **Step 3: Atualizar enricher**

Em `backend/app/pipeline/enricher.py`, substituir linhas 441-443:

```python
        if service_levels:
            site_analysis["service_levels"] = service_levels.model_dump()
            qualified = service_levels.qualificado
```

por:

```python
        if service_levels:
            site_analysis["service_levels"] = service_levels.model_dump()
            if service_levels.diagnostico_marketing:
                site_analysis["diagnostico_marketing"] = service_levels.diagnostico_marketing.model_dump()
            qualified = service_levels.qualificado
```

- [ ] **Step 4: Run — deve passar**

```bash
cd backend && pytest tests/test_enricher.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/enricher.py backend/tests/test_enricher.py
git commit -m "feat(enricher): persist diagnostico_marketing into site_analysis

When service_levels carries diagnostico_marketing, enricher copies
it to site_analysis so generator/outreach (which already read it)
get deeper context. Restores the old field that the new pipeline
had stopped emitting.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 7: Frontend types — expor diagnostico_marketing

**Files:**
- Modify: `frontend/src/components/leads/lead-app-types.ts`

- [ ] **Step 1: Adicionar tipos + campo**

Em `frontend/src/components/leads/lead-app-types.ts`, no topo (ou onde fizer sentido), adicionar:

```ts
export interface FunnelActionDM {
  acao: string;
  resultado_esperado: string;
  kpi: string;
}

export interface FunnelStageDM {
  diagnostico: string;
  acoes_top2: FunnelActionDM[];
}

export interface IAPotencialDM {
  score: number;
  oportunidades: string[];
  justificativa: string;
}

export interface DiagnosticoMarketing {
  resumo_executivo: string;
  momento_funil: "descoberta" | "atracao" | "consideracao" | "acao" | "apologia";
  potencial_ia_automacao: IAPotencialDM;
  prioridades_top3: string[];
  funil: Record<string, FunnelStageDM>;
}
```

No `LeadAppDetail`, adicionar o campo (encontre a interface e adicione junto aos outros campos opcionais):

```ts
  diagnostico_marketing?: DiagnosticoMarketing;
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/leads/lead-app-types.ts
git commit -m "feat(leads): add DiagnosticoMarketing types to LeadAppDetail

Mirror of backend MarketingDiagnostic Pydantic model.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 8: Mapear site_analysis.diagnostico_marketing em mapToDetail

**Files:**
- Modify: `frontend/src/app/app/leads/[id]/page.tsx`

- [ ] **Step 1: Extrair diag + adicionar no retorno**

Em `frontend/src/app/app/leads/[id]/page.tsx`, dentro de `mapToDetail` (linha ~23-77), logo após:

```ts
  const sl = (lead.site_analysis as Record<string, unknown>)?.service_levels as ServiceLevelAnalysis | undefined;
```

adicionar:

```ts
  const dm = (lead.site_analysis as Record<string, unknown>)?.diagnostico_marketing as
    import("@/components/leads/lead-app-types").DiagnosticoMarketing | undefined;
```

No objeto retornado (dentro do return), antes de `created_at`, adicionar:

```ts
    diagnostico_marketing: dm || undefined,
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/app/leads/[id]/page.tsx
git commit -m "feat(leads): map site_analysis.diagnostico_marketing into LeadAppDetail

Makes the field available to tab components via the mapped detail.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 9: Tab "Estratégia" — componente + registro

**Files:**
- Create: `frontend/src/components/leads/la-tab-strategy.tsx`
- Modify: `frontend/src/components/leads/lead-app-mock.ts`
- Modify: `frontend/src/app/app/leads/[id]/page.tsx`

- [ ] **Step 1: Criar LaTabStrategy**

Criar `frontend/src/components/leads/la-tab-strategy.tsx`:

```tsx
"use client";

import { Icon } from "@/components/ui";
import { DiagnosticPanel } from "@/components/diagnostic-panel";
import type { LeadAppDetail } from "./lead-app-types";

export function LaTabStrategy({ lead }: { lead: LeadAppDetail }) {
  const diag = lead.diagnostico_marketing;

  if (!diag) {
    return (
      <div className="state" style={{ margin: "32px auto" }}>
        <div className="state-icon">
          <Icon name="target" size={20} />
        </div>
        <div className="state-title">Estratégia não gerada</div>
        <div className="state-msg">
          Este lead ainda não tem diagnóstico de marketing. Execute o enriquecimento pra gerar.
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: "4px 0" }}>
      <DiagnosticPanel
        siteAnalysis={{ diagnostico_marketing: diag }}
        compact={false}
      />
    </div>
  );
}
```

(Se o ícone `target` não existir no `Icon`, usar `search` ou `info`.)

- [ ] **Step 2: Registrar tab em buildTabs + TAB_ACTIONS**

Em `frontend/src/components/leads/lead-app-mock.ts`, encontrar o `buildTabs` e adicionar a tab nova. Procurar código tipo:

```ts
export function buildTabs({ reasons, lpVersions, messages }: { reasons: number; lpVersions: number; messages: number }): TabConfig[] {
  return [
    { key: "diag", label: "Diagnóstico", count: reasons },
    { key: "lp", label: "Landing Page", count: lpVersions },
    { key: "msgs", label: "Mensagens", count: messages },
    { key: "info", label: "Informações" },
  ];
}
```

Substituir por:

```ts
export function buildTabs({
  reasons,
  lpVersions,
  messages,
  hasStrategy,
}: {
  reasons: number;
  lpVersions: number;
  messages: number;
  hasStrategy: boolean;
}): TabConfig[] {
  return [
    { key: "diag", label: "Diagnóstico", count: reasons },
    { key: "strategy", label: "Estratégia", count: hasStrategy ? 1 : 0 },
    { key: "lp", label: "Landing Page", count: lpVersions },
    { key: "msgs", label: "Mensagens", count: messages },
    { key: "info", label: "Informações" },
  ];
}
```

No mesmo arquivo, encontrar `TAB_ACTIONS`:

```ts
export const TAB_ACTIONS: Record<string, { label: string; action: string }> = {
  diag: { label: "Re-enriquecer", action: "enrich" },
  lp: { label: "Gerar LP", action: "generate" },
  msgs: { label: "Gerar mensagens", action: "outreach" },
};
```

Adicionar entrada:

```ts
  strategy: { label: "Re-enriquecer", action: "enrich" },
```

Resultado:

```ts
export const TAB_ACTIONS: Record<string, { label: string; action: string }> = {
  diag: { label: "Re-enriquecer", action: "enrich" },
  strategy: { label: "Re-enriquecer", action: "enrich" },
  lp: { label: "Gerar LP", action: "generate" },
  msgs: { label: "Gerar mensagens", action: "outreach" },
};
```

- [ ] **Step 3: Importar + renderizar em `page.tsx`**

Em `frontend/src/app/app/leads/[id]/page.tsx`, adicionar import no topo:

```ts
import { LaTabStrategy } from "@/components/leads/la-tab-strategy";
```

Atualizar call de `buildTabs` (linhas ~128-134) pra passar `hasStrategy`:

```ts
  const tabs = lead
    ? buildTabs({
        reasons: lead.opportunity_reasons.length,
        lpVersions: lead.lp_versions.length,
        messages: lead.messages.length,
        hasStrategy: !!lead.diagnostico_marketing,
      })
    : buildTabs({ reasons: 0, lpVersions: 0, messages: 0, hasStrategy: false });
```

Adicionar case em `tabContent()` (linhas ~175-184):

```ts
  const tabContent = () => {
    if (!lead) return null;
    switch (activeTab) {
      case "diag": return <LaTabDiag lead={lead} />;
      case "strategy": return <LaTabStrategy lead={lead} />;
      case "lp": return <LaTabLp lead={lead} onVersionActivated={fetchLandingPages} />;
      case "msgs": return <LaTabMsgs lead={lead} />;
      case "info": return <LaTabInfo lead={lead} />;
      default: return <LaTabDiag lead={lead} />;
    }
  };
```

Atualizar `handlePrimaryAction` pra cobrir o case `strategy` (roda enrich também). Em linhas ~139-173, dentro do `switch (activeTab)`:

```ts
      switch (activeTab) {
        case "diag":
        case "strategy":
          job = await runEnrich({ lead_ids: [lead.id] });
          onDone = () => { refreshLead(); refreshLeads(); };
          break;
        case "lp":
          job = await runGenerate({ lead_ids: [lead.id] });
          onDone = () => { refreshLead(); fetchLandingPages(); refreshLeads(); };
          break;
        case "msgs":
          job = await runOutreach({ lead_ids: [lead.id] });
          onDone = () => { refreshMessages(); refreshLead(); refreshLeads(); };
          break;
        default:
          return;
      }
```

- [ ] **Step 4: Lint**

```bash
cd frontend && npm run lint
```

Expected: sem erros nos arquivos tocados.

- [ ] **Step 5: Build**

```bash
cd frontend && npm run build
```

Expected: build passa.

- [ ] **Step 6: Smoke test manual**

```bash
cd frontend && npm run dev
```

- Abrir lead **sem** `diagnostico_marketing` → tab "Estratégia" mostra empty state
- Clicar "Re-enriquecer" → pipeline roda, recarrega
- Abrir lead **com** `diagnostico_marketing` → tab mostra DiagnosticPanel completo (resumo, funil, Potencial IA, Top 3, Detalhes por Etapa)

Pra forçar um lead ter diagnostico_marketing sem rodar LLM: no banco local, editar manualmente um lead:

```sql
UPDATE leads
SET site_analysis = site_analysis || '{"diagnostico_marketing": {
  "resumo_executivo": "Teste",
  "momento_funil": "descoberta",
  "potencial_ia_automacao": {"score": 70, "oportunidades": ["x"], "justificativa": "y"},
  "prioridades_top3": ["a", "b", "c"],
  "funil": {}
}}'::jsonb
WHERE id = <algum_id>;
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/leads/la-tab-strategy.tsx frontend/src/components/leads/lead-app-mock.ts frontend/src/app/app/leads/[id]/page.tsx
git commit -m "feat(leads): add Estratégia tab reusing DiagnosticPanel

New tab between Diagnóstico and Landing Page. Empty state with
'Re-enriquecer' CTA when diagnostico_marketing is missing.
Reuses the existing DiagnosticPanel component (already styled
with Instrumento DS tokens).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Final verification

- [ ] **Step 1: Backend tests**

```bash
cd backend && pytest
```

Expected: todos PASS.

- [ ] **Step 2: Frontend build**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Fluxo end-to-end manual**

1. Rodar `docker compose up`
2. Criar/escolher um lead via scrape
3. Rodar enrich via UI
4. Abrir `/app/leads/<id>`
5. Verificar:
   - Tab "Estratégia" aparece entre Diagnóstico e Landing Page
   - Depois do enrich completar, tab mostra funil + Potencial IA + Top 3
   - Mensagens de outreach (se gerar) usam o diagnóstico (não caem em template)
   - Tab Diagnóstico continua mostrando score dims + sinais (não regrediu)
