"""End-to-end integration test: orchestrator runs over a fake lead with mocks."""
from unittest.mock import patch, MagicMock

from app.pipeline.enrichment.orchestrator import EnrichmentOrchestrator


class FakeLead:
    def __init__(self, **kwargs):
        self.website = kwargs.get("website")
        self.email = kwargs.get("email")
        self.cnpj = kwargs.get("cnpj")
        self.nome = kwargs.get("nome", "Clinica X")
        self.cidade = kwargs.get("cidade", "Chapeco SC")
        self.telefone = kwargs.get("telefone")
        self.nicho = kwargs.get("nicho")
        self.categoria = kwargs.get("categoria")
        self.rating = kwargs.get("rating")
        self.reviews_count = kwargs.get("reviews_count", 0)
        self.top_reviews = kwargs.get("top_reviews", [])


@patch("app.pipeline.enrichment.providers.apollo_enricher.settings")
@patch("app.pipeline.enrichment.providers.email_discoverer.settings")
@patch("app.pipeline.enrichment.providers.website_crawler.check_pagespeed")
@patch("app.pipeline.enrichment.providers.website_crawler.requests.get")
def test_full_pipeline_on_website_lead(
    mock_crawler_get, mock_pagespeed, mock_email_settings, mock_apollo_settings
):
    mock_email_settings.hunter_api_key = ""
    mock_apollo_settings.apollo_api_key = ""

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.url = "https://clinicax.com"
    mock_resp.text = """
    <html>
    <head>
      <meta name="viewport" content="width=device-width">
      <meta name="generator" content="WordPress">
    </head>
    <body>
      <a href="mailto:contato@clinicax.com">email</a>
      <script src="/wp-content/themes/foo/bar.js"></script>
      <a href="https://instagram.com/clinicax">ig</a>
      <button>Agende sua consulta</button>
    </body>
    </html>
    """
    mock_resp.headers = {"Server": "nginx"}
    mock_crawler_get.return_value = mock_resp
    mock_pagespeed.return_value = {"performance_score": 75}

    lead = FakeLead(website="https://clinicax.com")
    orch = EnrichmentOrchestrator()

    with patch(
        "app.pipeline.enrichment.providers.website_crawler.settings"
    ) as mock_crawler_settings:
        mock_crawler_settings.apify_token = ""
        mock_crawler_settings.skip_social_scraping = True
        result = orch.run(lead)

    # Assertions
    assert result["opportunity_score"] is not None
    assert result["site_analysis"]["has_ssl"] is True
    assert result["site_analysis"]["has_responsive_meta"] is True
    # Tech stack detected WordPress
    names = [t["name"] for t in result["tech_stack"]]
    assert "WordPress" in names
    # Email extracted
    assert result.get("email") == "contato@clinicax.com"
    # Enrichment sources recorded
    source_names = [s["provider"] for s in result["enrichment_sources"]]
    assert "website_crawler" in source_names
    assert "schema_extractor" in source_names
    assert "tech_stack" in source_names
    assert "email_discoverer" in source_names


def test_full_pipeline_skips_providers_via_override():
    lead = FakeLead(website="https://example.com")
    orch = EnrichmentOrchestrator()
    plan = orch.plan(lead, skip_providers=["apollo", "email_discoverer", "website_crawler",
                                             "schema_extractor", "tech_stack", "cnpj_enricher",
                                             "classification"])
    assert plan.providers == []
