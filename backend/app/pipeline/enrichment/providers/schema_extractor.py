"""Schema.org Extractor — parses JSON-LD scripts from crawled HTML."""
from __future__ import annotations

import json
import logging
from bs4 import BeautifulSoup

from app.pipeline.enrichment.base_provider import (
    BaseProvider,
    EnrichmentContext,
    ProviderResult,
)

logger = logging.getLogger(__name__)

_TYPE_PRIORITY = {
    "LocalBusiness": 100,
    "Restaurant": 95,
    "MedicalBusiness": 95,
    "Store": 90,
    "Organization": 80,
    "Corporation": 80,
    "WebSite": 20,
    "WebPage": 10,
}


def _score_type(type_value) -> int:
    if isinstance(type_value, list) and type_value:
        type_value = type_value[0]
    if not isinstance(type_value, str):
        return 0
    return _TYPE_PRIORITY.get(type_value, 50)


def _flatten_candidates(data) -> list[dict]:
    if isinstance(data, list):
        out: list[dict] = []
        for item in data:
            out.extend(_flatten_candidates(item))
        return out
    if isinstance(data, dict):
        if "@graph" in data and isinstance(data["@graph"], list):
            return _flatten_candidates(data["@graph"])
        return [data]
    return []


def _build_structured(data: dict) -> dict:
    t = data.get("@type") or data.get("type") or ""
    return {
        "type": t if isinstance(t, str) else (t[0] if t else ""),
        "name": data.get("name", ""),
        "telephone": data.get("telephone", ""),
        "opening_hours": data.get("openingHours", ""),
        "address": data.get("address", {}),
        "raw": data,
    }


class SchemaOrgProvider(BaseProvider):
    name = "schema_extractor"
    display_name = "Schema.org Extractor"
    required_fields = []
    cost = "free"

    def can_run(self, lead, context: EnrichmentContext | None = None) -> bool:
        return bool(context and context.html_content)

    def run(self, lead, context: EnrichmentContext) -> ProviderResult:
        html = (context.html_content or "") if context else ""
        if not html:
            return ProviderResult(
                success=True,
                data={"site_analysis": {"structured_data": None}},
                errors=[],
                source=self.name,
            )

        candidates: list[dict] = []
        errors: list[str] = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            for script in soup.find_all("script", {"type": "application/ld+json"}):
                try:
                    text = script.string or script.get_text() or ""
                    if not text.strip():
                        continue
                    parsed = json.loads(text)
                    candidates.extend(_flatten_candidates(parsed))
                except (json.JSONDecodeError, ValueError) as exc:
                    errors.append(f"jsonld parse: {str(exc)[:80]}")
                    continue
        except Exception as exc:
            errors.append(f"soup: {str(exc)[:80]}")

        best = None
        best_score = -1
        for c in candidates:
            s = _score_type(c.get("@type") or c.get("type"))
            if s > best_score:
                best = c
                best_score = s

        structured = _build_structured(best) if best else {}

        return ProviderResult(
            success=True,
            data={"site_analysis": {"structured_data": structured}},
            errors=errors,
            source=self.name,
        )
