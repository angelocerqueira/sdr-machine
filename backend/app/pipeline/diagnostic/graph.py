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
    # Configure LangSmith tracing via env vars (LangGraph auto-instruments)
    import os
    if settings.langsmith_tracing and settings.langsmith_api_key:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
    else:
        os.environ.pop("LANGCHAIN_TRACING_V2", None)

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
