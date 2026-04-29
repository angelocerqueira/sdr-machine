"""Diagnostic Provider — wraps run_diagnostic (LangGraph) into the orchestrator.

Generates ServiceLevelAnalysis + MarketingDiagnostic and persists both into
``site_analysis`` (under ``service_levels`` and ``diagnostico_marketing``) so
generator/outreach/UI consume them via the standard merge path.

Reads crawl intermediates (site_data, html_analysis, pagespeed, social_profiles)
from EnrichmentContext, populated by WebsiteCrawlerProvider.
"""
from __future__ import annotations

import logging

from app.pipeline.enrichment.base_provider import (
    BaseProvider, EnrichmentContext, ProviderResult,
)
from app.pipeline.diagnostic import run_diagnostic

logger = logging.getLogger(__name__)


class DiagnosticProvider(BaseProvider):
    name = "diagnostic"
    display_name = "Service Level + Marketing Diagnostic"
    required_fields: list[str] = []
    cost = "paid"  # LLM call

    def can_run(self, lead, context: EnrichmentContext | None = None) -> bool:
        if context is None:
            return False
        # Needs a successful crawl to have content to diagnose
        return bool(context.html_content)

    def run(self, lead, context: EnrichmentContext) -> ProviderResult:
        try:
            lead_info = {
                "nome": getattr(lead, "nome", "") or "",
                "nicho": getattr(lead, "nicho", "") or getattr(lead, "categoria", "") or "",
                "cidade": getattr(lead, "cidade", "") or "",
                "telefone": getattr(lead, "telefone", "") or "",
                "endereco": getattr(lead, "endereco", "") or "",
                "rating": getattr(lead, "rating", None),
                "reviews_count": getattr(lead, "reviews_count", 0) or 0,
                "top_reviews": getattr(lead, "top_reviews", None) or [],
            }

            service_levels = run_diagnostic(
                lead_info=lead_info,
                site_data=context.site_data or {},
                html_analysis=context.html_analysis or {},
                pagespeed=context.pagespeed or {},
                html=context.html_content or "",
                social_profiles=context.social_profiles or {},
            )

            if service_levels is None:
                # LLM disabled or graph failed — non-fatal, just no diagnostic data
                return ProviderResult(
                    success=True, data={}, errors=[], source=self.name,
                )

            site_analysis: dict = {"service_levels": service_levels.model_dump()}
            if service_levels.diagnostico_marketing:
                site_analysis["diagnostico_marketing"] = (
                    service_levels.diagnostico_marketing.model_dump()
                )

            return ProviderResult(
                success=True,
                data={"site_analysis": site_analysis},
                errors=[],
                source=self.name,
            )

        except Exception as exc:
            logger.exception("diagnostic provider crashed: %s", exc)
            return ProviderResult(
                success=False,
                data={},
                errors=[f"unexpected: {str(exc)[:200]}"],
                source=self.name,
            )
