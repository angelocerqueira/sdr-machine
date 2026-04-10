"""Tests for WebsiteCrawlerProvider."""
from unittest.mock import patch, MagicMock

from app.pipeline.enrichment.base_provider import EnrichmentContext
from app.pipeline.enrichment.providers.website_crawler import WebsiteCrawlerProvider


class FakeLead:
    def __init__(self, website=None, nome="Test", nicho=None, cidade=None,
                 categoria=None, rating=None, reviews_count=0, top_reviews=None):
        self.website = website
        self.nome = nome
        self.nicho = nicho
        self.cidade = cidade
        self.categoria = categoria
        self.rating = rating
        self.reviews_count = reviews_count
        self.top_reviews = top_reviews or []


def test_can_run_with_website():
    lead = FakeLead(website="https://example.com")
    provider = WebsiteCrawlerProvider()
    assert provider.can_run(lead) is True


def test_can_run_without_website_uses_context():
    lead = FakeLead(website=None)
    provider = WebsiteCrawlerProvider()
    ctx = EnrichmentContext(discovered_website="https://found.com")
    # can_run can use context
    assert provider.can_run(lead, context=ctx) is True


def test_cannot_run_without_any_website():
    lead = FakeLead(website=None)
    provider = WebsiteCrawlerProvider()
    assert provider.can_run(lead) is False


@patch("app.pipeline.enrichment.providers.website_crawler.requests.get")
def test_run_populates_context_html(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><head><meta name=\"viewport\"></head><body></body></html>"
    mock_resp.url = "https://example.com"
    mock_resp.headers = {"Server": "nginx"}
    mock_get.return_value = mock_resp

    provider = WebsiteCrawlerProvider()
    lead = FakeLead(website="https://example.com")
    ctx = EnrichmentContext()

    with patch("app.pipeline.enrichment.providers.website_crawler.check_pagespeed",
               return_value={"performance_score": 80}):
        result = provider.run(lead, ctx)

    assert result.success is True
    assert ctx.html_content is not None
    assert "<html>" in ctx.html_content
    assert ctx.response_headers.get("Server") == "nginx"
    assert result.data["site_analysis"]["has_ssl"] is True


@patch("app.pipeline.enrichment.providers.website_crawler.requests.get")
def test_run_handles_connection_error(mock_get):
    import requests
    mock_get.side_effect = requests.exceptions.ConnectionError("boom")

    provider = WebsiteCrawlerProvider()
    lead = FakeLead(website="https://example.com")
    ctx = EnrichmentContext()
    result = provider.run(lead, ctx)

    # Not fatal — still success but with error status in data
    assert result.data["site_analysis"]["status"] == "connection_error"


@patch("app.pipeline.enrichment.providers.website_crawler.requests.get")
def test_run_handles_timeout(mock_get):
    import requests
    mock_get.side_effect = requests.exceptions.Timeout("slow")

    provider = WebsiteCrawlerProvider()
    lead = FakeLead(website="https://example.com")
    ctx = EnrichmentContext()
    result = provider.run(lead, ctx)
    assert result.data["site_analysis"]["status"] == "timeout"


# --- EC1, EC2, EC3: URL normalization ---

@patch("app.pipeline.enrichment.providers.website_crawler.requests.get")
def test_url_without_scheme_is_prefixed_with_https(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html></html>"
    mock_resp.url = "https://www.example.com"
    mock_resp.headers = {}
    mock_get.return_value = mock_resp

    provider = WebsiteCrawlerProvider()
    lead = FakeLead(website="www.example.com")
    ctx = EnrichmentContext()

    with patch("app.pipeline.enrichment.providers.website_crawler.check_pagespeed",
               return_value={"performance_score": 50}):
        provider.run(lead, ctx)

    called_url = mock_get.call_args[0][0]
    assert called_url.startswith("https://")


def test_empty_website_string_treated_as_missing():
    provider = WebsiteCrawlerProvider()
    lead = FakeLead(website="")
    assert provider.can_run(lead) is False


@patch("app.pipeline.enrichment.providers.website_crawler.requests.get")
def test_url_with_path_and_query_preserved(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html></html>"
    mock_resp.url = "https://x.com/about?ref=ad"
    mock_resp.headers = {}
    mock_get.return_value = mock_resp

    provider = WebsiteCrawlerProvider()
    lead = FakeLead(website="https://x.com/about?ref=ad")
    ctx = EnrichmentContext()

    with patch("app.pipeline.enrichment.providers.website_crawler.check_pagespeed",
               return_value={"performance_score": 50}):
        provider.run(lead, ctx)

    called_url = mock_get.call_args[0][0]
    assert called_url == "https://x.com/about?ref=ad"
