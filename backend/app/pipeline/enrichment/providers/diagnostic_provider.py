"""Diagnostic Provider — wraps run_diagnostic (LangGraph) into the orchestrator.

Generates ServiceLevelAnalysis + MarketingDiagnostic and persists both into
``site_analysis`` (under ``service_levels`` and ``diagnostico_marketing``) so
generator/outreach/UI consume them via the standard merge path.

Reads crawl intermediates (site_data, html_analysis, pagespeed, social_profiles)
from EnrichmentContext, populated by WebsiteCrawlerProvider. Runs even when
the crawl chain is empty: the LLM still receives lead_info (nicho, cidade,
rating, reviews, top_reviews) and produces a marketing diagnostic from that.
"""
from __future__ import annotations

import logging

from app.config import settings
from app.integrations.resolver import provider_config_for
from app.pipeline.enrichment.base_provider import (
    BaseProvider, EnrichmentContext, ProviderResult,
)
from app.pipeline.diagnostic import run_diagnostic

logger = logging.getLogger(__name__)


def _none_reason() -> str:
    """Why run_diagnostic might have returned None — used for audit trail."""
    if settings.skip_service_level_analysis:
        return "service level analysis disabled (settings.skip_service_level_analysis)"
    llm_cfg = provider_config_for("llm") or {}
    if not llm_cfg.get("api_key"):
        return "LLM_API_KEY not configured"
    return "graph returned None (check logs for upstream cause)"


def _normalize_top_reviews(raw, limit: int = 3) -> list[str]:
    """Coerce stored top_reviews into a list[str] for prompts.

    Lead.top_reviews is JSON — usually list[str] from the scraper, but legacy
    CSV imports can store list[dict] (with `text` or `comment` keys). The LLM
    prompt formats each entry directly, so dicts must be flattened first.
    """
    if not raw:
        return []
    out: list[str] = []
    for r in raw[:limit]:
        if isinstance(r, dict):
            text = r.get("text") or r.get("comment") or ""
        elif isinstance(r, str):
            text = r
        else:
            text = ""
        if text:
            out.append(text)
    return out


class DiagnosticProvider(BaseProvider):
    name = "diagnostic"
    display_name = "Service Level + Marketing Diagnostic"
    required_fields: list[str] = []
    cost = "paid"  # LLM call

    def can_run(self, lead, context: EnrichmentContext | None = None) -> bool:
        # Always runs — generates MarketingDiagnostic from lead_info even
        # when no site was crawled. Leads without a website are the highest
        # opportunity ones and need the strategy the most.
        return True

    def run(self, lead, context: EnrichmentContext) -> ProviderResult:
        try:
            lead_info = {
                "nome": getattr(lead, "nome", "") or "",
                "nicho": getattr(lead, "nicho", "") or "",
                "categoria": getattr(lead, "categoria", "") or "",
                "cidade": getattr(lead, "cidade", "") or "",
                "telefone": getattr(lead, "telefone", "") or "",
                "endereco": getattr(lead, "endereco", "") or "",
                "rating": getattr(lead, "rating", None),
                "reviews_count": getattr(lead, "reviews_count", 0) or 0,
                "top_reviews": _normalize_top_reviews(
                    getattr(lead, "top_reviews", None)
                ),
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
                # LLM disabled or graph failed — non-fatal, but surface the
                # reason in result.errors so the orchestrator records it in
                # enrichment_sources (otherwise the skip is invisible).
                reason = _none_reason()
                logger.warning("diagnostic skipped: %s", reason)
                return ProviderResult(
                    success=True, data={}, errors=[reason], source=self.name,
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
