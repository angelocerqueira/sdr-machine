"""LangGraph diagnostic graph — parallel fan-out to 4 analyzers, fan-in to qualifier."""

import logging
import os
from typing import Annotated

from langgraph.graph import StateGraph, START, END

from app.config import settings
from app.integrations.resolver import provider_config_for
from app.pipeline.diagnostic.state import GraphState, ServiceLevelAnalysis
from app.pipeline.diagnostic.nodes.collect import collect_context
from app.pipeline.diagnostic.nodes.analyzers import (
    analyze_lp,
    analyze_automation,
    analyze_advanced,
    analyze_os,
)
from app.pipeline.diagnostic.nodes.marketing import analyze_marketing
from app.pipeline.diagnostic.nodes.qualify import qualify

logger = logging.getLogger(__name__)


def _configure_langsmith() -> None:
    """Configure LangSmith tracing from DB config (provider_config_for) with env fallback."""
    _cfg = provider_config_for("langsmith") or {}
    _api_key = _cfg.get("api_key", "")
    _project = _cfg.get("project", "")
    _tracing = _cfg.get("tracing", False)
    if _tracing and _api_key:
        os.environ["LANGSMITH_API_KEY"] = _api_key
        os.environ["LANGSMITH_PROJECT"] = _project or "sdr-machine"
        os.environ["LANGCHAIN_TRACING_V2"] = "true"


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

    _llm_cfg = provider_config_for("llm") or {}
    if not _llm_cfg.get("api_key", ""):
        logger.warning("Service Level Analysis: LLM_API_KEY não configurada")
        return None

    _configure_langsmith()

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
