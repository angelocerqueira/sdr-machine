"""Tests for backward-compatible behavior of the refactored scoring module.

These tests verify the DimensionalScore properties that replace the old
(int, list[str]) return value.
"""
from datetime import date
from app.pipeline.enrichment.scoring import calculate_score, DimensionalScore


def test_returns_dimensional_score():
    result = calculate_score({}, {})
    assert isinstance(result, DimensionalScore)


def test_no_website_scores_95_lp():
    result = calculate_score({"website": None}, {"status": "no_website"})
    assert result.lp_site == 95
    assert "Sem website" in result.reasons["lp_site"][0]


def test_site_down_scores_85_lp():
    result = calculate_score({"website": "https://ex.com"}, {"status": "connection_error"})
    assert result.lp_site == 85


def test_no_ssl_adds_15_to_lp():
    site = {
        "status": "ok", "has_ssl": False,
        "has_responsive_meta": True, "has_whatsapp_link": True,
        "has_analytics": True, "has_chatbot": True, "has_cta": True,
        "pagespeed": 80, "word_count": 400, "is_template": False,
        "image_count": 5, "has_social_links": True, "structured_data": True,
    }
    result = calculate_score({"website": "https://ex.com"}, site)
    assert result.lp_site == 15
    assert any("SSL" in r for r in result.reasons["lp_site"])


def test_score_capped_at_100():
    site = {
        "status": "ok", "has_ssl": False, "has_responsive_meta": False,
        "has_whatsapp_link": False, "has_analytics": False, "has_chatbot": False,
        "has_cta": False, "pagespeed": 10, "word_count": 50, "is_template": True,
        "image_count": 0, "has_social_links": False, "structured_data": None,
    }
    result = calculate_score({"website": "https://ex.com"}, site)
    assert result.lp_site <= 100


def test_dated_tech_adds_to_lp():
    site = {"status": "ok", "has_ssl": True, "has_responsive_meta": True,
            "has_whatsapp_link": True, "has_analytics": True, "has_chatbot": True,
            "has_cta": True, "pagespeed": 80, "word_count": 400, "is_template": False,
            "image_count": 5, "has_social_links": True, "structured_data": True}
    without = calculate_score({"website": "https://ex.com"}, site, tech_stack=[])
    with_dated = calculate_score(
        {"website": "https://ex.com"}, site,
        tech_stack=[{"name": "jQuery 1", "category": "library"}]
    )
    assert with_dated.lp_site > without.lp_site


def test_established_company_with_bad_site_adds_bonus():
    site = {
        "status": "ok", "has_ssl": False, "has_responsive_meta": False,
        "has_whatsapp_link": False, "has_analytics": False, "has_chatbot": False,
        "has_cta": False, "pagespeed": 30, "word_count": 100, "is_template": True,
        "image_count": 0, "has_social_links": False, "structured_data": None,
    }
    without_fundacao = calculate_score({"website": "https://ex.com"}, site)
    with_fundacao = calculate_score(
        {"website": "https://ex.com"}, site,
        data_fundacao=date(2010, 1, 1)
    )
    assert with_fundacao.lp_site >= without_fundacao.lp_site


def test_composite_is_zero_when_unreachable():
    result = calculate_score({"telefone": None, "website": None}, {"status": "no_website"})
    assert result.composite == 0


def test_flat_reasons_contains_all_dimensions():
    result = calculate_score(
        {"telefone": "11999998888", "website": None, "google_maps_url": None},
        {"status": "no_website"},
    )
    flat = result.flat_reasons
    assert any("[LP_SITE]" in r for r in flat)
    assert any("[MAPA_REPUTACAO]" in r for r in flat)


def test_bad_site_accumulates_points():
    site = {
        "status": "ok", "has_ssl": False, "has_responsive_meta": False,
        "has_whatsapp_link": False, "has_analytics": False, "has_chatbot": False,
        "has_cta": False, "pagespeed": 30, "word_count": 100, "is_template": True,
        "image_count": 0, "has_social_links": False, "structured_data": None,
    }
    result = calculate_score({"website": "https://ex.com"}, site)
    assert result.lp_site >= 50


def test_gmail_email_adds_points_to_lp():
    site = {"status": "ok", "has_ssl": True, "has_responsive_meta": True,
            "has_whatsapp_link": True, "has_analytics": True, "has_chatbot": True,
            "has_cta": True, "pagespeed": 80, "word_count": 400, "is_template": False,
            "image_count": 5, "has_social_links": True, "structured_data": True}
    without_email = calculate_score({"website": "https://ex.com"}, site)
    with_gmail = calculate_score({"website": "https://ex.com", "email": "empresa@gmail.com"}, site)
    assert with_gmail.lp_site > without_email.lp_site
