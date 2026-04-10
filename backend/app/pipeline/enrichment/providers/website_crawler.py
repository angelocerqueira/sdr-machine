"""Website Crawler Provider — fetches site HTML, analyzes SSL/responsive/CTA,
runs PageSpeed, extracts social URLs. Reuses the existing logic from the legacy
enricher module (analyze_html, check_pagespeed, scrape_social_profiles).

Populates context.html_content and context.response_headers for downstream providers.
"""
from __future__ import annotations

import time
import logging
import requests

from app.pipeline.enrichment.base_provider import (
    BaseProvider,
    EnrichmentContext,
    ProviderResult,
)
from app.pipeline.enricher import (
    analyze_html,
    check_pagespeed,
    scrape_social_profiles,
)
from app.config import settings

logger = logging.getLogger(__name__)


def _normalize_url(value: str | None) -> str | None:
    """Normalize a website value into a crawlable URL.

    Returns None for empty / None. Preserves path/query/fragment. Adds https://
    if no scheme is present.
    """
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    if value.startswith(("http://", "https://")):
        return value
    return f"https://{value}"


class WebsiteCrawlerProvider(BaseProvider):
    name = "website_crawler"
    display_name = "Website Crawler"
    required_fields = ["website"]
    cost = "free"

    def can_run(self, lead, context: EnrichmentContext | None = None) -> bool:
        if _normalize_url(getattr(lead, "website", None)):
            return True
        if context and _normalize_url(context.discovered_website):
            return True
        return False

    def run(self, lead, context: EnrichmentContext) -> ProviderResult:
        # Resolve URL (lead.website takes precedence over context.discovered_website)
        raw_website = getattr(lead, "website", None) or (
            context.discovered_website if context else None
        )
        url = _normalize_url(raw_website)
        errors: list[str] = []
        site_data: dict = {}
        html = ""

        if not url:
            return ProviderResult(
                success=False,
                data={"site_analysis": {"status": "no_website"}},
                errors=["no_website"],
                source=self.name,
            )

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            html = resp.text[:15000]
            context.html_content = html
            context.response_headers = dict(resp.headers)
            is_ok = 200 <= resp.status_code < 400
            site_data = {
                "status": "ok" if is_ok else "http_error",
                "status_code": resp.status_code,
                "final_url": resp.url,
                "has_ssl": str(resp.url).startswith("https"),
                "content_length": len(resp.text),
            }
            if not is_ok:
                errors.append(f"http_{resp.status_code}")
        except requests.exceptions.SSLError:
            site_data = {"status": "ssl_error", "has_ssl": False}
            errors.append("ssl_error")
        except requests.exceptions.ConnectionError:
            site_data = {"status": "connection_error", "error": "Site fora do ar"}
            errors.append("connection_error")
        except requests.exceptions.Timeout:
            site_data = {"status": "timeout", "error": "Site muito lento"}
            errors.append("timeout")
        except Exception as exc:
            site_data = {"status": "error", "error": str(exc)[:100]}
            errors.append(str(exc)[:100])

        html_analysis = analyze_html(html) if html else {}

        pagespeed: dict = {}
        if site_data.get("status") == "ok":
            try:
                pagespeed = check_pagespeed(url)
                time.sleep(1)
            except Exception as exc:
                errors.append(f"pagespeed: {str(exc)[:100]}")

        site_analysis = {
            "status": site_data.get("status"),
            "has_ssl": site_data.get("has_ssl"),
            **html_analysis,
            "pagespeed": (pagespeed or {}).get("performance_score"),
        }

        social_profiles: dict = {}
        skip_social = getattr(settings, "skip_social_scraping", False)
        if getattr(settings, "apify_token", "") and not skip_social:
            try:
                lead_info = {
                    "nome": getattr(lead, "nome", ""),
                    "cidade": getattr(lead, "cidade", ""),
                }
                social_profiles = scrape_social_profiles(
                    lead_info, html_analysis.get("social_urls", {})
                )
            except Exception as exc:
                errors.append(f"social: {str(exc)[:100]}")

        data = {
            "site_analysis": site_analysis,
            "social_profiles": social_profiles,
        }

        # Always success=True when we have site status data — even for broken
        # sites. The site_analysis.status field communicates the *site's* health,
        # while success=True means the provider itself ran correctly.
        return ProviderResult(
            success=bool(site_data),
            data=data,
            errors=errors,
            source=self.name,
        )
