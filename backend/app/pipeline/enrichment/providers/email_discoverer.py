"""Email Discoverer — extracts emails from crawled HTML + optional Hunter.io."""
from __future__ import annotations

import re
import logging
import requests

from app.pipeline.enrichment.base_provider import (
    BaseProvider,
    EnrichmentContext,
    ProviderResult,
)
from app.integrations.resolver import provider_config_for

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico")

HUNTER_DOMAIN_URL = "https://api.hunter.io/v2/domain-search"

_IGNORE_LOCAL_PARTS = {"noreply", "no-reply", "donotreply", "do-not-reply"}
_IGNORE_DOMAINS = {"sentry.io", "wixpress.com", "example.com"}


def _extract_domain(website: str) -> str:
    if not website:
        return ""
    match = re.search(r"https?://(?:www\.)?([^/]+)", website)
    if match:
        return match.group(1).lower()
    return ""


def _filter_emails(emails: list[str]) -> list[str]:
    result = []
    seen = set()
    for e in emails:
        e_lower = e.strip().lower()
        if e_lower in seen:
            continue
        if e_lower.endswith(_IMAGE_EXTS):
            continue
        local, _, domain = e_lower.partition("@")
        if not local or not domain or "." not in domain:
            continue
        if local in _IGNORE_LOCAL_PARTS:
            continue
        if domain in _IGNORE_DOMAINS:
            continue
        if re.fullmatch(r"\d+x", local):
            continue
        seen.add(e_lower)
        result.append(e_lower)
    return result


class EmailDiscovererProvider(BaseProvider):
    name = "email_discoverer"
    display_name = "Email Discoverer"
    required_fields = ["website"]
    cost = "freemium"

    def can_run(self, lead, context: EnrichmentContext | None = None) -> bool:
        has_html = bool(context and context.html_content)
        has_website = bool(getattr(lead, "website", None) or (context and context.discovered_website))
        return has_html or has_website

    def run(self, lead, context: EnrichmentContext) -> ProviderResult:
        html = (context.html_content or "") if context else ""
        emails_found: list[str] = []
        errors: list[str] = []

        if html:
            emails_found.extend(EMAIL_RE.findall(html))

        emails_found = _filter_emails(emails_found)

        website = getattr(lead, "website", None) or (context.discovered_website if context else None)
        _cfg = provider_config_for("hunter") or {}
        _api_key = _cfg.get("api_key", "")
        if _api_key and website:
            domain = _extract_domain(website)
            if domain:
                try:
                    resp = requests.get(
                        HUNTER_DOMAIN_URL,
                        params={
                            "domain": domain,
                            "api_key": _api_key,
                            "limit": 10,
                        },
                        timeout=15,
                    )
                    if resp.status_code == 200:
                        body = resp.json() or {}
                        hunter_emails = [
                            e.get("value")
                            for e in (body.get("data", {}).get("emails") or [])
                            if e.get("value")
                        ]
                        for e in _filter_emails(hunter_emails):
                            if e not in emails_found:
                                emails_found.append(e)
                    else:
                        errors.append(f"hunter http {resp.status_code}")
                except Exception as exc:
                    errors.append(f"hunter: {str(exc)[:100]}")

        data: dict = {"site_analysis": {"emails_found": emails_found}}

        existing_email = getattr(lead, "email", None)
        if not existing_email and emails_found:
            domain = _extract_domain(website or "")
            preferred = next(
                (e for e in emails_found if domain and e.endswith(f"@{domain}")),
                emails_found[0],
            )
            data["email"] = preferred

        return ProviderResult(
            success=True,
            data=data,
            errors=errors,
            source=self.name,
        )
