"""LLM analyzer nodes — one per service level, run in parallel."""

import logging

from langchain_openai import ChatOpenAI

from app.config import settings
from app.pipeline.diagnostic.state import GraphState, NivelScore, FALLBACK_NIVEL
from app.pipeline.diagnostic.prompts.shared import format_lead_context
from app.pipeline.diagnostic.prompts.lp import LP_SYSTEM_PROMPT, build_lp_prompt
from app.pipeline.diagnostic.prompts.automation import AUTOMATION_SYSTEM_PROMPT, build_automation_prompt
from app.pipeline.diagnostic.prompts.advanced import ADVANCED_SYSTEM_PROMPT, build_advanced_prompt
from app.pipeline.diagnostic.prompts.os import OS_SYSTEM_PROMPT, build_os_prompt
from app.pipeline.html_utils import _extract_visible_text

logger = logging.getLogger(__name__)


def _get_llm() -> ChatOpenAI:
    """Create a ChatOpenAI instance pointing at the configured LLM provider."""
    model = settings.diagnostic_model or settings.llm_model
    return ChatOpenAI(
        model=model,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
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
