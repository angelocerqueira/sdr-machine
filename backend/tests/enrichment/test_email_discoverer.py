"""Tests for EmailDiscovererProvider."""
from unittest.mock import patch, MagicMock

from app.pipeline.enrichment.base_provider import EnrichmentContext
from app.pipeline.enrichment.providers.email_discoverer import EmailDiscovererProvider


class FakeLead:
    def __init__(self, website=None, email=None):
        self.website = website
        self.email = email


HTML_WITH_EMAIL = """
<html><body>
<a href="mailto:contato@clinica.com.br">Email</a>
Também: atendimento@clinica.com.br
</body></html>
"""

HTML_WITHOUT_EMAIL = "<html><body><p>nothing</p></body></html>"


def test_cannot_run_without_website_or_html():
    provider = EmailDiscovererProvider()
    assert provider.can_run(FakeLead(), context=EnrichmentContext()) is False


def test_can_run_with_html_in_context():
    provider = EmailDiscovererProvider()
    ctx = EnrichmentContext(html_content="<html></html>")
    lead = FakeLead(website="https://x.com")
    assert provider.can_run(lead, context=ctx) is True


def test_extracts_email_from_html():
    provider = EmailDiscovererProvider()
    ctx = EnrichmentContext(html_content=HTML_WITH_EMAIL)
    lead = FakeLead(website="https://clinica.com.br")
    result = provider.run(lead, ctx)
    assert result.success is True
    assert result.data["email"] in ("contato@clinica.com.br", "atendimento@clinica.com.br")
    found = result.data["site_analysis"]["emails_found"]
    assert "contato@clinica.com.br" in found
    assert "atendimento@clinica.com.br" in found


def test_skips_if_lead_already_has_email():
    provider = EmailDiscovererProvider()
    ctx = EnrichmentContext(html_content=HTML_WITH_EMAIL)
    lead = FakeLead(website="https://x.com", email="existing@x.com")
    result = provider.run(lead, ctx)
    assert "email" not in result.data
    assert len(result.data["site_analysis"]["emails_found"]) > 0


# --- EC14: email regex false positive ---

def test_ignores_image_filename_false_positives():
    html = '<img src="logo.png" srcset="logo@2x.png 2x, logo@3x.png 3x">'
    provider = EmailDiscovererProvider()
    ctx = EnrichmentContext(html_content=html)
    lead = FakeLead(website="https://x.com")
    result = provider.run(lead, ctx)
    found = result.data["site_analysis"]["emails_found"]
    assert all(not e.endswith(".png") for e in found)
    assert all(not e.endswith(".jpg") for e in found)


# --- EC5: email normalization (mixed case + whitespace) ---

def test_normalizes_mixed_case_emails():
    html = '<a href="mailto:Contato@Clinica.COM.BR">  Contato@Clinica.COM.BR  </a>'
    provider = EmailDiscovererProvider()
    ctx = EnrichmentContext(html_content=html)
    lead = FakeLead(website="https://clinica.com.br")
    result = provider.run(lead, ctx)
    found = result.data["site_analysis"]["emails_found"]
    assert "contato@clinica.com.br" in found


# --- EC16: Hunter 402 quota exceeded ---

@patch("app.pipeline.enrichment.providers.email_discoverer.provider_config_for", return_value={"api_key": "fake"})
@patch("app.pipeline.enrichment.providers.email_discoverer.requests.get")
def test_hunter_402_recorded_as_error_not_crash(mock_get, mock_pcf):
    mock_resp = MagicMock()
    mock_resp.status_code = 402
    mock_get.return_value = mock_resp

    provider = EmailDiscovererProvider()
    ctx = EnrichmentContext(html_content="<html></html>")
    lead = FakeLead(website="https://empresa.com")
    result = provider.run(lead, ctx)
    assert result.success is True
    assert any("402" in e for e in result.errors)


def test_no_emails_returns_success_with_empty():
    provider = EmailDiscovererProvider()
    ctx = EnrichmentContext(html_content=HTML_WITHOUT_EMAIL)
    lead = FakeLead(website="https://x.com")
    result = provider.run(lead, ctx)
    assert result.success is True
    assert result.data["site_analysis"]["emails_found"] == []


@patch("app.pipeline.enrichment.providers.email_discoverer.provider_config_for", return_value={"api_key": "fake_key"})
@patch("app.pipeline.enrichment.providers.email_discoverer.requests.get")
def test_hunter_api_called_when_key_configured(mock_get, mock_pcf):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": {
            "emails": [
                {"value": "contato@empresa.com.br", "confidence": 90},
                {"value": "vendas@empresa.com.br", "confidence": 80},
            ]
        }
    }
    mock_get.return_value = mock_resp

    provider = EmailDiscovererProvider()
    ctx = EnrichmentContext(html_content="<html></html>")
    lead = FakeLead(website="https://empresa.com.br")
    result = provider.run(lead, ctx)

    assert result.success is True
    assert "contato@empresa.com.br" in result.data["site_analysis"]["emails_found"]
