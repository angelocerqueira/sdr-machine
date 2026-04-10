"""Tests for ApolloProvider."""
from unittest.mock import patch, MagicMock

from app.pipeline.enrichment.base_provider import EnrichmentContext
from app.pipeline.enrichment.providers.apollo_enricher import ApolloProvider


class FakeLead:
    def __init__(self, website=None, email=None):
        self.website = website
        self.email = email


@patch("app.pipeline.enrichment.providers.apollo_enricher.settings")
def test_cannot_run_without_api_key(mock_settings):
    mock_settings.apollo_api_key = ""
    provider = ApolloProvider()
    assert provider.can_run(FakeLead(website="https://x.com")) is False


@patch("app.pipeline.enrichment.providers.apollo_enricher.settings")
def test_cannot_run_without_website_or_email(mock_settings):
    mock_settings.apollo_api_key = "fake"
    provider = ApolloProvider()
    assert provider.can_run(FakeLead()) is False


@patch("app.pipeline.enrichment.providers.apollo_enricher.settings")
def test_can_run_with_key_and_website(mock_settings):
    mock_settings.apollo_api_key = "fake"
    provider = ApolloProvider()
    assert provider.can_run(FakeLead(website="https://x.com")) is True


@patch("app.pipeline.enrichment.providers.apollo_enricher.settings")
@patch("app.pipeline.enrichment.providers.apollo_enricher.requests.get")
def test_enrich_organization(mock_get, mock_settings):
    mock_settings.apollo_api_key = "fake_key"
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "organization": {
            "name": "Clinica X",
            "short_description": "Odonto",
            "industry": "Healthcare",
            "estimated_num_employees": 25,
            "linkedin_url": "https://linkedin.com/company/x",
        }
    }
    mock_get.return_value = mock_resp

    provider = ApolloProvider()
    lead = FakeLead(website="https://clinicax.com")
    ctx = EnrichmentContext()
    result = provider.run(lead, ctx)

    assert result.success is True
    apollo_data = result.data["site_analysis"]["apollo_data"]
    assert apollo_data["name"] == "Clinica X"
    assert apollo_data["estimated_num_employees"] == 25

    # API key must be in header, not query params (security)
    call_kwargs = mock_get.call_args
    assert call_kwargs.kwargs.get("headers", {}).get("X-Api-Key") == "fake_key"
    assert "api_key" not in (call_kwargs.kwargs.get("params") or {})


# --- EC17: Apollo 200 with null organization ---

@patch("app.pipeline.enrichment.providers.apollo_enricher.settings")
@patch("app.pipeline.enrichment.providers.apollo_enricher.requests.get")
def test_handles_null_organization(mock_get, mock_settings):
    mock_settings.apollo_api_key = "fake"
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"organization": None}
    mock_get.return_value = mock_resp

    provider = ApolloProvider()
    result = provider.run(FakeLead(website="https://x.com"), EnrichmentContext())
    assert result.success is True
    apollo_data = result.data["site_analysis"].get("apollo_data", {})
    assert not apollo_data.get("name")


@patch("app.pipeline.enrichment.providers.apollo_enricher.settings")
@patch("app.pipeline.enrichment.providers.apollo_enricher.requests.get")
def test_handles_rate_limit(mock_get, mock_settings):
    mock_settings.apollo_api_key = "fake_key"
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_get.return_value = mock_resp

    provider = ApolloProvider()
    lead = FakeLead(website="https://x.com")
    ctx = EnrichmentContext()
    result = provider.run(lead, ctx)
    assert result.success is False
    assert any("429" in e or "rate" in e.lower() for e in result.errors)
