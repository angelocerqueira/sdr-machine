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
