"""
Módulo 1: Scraping de Google Maps via Apify
Puxa negócios locais com todos os dados de contato.
"""

import requests

from app.config import settings


def scrape_google_maps(niche: str, city: str, max_results: int | None = None) -> list[dict]:
    """
    Scrape Google Maps via Apify Actor 'compass/crawler-google-places'.
    Retorna lista de negócios com nome, telefone, site, rating, etc.
    """
    if max_results is None:
        max_results = settings.max_results_per_search

    url = "https://api.apify.com/v2/acts/compass~crawler-google-places/run-sync-get-dataset-items"

    payload = {
        "searchStringsArray": [f"{niche} em {city}"],
        "maxCrawledPlacesPerSearch": max_results,
        "language": "pt-BR",
        "includeWebResults": False,
        "maxImages": 0,
        "maxReviews": 3,
        "onlyDataFromSearchPage": False,
    }

    headers = {
        "Content-Type": "application/json",
    }

    params = {
        "token": settings.apify_token,
        "timeout": 120,
        "memory": 1024,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, params=params, timeout=180)
        resp.raise_for_status()
        results = resp.json()

        leads = []
        for item in results:
            rating = item.get("totalScore", 0) or 0
            if rating < settings.min_rating:
                continue

            lead = {
                "nome": item.get("title", "").strip(),
                "telefone": item.get("phone", ""),
                "website": item.get("website", ""),
                "endereco": item.get("address", ""),
                "cidade": city,
                "nicho": niche,
                "rating": rating,
                "reviews_count": item.get("reviewsCount", 0),
                "google_maps_url": item.get("url", ""),
                "categoria": item.get("categoryName", ""),
                "top_reviews": [
                    r.get("text", "")[:200]
                    for r in (item.get("reviews", []) or [])[:3]
                    if r.get("text")
                ],
            }

            if lead["nome"]:
                leads.append(lead)

        return leads

    except requests.exceptions.RequestException:
        return []


def scrape_all(nichos: list[str], cidades: list[str], max_results: int | None = None) -> list[dict]:
    """
    Roda o scraping pra todas as combinações nicho x cidade.
    Deduplica por telefone/nome.
    """
    all_leads: list[dict] = []
    seen: set[str] = set()

    for niche in nichos:
        for city in cidades:
            leads = scrape_google_maps(niche, city, max_results)
            for lead in leads:
                key = lead["telefone"] or lead["nome"]
                if key and key not in seen:
                    seen.add(key)
                    all_leads.append(lead)

    return all_leads
