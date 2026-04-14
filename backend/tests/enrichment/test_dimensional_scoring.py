"""Tests for the multi-dimensional opportunity scoring system."""
import pytest
from datetime import date
from app.pipeline.enrichment.scoring import (
    calculate_score,
    DimensionalScore,
    _ACESSIBILIDADE_GATE,
)


# ─── Retorno da função ─────────────────────────────────────────────────────────

def test_calculate_score_returns_dimensional_score():
    result = calculate_score({"telefone": "11999998888"}, {})
    assert isinstance(result, DimensionalScore)


# ─── Acessibilidade ───────────────────────────────────────────────────────────

def test_no_phone_no_email_fails_gate():
    result = calculate_score({"telefone": None, "email": None}, {})
    assert result.acessibilidade < _ACESSIBILIDADE_GATE
    assert not result.qualificado

def test_short_phone_fails_gate():
    result = calculate_score({"telefone": "12345", "email": None}, {})
    assert result.acessibilidade < _ACESSIBILIDADE_GATE

def test_mobile_phone_passes_gate():
    # 11 dígitos, posição [2] == '9'
    result = calculate_score({"telefone": "11999998888"}, {})
    assert result.acessibilidade >= _ACESSIBILIDADE_GATE

def test_landline_passes_gate():
    # 10 dígitos
    result = calculate_score({"telefone": "1133334444"}, {})
    assert result.acessibilidade >= _ACESSIBILIDADE_GATE

def test_mobile_scores_higher_than_landline():
    mobile = calculate_score({"telefone": "11999998888"}, {})
    landline = calculate_score({"telefone": "1133334444"}, {})
    assert mobile.acessibilidade > landline.acessibilidade

def test_professional_email_boosts_acessibilidade():
    base = calculate_score({"telefone": "11999998888"}, {})
    with_pro = calculate_score({"telefone": "11999998888", "email": "contato@empresa.com.br"}, {})
    assert with_pro.acessibilidade > base.acessibilidade

def test_generic_email_adds_less_than_professional():
    generic = calculate_score({"telefone": "11999998888", "email": "empresa@gmail.com"}, {})
    professional = calculate_score({"telefone": "11999998888", "email": "contato@empresa.com.br"}, {})
    assert professional.acessibilidade > generic.acessibilidade

def test_phone_with_formatting_is_valid():
    # Telefone com formatação como vem do Google Maps
    result = calculate_score({"telefone": "(11) 99999-8888"}, {})
    assert result.acessibilidade >= _ACESSIBILIDADE_GATE


# ─── LP / Site ────────────────────────────────────────────────────────────────

def test_no_website_max_lp_score():
    result = calculate_score({"website": None}, {"status": "no_website"})
    assert result.lp_site == 95

def test_site_down_high_lp_score():
    result = calculate_score({"website": "https://ex.com"}, {"status": "connection_error"})
    assert result.lp_site == 85

def test_perfect_site_low_lp_score():
    site = {
        "status": "ok", "has_ssl": True, "has_responsive_meta": True,
        "has_whatsapp_link": True, "has_analytics": True, "has_chatbot": True,
        "has_cta": True, "pagespeed": 90, "word_count": 800, "is_template": False,
        "image_count": 10, "has_social_links": True,
        "structured_data": {"type": "LocalBusiness"},
    }
    result = calculate_score({"website": "https://ex.com"}, site)
    assert result.lp_site < 15

def test_bad_site_scores_above_50_lp():
    site = {
        "status": "ok", "has_ssl": False, "has_responsive_meta": False,
        "has_whatsapp_link": False, "has_analytics": False, "has_chatbot": False,
        "has_cta": False, "pagespeed": 30, "word_count": 100, "is_template": True,
        "image_count": 0, "has_social_links": False, "structured_data": None,
    }
    result = calculate_score({"website": "https://ex.com"}, site)
    assert result.lp_site >= 50


# ─── Mapa / Reputação ─────────────────────────────────────────────────────────

def test_no_maps_url_scores_mapa():
    result = calculate_score({"google_maps_url": None}, {})
    assert result.mapa_reputacao >= 20

def test_low_rating_scores_high_mapa():
    result = calculate_score({
        "google_maps_url": "https://maps.google.com/place/x",
        "rating": 2.5, "reviews_count": 5,
    }, {})
    assert result.mapa_reputacao >= 50

def test_high_rating_few_reviews_still_scores():
    result = calculate_score({
        "google_maps_url": "https://maps.google.com/place/x",
        "rating": 4.8, "reviews_count": 3,
    }, {})
    assert result.mapa_reputacao >= 20

def test_contactability_keywords_in_reviews_boost_mapa():
    reviews = [{"text": "Tentei ligar várias vezes, não atendem nunca"}]
    baseline = calculate_score({
        "google_maps_url": "https://maps.google.com/place/x",
        "rating": 4.0, "reviews_count": 20, "top_reviews": [],
    }, {})
    with_keywords = calculate_score({
        "google_maps_url": "https://maps.google.com/place/x",
        "rating": 4.0, "reviews_count": 20, "top_reviews": reviews,
    }, {})
    assert with_keywords.mapa_reputacao > baseline.mapa_reputacao

def test_good_maps_profile_low_mapa_score():
    result = calculate_score({
        "google_maps_url": "https://maps.google.com/place/x",
        "rating": 4.8, "reviews_count": 250, "top_reviews": [],
    }, {})
    assert result.mapa_reputacao < 15


# ─── Automação ────────────────────────────────────────────────────────────────

def test_no_automation_signals_scores_high():
    site = {
        "status": "ok",
        "has_chatbot": False, "has_booking_link": False,
        "has_payment_link": False, "has_analytics": False,
        "contact_channels_count": 4,
    }
    result = calculate_score({"reviews_count": 150}, site, tech_stack=[])
    assert result.automacao >= 50

def test_good_site_still_has_automacao_opportunity():
    """Lead com site bom mas sem automação ainda deve ter opportunity de automação."""
    site = {
        "status": "ok", "has_ssl": True, "has_responsive_meta": True,
        "has_whatsapp_link": True, "has_analytics": True, "has_cta": True,
        "has_chatbot": False, "has_booking_link": False, "has_payment_link": False,
        "contact_channels_count": 2, "pagespeed": 85, "word_count": 600,
        "is_template": False, "image_count": 8, "has_social_links": True,
        "structured_data": {"type": "LocalBusiness"},
    }
    result = calculate_score(
        {"telefone": "11999998888", "reviews_count": 80, "website": "https://exemplo.com.br"},
        site,
    )
    assert result.lp_site < 20       # bom site
    assert result.automacao >= 30    # mas tem oportunidade de automação


# ─── Composite + nivel_recomendado + qualificado ──────────────────────────────

def test_unreachable_lead_zero_composite():
    result = calculate_score({"telefone": None, "email": None}, {"status": "no_website"})
    assert result.composite == 0

def test_reachable_no_website_qualifies():
    result = calculate_score({"telefone": "11999998888"}, {"status": "no_website"})
    assert result.qualificado is True
    assert result.composite > 0

def test_not_qualificado_without_phone():
    result = calculate_score({"telefone": None, "email": None}, {"status": "no_website"})
    assert result.qualificado is False

def test_nivel_recomendado_picks_highest():
    # Bom site, boa reputação, mas sem automação → deve recomendar automação
    site = {
        "status": "ok", "has_ssl": True, "has_responsive_meta": True,
        "has_whatsapp_link": True, "has_analytics": True, "has_cta": True,
        "has_chatbot": False, "has_booking_link": False, "has_payment_link": False,
        "has_social_links": True, "structured_data": True,
        "contact_channels_count": 4, "pagespeed": 85, "word_count": 600,
        "image_count": 8, "is_template": False,
    }
    result = calculate_score({
        "telefone": "11999998888",
        "website": "https://exemplo.com.br",
        "reviews_count": 150,
        "google_maps_url": "https://maps.google.com/place/x",
        "rating": 4.8,
    }, site)
    assert result.nivel_recomendado == "automacao"

def test_flat_reasons_prefixed_by_dimension():
    result = calculate_score({"telefone": None}, {"status": "no_website"})
    prefixes = {r.split("]")[0].strip("[") for r in result.flat_reasons}
    assert "ACESSIBILIDADE" in prefixes

def test_composite_is_max_of_service_dims_when_reachable():
    result = calculate_score({"telefone": "11999998888"}, {"status": "no_website"})
    assert result.composite == max(result.lp_site, result.automacao, result.mapa_reputacao)
