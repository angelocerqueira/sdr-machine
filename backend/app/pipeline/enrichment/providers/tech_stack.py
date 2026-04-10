"""Tech Stack Detector — pattern-matches technologies from HTML and headers."""
from __future__ import annotations

import re
import logging
from bs4 import BeautifulSoup

from app.pipeline.enrichment.base_provider import (
    BaseProvider,
    EnrichmentContext,
    ProviderResult,
)
from app.pipeline.enrichment.providers.tech_stack_patterns import (
    HTML_PATTERNS,
    META_GENERATOR_PATTERNS,
    HEADER_PATTERNS,
)

logger = logging.getLogger(__name__)


class TechStackProvider(BaseProvider):
    name = "tech_stack"
    display_name = "Tech Stack Detector"
    required_fields = []
    cost = "free"

    def can_run(self, lead, context: EnrichmentContext | None = None) -> bool:
        return bool(context and context.html_content)

    def run(self, lead, context: EnrichmentContext) -> ProviderResult:
        html = context.html_content or ""
        headers = context.response_headers or {}
        detected: list[dict] = []
        seen: set[str] = set()

        def _add(name: str, category: str):
            if name in seen:
                return
            seen.add(name)
            detected.append({"name": name, "category": category})

        for pattern, name, category in HTML_PATTERNS:
            try:
                if re.search(pattern, html, re.IGNORECASE):
                    _add(name, category)
            except re.error:
                continue

        try:
            soup = BeautifulSoup(html, "html.parser")
            gen = soup.find("meta", {"name": "generator"})
            if gen and gen.get("content"):
                content = gen["content"].lower()
                for pattern, name, category in META_GENERATOR_PATTERNS:
                    if re.search(pattern, content, re.IGNORECASE):
                        _add(name, category)
        except Exception:
            pass

        headers_lower = {k.lower(): (v or "") for k, v in headers.items()}
        for header_name, regex, name, category in HEADER_PATTERNS:
            val = headers_lower.get(header_name, "")
            if val and re.search(regex, val, re.IGNORECASE):
                _add(name, category)

        return ProviderResult(
            success=True,
            data={"tech_stack": detected},
            errors=[],
            source=self.name,
        )
