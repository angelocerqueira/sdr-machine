"""Tests for DiagnosticProvider — wraps run_diagnostic into the orchestrator chain."""
from unittest.mock import patch, MagicMock

from app.pipeline.enrichment.base_provider import EnrichmentContext
from app.pipeline.enrichment.providers.diagnostic_provider import DiagnosticProvider


class FakeLead:
    def __init__(self, **kwargs):
        self.website = kwargs.get("website", "https://example.com")
        self.nome = kwargs.get("nome", "Test")
        self.cidade = kwargs.get("cidade", "Porto Alegre")
        self.nicho = kwargs.get("nicho", "advogados")
        self.categoria = kwargs.get("categoria")
        self.telefone = kwargs.get("telefone")
        self.endereco = kwargs.get("endereco")
        self.rating = kwargs.get("rating")
        self.reviews_count = kwargs.get("reviews_count", 0)
        self.top_reviews = kwargs.get("top_reviews", [])


def test_can_run_always_returns_true():
    """Provider runs even without a crawled site — the LLM uses lead_info
    (nicho, cidade, rating, reviews, top_reviews) to generate a marketing
    diagnostic. Leads without a website are the highest-opportunity ones
    and were the segment most penalized by the previous html_content gate."""
    provider = DiagnosticProvider()
    lead = FakeLead()

    assert provider.can_run(lead, EnrichmentContext()) is True
    assert provider.can_run(lead, None) is True

    ctx = EnrichmentContext(html_content="<html></html>")
    ctx.site_data = {"status": "ok"}
    ctx.html_analysis = {"title": "x"}
    ctx.pagespeed = {}
    assert provider.can_run(lead, ctx) is True


def test_run_records_skip_reason_when_llm_disabled(monkeypatch):
    """When run_diagnostic returns None, the provider surfaces the reason
    in result.errors so it's captured in enrichment_sources audit trail."""
    provider = DiagnosticProvider()
    lead = FakeLead()
    ctx = EnrichmentContext()

    monkeypatch.setattr(
        "app.pipeline.enrichment.providers.diagnostic_provider.settings",
        type("S", (), {"skip_service_level_analysis": True})(),
    )

    with patch(
        "app.pipeline.enrichment.providers.diagnostic_provider.run_diagnostic",
        return_value=None,
    ):
        result = provider.run(lead, ctx)

    assert result.success is True
    assert any("disabled" in e for e in result.errors)


def test_run_persists_diagnostico_marketing_into_site_analysis():
    provider = DiagnosticProvider()
    lead = FakeLead()
    ctx = EnrichmentContext(html_content="<html></html>")
    ctx.site_data = {"status": "ok", "has_ssl": True}
    ctx.html_analysis = {"title": "Site Test"}
    ctx.pagespeed = {"performance_score": 50}

    fake_diag = MagicMock()
    fake_diag.model_dump.return_value = {
        "resumo_executivo": "ok",
        "momento_funil": "descoberta",
    }
    fake_service_levels = MagicMock()
    fake_service_levels.diagnostico_marketing = fake_diag
    fake_service_levels.model_dump.return_value = {
        "nivel_recomendado": "lp",
        "qualificado": True,
    }

    with patch(
        "app.pipeline.enrichment.providers.diagnostic_provider.run_diagnostic",
        return_value=fake_service_levels,
    ):
        result = provider.run(lead, ctx)

    assert result.success is True
    sa = result.data["site_analysis"]
    assert sa["service_levels"]["nivel_recomendado"] == "lp"
    assert sa["diagnostico_marketing"]["momento_funil"] == "descoberta"


def test_run_handles_none_when_llm_disabled():
    """When run_diagnostic returns None (e.g., no LLM key), provider succeeds without data."""
    provider = DiagnosticProvider()
    lead = FakeLead()
    ctx = EnrichmentContext(html_content="<html></html>")
    ctx.site_data = {"status": "ok"}
    ctx.html_analysis = {}
    ctx.pagespeed = {}

    with patch(
        "app.pipeline.enrichment.providers.diagnostic_provider.run_diagnostic",
        return_value=None,
    ):
        result = provider.run(lead, ctx)

    # Provider didn't crash; just had nothing to add
    assert result.success is True
    assert "diagnostico_marketing" not in result.data.get("site_analysis", {})


def test_run_isolated_from_diagnostic_exceptions():
    """If run_diagnostic raises, provider returns success=False but doesn't propagate."""
    provider = DiagnosticProvider()
    lead = FakeLead()
    ctx = EnrichmentContext(html_content="<html></html>")
    ctx.site_data = {"status": "ok"}
    ctx.html_analysis = {}
    ctx.pagespeed = {}

    with patch(
        "app.pipeline.enrichment.providers.diagnostic_provider.run_diagnostic",
        side_effect=RuntimeError("boom"),
    ):
        result = provider.run(lead, ctx)

    assert result.success is False
    assert any("boom" in e for e in result.errors)


def test_lead_info_passes_nicho_and_categoria_separately():
    """Prompt em diagnostic/prompts/shared.py usa AMBOS os campos:
    `Nicho/Categoria: {nicho} / {categoria}`. Eles devem chegar separados."""
    provider = DiagnosticProvider()
    lead = FakeLead(nicho="dentista", categoria="Dentista")
    ctx = EnrichmentContext(html_content="<html></html>")
    ctx.site_data = {"status": "ok"}
    ctx.html_analysis = {}
    ctx.pagespeed = {}

    captured: dict = {}

    def _capture(lead_info, **kwargs):
        captured.update(lead_info)
        return None  # short-circuit; we only care about lead_info shape

    with patch(
        "app.pipeline.enrichment.providers.diagnostic_provider.run_diagnostic",
        side_effect=_capture,
    ):
        provider.run(lead, ctx)

    assert captured.get("nicho") == "dentista"
    assert captured.get("categoria") == "Dentista"


def test_top_reviews_normalized_when_stored_as_dicts():
    """Some leads have top_reviews as list[dict] (CSV import / legacy data).
    Provider must extract the text so the prompt doesn't print raw dicts."""
    provider = DiagnosticProvider()
    lead = FakeLead()
    lead.top_reviews = [
        {"text": "Excelente atendimento!", "rating": 5},
        {"comment": "Muito profissional"},
        "Já vem normalizado",
        {"text": ""},  # empty text should be dropped
    ]
    ctx = EnrichmentContext(html_content="<html></html>")
    ctx.site_data = {"status": "ok"}
    ctx.html_analysis = {}
    ctx.pagespeed = {}

    captured: dict = {}

    def _capture(lead_info, **kwargs):
        captured.update(lead_info)
        return None

    with patch(
        "app.pipeline.enrichment.providers.diagnostic_provider.run_diagnostic",
        side_effect=_capture,
    ):
        provider.run(lead, ctx)

    reviews = captured.get("top_reviews")
    assert reviews == [
        "Excelente atendimento!",
        "Muito profissional",
        "Já vem normalizado",
    ]
