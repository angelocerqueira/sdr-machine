"""Base types for enrichment providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import Lead


@dataclass
class EnrichmentContext:
    """Mutable context shared between providers during a single enrichment run.

    Providers can read values set by earlier providers (e.g. html_content from
    the Website Crawler) and write values for later providers to consume.
    """
    html_content: str | None = None
    response_headers: dict = field(default_factory=dict)
    discovered_website: str | None = None
    computed_score: int | None = None  # set by orchestrator after scoring, before classification


@dataclass
class ProviderResult:
    """Result returned by a provider's run() method.

    - `data`: fields to merge into the Lead (keys should match Lead column names
      or nested dicts like `site_analysis`).
    - `errors`: non-fatal errors (do not stop subsequent providers).
    - `source`: provider name, used to build `enrichment_sources` audit trail.
    """
    success: bool
    data: dict
    errors: list[str]
    source: str


class BaseProvider(ABC):
    """Abstract base class for enrichment providers.

    Subclasses must set class attributes `name`, `display_name`,
    `required_fields`, `cost` and implement `can_run` and `run`.
    """
    name: str = ""
    display_name: str = ""
    required_fields: list[str] = []
    cost: str = "free"  # "free" | "freemium"

    @abstractmethod
    def can_run(self, lead: "Lead", context: "EnrichmentContext | None" = None) -> bool:
        """Return True if the provider has the minimum data it needs."""

    @abstractmethod
    def run(self, lead: "Lead", context: EnrichmentContext) -> ProviderResult:
        """Execute enrichment. Should not raise — catch exceptions and return a
        ProviderResult with success=False and the error in `errors`.
        """
