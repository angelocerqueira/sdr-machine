import pytest

from app.pipeline.enrichment.classifier import classify, ClassificationResult
from app.pipeline.enrichment.classifier_enums import (
    LeadProfile, NichoCanonico, NichoSource, PacoteSugerido, Prioridade,
)


def _base_lead(**overrides) -> dict:
    """Lead minimally valid to pass DISQUALIFIED gate."""
    base = {
        "has_website": True, "score": 40,
        "rating": 4.0, "review_count": 20,
        "has_ssl": False, "has_analytics": False,
        "has_chatbot": False, "has_whatsapp_cta": False,
        "has_instagram": False,
        "nicho_raw": "qualquer coisa",
        "nome": "Lead Teste", "descricao": "", "reviews": [],
        "telefone": "11999999999",
    }
    base.update(overrides)
    return base


def test_returns_classification_result_type():
    result = classify(_base_lead())
    assert isinstance(result, ClassificationResult)


def test_disqualified_rating_below_threshold():
    result = classify(_base_lead(rating=2.5))
    assert result.perfil_lead == LeadProfile.DISQUALIFIED


def test_disqualified_no_phone_and_few_reviews():
    result = classify(_base_lead(telefone=None, review_count=1))
    assert result.perfil_lead == LeadProfile.DISQUALIFIED


def test_hot_no_site():
    result = classify(_base_lead(
        has_website=False, rating=4.5, review_count=80,
    ))
    assert result.perfil_lead == LeadProfile.HOT_NO_SITE
    assert result.pacote_sugerido == PacoteSugerido.ESSENCIAL
    assert result.prioridade == Prioridade.MAXIMA


def test_hot_bad_site_with_instagram():
    result = classify(_base_lead(
        has_website=True, score=72, has_instagram=True, review_count=5,
    ))
    assert result.perfil_lead == LeadProfile.HOT_BAD_SITE


def test_hot_bad_site_without_instagram_many_reviews():
    result = classify(_base_lead(
        has_website=True, score=72, has_instagram=False, review_count=60,
    ))
    assert result.perfil_lead == LeadProfile.HOT_BAD_SITE


def test_not_hot_bad_site_if_score_too_low():
    result = classify(_base_lead(
        has_website=True, score=50, has_instagram=True,
    ))
    # 50 < 60 → não HOT_BAD_SITE; cai em WARM
    assert result.perfil_lead == LeadProfile.WARM


def test_cold_site():
    result = classify(_base_lead(
        has_website=True, score=10,
        has_ssl=True, has_analytics=True, has_chatbot=True,
    ))
    assert result.perfil_lead == LeadProfile.COLD
    assert result.pacote_sugerido == PacoteSugerido.SKIP
    assert result.prioridade == Prioridade.BAIXA


def test_warm_catch_all():
    result = classify(_base_lead(
        has_website=True, score=35, has_analytics=True,
    ))
    assert result.perfil_lead == LeadProfile.WARM


def test_missing_score_defaults_to_warm():
    result = classify(_base_lead(has_website=True, score=None))
    # Default score=50 → catch-all WARM
    assert result.perfil_lead == LeadProfile.WARM


def test_missing_rating_and_reviews_disqualifies():
    result = classify(_base_lead(
        rating=None, review_count=None, telefone=None,
    ))
    assert result.perfil_lead == LeadProfile.DISQUALIFIED


def test_missing_has_website_treated_as_false():
    # Ausência de site, mas rating/reviews alto → HOT_NO_SITE
    result = classify(_base_lead(
        has_website=None, rating=4.5, review_count=50,
    ))
    assert result.perfil_lead == LeadProfile.HOT_NO_SITE


def test_classification_hash_is_deterministic():
    data = _base_lead()
    r1 = classify(data)
    r2 = classify(data)
    assert r1.classification_hash == r2.classification_hash


def test_classification_hash_changes_when_key_field_changes():
    r1 = classify(_base_lead(score=40))
    r2 = classify(_base_lead(score=70))
    assert r1.classification_hash != r2.classification_hash


def test_never_raises_on_empty_input():
    result = classify({})
    assert isinstance(result, ClassificationResult)
    assert result.perfil_lead == LeadProfile.DISQUALIFIED


def test_never_raises_on_garbage_types():
    result = classify({
        "score": "not-a-number",
        "rating": [],
        "review_count": {"wat": 1},
        "has_website": "yes",
    })
    assert isinstance(result, ClassificationResult)
