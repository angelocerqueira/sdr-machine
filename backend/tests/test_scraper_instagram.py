from app.pipeline.scraper import extract_has_instagram


def test_extract_has_instagram_from_url_field():
    payload = {"website": "https://restaurante.com", "instagramUrl": "https://instagram.com/abc"}
    assert extract_has_instagram(payload) is True


def test_extract_has_instagram_from_social_links():
    payload = {"socialLinks": [{"service": "Instagram", "url": "https://ig.com/x"}]}
    assert extract_has_instagram(payload) is True


def test_extract_has_instagram_from_social_links_url_only():
    payload = {"socialLinks": [{"url": "https://www.instagram.com/mybiz"}]}
    assert extract_has_instagram(payload) is True


def test_extract_has_instagram_returns_false_when_absent():
    payload = {"website": "https://foo.com"}
    assert extract_has_instagram(payload) is False


def test_extract_has_instagram_handles_none():
    assert extract_has_instagram({}) is False
    assert extract_has_instagram(None) is False


def test_extract_has_instagram_handles_description_link():
    payload = {"description": "Siga-nos no instagram.com/meunegocio"}
    assert extract_has_instagram(payload) is True


def test_extract_has_instagram_ignores_malformed_social_links():
    payload = {"socialLinks": [None, 42, {"service": None, "url": None}]}
    assert extract_has_instagram(payload) is False
