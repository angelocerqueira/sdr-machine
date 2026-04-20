"""Classification provider — consumes data from all earlier providers."""
from __future__ import annotations

import logging
from typing import Any

from app.pipeline.enrichment.base_provider import (
    BaseProvider, EnrichmentContext, ProviderResult,
)
from app.pipeline.enrichment.classifier import classify

logger = logging.getLogger(__name__)


class ClassificationProvider(BaseProvider):
    name = "classification"
    display_name = "Lead Profile & Nicho Classification"
    required_fields: list[str] = []
    cost = "free"

    def __init__(self, llm_client: Any = None):
        self._llm_client = llm_client

    def can_run(self, lead, context: EnrichmentContext | None = None) -> bool:
        return True

    def run(self, lead, context: EnrichmentContext) -> ProviderResult:
        try:
            lead_data = self._consolidate(lead)
            result = classify(lead_data, llm_client=self._llm_client)
            return ProviderResult(
                success=True,
                data=result.to_dict(),
                errors=[result.error_reason] if result.error_reason else [],
                source=self.name,
            )
        except Exception as exc:
            logger.exception("classification provider crashed: %s", exc)
            return ProviderResult(
                success=False,
                data={},
                errors=[f"unexpected: {str(exc)[:200]}"],
                source=self.name,
            )

    def _consolidate(self, lead) -> dict:
        """Build the dict passed to classify()."""
        sa = getattr(lead, "site_analysis", None) or {}
        top_reviews = getattr(lead, "top_reviews", None) or []
        reviews_text = []
        for r in top_reviews[:3]:
            if isinstance(r, dict):
                reviews_text.append(r.get("text") or r.get("comment") or "")
            elif isinstance(r, str):
                reviews_text.append(r)

        rating = getattr(lead, "rating", None)
        return {
            "has_website": bool(getattr(lead, "website", None)),
            "score": getattr(lead, "opportunity_score", None),
            "rating": float(rating) if rating is not None else None,
            "review_count": getattr(lead, "reviews_count", None),
            "has_ssl": sa.get("has_ssl"),
            "has_analytics": sa.get("has_analytics"),
            "has_chatbot": sa.get("has_chatbot"),
            "has_whatsapp_cta": sa.get("has_whatsapp_cta"),
            "has_instagram": getattr(lead, "has_instagram", None),
            "nicho_raw": getattr(lead, "nicho", None) or getattr(lead, "categoria", None),
            "nome": getattr(lead, "nome", None),
            "descricao": sa.get("description") or "",
            "reviews": [r for r in reviews_text if r],
            "telefone": getattr(lead, "telefone", None),
            "endereco": getattr(lead, "endereco", None),
        }
