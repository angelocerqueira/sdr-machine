"""Apollo Enricher — calls Apollo.io Organization Enrichment API."""
from __future__ import annotations

import logging
import re
import requests

from app.pipeline.enrichment.base_provider import (
    BaseProvider,
    EnrichmentContext,
    ProviderResult,
)
from app.config import settings

logger = logging.getLogger(__name__)

APOLLO_ORG_ENRICH_URL = "https://api.apollo.io/v1/organizations/enrich"


def _extract_domain(website: str) -> str:
    match = re.search(r"https?://(?:www\.)?([^/]+)", website or "")
    return match.group(1).lower() if match else ""


class ApolloProvider(BaseProvider):
    name = "apollo"
    display_name = "Apollo.io"
    required_fields = ["website"]
    cost = "freemium"

    def can_run(self, lead, context: EnrichmentContext | None = None) -> bool:
        if not settings.apollo_api_key:
            return False
        website = getattr(lead, "website", None) or (context.discovered_website if context else None)
        email = getattr(lead, "email", None)
        return bool(website or email)

    def run(self, lead, context: EnrichmentContext) -> ProviderResult:
        website = getattr(lead, "website", None) or (context.discovered_website if context else None)
        domain = _extract_domain(website or "")
        if not domain:
            email = getattr(lead, "email", None) or ""
            if "@" in email:
                domain = email.split("@", 1)[1].strip().lower()

        if not domain:
            return ProviderResult(
                success=False, data={}, errors=["no domain"], source=self.name
            )

        try:
            resp = requests.get(
                APOLLO_ORG_ENRICH_URL,
                headers={"X-Api-Key": settings.apollo_api_key},
                params={"domain": domain},
                timeout=20,
            )
        except Exception as exc:
            return ProviderResult(
                success=False, data={}, errors=[f"http: {str(exc)[:80]}"], source=self.name
            )

        if resp.status_code == 429:
            return ProviderResult(
                success=False, data={}, errors=["http 429 rate limit"], source=self.name
            )
        if resp.status_code != 200:
            return ProviderResult(
                success=False, data={}, errors=[f"http {resp.status_code}"], source=self.name
            )

        try:
            body = resp.json() or {}
        except Exception as exc:
            return ProviderResult(
                success=False, data={}, errors=[f"json: {str(exc)[:80]}"], source=self.name
            )

        org = body.get("organization") or {}
        apollo_data = {
            "name": org.get("name", ""),
            "description": (org.get("short_description") or "")[:500],
            "industry": org.get("industry", ""),
            "estimated_num_employees": org.get("estimated_num_employees"),
            "linkedin_url": org.get("linkedin_url", ""),
            "founded_year": org.get("founded_year"),
            "logo_url": org.get("logo_url", ""),
        }

        return ProviderResult(
            success=True,
            data={"site_analysis": {"apollo_data": apollo_data}},
            errors=[],
            source=self.name,
        )
