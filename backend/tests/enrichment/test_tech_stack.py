"""Tests for TechStackProvider."""
from app.pipeline.enrichment.base_provider import EnrichmentContext
from app.pipeline.enrichment.providers.tech_stack import TechStackProvider


class FakeLead:
    pass


def test_cannot_run_without_html():
    provider = TechStackProvider()
    assert provider.can_run(FakeLead(), context=EnrichmentContext()) is False


def test_cannot_run_with_empty_string_html():
    provider = TechStackProvider()
    ctx = EnrichmentContext(html_content="")
    assert provider.can_run(FakeLead(), context=ctx) is False


def test_detects_wordpress():
    html = '<html><head><link rel="stylesheet" href="/wp-content/themes/x.css"></head></html>'
    ctx = EnrichmentContext(html_content=html)
    provider = TechStackProvider()
    result = provider.run(FakeLead(), ctx)
    assert result.success is True
    names = [t["name"] for t in result.data["tech_stack"]]
    assert "WordPress" in names


def test_detects_google_analytics():
    html = '<html><head><script src="https://www.googletagmanager.com/gtag/js"></script></head></html>'
    ctx = EnrichmentContext(html_content=html)
    provider = TechStackProvider()
    result = provider.run(FakeLead(), ctx)
    names = [t["name"] for t in result.data["tech_stack"]]
    assert "Google Analytics" in names or "Google Tag Manager" in names


def test_detects_from_headers():
    html = "<html></html>"
    ctx = EnrichmentContext(
        html_content=html,
        response_headers={"X-Powered-By": "PHP/7.4"},
    )
    provider = TechStackProvider()
    result = provider.run(FakeLead(), ctx)
    names = [t["name"] for t in result.data["tech_stack"]]
    assert "PHP" in names


def test_empty_html_returns_empty_stack():
    ctx = EnrichmentContext(html_content="<html></html>")
    provider = TechStackProvider()
    result = provider.run(FakeLead(), ctx)
    assert result.success is True
    assert result.data["tech_stack"] == []


def test_detects_wix_template():
    html = '<html><head><meta name="generator" content="Wix.com Website Builder"></head></html>'
    ctx = EnrichmentContext(html_content=html)
    provider = TechStackProvider()
    result = provider.run(FakeLead(), ctx)
    names = [t["name"] for t in result.data["tech_stack"]]
    assert "Wix" in names
