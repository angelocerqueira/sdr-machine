import pytest
from unittest.mock import MagicMock

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


def test_rating_zero_does_not_disqualify_by_rating_rule_alone():
    """rating=0.0 means 'missing'; a lead with valid phone + reviews should flow through,
    not be blocked by the rating rule (caught elsewhere if truly bad)."""
    result = classify(_base_lead(
        rating=0.0, review_count=50, telefone="11999", has_website=False,
    ))
    # rating=0.0 bypasses Rule 1 (correct — 0.0 is sentinel for absent rating).
    # has_website=False + rating=0.0 (< hot_no_site threshold) → falls through to WARM.
    assert result.perfil_lead == LeadProfile.WARM


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


class _FakeToolUse:
    """Mimics anthropic.types.ToolUseBlock."""
    def __init__(self, input_dict):
        self.type = "tool_use"
        self.name = "classify_nicho"
        self.input = input_dict


class _FakeResponse:
    def __init__(self, content_blocks):
        self.content = content_blocks


def _make_llm(nicho_val, confidence=0.9):
    """Return a mock anthropic client that responds with a tool_use block."""
    client = MagicMock()
    client.messages.create.return_value = _FakeResponse([
        _FakeToolUse({
            "nicho_canonico": nicho_val,
            "confidence": confidence,
            "reasoning": "mock",
        })
    ])
    return client


def test_nicho_llm_fallback_used_when_fuzzy_fails():
    llm = _make_llm("advocacia", 0.92)
    result = classify(
        _base_lead(nicho_raw="Consultoria jurídica especializada"),
        llm_client=llm,
    )
    assert result.nicho_canonico == NichoCanonico.ADVOCACIA
    assert result.nicho_source == NichoSource.LLM_INFERRED
    assert result.nicho_confidence == 0.92


def test_nicho_llm_invalid_enum_value_falls_back_to_outros():
    llm = _make_llm("banco")  # not a valid bucket
    result = classify(
        _base_lead(nicho_raw="Agência bancária"),
        llm_client=llm,
    )
    assert result.nicho_canonico == NichoCanonico.OUTROS
    assert result.nicho_source == NichoSource.FAILED


def test_nicho_llm_exception_falls_back():
    llm = MagicMock()
    llm.messages.create.side_effect = Exception("boom")
    result = classify(
        _base_lead(nicho_raw="Negocio desconhecido xpto"),
        llm_client=llm,
    )
    assert result.nicho_canonico == NichoCanonico.OUTROS
    assert result.nicho_source == NichoSource.FAILED


def test_nicho_llm_not_called_when_fuzzy_matches():
    llm = _make_llm("academia")  # this should NOT be invoked
    result = classify(
        _base_lead(nicho_raw="Clínica Odontológica Dr Silva"),
        llm_client=llm,
    )
    # Fuzzy hits dentista directly; LLM is skipped
    assert result.nicho_canonico == NichoCanonico.DENTISTA
    llm.messages.create.assert_not_called()


def test_nicho_llm_low_confidence_kept_as_llm_inferred():
    llm = _make_llm("industria", 0.3)
    result = classify(
        _base_lead(nicho_raw="Fornecedor de peças automotivas B2B"),
        llm_client=llm,
    )
    # Source stays as LLM_INFERRED; review table picks it up via confidence<0.5
    assert result.nicho_source == NichoSource.LLM_INFERRED
    assert result.nicho_confidence == 0.3
