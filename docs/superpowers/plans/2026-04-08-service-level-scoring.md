# Service Level Scoring — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-prompt marketing diagnostic with a LangGraph parallel graph that scores each lead across 4 service levels (LP, Automação Básica, Mapa+Automações, Vertical OS), then display results as tabs in the frontend lead sheet.

**Architecture:** LangGraph graph with 6 nodes — 1 collector (Python), 4 parallel LLM analyzers (MiniMax M2.7 via `langchain-openai`), 1 qualifier (Python). The graph replaces `generate_diagnostic()` in `enricher.py`. Frontend gets a new `ServiceLevelTabs` component replacing `DiagnosticPanel` for enriched leads.

**Tech Stack:** LangGraph, langchain-openai, langchain-core, Pydantic v2, MiniMax M2.7 API, React/TypeScript, Tailwind CSS

**Spec:** `docs/superpowers/specs/2026-04-08-service-level-scoring-design.md`

---

### Task 1: Add dependencies and config

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config.py:5-38`

- [ ] **Step 1: Add LangGraph dependencies to requirements.txt**

Add these lines to `backend/requirements.txt` after `sse-starlette==2.1.0`:

```
langgraph>=0.4
langchain-openai>=0.3
langchain-core>=0.3
```

- [ ] **Step 2: Add new config settings**

In `backend/app/config.py`, add two new fields after line 32 (`ai_potential_threshold`):

```python
    disqualify_threshold: int = 25
    skip_service_level_analysis: bool = False
```

- [ ] **Step 3: Install dependencies**

Run: `cd backend && pip install -r requirements.txt`
Expected: All packages install successfully, including `langgraph`, `langchain-openai`, `langchain-core`

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt backend/app/config.py
git commit -m "chore: add langgraph deps and service level config"
```

---

### Task 2: Create Pydantic state models

**Files:**
- Create: `backend/app/pipeline/diagnostic/__init__.py`
- Create: `backend/app/pipeline/diagnostic/state.py`
- Create: `backend/tests/test_diagnostic_state.py`

- [ ] **Step 1: Create the diagnostic package**

Create `backend/app/pipeline/diagnostic/__init__.py`:

```python
"""Service Level Scoring diagnostic graph."""

from app.pipeline.diagnostic.graph import run_diagnostic

__all__ = ["run_diagnostic"]
```

- [ ] **Step 2: Write failing tests for state models**

Create `backend/tests/test_diagnostic_state.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_diagnostic_state.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.pipeline.diagnostic.state'`

- [ ] **Step 4: Implement state models**

Create `backend/app/pipeline/diagnostic/state.py`:

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_diagnostic_state.py -v`
Expected: All 7 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/pipeline/diagnostic/ backend/tests/test_diagnostic_state.py
git commit -m "feat: add diagnostic state Pydantic models"
```

---

### Task 3: Create prompt templates

**Files:**
- Create: `backend/app/pipeline/diagnostic/prompts/__init__.py`
- Create: `backend/app/pipeline/diagnostic/prompts/lp.py`
- Create: `backend/app/pipeline/diagnostic/prompts/automation.py`
- Create: `backend/app/pipeline/diagnostic/prompts/advanced.py`
- Create: `backend/app/pipeline/diagnostic/prompts/os.py`
- Create: `backend/app/pipeline/diagnostic/prompts/shared.py`

- [ ] **Step 1: Create shared context builder**

Create `backend/app/pipeline/diagnostic/prompts/__init__.py` (empty):

```python
```

Create `backend/app/pipeline/diagnostic/prompts/shared.py`:

```python
"""Shared context formatting used by all analyzer prompts."""


def format_lead_context(
    lead_info: dict,
    site_data: dict,
    html_analysis: dict,
    pagespeed: dict,
    visible_text: str,
    social_profiles: dict,
) -> str:
    """Build the shared context block that all 4 analyzers receive."""
    reviews_text = ""
    if lead_info.get("top_reviews"):
        reviews_text = "\n".join(f'- "{r}"' for r in lead_info["top_reviews"][:3])

    site_status = site_data.get("status", "unknown")
    has_site = site_status == "ok"

    # Social profiles
    social_lines = []
    ig = social_profiles.get("instagram")
    if ig and isinstance(ig, dict) and ig.get("followers") is not None:
        social_lines.append(
            f"- Instagram: @{ig.get('username', '?')} | {ig.get('followers', 0)} seguidores | "
            f"{ig.get('posts_count', 0)} posts | {'Comercial' if ig.get('is_business') else 'Pessoal'}"
        )
    li = social_profiles.get("linkedin")
    if li and isinstance(li, dict) and li.get("name"):
        social_lines.append(
            f"- LinkedIn: {li.get('name', '?')} | {li.get('followers', 0)} seguidores | "
            f"{li.get('employees_range', '?')} funcionários"
        )
    for platform in ("facebook", "tiktok", "youtube"):
        p = social_profiles.get(platform)
        if p and isinstance(p, dict):
            social_lines.append(f"- {platform.capitalize()}: {p.get('url', 'perfil encontrado')}")
    social_text = "\n".join(social_lines) if social_lines else "Nenhum perfil encontrado."

    return f"""DADOS DO NEGÓCIO:
- Nome: {lead_info.get('nome', 'N/A')}
- Nicho/Categoria: {lead_info.get('nicho', 'N/A')} / {lead_info.get('categoria', 'N/A')}
- Cidade: {lead_info.get('cidade', 'N/A')}
- Nota Google: {lead_info.get('rating', 'N/A')} ({lead_info.get('reviews_count', 0)} avaliações)
- Avaliações destaque:
{reviews_text or 'Sem avaliações disponíveis'}

ANÁLISE TÉCNICA DO SITE:
- Status: {"Site funcional" if has_site else f"Problemas: {site_status}"}
- SSL/HTTPS: {"Sim" if html_analysis.get("has_ssl", site_data.get("has_ssl")) else "Não"}
- Responsivo (mobile): {"Sim" if html_analysis.get("has_responsive_meta") else "Não"}
- Link WhatsApp: {"Sim" if html_analysis.get("has_whatsapp_link") else "Não"}
- Google Analytics: {"Sim" if html_analysis.get("has_analytics") else "Não"}
- Chatbot: {"Sim" if html_analysis.get("has_chatbot") else "Não"}
- CTA: {"Sim" if html_analysis.get("has_cta") else "Não"}
- Redes sociais no site: {"Sim" if html_analysis.get("has_social_links") else "Não"}
- Conteúdo: {html_analysis.get("word_count", 0)} palavras, {html_analysis.get("image_count", 0)} imagens
- Template genérico: {"Sim" if html_analysis.get("is_template") else "Não"}
- PageSpeed mobile: {pagespeed.get("performance_score", "N/A")}/100
- Título: {html_analysis.get("title", "N/A")}

{"CONTEÚDO VISÍVEL (trecho):" + chr(10) + visible_text if visible_text else "SEM WEBSITE."}

REDES SOCIAIS:
{social_text}"""
```

- [ ] **Step 2: Create LP prompt**

Create `backend/app/pipeline/diagnostic/prompts/lp.py`:

```python
"""Prompt template for LP (Landing Page) service level analysis."""

LP_SYSTEM_PROMPT = """Você é um analista especializado em presença digital de negócios locais brasileiros.
Sua tarefa é avaliar se este negócio precisa de uma Landing Page profissional e quão fácil seria fechar essa venda.

Avalie com base nos dados fornecidos e retorne um score de 0 a 100."""


def build_lp_prompt(context: str) -> str:
    return f"""{context}

CRITÉRIOS DE AVALIAÇÃO — LANDING PAGE:

SCORE ALTO (70-100) quando:
- Sem site ou site muito ruim (quebrado, lento, não responsivo)
- Concorrentes do nicho na mesma cidade têm presença digital melhor
- Negócio tem reviews boas mas o site não reflete a qualidade do serviço
- Nicho que depende de presença online (restaurante, clínica, salão, etc.)
- Sinais de que o dono sente a dor (reviews mencionam dificuldade de encontrar info)

SCORE BAIXO (0-30) quando:
- Já tem site decente e funcional
- Nicho que não depende de site (distribuidora B2B, atacadista, etc.)
- Site recente e bem feito

Responda com:
- score: 0 a 100
- sinais: lista de evidências encontradas nos dados
- oportunidades: o que pode ser oferecido como LP
- justificativa: por que esse score, em 2-3 frases"""
```

- [ ] **Step 3: Create Automation prompt**

Create `backend/app/pipeline/diagnostic/prompts/automation.py`:

```python
"""Prompt template for Automação Básica service level analysis."""

AUTOMATION_SYSTEM_PROMPT = """Você é um analista especializado em automação comercial para negócios locais brasileiros.
Sua tarefa é avaliar se este negócio precisa de automações básicas (que não exigem integração complexa entre sistemas).

Avalie com base nos dados fornecidos e retorne um score de 0 a 100."""


def build_automation_prompt(context: str) -> str:
    return f"""{context}

CRITÉRIOS DE AVALIAÇÃO — AUTOMAÇÃO BÁSICA:

Automação básica inclui: chatbot WhatsApp, auto-resposta, CRM simples, email marketing básico,
agendamento online, formulários inteligentes. NÃO inclui integrações complexas entre múltiplos sistemas.

SCORE ALTO (70-100) quando:
- Atendimento 100% manual com volume significativo de interações
- Canais desconectados (Instagram DM + WhatsApp + telefone sem integração)
- Processos repetitivos visíveis (reviews mencionam "demora pra responder", "não consegui agendar")
- Nicho com alto volume de interações repetitivas (agendamento, orçamento, FAQ)
- Sem chatbot, sem auto-resposta, sem CRM

SCORE BAIXO (0-30) quando:
- Já usa chatbot ou CRM funcional
- Negócio com baixo volume de interação com clientes
- Operação simples sem processos repetitivos

Responda com:
- score: 0 a 100
- sinais: lista de evidências encontradas nos dados
- oportunidades: quais automações básicas implementar
- justificativa: por que esse score, em 2-3 frases"""
```

- [ ] **Step 4: Create Advanced prompt**

Create `backend/app/pipeline/diagnostic/prompts/advanced.py`:

```python
"""Prompt template for Mapa + Automações Completas service level analysis."""

ADVANCED_SYSTEM_PROMPT = """Você é um analista especializado em automação avançada e presença digital completa para negócios locais brasileiros.
Sua tarefa é avaliar se este negócio precisa de automações completas com múltiplos canais integrados e agents de IA.

Avalie com base nos dados fornecidos e retorne um score de 0 a 100."""


def build_advanced_prompt(context: str) -> str:
    return f"""{context}

CRITÉRIOS DE AVALIAÇÃO — MAPA + AUTOMAÇÕES COMPLETAS:

Este nível inclui: otimização de Google Meu Negócio, fluxos integrados multi-canal
(agendamento → confirmação → follow-up → remarketing), agents de IA que executam tarefas
(não só respondem), integrações entre CRM + WhatsApp + email + redes sociais.

SCORE ALTO (70-100) quando:
- Operação com múltiplos pontos de contato com cliente
- Fluxo de venda/atendimento com 3+ etapas que hoje são manuais
- Google Meu Negócio desotimizado mas com potencial claro
- Já tem alguma base digital (site ou redes) mas fluxos completamente desconectados
- Nicho com jornada de cliente complexa (clínica, imobiliária, escola)

SCORE BAIXO (0-30) quando:
- Negócio simples demais para automações complexas
- Sem maturidade digital para absorver (nem WhatsApp Business usa)
- Operação com pouca recorrência de clientes
- Nicho com jornada de compra muito simples (compra única)

Responda com:
- score: 0 a 100
- sinais: lista de evidências encontradas nos dados
- oportunidades: quais automações completas e integrações implementar
- justificativa: por que esse score, em 2-3 frases"""
```

- [ ] **Step 5: Create OS prompt**

Create `backend/app/pipeline/diagnostic/prompts/os.py`:

```python
"""Prompt template for Vertical OS service level analysis."""

OS_SYSTEM_PROMPT = """Você é um analista especializado em plataformas verticais (Vertical OS) para negócios brasileiros.
Sua tarefa é avaliar se este negócio tem potencial para adotar um sistema operacional vertical —
uma plataforma única que substitui todas as ferramentas e centraliza toda a operação do nicho.

Avalie com base nos dados fornecidos e retorne um score de 0 a 100."""


def build_os_prompt(context: str) -> str:
    return f"""{context}

CRITÉRIOS DE AVALIAÇÃO — VERTICAL OS:

Vertical OS é um sistema completo que substitui TODAS as ferramentas do negócio (ERP + CRM +
agendamento + financeiro + marketing + gestão de equipe) numa plataforma única customizada
para o nicho. Exemplos: Toast (restaurantes), ServiceTitan (serviços de campo), Mindbody (wellness).

SCORE ALTO (70-100) quando:
- Operação complexa com múltiplas áreas (agendamento + prontuário/estoque + financeiro + marketing)
- Equipe de 5+ pessoas com necessidade de coordenação
- Nicho com processos fragmentados (provavelmente usa 5+ ferramentas desconectadas)
- Demanda recorrente de clientes (assinatura, manutenção, retorno periódico)
- Reviews ou site indicam operação sofisticada com múltiplos serviços
- Nicho onde existem vertical OS no mercado (validação de mercado)

SCORE BAIXO (0-30) quando:
- Negócio de 1-2 pessoas sem equipe
- Operação simples sem necessidade de sistema integrado
- Nicho já dominado por um OS vertical existente que o lead provavelmente já usa
- Sem escala para justificar investimento em plataforma

Responda com:
- score: 0 a 100
- sinais: lista de evidências encontradas nos dados
- oportunidades: que tipo de vertical OS seria adequado
- justificativa: por que esse score, em 2-3 frases"""
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/pipeline/diagnostic/prompts/
git commit -m "feat: add prompt templates for 4 service levels"
```

---

### Task 4: Create analyzer and qualifier nodes

**Files:**
- Create: `backend/app/pipeline/diagnostic/nodes/__init__.py`
- Create: `backend/app/pipeline/diagnostic/nodes/collect.py`
- Create: `backend/app/pipeline/diagnostic/nodes/analyzers.py`
- Create: `backend/app/pipeline/diagnostic/nodes/qualify.py`
- Create: `backend/tests/test_diagnostic_nodes.py`

- [ ] **Step 1: Write failing tests for qualifier node**

Create `backend/tests/test_diagnostic_nodes.py`:

```python
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
        # advanced has 45 >= 40, automacao has 70 >= 40
        # Highest viable (top-down): advanced (45) is viable
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
        # None >= 40 threshold, but lp has highest (35) and is above disqualify (25)
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
        # Missing results get score 0
        assert final.automacao_basica.score == 0

    def test_resumo_executivo_present(self):
        state = _make_state()
        result = qualify(state)
        assert len(result["final_result"].resumo_executivo) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_diagnostic_nodes.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement nodes**

Create `backend/app/pipeline/diagnostic/nodes/__init__.py` (empty):

```python
```

Create `backend/app/pipeline/diagnostic/nodes/collect.py`:

```python
"""Collector node — assembles context from raw enrichment data."""

from app.pipeline.diagnostic.state import GraphState
from app.pipeline.enricher import _extract_visible_text


def collect_context(
    lead_info: dict,
    site_data: dict,
    html_analysis: dict,
    pagespeed: dict,
    html: str,
    social_profiles: dict,
) -> GraphState:
    """Create the initial GraphState from enrichment data."""
    return GraphState(
        lead_info=lead_info,
        site_data=site_data,
        html_analysis=html_analysis,
        pagespeed=pagespeed,
        html=html,
        social_profiles=social_profiles,
    )
```

Create `backend/app/pipeline/diagnostic/nodes/analyzers.py`:

```python
"""LLM analyzer nodes — one per service level, run in parallel."""

import logging

from langchain_openai import ChatOpenAI

from app.config import settings
from app.pipeline.diagnostic.state import GraphState, NivelScore
from app.pipeline.diagnostic.prompts.shared import format_lead_context
from app.pipeline.diagnostic.prompts.lp import LP_SYSTEM_PROMPT, build_lp_prompt
from app.pipeline.diagnostic.prompts.automation import AUTOMATION_SYSTEM_PROMPT, build_automation_prompt
from app.pipeline.diagnostic.prompts.advanced import ADVANCED_SYSTEM_PROMPT, build_advanced_prompt
from app.pipeline.diagnostic.prompts.os import OS_SYSTEM_PROMPT, build_os_prompt
from app.pipeline.enricher import _extract_visible_text

logger = logging.getLogger(__name__)

FALLBACK_NIVEL = NivelScore(
    score=0,
    sinais=["Análise indisponível"],
    oportunidades=[],
    justificativa="Falha na análise — resultado indisponível.",
)


def _get_llm() -> ChatOpenAI:
    """Create a ChatOpenAI instance pointing at the configured LLM provider."""
    model = settings.diagnostic_model or settings.llm_model
    return ChatOpenAI(
        model=model,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        max_tokens=1000,
        timeout=60,
    )


def _build_context(state: GraphState) -> str:
    """Build the shared context string from graph state."""
    visible_text = _extract_visible_text(state.html)
    return format_lead_context(
        lead_info=state.lead_info,
        site_data=state.site_data,
        html_analysis=state.html_analysis,
        pagespeed=state.pagespeed,
        visible_text=visible_text,
        social_profiles=state.social_profiles,
    )


def _run_analyzer(
    state: GraphState,
    system_prompt: str,
    build_prompt_fn,
    result_key: str,
) -> dict:
    """Generic analyzer runner. Calls LLM with structured output and returns state update."""
    try:
        llm = _get_llm().with_structured_output(NivelScore)
        context = _build_context(state)
        user_prompt = build_prompt_fn(context)
        result = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])
        return {result_key: result}
    except Exception as exc:
        logger.error("Analyzer %s failed: %s", result_key, str(exc)[:200])
        return {result_key: FALLBACK_NIVEL}


def analyze_lp(state: GraphState) -> dict:
    """Analyze LP (Landing Page) potential."""
    return _run_analyzer(state, LP_SYSTEM_PROMPT, build_lp_prompt, "lp_result")


def analyze_automation(state: GraphState) -> dict:
    """Analyze Automação Básica potential."""
    return _run_analyzer(state, AUTOMATION_SYSTEM_PROMPT, build_automation_prompt, "automacao_result")


def analyze_advanced(state: GraphState) -> dict:
    """Analyze Mapa + Automações Completas potential."""
    return _run_analyzer(state, ADVANCED_SYSTEM_PROMPT, build_advanced_prompt, "advanced_result")


def analyze_os(state: GraphState) -> dict:
    """Analyze Vertical OS potential."""
    return _run_analyzer(state, OS_SYSTEM_PROMPT, build_os_prompt, "os_result")
```

Create `backend/app/pipeline/diagnostic/nodes/qualify.py`:

```python
"""Qualifier node — consolidates 4 analyzer results into final recommendation."""

from app.config import settings
from app.pipeline.diagnostic.state import (
    GraphState,
    NivelScore,
    ServiceLevelAnalysis,
    NivelKey,
    NIVEL_KEYS,
)

FALLBACK_NIVEL = NivelScore(
    score=0,
    sinais=["Análise indisponível"],
    oportunidades=[],
    justificativa="Falha na análise — resultado indisponível.",
)

# Map state result keys to ServiceLevelAnalysis field names
_RESULT_MAP: list[tuple[str, NivelKey]] = [
    ("lp_result", "lp"),
    ("automacao_result", "automacao_basica"),
    ("advanced_result", "mapa_automacoes"),
    ("os_result", "vertical_os"),
]

VIABLE_THRESHOLD = 40


def qualify(state: GraphState, disqualify_threshold: int | None = None) -> dict:
    """Consolidate 4 analyzer results into a ServiceLevelAnalysis."""
    threshold = disqualify_threshold if disqualify_threshold is not None else settings.disqualify_threshold

    # Collect results, using fallback for missing
    results: dict[NivelKey, NivelScore] = {}
    for state_key, nivel_key in _RESULT_MAP:
        result = getattr(state, state_key)
        results[nivel_key] = result if result is not None else FALLBACK_NIVEL

    scores = {k: v.score for k, v in results.items()}

    # Check disqualification: all scores below threshold
    all_below = all(s < threshold for s in scores.values())
    if all_below:
        qualificado = False
        motivo = f"Todos os scores abaixo de {threshold}: " + ", ".join(
            f"{k}={s}" for k, s in scores.items()
        )
        # Still pick the highest as "recommended" even if disqualified
        nivel_recomendado = max(scores, key=scores.get)
    else:
        qualificado = True
        motivo = None
        # Pick highest viable level (top-down: OS → Advanced → Automation → LP)
        nivel_recomendado = None
        for nivel_key in reversed(NIVEL_KEYS):
            if scores[nivel_key] >= VIABLE_THRESHOLD:
                nivel_recomendado = nivel_key
                break
        # Fallback: highest absolute score
        if nivel_recomendado is None:
            nivel_recomendado = max(scores, key=scores.get)

    # Build resumo executivo
    nome = state.lead_info.get("nome", "Lead")
    top_nivel_label = {
        "lp": "Landing Page",
        "automacao_basica": "Automação Básica",
        "mapa_automacoes": "Mapa + Automações",
        "vertical_os": "Vertical OS",
    }
    best = results[nivel_recomendado]
    resumo_parts = [
        f"{nome}: nível recomendado é {top_nivel_label[nivel_recomendado]} (score {scores[nivel_recomendado]}/100).",
    ]
    if best.oportunidades:
        resumo_parts.append(f"Oportunidades: {', '.join(best.oportunidades[:3])}.")
    resumo = " ".join(resumo_parts)

    final = ServiceLevelAnalysis(
        lp=results["lp"],
        automacao_basica=results["automacao_basica"],
        mapa_automacoes=results["mapa_automacoes"],
        vertical_os=results["vertical_os"],
        nivel_recomendado=nivel_recomendado,
        qualificado=qualificado,
        motivo_desqualificacao=motivo,
        resumo_executivo=resumo,
    )

    return {"final_result": final}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_diagnostic_nodes.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/diagnostic/nodes/ backend/tests/test_diagnostic_nodes.py
git commit -m "feat: add collector, analyzer, and qualifier nodes"
```

---

### Task 5: Assemble the LangGraph graph

**Files:**
- Create: `backend/app/pipeline/diagnostic/graph.py`
- Create: `backend/tests/test_diagnostic_graph.py`

- [ ] **Step 1: Write failing test for the graph**

Create `backend/tests/test_diagnostic_graph.py`:

```python
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
        # Each call returns a different score
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

    @patch("app.pipeline.diagnostic.nodes.analyzers.settings")
    def test_returns_none_when_no_api_key(self, mock_settings):
        mock_settings.llm_api_key = ""
        mock_settings.skip_service_level_analysis = False

        result = run_diagnostic(
            lead_info=SAMPLE_LEAD_INFO,
            site_data={"status": "ok"},
            html_analysis={},
            pagespeed={},
            html="",
            social_profiles={},
        )

        assert result is None

    @patch("app.pipeline.diagnostic.nodes.analyzers.settings")
    def test_returns_none_when_disabled(self, mock_settings):
        mock_settings.skip_service_level_analysis = True

        result = run_diagnostic(
            lead_info=SAMPLE_LEAD_INFO,
            site_data={},
            html_analysis={},
            pagespeed={},
            html="",
            social_profiles={},
        )

        assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_diagnostic_graph.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.pipeline.diagnostic.graph'`

- [ ] **Step 3: Implement the graph**

Create `backend/app/pipeline/diagnostic/graph.py`:

```python
"""LangGraph diagnostic graph — parallel fan-out to 4 analyzers, fan-in to qualifier."""

import logging
from typing import Annotated

from langgraph.graph import StateGraph, START, END

from app.config import settings
from app.pipeline.diagnostic.state import GraphState, ServiceLevelAnalysis
from app.pipeline.diagnostic.nodes.collect import collect_context
from app.pipeline.diagnostic.nodes.analyzers import (
    analyze_lp,
    analyze_automation,
    analyze_advanced,
    analyze_os,
)
from app.pipeline.diagnostic.nodes.qualify import qualify

logger = logging.getLogger(__name__)


def _build_graph() -> StateGraph:
    """Build the diagnostic StateGraph with parallel analyzer fan-out."""
    graph = StateGraph(GraphState)

    # Add nodes
    graph.add_node("analyze_lp", analyze_lp)
    graph.add_node("analyze_automation", analyze_automation)
    graph.add_node("analyze_advanced", analyze_advanced)
    graph.add_node("analyze_os", analyze_os)
    graph.add_node("qualify", qualify)

    # Fan-out: START → all 4 analyzers in parallel
    graph.add_edge(START, "analyze_lp")
    graph.add_edge(START, "analyze_automation")
    graph.add_edge(START, "analyze_advanced")
    graph.add_edge(START, "analyze_os")

    # Fan-in: all 4 analyzers → qualify
    graph.add_edge("analyze_lp", "qualify")
    graph.add_edge("analyze_automation", "qualify")
    graph.add_edge("analyze_advanced", "qualify")
    graph.add_edge("analyze_os", "qualify")

    # qualify → END
    graph.add_edge("qualify", END)

    return graph.compile()


# Compile once at module level
_compiled_graph = None


def _get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = _build_graph()
    return _compiled_graph


def run_diagnostic(
    lead_info: dict,
    site_data: dict,
    html_analysis: dict,
    pagespeed: dict,
    html: str,
    social_profiles: dict,
) -> ServiceLevelAnalysis | None:
    """
    Run the full diagnostic graph for a single lead.
    Returns ServiceLevelAnalysis or None if disabled/no API key.
    """
    if settings.skip_service_level_analysis:
        return None

    if not settings.llm_api_key:
        logger.warning("Service Level Analysis: LLM_API_KEY não configurada")
        return None

    try:
        initial_state = collect_context(
            lead_info=lead_info,
            site_data=site_data,
            html_analysis=html_analysis,
            pagespeed=pagespeed,
            html=html,
            social_profiles=social_profiles,
        )

        graph = _get_graph()
        final_state = graph.invoke(initial_state.model_dump())

        # Extract final result
        final_result = final_state.get("final_result")
        if final_result is None:
            logger.error("Service Level Analysis: graph returned no final_result")
            return None

        if isinstance(final_result, dict):
            return ServiceLevelAnalysis(**final_result)
        return final_result

    except Exception as exc:
        logger.error("Service Level Analysis: graph execution failed: %s", str(exc)[:200])
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_diagnostic_graph.py -v`
Expected: Tests pass (mocked LLM calls)

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/diagnostic/graph.py backend/tests/test_diagnostic_graph.py
git commit -m "feat: assemble LangGraph diagnostic graph with parallel fan-out"
```

---

### Task 6: Integrate graph into enricher.py

**Files:**
- Modify: `backend/app/pipeline/enricher.py:622-655`
- Modify: `backend/tests/test_enricher.py`

- [ ] **Step 1: Write failing test for new integration**

Add to `backend/tests/test_enricher.py`, at the end of `TestEnrichLeadData`:

```python
    @patch("app.pipeline.enricher.run_diagnostic")
    @patch("app.pipeline.enricher.check_pagespeed")
    @patch("app.pipeline.enricher.fetch_website")
    def test_with_service_levels(self, mock_fetch, mock_pagespeed, mock_run_diag):
        from app.pipeline.diagnostic.state import NivelScore, ServiceLevelAnalysis

        mock_fetch.return_value = {"status": "ok", "html": SAMPLE_HTML, "has_ssl": True}
        mock_pagespeed.return_value = {"performance_score": 70}

        sla = ServiceLevelAnalysis(
            lp=NivelScore(score=80, sinais=["Sem site"], oportunidades=["LP"], justificativa="j"),
            automacao_basica=NivelScore(score=60, sinais=["s"], oportunidades=["o"], justificativa="j"),
            mapa_automacoes=NivelScore(score=40, sinais=["s"], oportunidades=["o"], justificativa="j"),
            vertical_os=NivelScore(score=15, sinais=["s"], oportunidades=["o"], justificativa="j"),
            nivel_recomendado="lp",
            qualificado=True,
            motivo_desqualificacao=None,
            resumo_executivo="Resumo.",
        )
        mock_run_diag.return_value = sla

        result = enrich_lead_data("http://example.com", lead_info=SAMPLE_LEAD_INFO)

        assert result["qualified"] is True
        assert "service_levels" in result["site_analysis"]
        assert result["site_analysis"]["service_levels"]["lp"]["score"] == 80
        assert result["site_analysis"]["service_levels"]["nivel_recomendado"] == "lp"

    @patch("app.pipeline.enricher.run_diagnostic")
    @patch("app.pipeline.enricher.check_pagespeed")
    @patch("app.pipeline.enricher.fetch_website")
    def test_with_service_levels_disqualified(self, mock_fetch, mock_pagespeed, mock_run_diag):
        from app.pipeline.diagnostic.state import NivelScore, ServiceLevelAnalysis

        mock_fetch.return_value = {"status": "ok", "html": SAMPLE_HTML, "has_ssl": True}
        mock_pagespeed.return_value = {"performance_score": 70}

        sla = ServiceLevelAnalysis(
            lp=NivelScore(score=10, sinais=["s"], oportunidades=[], justificativa="j"),
            automacao_basica=NivelScore(score=5, sinais=["s"], oportunidades=[], justificativa="j"),
            mapa_automacoes=NivelScore(score=8, sinais=["s"], oportunidades=[], justificativa="j"),
            vertical_os=NivelScore(score=3, sinais=["s"], oportunidades=[], justificativa="j"),
            nivel_recomendado="lp",
            qualificado=False,
            motivo_desqualificacao="Sem potencial",
            resumo_executivo="Desqualificado.",
        )
        mock_run_diag.return_value = sla

        result = enrich_lead_data("http://example.com", lead_info=SAMPLE_LEAD_INFO)

        assert result["qualified"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_enricher.py::TestEnrichLeadData::test_with_service_levels -v`
Expected: FAIL — `run_diagnostic` not imported

- [ ] **Step 3: Modify enricher.py to use the graph**

In `backend/app/pipeline/enricher.py`, add import at the top (after existing imports):

```python
from app.pipeline.diagnostic import run_diagnostic
```

Then replace lines 622-655 (the `# 6. Diagnóstico de marketing via IA` section and the return statement) with:

```python
    # 6. Service Level Analysis via LangGraph
    qualified = True
    if lead_info:
        lead_info_with_social = {**lead_info, "social_profiles": social_profiles}
        service_levels = run_diagnostic(
            lead_info=lead_info_with_social,
            site_data=site_data,
            html_analysis=html_analysis,
            pagespeed=pagespeed,
            html=site_data.get("html", ""),
            social_profiles=social_profiles,
        )

        if service_levels:
            site_analysis["service_levels"] = service_levels.model_dump()
            qualified = service_levels.qualificado

    return {
        "opportunity_score": score,
        "opportunity_reasons": reasons,
        "site_analysis": site_analysis,
        "social_profiles": social_profiles,
        "qualified": qualified,
    }
```

- [ ] **Step 4: Update existing enricher tests**

The existing tests that mock `generate_diagnostic` and check for `diagnostico_marketing` need updating. In `TestEnrichLeadData`:

- `test_with_diagnostic_qualified`: change mock from `generate_diagnostic` to `run_diagnostic`, change assertion from `diagnostico_marketing` to `service_levels`
- `test_with_diagnostic_disqualified`: same pattern
- `test_diagnostic_failure_still_enriches`: change mock, check `service_levels` not in `site_analysis`

Replace the first 3 tests in `TestEnrichLeadData`:

```python
    @patch("app.pipeline.enricher.run_diagnostic")
    @patch("app.pipeline.enricher.check_pagespeed")
    @patch("app.pipeline.enricher.fetch_website")
    def test_with_diagnostic_qualified(self, mock_fetch, mock_pagespeed, mock_diag):
        from app.pipeline.diagnostic.state import NivelScore, ServiceLevelAnalysis

        mock_fetch.return_value = {"status": "ok", "html": SAMPLE_HTML, "has_ssl": True}
        mock_pagespeed.return_value = {"performance_score": 70}
        sla = ServiceLevelAnalysis(
            lp=NivelScore(score=80, sinais=["s"], oportunidades=["o"], justificativa="j"),
            automacao_basica=NivelScore(score=60, sinais=["s"], oportunidades=["o"], justificativa="j"),
            mapa_automacoes=NivelScore(score=40, sinais=["s"], oportunidades=["o"], justificativa="j"),
            vertical_os=NivelScore(score=15, sinais=["s"], oportunidades=["o"], justificativa="j"),
            nivel_recomendado="lp",
            qualificado=True,
            motivo_desqualificacao=None,
            resumo_executivo="Resumo.",
        )
        mock_diag.return_value = sla

        result = enrich_lead_data("http://example.com", lead_info=SAMPLE_LEAD_INFO)

        assert result["qualified"] is True
        assert "service_levels" in result["site_analysis"]

    @patch("app.pipeline.enricher.settings")
    @patch("app.pipeline.enricher.run_diagnostic")
    @patch("app.pipeline.enricher.check_pagespeed")
    @patch("app.pipeline.enricher.fetch_website")
    def test_with_diagnostic_disqualified(self, mock_fetch, mock_pagespeed, mock_diag, mock_settings):
        from app.pipeline.diagnostic.state import NivelScore, ServiceLevelAnalysis

        mock_settings.ai_potential_threshold = 25
        mock_settings.skip_social_scraping = True
        mock_settings.apify_token = ""
        mock_fetch.return_value = {"status": "ok", "html": SAMPLE_HTML, "has_ssl": True}
        mock_pagespeed.return_value = {"performance_score": 70}
        sla = ServiceLevelAnalysis(
            lp=NivelScore(score=10, sinais=["s"], oportunidades=[], justificativa="j"),
            automacao_basica=NivelScore(score=5, sinais=["s"], oportunidades=[], justificativa="j"),
            mapa_automacoes=NivelScore(score=8, sinais=["s"], oportunidades=[], justificativa="j"),
            vertical_os=NivelScore(score=3, sinais=["s"], oportunidades=[], justificativa="j"),
            nivel_recomendado="lp",
            qualificado=False,
            motivo_desqualificacao="Sem potencial",
            resumo_executivo="Desqualificado.",
        )
        mock_diag.return_value = sla

        result = enrich_lead_data("http://example.com", lead_info=SAMPLE_LEAD_INFO)

        assert result["qualified"] is False
        assert "service_levels" in result["site_analysis"]

    @patch("app.pipeline.enricher.run_diagnostic")
    @patch("app.pipeline.enricher.check_pagespeed")
    @patch("app.pipeline.enricher.fetch_website")
    def test_diagnostic_failure_still_enriches(self, mock_fetch, mock_pagespeed, mock_diag):
        mock_fetch.return_value = {"status": "ok", "html": SAMPLE_HTML, "has_ssl": True}
        mock_pagespeed.return_value = {"performance_score": 70}
        mock_diag.return_value = None  # Graph failure

        result = enrich_lead_data("http://example.com", lead_info=SAMPLE_LEAD_INFO)

        assert result["qualified"] is True  # Default: qualified when no diagnostic
        assert "service_levels" not in result["site_analysis"]
        assert result["opportunity_score"] is not None
```

- [ ] **Step 5: Remove old imports no longer needed**

Remove `generate_diagnostic` from the test imports at the top of `test_enricher.py`. The import line should become:

```python
from app.pipeline.enricher import (
    analyze_html,
    calculate_score,
    _extract_visible_text,
    _extract_social_urls,
    _is_profile_url,
    _parse_diagnostic_response,
    _scrape_instagram_profile,
    scrape_social_profiles,
    enrich_lead_data,
)
```

Note: keep `generate_diagnostic` and `_parse_diagnostic_response` functions in `enricher.py` — they are not deleted yet, just no longer called by `enrich_lead_data`. The `TestGenerateDiagnostic` and `TestParseDiagnosticResponse` test classes can remain for now as they test standalone functions.

- [ ] **Step 6: Run all enricher tests**

Run: `cd backend && python -m pytest tests/test_enricher.py -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/pipeline/enricher.py backend/tests/test_enricher.py
git commit -m "feat: integrate LangGraph diagnostic into enricher pipeline"
```

---

### Task 7: Add TypeScript types for service levels

**Files:**
- Modify: `frontend/src/lib/types.ts:1-24`

- [ ] **Step 1: Add ServiceLevels types**

Add the following types at the end of `frontend/src/lib/types.ts`, before the `KANBAN_COLUMNS` export:

```typescript
export interface NivelScore {
  score: number;
  sinais: string[];
  oportunidades: string[];
  justificativa: string;
}

export type NivelKey = "lp" | "automacao_basica" | "mapa_automacoes" | "vertical_os";

export interface ServiceLevels {
  lp: NivelScore;
  automacao_basica: NivelScore;
  mapa_automacoes: NivelScore;
  vertical_os: NivelScore;
  nivel_recomendado: NivelKey;
  qualificado: boolean;
  motivo_desqualificacao: string | null;
  resumo_executivo: string;
}
```

- [ ] **Step 2: Run lint**

Run: `cd frontend && npm run lint`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/types.ts
git commit -m "feat: add ServiceLevels TypeScript types"
```

---

### Task 8: Create ServiceLevelTabs component

**Files:**
- Create: `frontend/src/components/service-level-tabs.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/service-level-tabs.tsx`:

```tsx
"use client";

import { useState } from "react";
import type { ServiceLevels, NivelScore, NivelKey } from "@/lib/types";

const NIVEL_LABELS: Record<NivelKey, string> = {
  lp: "LP",
  automacao_basica: "Automação",
  mapa_automacoes: "Mapa+Auto",
  vertical_os: "OS",
};

const NIVEL_FULL_LABELS: Record<NivelKey, string> = {
  lp: "Landing Page",
  automacao_basica: "Automação Básica",
  mapa_automacoes: "Mapa + Automações",
  vertical_os: "Vertical OS",
};

const NIVEL_ORDER: NivelKey[] = ["lp", "automacao_basica", "mapa_automacoes", "vertical_os"];

function scoreColor(score: number): string {
  if (score >= 60) return "text-accent";
  if (score >= 40) return "text-warning";
  return "text-text-muted";
}

function scoreBgColor(score: number): string {
  if (score >= 60) return "bg-accent";
  if (score >= 40) return "bg-warning";
  return "bg-text-muted";
}

function ScoreBar({ score }: { score: number }) {
  return (
    <div className="w-full h-1.5 rounded-full bg-surface-overlay">
      <div
        className={`h-full rounded-full transition-all ${scoreBgColor(score)}`}
        style={{ width: `${score}%` }}
      />
    </div>
  );
}

function NivelDetail({ nivel, label }: { nivel: NivelScore; label: string }) {
  return (
    <div className="space-y-3">
      {/* Score header */}
      <div className="flex items-center justify-between">
        <h4 className="text-[11px] uppercase tracking-widest font-[family-name:var(--font-mono)] text-text-muted">
          {label}
        </h4>
        <span className={`text-[13px] font-bold font-[family-name:var(--font-mono)] ${scoreColor(nivel.score)}`}>
          {nivel.score}/100
        </span>
      </div>
      <ScoreBar score={nivel.score} />

      {/* Sinais */}
      {nivel.sinais.length > 0 && (
        <div>
          <p className="text-[10px] uppercase tracking-widest font-[family-name:var(--font-mono)] text-text-muted mb-1.5">
            Sinais detectados
          </p>
          <div className="space-y-1">
            {nivel.sinais.map((sinal, i) => (
              <div key={i} className="flex items-start gap-2 text-[12px] text-text-secondary">
                <span className="w-1 h-1 rounded-full bg-text-muted shrink-0 mt-1.5" />
                {sinal}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Oportunidades */}
      {nivel.oportunidades.length > 0 && (
        <div>
          <p className="text-[10px] uppercase tracking-widest font-[family-name:var(--font-mono)] text-text-muted mb-1.5">
            Oportunidades
          </p>
          <div className="flex flex-wrap gap-1.5">
            {nivel.oportunidades.map((opp, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-info/10 border border-info/20 text-[10px] text-info font-[family-name:var(--font-mono)]"
              >
                {opp}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Justificativa */}
      <p className="text-[12px] text-text-secondary leading-relaxed">
        {nivel.justificativa}
      </p>
    </div>
  );
}

interface ServiceLevelTabsProps {
  serviceLevels: ServiceLevels;
}

export function ServiceLevelTabs({ serviceLevels }: ServiceLevelTabsProps) {
  const [activeTab, setActiveTab] = useState<NivelKey>(serviceLevels.nivel_recomendado);

  const activeNivel = serviceLevels[activeTab] as NivelScore;

  return (
    <div className="space-y-4">
      {/* Disqualification banner */}
      {!serviceLevels.qualificado && serviceLevels.motivo_desqualificacao && (
        <div className="rounded-lg border border-danger/30 bg-danger/5 px-3 py-2">
          <p className="text-[11px] text-danger font-[family-name:var(--font-mono)]">
            Desqualificado: {serviceLevels.motivo_desqualificacao}
          </p>
        </div>
      )}

      {/* Recommended level badge + resumo */}
      <div className="rounded-xl border border-border bg-surface p-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-[10px] uppercase tracking-widest font-[family-name:var(--font-mono)] text-text-muted">
            Nível recomendado
          </span>
          <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-accent-subtle border border-accent/20 text-[11px] text-accent font-semibold font-[family-name:var(--font-mono)]">
            {NIVEL_FULL_LABELS[serviceLevels.nivel_recomendado]}
          </span>
        </div>
        <p className="text-[13px] text-text-secondary leading-relaxed">
          {serviceLevels.resumo_executivo}
        </p>
      </div>

      {/* Tab bar */}
      <div className="rounded-xl border border-border bg-surface overflow-hidden">
        <div className="flex border-b border-border">
          {NIVEL_ORDER.map((key) => {
            const nivel = serviceLevels[key] as NivelScore;
            const isActive = key === activeTab;
            const isRecommended = key === serviceLevels.nivel_recomendado;
            return (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                className={`flex-1 flex flex-col items-center gap-0.5 px-2 py-2.5 transition-colors relative ${
                  isActive
                    ? "bg-surface-raised"
                    : "hover:bg-surface-raised/50"
                }`}
              >
                <span className={`text-[10px] font-[family-name:var(--font-mono)] uppercase tracking-wider ${
                  isActive ? "text-text" : "text-text-muted"
                }`}>
                  {NIVEL_LABELS[key]}
                </span>
                <span className={`text-[14px] font-bold font-[family-name:var(--font-mono)] ${scoreColor(nivel.score)}`}>
                  {nivel.score}
                </span>
                {/* Active indicator */}
                {isActive && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent" />
                )}
                {/* Recommended dot */}
                {isRecommended && !isActive && (
                  <div className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-accent" />
                )}
              </button>
            );
          })}
        </div>

        {/* Active tab content */}
        <div className="p-4">
          <NivelDetail
            nivel={activeNivel}
            label={NIVEL_FULL_LABELS[activeTab]}
          />
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Run lint**

Run: `cd frontend && npm run lint`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/service-level-tabs.tsx
git commit -m "feat: add ServiceLevelTabs component with 4-level scoring tabs"
```

---

### Task 9: Integrate tabs into LeadSheet and LeadDetail

**Files:**
- Modify: `frontend/src/components/lead-sheet.tsx:234-235`
- Modify: `frontend/src/components/lead-detail.tsx:64-65`

- [ ] **Step 1: Update LeadSheet**

In `frontend/src/components/lead-sheet.tsx`, add import at the top:

```typescript
import { ServiceLevelTabs } from "./service-level-tabs";
import type { ServiceLevels } from "@/lib/types";
```

Then replace line 235 (`<DiagnosticPanel siteAnalysis={lead.site_analysis as Record<string, unknown>} />`):

```tsx
              {/* Service Level Tabs or legacy DiagnosticPanel */}
              {(lead.site_analysis as Record<string, unknown>)?.service_levels ? (
                <ServiceLevelTabs
                  serviceLevels={(lead.site_analysis as Record<string, unknown>).service_levels as ServiceLevels}
                />
              ) : (
                <DiagnosticPanel siteAnalysis={lead.site_analysis as Record<string, unknown>} />
              )}
```

- [ ] **Step 2: Update LeadDetail**

In `frontend/src/components/lead-detail.tsx`, add import at the top:

```typescript
import { ServiceLevelTabs } from "./service-level-tabs";
import type { ServiceLevels } from "@/lib/types";
```

Then replace line 65 (`<DiagnosticPanel siteAnalysis={lead.site_analysis as Record<string, unknown>} compact />`):

```tsx
      {/* Service Level Tabs or legacy DiagnosticPanel */}
      {(lead.site_analysis as Record<string, unknown>)?.service_levels ? (
        <ServiceLevelTabs
          serviceLevels={(lead.site_analysis as Record<string, unknown>).service_levels as ServiceLevels}
        />
      ) : (
        <DiagnosticPanel siteAnalysis={lead.site_analysis as Record<string, unknown>} compact />
      )}
```

- [ ] **Step 3: Run lint**

Run: `cd frontend && npm run lint`
Expected: No errors

- [ ] **Step 4: Run build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/lead-sheet.tsx frontend/src/components/lead-detail.tsx
git commit -m "feat: integrate ServiceLevelTabs into lead sheet and detail views"
```

---

### Task 10: Integrar LangSmith (observabilidade)

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config.py`
- Modify: `backend/app/pipeline/diagnostic/graph.py`
- Modify: `backend/.env.example`

- [ ] **Step 1: Add langsmith dependency**

Add to `backend/requirements.txt` after `langchain-core`:

```
langsmith>=0.3
```

- [ ] **Step 2: Add config vars**

In `backend/app/config.py`, add after `skip_service_level_analysis`:

```python
    langsmith_api_key: str = ""
    langsmith_project: str = "sdr-machine"
    langsmith_tracing: bool = False
```

- [ ] **Step 3: Add env vars to .env.example**

Add to `backend/.env.example`:

```bash
# LangSmith (observabilidade do grafo de diagnóstico)
# LANGSMITH_API_KEY=ls__...
# LANGSMITH_PROJECT=sdr-machine
# LANGSMITH_TRACING=false
```

- [ ] **Step 4: Configure tracing in graph.py**

In `backend/app/pipeline/diagnostic/graph.py`, add this setup at the top of `run_diagnostic()`, before the guard clauses:

```python
    # Configure LangSmith tracing via env vars (LangGraph auto-instruments)
    import os
    if settings.langsmith_tracing and settings.langsmith_api_key:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
    else:
        os.environ.pop("LANGCHAIN_TRACING_V2", None)
```

This is all that's needed — LangGraph auto-sends traces to LangSmith when `LANGCHAIN_TRACING_V2=true`. Each graph execution appears as a trace with:
- Nós individuais (analyze_lp, analyze_automation, etc.)
- Input/output de cada nó
- Latência por nó e total
- Tokens consumidos por chamada LLM
- Erros capturados

- [ ] **Step 5: Install dependency**

Run: `cd backend && pip install -r requirements.txt`
Expected: `langsmith` installs successfully

- [ ] **Step 6: Commit**

```bash
git add backend/requirements.txt backend/app/config.py backend/app/pipeline/diagnostic/graph.py backend/.env.example
git commit -m "feat: add LangSmith tracing for diagnostic graph observability"
```

---

### Task 11: Run full test suite and final commit

**Files:** None (verification only)

- [ ] **Step 1: Run all backend tests**

Run: `cd backend && python -m pytest -v`
Expected: All tests pass

- [ ] **Step 2: Run frontend lint + build**

Run: `cd frontend && npm run lint && npm run build`
Expected: No errors

- [ ] **Step 3: Final commit if any remaining changes**

```bash
git status
```

If any unstaged changes exist, commit them.
