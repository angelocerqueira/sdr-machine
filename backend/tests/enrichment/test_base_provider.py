"""Tests for BaseProvider ABC and helper types."""
import pytest
from app.pipeline.enrichment.base_provider import (
    BaseProvider,
    EnrichmentContext,
    ProviderResult,
)


def test_enrichment_context_defaults():
    ctx = EnrichmentContext()
    assert ctx.html_content is None
    assert ctx.response_headers == {}
    assert ctx.discovered_website is None


def test_enrichment_context_with_values():
    ctx = EnrichmentContext(
        html_content="<html></html>",
        response_headers={"Server": "nginx"},
        discovered_website="https://example.com",
    )
    assert ctx.html_content == "<html></html>"
    assert ctx.response_headers == {"Server": "nginx"}
    assert ctx.discovered_website == "https://example.com"


def test_provider_result_success():
    result = ProviderResult(
        success=True,
        data={"email": "a@b.com"},
        errors=[],
        source="email_discoverer",
    )
    assert result.success is True
    assert result.data == {"email": "a@b.com"}
    assert result.errors == []
    assert result.source == "email_discoverer"


def test_provider_result_failure():
    result = ProviderResult(
        success=False,
        data={},
        errors=["HTTP 500"],
        source="apollo",
    )
    assert result.success is False
    assert result.errors == ["HTTP 500"]


def test_base_provider_is_abstract():
    with pytest.raises(TypeError):
        BaseProvider()  # type: ignore


class _DummyProvider(BaseProvider):
    name = "dummy"
    display_name = "Dummy Provider"
    required_fields = ["website"]
    cost = "free"

    def can_run(self, lead) -> bool:
        return bool(getattr(lead, "website", None))

    def run(self, lead, context):
        return ProviderResult(
            success=True,
            data={"site_analysis": {"dummy": True}},
            errors=[],
            source=self.name,
        )


def test_provider_can_run_true():
    class FakeLead:
        website = "https://example.com"
    provider = _DummyProvider()
    assert provider.can_run(FakeLead()) is True


def test_provider_can_run_false():
    class FakeLead:
        website = None
    provider = _DummyProvider()
    assert provider.can_run(FakeLead()) is False


def test_provider_run_returns_result():
    class FakeLead:
        website = "https://example.com"
    provider = _DummyProvider()
    ctx = EnrichmentContext()
    result = provider.run(FakeLead(), ctx)
    assert result.success is True
    assert result.source == "dummy"
