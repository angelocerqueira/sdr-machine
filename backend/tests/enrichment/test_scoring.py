"""Tests for the enrichment scoring algorithm."""
from app.pipeline.enrichment.scoring import calculate_score


def test_no_website_base_score():
    lead_data = {"website": None}
    site_analysis = {}
    score, reasons = calculate_score(lead_data, site_analysis)
    assert score == 95
    assert any("Sem website" in r for r in reasons)


def test_broken_site_scores_85():
    lead_data = {"website": "https://example.com"}
    for status in ("connection_error", "timeout", "ssl_error"):
        site_analysis = {"status": status}
        score, reasons = calculate_score(lead_data, site_analysis)
        assert score == 85
        assert any("problemas" in r.lower() for r in reasons)


def test_perfect_site_low_score():
    lead_data = {"website": "https://example.com", "email": "contato@example.com"}
    site_analysis = {
        "status": "ok",
        "has_ssl": True,
        "has_responsive_meta": True,
        "has_cta": True,
        "has_social_links": True,
        "has_whatsapp_link": True,
        "has_analytics": True,
        "has_chatbot": True,
        "pagespeed": 90,
        "structured_data": {"type": "LocalBusiness"},
        "word_count": 500,
        "image_count": 10,
    }
    score, reasons = calculate_score(lead_data, site_analysis)
    assert score <= 10
    assert reasons == [] or all("Sem" not in r for r in reasons)


def test_bad_site_accumulates_points():
    lead_data = {"website": "http://example.com", "email": "fulano@gmail.com"}
    site_analysis = {
        "status": "ok",
        "has_ssl": False,
        "has_responsive_meta": False,
        "has_cta": False,
        "has_social_links": False,
        "has_whatsapp_link": False,
        "has_analytics": False,
        "has_chatbot": False,
        "pagespeed": 30,
        "word_count": 50,
        "image_count": 0,
    }
    score, reasons = calculate_score(lead_data, site_analysis)
    # SSL 15 + responsive 15 + whatsapp 10 + analytics 8 + chatbot 8 + CTA 10
    # + PageSpeed 10 + word_count 10 + images 5 + social 5 + gmail 5 + no structured 3 = 100 (capped)
    assert score == 100
    assert any("SSL" in r or "HTTPS" in r for r in reasons)
    assert any("responsivo" in r.lower() for r in reasons)
    assert any("WhatsApp" in r for r in reasons)


def test_tech_stack_dated_adds_points():
    lead_data = {"website": "https://example.com"}
    site_analysis = {
        "status": "ok",
        "has_ssl": True,
        "has_responsive_meta": True,
        "has_cta": True,
        "has_social_links": True,
        "pagespeed": 90,
    }
    tech_stack = [{"name": "Adobe Flash", "category": "runtime"}]
    score, reasons = calculate_score(lead_data, site_analysis, tech_stack=tech_stack)
    assert any("defasado" in r.lower() or "flash" in r.lower() for r in reasons)


def test_score_capped_at_100():
    lead_data = {"website": None, "email": "x@gmail.com"}
    site_analysis = {"status": "no_website"}
    tech_stack = [{"name": "Adobe Flash", "category": "runtime"}]
    score, _ = calculate_score(lead_data, site_analysis, tech_stack=tech_stack)
    assert score <= 100


def test_gmail_email_adds_points():
    lead_data = {"website": "https://example.com", "email": "fulano@gmail.com"}
    site_analysis = {
        "status": "ok",
        "has_ssl": True,
        "has_responsive_meta": True,
        "has_cta": True,
        "has_social_links": True,
        "pagespeed": 90,
    }
    score_with_gmail, reasons = calculate_score(lead_data, site_analysis)
    lead_data_pro = {"website": "https://example.com", "email": "contato@example.com"}
    score_pro, _ = calculate_score(lead_data_pro, site_analysis)
    assert score_with_gmail > score_pro
    assert any("email" in r.lower() for r in reasons)
