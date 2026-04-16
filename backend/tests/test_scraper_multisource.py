from unittest.mock import patch
from app.pipeline.scraper import scrape_all


_GM_LEAD = {
    "nome": "Clínica A", "telefone": "4933334444", "website": "https://a.com",
    "cidade": "Chapecó SC", "nicho": "dentista", "categoria": "Dentista",
    "rating": 4.2, "reviews_count": 30, "google_maps_url": "https://maps.google.com/a",
    "top_reviews": [], "endereco": "Rua A 1",
}
_CNPJ_LEAD = {
    "nome": "Clínica B", "telefone": "4944445555", "cnpj": "00000000000100",
    "website": None, "cidade": "Chapecó SC", "nicho": "dentista",
    "rating": None, "reviews_count": 0, "google_maps_url": None,
    "top_reviews": [], "endereco": "Rua B 2", "fonte": "cnpj",
}
_CNPJ_LEAD_SAME_PHONE = {**_CNPJ_LEAD, "telefone": "4933334444", "cnpj": "00000000000200"}


def test_both_sources_combined():
    with patch("app.pipeline.scraper.scrape_google_maps", return_value=[_GM_LEAD]):
        with patch("app.pipeline.scraper.scrape_cnpj", return_value=[_CNPJ_LEAD]):
            leads, errors = scrape_all(["dentista"], ["Chapecó SC"], fontes=["google_maps", "cnpj"])
    assert len(leads) == 2
    assert errors == []


def test_dedup_by_phone_across_sources():
    """Same phone in Google Maps and CNPJ — only one lead created."""
    with patch("app.pipeline.scraper.scrape_google_maps", return_value=[_GM_LEAD]):
        with patch("app.pipeline.scraper.scrape_cnpj", return_value=[_CNPJ_LEAD_SAME_PHONE]):
            leads, errors = scrape_all(["dentista"], ["Chapecó SC"], fontes=["google_maps", "cnpj"])
    assert len(leads) == 1


def test_google_maps_failure_does_not_fail_job():
    with patch("app.pipeline.scraper.scrape_google_maps", side_effect=Exception("Apify down")):
        with patch("app.pipeline.scraper.scrape_cnpj", return_value=[_CNPJ_LEAD]):
            leads, errors = scrape_all(["dentista"], ["Chapecó SC"], fontes=["google_maps", "cnpj"])
    assert len(leads) == 1
    assert any("google_maps" in e for e in errors)


def test_cnpj_failure_does_not_fail_job():
    with patch("app.pipeline.scraper.scrape_google_maps", return_value=[_GM_LEAD]):
        with patch("app.pipeline.scraper.scrape_cnpj", side_effect=Exception("timeout")):
            leads, errors = scrape_all(["dentista"], ["Chapecó SC"], fontes=["google_maps", "cnpj"])
    assert len(leads) == 1
    assert any("cnpj" in e for e in errors)


def test_both_sources_fail_returns_empty_with_errors():
    with patch("app.pipeline.scraper.scrape_google_maps", side_effect=Exception("Apify down")):
        with patch("app.pipeline.scraper.scrape_cnpj", side_effect=Exception("timeout")):
            leads, errors = scrape_all(["dentista"], ["Chapecó SC"], fontes=["google_maps", "cnpj"])
    assert leads == []
    assert len(errors) == 2


def test_only_google_maps_fonte():
    with patch("app.pipeline.scraper.scrape_google_maps", return_value=[_GM_LEAD]) as mock_gm:
        with patch("app.pipeline.scraper.scrape_cnpj", return_value=[_CNPJ_LEAD]) as mock_cnpj:
            leads, _ = scrape_all(["dentista"], ["Chapecó SC"], fontes=["google_maps"])
    mock_gm.assert_called_once()
    mock_cnpj.assert_not_called()
    assert len(leads) == 1


def test_only_cnpj_fonte():
    with patch("app.pipeline.scraper.scrape_google_maps", return_value=[_GM_LEAD]) as mock_gm:
        with patch("app.pipeline.scraper.scrape_cnpj", return_value=[_CNPJ_LEAD]) as mock_cnpj:
            leads, _ = scrape_all(["dentista"], ["Chapecó SC"], fontes=["cnpj"])
    mock_gm.assert_not_called()
    mock_cnpj.assert_called_once()


def test_default_fontes_uses_both():
    with patch("app.pipeline.scraper.scrape_google_maps", return_value=[_GM_LEAD]):
        with patch("app.pipeline.scraper.scrape_cnpj", return_value=[]):
            leads, _ = scrape_all(["dentista"], ["Chapecó SC"])  # no fontes param
    assert len(leads) == 1
