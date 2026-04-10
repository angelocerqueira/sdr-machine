"""Enrichment Orchestrator — decides which providers to run and executes them.

Phases:
  1. Discovery — CNPJ (can discover website)
  2. Crawl — WebsiteCrawler, Schema.org, TechStack (chain via context.html_content)
  3. Contact — EmailDiscoverer, Apollo
  4. Scoring — recalculate opportunity_score

Supports `skip_providers` and `force_providers` to override the auto-plan.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, date, timezone

from app.pipeline.enrichment.base_provider import (
    BaseProvider,
    EnrichmentContext,
    ProviderResult,
)
from app.pipeline.enrichment.providers.website_crawler import WebsiteCrawlerProvider
from app.pipeline.enrichment.providers.schema_extractor import SchemaOrgProvider
from app.pipeline.enrichment.providers.tech_stack import TechStackProvider
from app.pipeline.enrichment.providers.cnpj_enricher import CnpjProvider
from app.pipeline.enrichment.providers.email_discoverer import EmailDiscovererProvider
from app.pipeline.enrichment.providers.apollo_enricher import ApolloProvider
from app.pipeline.enrichment.scoring import calculate_score

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentPlan:
    providers: list[BaseProvider] = field(default_factory=list)


def _default_providers() -> list[BaseProvider]:
    return [
        CnpjProvider(),
        WebsiteCrawlerProvider(),
        SchemaOrgProvider(),
        TechStackProvider(),
        EmailDiscovererProvider(),
        ApolloProvider(),
    ]


_PHASE_ORDER = [
    "cnpj_enricher",
    "website_crawler",
    "schema_extractor",
    "tech_stack",
    "email_discoverer",
    "apollo",
]


class EnrichmentOrchestrator:
    """Central coordination module for the smart enrichment pipeline."""

    def __init__(self, providers: list[BaseProvider] | None = None):
        providers = providers or _default_providers()
        self._providers_by_name: dict[str, BaseProvider] = {
            p.name: p for p in providers
        }

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------

    def plan(
        self,
        lead,
        skip_providers: list[str] | None = None,
        force_providers: list[str] | None = None,
    ) -> EnrichmentPlan:
        """Build an ordered list of providers to run for *lead*.

        - ``skip_providers`` removes providers regardless of eligibility.
        - ``force_providers`` adds providers even if ``can_run`` returns False.
        - When both specify the same provider, *skip wins*.
        """
        skip = set(skip_providers or [])
        force = set(force_providers or []) - skip  # skip overrides force
        selected: list[BaseProvider] = []

        has_website = bool(getattr(lead, "website", None))
        might_discover_website = (
            bool(getattr(lead, "cnpj", None))
            and not has_website
            and "cnpj_enricher" not in skip
        )
        include_crawl_chain = has_website or might_discover_website

        # Names that should be included optimistically when a crawl chain is
        # expected (the individual provider's ``can_run`` will still gate
        # actual execution in ``execute``).
        optimistic_names = (
            {
                "website_crawler",
                "schema_extractor",
                "tech_stack",
                "email_discoverer",
                "apollo",
            }
            if include_crawl_chain
            else set()
        )

        for name in _PHASE_ORDER:
            provider = self._providers_by_name.get(name)
            if not provider:
                continue
            if name in skip:
                continue
            if name in force:
                selected.append(provider)
                continue
            if name in optimistic_names:
                selected.append(provider)
                continue
            # Fall back to asking the provider itself
            try:
                runnable = provider.can_run(lead)
                if runnable:
                    selected.append(provider)
            except Exception as exc:
                logger.warning("can_run failed for %s: %s", name, exc)

        return EnrichmentPlan(providers=selected)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(self, lead, plan: EnrichmentPlan) -> dict:
        """Run every provider in *plan* sequentially, merge results, and score."""
        context = EnrichmentContext()

        merged_site_analysis: dict = {}
        merged_social_profiles: dict = {}
        merged_tech_stack: list = []
        merged_socios: list = []
        enrichment_sources: list = []
        flat: dict = {}

        # Snapshot existing lead fields so we never overwrite them.
        _PROTECTED_KEYS = (
            "email", "cnpj", "razao_social", "porte", "cnae",
            "data_fundacao", "website",
        )
        existing_flat = {
            key: getattr(lead, key, None)
            for key in _PROTECTED_KEYS
        }

        for provider in plan.providers:
            source_entry: dict = {
                "provider": provider.name,
                "status": "ok",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            try:
                # Gate: re-check can_run with current context
                runnable = provider.can_run(lead, context=context)
                if not runnable:
                    source_entry["status"] = "skipped"
                    source_entry["error"] = "preconditions not met"
                    enrichment_sources.append(source_entry)
                    continue

                result = provider.run(lead, context)

                if not isinstance(result, ProviderResult):
                    source_entry["status"] = "error"
                    source_entry["error"] = "invalid result type"
                    enrichment_sources.append(source_entry)
                    continue

                if not result.success:
                    source_entry["status"] = "skipped"
                    if result.errors:
                        source_entry["error"] = "; ".join(result.errors)[:200]
                    enrichment_sources.append(source_entry)
                    continue

                # --- Merge data ---
                data = result.data or {}

                sa = data.get("site_analysis") or {}
                if sa:
                    merged_site_analysis.update(sa)

                sp = data.get("social_profiles") or {}
                if sp:
                    merged_social_profiles.update(sp)

                ts = data.get("tech_stack") or []
                if ts:
                    merged_tech_stack = ts

                sc = data.get("socios") or []
                if sc:
                    merged_socios = sc

                # Flat fields — first-writer wins, existing lead values protected
                for key in _PROTECTED_KEYS:
                    if key not in data or not data[key]:
                        continue
                    if existing_flat.get(key):
                        continue
                    if flat.get(key):
                        continue
                    flat[key] = data[key]

                if result.errors:
                    source_entry["error"] = "; ".join(result.errors)[:200]

            except Exception as exc:
                logger.exception("provider %s crashed", provider.name)
                source_entry["status"] = "error"
                source_entry["error"] = str(exc)[:200]

            enrichment_sources.append(source_entry)

        # --- Scoring ---
        lead_view = {
            "website": flat.get("website") or getattr(lead, "website", None),
            "email": flat.get("email") or getattr(lead, "email", None),
        }

        data_fundacao_val = flat.get("data_fundacao")
        data_fundacao_date: date | None = None
        if isinstance(data_fundacao_val, str):
            try:
                data_fundacao_date = datetime.fromisoformat(data_fundacao_val).date()
            except ValueError:
                data_fundacao_date = None

        score, reasons = calculate_score(
            lead_view,
            merged_site_analysis,
            tech_stack=merged_tech_stack,
            data_fundacao=data_fundacao_date,
        )

        return {
            "opportunity_score": score,
            "opportunity_reasons": reasons,
            "site_analysis": merged_site_analysis,
            "social_profiles": merged_social_profiles,
            "tech_stack": merged_tech_stack,
            "socios": merged_socios,
            "enrichment_sources": enrichment_sources,
            **flat,
        }

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def run(
        self,
        lead,
        skip_providers: list[str] | None = None,
        force_providers: list[str] | None = None,
    ) -> dict:
        """Plan + execute in one call."""
        plan = self.plan(
            lead,
            skip_providers=skip_providers,
            force_providers=force_providers,
        )
        return self.execute(lead, plan)
