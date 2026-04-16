"""Tests for EnrichmentOrchestrator — planning + execution."""
from unittest.mock import patch, MagicMock

from app.pipeline.enrichment.base_provider import (
    BaseProvider,
    EnrichmentContext,
    ProviderResult,
)
from app.pipeline.enrichment.orchestrator import (
    EnrichmentOrchestrator,
    EnrichmentPlan,
)


class FakeLead:
    def __init__(self, **kwargs):
        self.website = kwargs.get("website")
        self.email = kwargs.get("email")
        self.cnpj = kwargs.get("cnpj")
        self.nome = kwargs.get("nome", "Test")
        self.cidade = kwargs.get("cidade")
        self.telefone = kwargs.get("telefone")
        self.nicho = kwargs.get("nicho")
        self.categoria = kwargs.get("categoria")
        self.rating = kwargs.get("rating")
        self.reviews_count = kwargs.get("reviews_count", 0)
        self.top_reviews = kwargs.get("top_reviews", [])


class StubProvider(BaseProvider):
    """Provider that records invocations and returns a preset ProviderResult."""
    def __init__(self, name: str, cost="free", result=None, can_run_result=True):
        self.name = name
        self.display_name = name
        self.required_fields = []
        self.cost = cost
        self._result = result or ProviderResult(
            success=True, data={}, errors=[], source=name
        )
        self._can_run = can_run_result
        self.calls = 0

    def can_run(self, lead, context=None):
        return self._can_run

    def run(self, lead, context):
        self.calls += 1
        return self._result


def test_plan_with_website_runs_crawler_chain():
    lead = FakeLead(website="https://example.com")
    orch = EnrichmentOrchestrator()
    plan = orch.plan(lead)
    names = [p.name for p in plan.providers]
    assert "website_crawler" in names
    assert "schema_extractor" in names
    assert "tech_stack" in names


def test_plan_without_website_but_with_cnpj_discovers_first():
    lead = FakeLead(cnpj="12345678000190")
    orch = EnrichmentOrchestrator()
    plan = orch.plan(lead)
    names = [p.name for p in plan.providers]
    assert names[0] == "cnpj_enricher"
    assert "website_crawler" in names
    assert "schema_extractor" in names
    assert "tech_stack" in names


def test_plan_with_only_nome_and_phone_is_mostly_empty():
    lead = FakeLead(nome="Nada", telefone="+554999")
    orch = EnrichmentOrchestrator()
    plan = orch.plan(lead)
    names = [p.name for p in plan.providers]
    assert "website_crawler" not in names
    assert "cnpj_enricher" not in names
    assert "apollo" not in names


def test_skip_providers_honored():
    lead = FakeLead(website="https://example.com")
    orch = EnrichmentOrchestrator()
    plan = orch.plan(lead, skip_providers=["apollo", "email_discoverer"])
    names = [p.name for p in plan.providers]
    assert "apollo" not in names
    assert "email_discoverer" not in names
    assert "website_crawler" in names


def test_force_providers_bypasses_can_run():
    lead = FakeLead()
    orch = EnrichmentOrchestrator()
    plan = orch.plan(lead, force_providers=["apollo"])
    names = [p.name for p in plan.providers]
    assert "apollo" in names


def test_execute_merges_provider_data():
    lead = FakeLead(website="https://example.com")
    orch = EnrichmentOrchestrator()
    stub_crawler = StubProvider(
        "website_crawler",
        result=ProviderResult(
            success=True,
            data={"site_analysis": {"has_ssl": True, "status": "ok"}},
            errors=[],
            source="website_crawler",
        ),
    )
    stub_cnpj = StubProvider(
        "cnpj_enricher",
        result=ProviderResult(
            success=True,
            data={"razao_social": "TEST LTDA", "porte": "ME"},
            errors=[],
            source="cnpj_enricher",
        ),
    )
    orch._providers_by_name = {
        "website_crawler": stub_crawler,
        "cnpj_enricher": stub_cnpj,
    }
    plan = EnrichmentPlan(providers=[stub_crawler, stub_cnpj])
    result = orch.execute(lead, plan)

    assert result["opportunity_score"] is not None
    assert result["site_analysis"]["has_ssl"] is True
    assert result["razao_social"] == "TEST LTDA"
    sources = [s["provider"] for s in result["enrichment_sources"]]
    assert "website_crawler" in sources
    assert "cnpj_enricher" in sources


def test_existing_email_preserved_over_discovered():
    lead = FakeLead(website="https://x.com", email="existing@x.com")
    orch = EnrichmentOrchestrator()
    stub = StubProvider(
        "email_discoverer",
        result=ProviderResult(
            success=True,
            data={"email": "discovered@x.com"},
            errors=[],
            source="email_discoverer",
        ),
    )
    plan = EnrichmentPlan(providers=[stub])
    result = orch.execute(lead, plan)
    assert "email" not in result or result["email"] == "existing@x.com"


def test_existing_website_preserved_over_discovered():
    lead = FakeLead(website="https://existing.com")
    orch = EnrichmentOrchestrator()
    stub = StubProvider(
        "cnpj_enricher",
        result=ProviderResult(
            success=True,
            data={"website": "https://discovered.com", "razao_social": "X LTDA"},
            errors=[],
            source="cnpj_enricher",
        ),
    )
    plan = EnrichmentPlan(providers=[stub])
    result = orch.execute(lead, plan)
    assert "website" not in result or result["website"] == "https://existing.com"
    assert result["razao_social"] == "X LTDA"


def test_existing_cnpj_preserved():
    lead = FakeLead()
    lead.cnpj = "99999999000100"
    orch = EnrichmentOrchestrator()
    stub = StubProvider(
        "cnpj_enricher",
        result=ProviderResult(
            success=True,
            data={"cnpj": "11111111000100", "razao_social": "Y LTDA"},
            errors=[],
            source="cnpj_enricher",
        ),
    )
    plan = EnrichmentPlan(providers=[stub])
    result = orch.execute(lead, plan)
    assert "cnpj" not in result or result["cnpj"] == "99999999000100"


def test_empty_plan_returns_valid_result():
    lead = FakeLead(nome="Only Name Lead", telefone="+554999")
    orch = EnrichmentOrchestrator()
    plan = EnrichmentPlan(providers=[])
    result = orch.execute(lead, plan)
    assert result["opportunity_score"] is not None
    assert result["opportunity_reasons"] is not None
    assert result["enrichment_sources"] == []
    assert result["site_analysis"] == {}
    assert result["tech_stack"] == []


def test_run_returns_fresh_lists_not_appended():
    lead = FakeLead(website="https://x.com")
    lead.enrichment_sources = [{"provider": "old", "status": "ok"}]
    lead.tech_stack = [{"name": "OldTech", "category": "x"}]

    orch = EnrichmentOrchestrator()
    stub = StubProvider(
        "website_crawler",
        result=ProviderResult(
            success=True,
            data={
                "site_analysis": {"status": "ok", "has_ssl": True},
                "tech_stack": [{"name": "NewTech", "category": "y"}],
            },
            errors=[],
            source="website_crawler",
        ),
    )
    plan = EnrichmentPlan(providers=[stub])
    result = orch.execute(lead, plan)

    sources = result["enrichment_sources"]
    assert all(s["provider"] != "old" for s in sources)
    assert any(s["provider"] == "website_crawler" for s in sources)

    names = [t["name"] for t in result["tech_stack"]]
    assert "OldTech" not in names


def test_provider_returns_invalid_type_recorded_as_error():
    lead = FakeLead(website="https://x.com")
    orch = EnrichmentOrchestrator()

    class BadProvider(BaseProvider):
        name = "bad"
        display_name = "bad"
        required_fields = []
        cost = "free"
        def can_run(self, lead, context=None): return True
        def run(self, lead, context):
            return {"not": "a ProviderResult"}

    plan = EnrichmentPlan(providers=[BadProvider()])
    result = orch.execute(lead, plan)
    entry = next((s for s in result["enrichment_sources"] if s["provider"] == "bad"), None)
    assert entry is not None
    assert entry["status"] == "error"


def test_skip_overrides_force_when_both_specified():
    lead = FakeLead(website="https://x.com")
    orch = EnrichmentOrchestrator()
    plan = orch.plan(
        lead,
        skip_providers=["apollo"],
        force_providers=["apollo"],
    )
    names = [p.name for p in plan.providers]
    assert "apollo" not in names


def test_execute_continues_on_provider_exception():
    lead = FakeLead(website="https://example.com")
    orch = EnrichmentOrchestrator()

    class FailingProvider(BaseProvider):
        name = "failing"
        display_name = "failing"
        required_fields = []
        cost = "free"
        def can_run(self, lead, context=None): return True
        def run(self, lead, context):
            raise RuntimeError("boom")

    good_provider = StubProvider(
        "website_crawler",
        result=ProviderResult(
            success=True,
            data={"site_analysis": {"status": "ok", "has_ssl": True}},
            errors=[],
            source="website_crawler",
        ),
    )

    plan = EnrichmentPlan(providers=[FailingProvider(), good_provider])
    result = orch.execute(lead, plan)

    sources = result["enrichment_sources"]
    failing_entry = next((s for s in sources if s["provider"] == "failing"), None)
    assert failing_entry is not None
    assert failing_entry["status"] == "error"
    assert good_provider.calls == 1


def test_orchestrator_returns_dimensional_score_fields():
    """Garante que o orchestrator retorna os 5 novos campos de score dimensional."""
    orch = EnrichmentOrchestrator(providers=[])

    class _FakeLead:
        nome = "Clínica Teste"
        telefone = "11999998888"
        website = None
        rating = 2.5
        reviews_count = 5
        google_maps_url = "https://maps.google.com/place/x"
        top_reviews = []
        cnpj = None
        email = None

    result = orch.run(_FakeLead())

    assert "score_acessibilidade" in result
    assert "score_lp" in result
    assert "score_automacao" in result
    assert "score_mapa" in result
    assert "nivel_recomendado" in result
    # Com celular válido, acessibilidade deve passar o gate
    assert result["score_acessibilidade"] >= 40
    # Com rating baixo e poucas reviews, score_mapa deve ser alto
    assert result["score_mapa"] >= 40
    # nivel_recomendado deve ser um dos valores válidos
    assert result["nivel_recomendado"] in ("lp", "automacao", "mapa")
