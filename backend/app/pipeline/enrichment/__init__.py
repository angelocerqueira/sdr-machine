"""Smart enrichment pipeline package."""
from app.pipeline.enrichment.base_provider import (
    BaseProvider,
    EnrichmentContext,
    ProviderResult,
)
from app.pipeline.enrichment.orchestrator import (
    EnrichmentOrchestrator,
    EnrichmentPlan,
)
from app.pipeline.enrichment.scoring import calculate_score

__all__ = [
    "BaseProvider",
    "EnrichmentContext",
    "ProviderResult",
    "EnrichmentOrchestrator",
    "EnrichmentPlan",
    "calculate_score",
]
