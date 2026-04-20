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
