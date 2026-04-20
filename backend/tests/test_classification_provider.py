from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.models import Lead
from app.pipeline.enrichment.base_provider import EnrichmentContext, ProviderResult
from app.pipeline.enrichment.providers.classification_provider import (
    ClassificationProvider,
)


def _lead(**kw):
    return Lead(
        nome=kw.get("nome", "Lead X"),
        rating=kw.get("rating", 4.5),
        reviews_count=kw.get("reviews_count", 50),
        website=kw.get("website", None),
        opportunity_score=kw.get("opportunity_score", 40),
        site_analysis=kw.get("site_analysis") or {},
        nicho=kw.get("nicho", "Clinica Odontologica"),
        has_instagram=kw.get("has_instagram", False),
        telefone="11999999999",
    )


def test_can_run_returns_true_always():
    provider = ClassificationProvider()
    assert provider.can_run(_lead()) is True
    assert provider.can_run(_lead(rating=None, reviews_count=None)) is True


def test_run_returns_provider_result():
    provider = ClassificationProvider(llm_client=None)
    result = provider.run(_lead(), EnrichmentContext())
    assert isinstance(result, ProviderResult)
    assert result.success is True
    assert result.source == "classification"
    assert "perfil_lead" in result.data
    assert "nicho_canonico" in result.data


def test_run_returns_hot_no_site_when_appropriate():
    lead = _lead(
        website=None, rating=4.7, reviews_count=80, nicho="Dentist",
    )
    provider = ClassificationProvider()
    result = provider.run(lead, EnrichmentContext())
    assert result.data["perfil_lead"] == "hot_no_site"
    assert result.data["nicho_canonico"] == "dentista"


def test_run_consolidates_site_analysis_flags():
    lead = _lead(
        website="https://foo.com",
        opportunity_score=10,
        site_analysis={
            "has_ssl": True, "has_analytics": True, "has_whatsapp_cta": True,
        },
    )
    provider = ClassificationProvider()
    result = provider.run(lead, EnrichmentContext())
    assert result.data["perfil_lead"] == "cold"


def test_run_never_raises():
    provider = ClassificationProvider()
    lead = Lead(nome=None, telefone=None)
    result = provider.run(lead, EnrichmentContext())
    assert isinstance(result, ProviderResult)
    assert result.success is True  # result é válido, com DISQUALIFIED


from app.pipeline.enrichment.orchestrator import EnrichmentOrchestrator


def test_orchestrator_includes_classification_in_phase_order():
    orch = EnrichmentOrchestrator()
    assert "classification" in orch._providers_by_name


def test_orchestrator_always_runs_classification():
    from app.models import Lead
    lead = Lead(nome="X", telefone="11", rating=4.0, reviews_count=10)
    orch = EnrichmentOrchestrator()
    plan = orch.plan(lead, skip_providers=["cnpj_enricher"])
    names = [p.name for p in plan.providers]
    assert "classification" in names
    assert names.index("classification") == len(names) - 1  # sempre última


def test_orchestrator_execute_writes_classification_fields():
    from app.models import Lead
    lead = Lead(
        nome="X", telefone="11999", rating=4.5, reviews_count=60,
        nicho="Pizzaria",
    )
    orch = EnrichmentOrchestrator()
    plan = orch.plan(lead, skip_providers=[
        "cnpj_enricher", "website_crawler", "schema_extractor",
        "tech_stack", "email_discoverer", "apollo",
    ])
    out = orch.execute(lead, plan)
    assert "perfil_lead" in out
    assert out["perfil_lead"] == "hot_no_site"
    assert out["nicho_canonico"] == "restaurante"


from app.pipeline.enricher import enrich_lead_via_orchestrator
from app.routers.pipeline import _run_enrich
from app.models import Job


def test_run_enrich_persists_classification_fields(db):
    """Exercises the real _run_enrich path end-to-end (not bypassed).

    _run_enrich creates its own SessionLocal() internally, which is a
    different session from the test's `db` fixture.  We patch
    app.routers.pipeline.SessionLocal to return the *same* test session
    so both sides share one DB connection and can see each other's commits.
    """
    from unittest.mock import patch
    from app.models import Lead
    from tests.conftest import TestSession  # same sessionmaker the fixture uses

    # Create a Job and a Lead in the test DB
    job = Job(type="enrich", status="pending", params={})
    db.add(job)
    db.commit()

    lead = Lead(
        nome="Pizzaria Bella",
        telefone="11999999999",
        rating=4.5,
        reviews_count=60,
        nicho="Pizzaria",
        job_id=job.id,
        status="scraped",
    )
    db.add(lead)
    db.commit()
    lead_id = lead.id

    # Patch SessionLocal inside pipeline.py so _run_enrich shares the same
    # SQLite file-based DB that the test fixture already populated.
    with patch("app.routers.pipeline.SessionLocal", new=TestSession):
        _run_enrich(job.id, {
            "lead_ids": [lead_id],
            "skip_providers": [
                "cnpj_enricher", "website_crawler", "schema_extractor",
                "tech_stack", "email_discoverer", "apollo",
            ],
        })

    # _run_enrich committed via its own session; force our session to reload.
    db.expire_all()
    lead_fresh = db.get(Lead, lead_id)

    assert lead_fresh.perfil_lead == "hot_no_site"
    assert lead_fresh.nicho_canonico == "restaurante"
    assert lead_fresh.pacote_sugerido is not None
    assert lead_fresh.prioridade is not None
    assert lead_fresh.classification_hash is not None
    assert lead_fresh.classified_at is not None
