"""Tests for SchemaOrgProvider."""
from app.pipeline.enrichment.base_provider import EnrichmentContext
from app.pipeline.enrichment.providers.schema_extractor import SchemaOrgProvider


class FakeLead:
    pass


HTML_WITH_JSONLD = """
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  "name": "Clinic XYZ",
  "telephone": "+554999887766",
  "openingHours": "Mo-Fr 08:00-18:00",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "Rua das Flores 123",
    "addressLocality": "Chapecó"
  }
}
</script>
</head><body></body></html>
"""

HTML_WITHOUT_JSONLD = "<html><body><p>nothing</p></body></html>"


def test_cannot_run_without_html():
    provider = SchemaOrgProvider()
    ctx = EnrichmentContext()
    assert provider.can_run(FakeLead(), context=ctx) is False


def test_can_run_with_html():
    provider = SchemaOrgProvider()
    ctx = EnrichmentContext(html_content="<html></html>")
    assert provider.can_run(FakeLead(), context=ctx) is True


def test_extracts_jsonld():
    provider = SchemaOrgProvider()
    ctx = EnrichmentContext(html_content=HTML_WITH_JSONLD)
    result = provider.run(FakeLead(), ctx)
    assert result.success is True
    structured = result.data["site_analysis"]["structured_data"]
    assert structured["type"] == "LocalBusiness"
    assert "Clinic XYZ" in structured.get("name", "")


def test_handles_no_jsonld():
    provider = SchemaOrgProvider()
    ctx = EnrichmentContext(html_content=HTML_WITHOUT_JSONLD)
    result = provider.run(FakeLead(), ctx)
    # Not an error — just nothing to extract
    assert result.success is True
    assert result.data["site_analysis"]["structured_data"] in (None, {}, [])


def test_handles_malformed_jsonld():
    bad_html = '<script type="application/ld+json">{not json}</script>'
    provider = SchemaOrgProvider()
    ctx = EnrichmentContext(html_content=bad_html)
    result = provider.run(FakeLead(), ctx)
    # Should not raise
    assert result.success is True


# --- EC11: @graph wrapper ---

def test_extracts_jsonld_with_graph_wrapper():
    html = """
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@graph": [
        {"@type": "WebSite", "name": "Site X"},
        {"@type": "LocalBusiness", "name": "Clinic X", "telephone": "+554999"}
      ]
    }
    </script>
    """
    provider = SchemaOrgProvider()
    ctx = EnrichmentContext(html_content=html)
    result = provider.run(FakeLead(), ctx)
    structured = result.data["site_analysis"]["structured_data"]
    # Prefer LocalBusiness over WebSite
    assert structured["type"] == "LocalBusiness"
    assert structured["name"] == "Clinic X"


# --- EC12: top-level array ---

def test_extracts_jsonld_top_level_array():
    html = """
    <script type="application/ld+json">
    [
      {"@type": "Organization", "name": "Org A"},
      {"@type": "LocalBusiness", "name": "Clinic Y"}
    ]
    </script>
    """
    provider = SchemaOrgProvider()
    ctx = EnrichmentContext(html_content=html)
    result = provider.run(FakeLead(), ctx)
    structured = result.data["site_analysis"]["structured_data"]
    assert structured["type"] in ("Organization", "LocalBusiness")


# --- EC13: empty html string ---

def test_empty_string_html():
    provider = SchemaOrgProvider()
    ctx = EnrichmentContext(html_content="")
    # can_run returns False for empty string (distinct from None)
    assert provider.can_run(FakeLead(), context=ctx) is False
