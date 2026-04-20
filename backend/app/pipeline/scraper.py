"""
Módulo 1: Scraping de negócios locais.
Fontes: Google Maps (Apify) e CNPJ (MinhaReceita).
"""

import re
import requests

from app.config import settings
from app.pipeline.cnpj_scraper import scrape_cnpj


def extract_has_instagram(payload: dict | None) -> bool:
    """Check if Apify Google Maps payload indicates Instagram presence.

    Checks common fields: 'instagramUrl', 'socialLinks' entries, and
    description/website text for instagram.com references. Never raises.
    """
    if not payload or not isinstance(payload, dict):
        return False

    # Direct field from some Apify actors
    if payload.get("instagramUrl"):
        return True

    # socialLinks array (compass actor format)
    social = payload.get("socialLinks") or []
    if isinstance(social, list):
        for entry in social:
            if not isinstance(entry, dict):
                continue
            service = (entry.get("service") or entry.get("platform") or "").lower()
            url = (entry.get("url") or "").lower()
            if "instagram" in service or "instagram.com" in url:
                return True

    # Inline instagram link in website or description fields
    for key in ("website", "websiteUri", "url", "description"):
        v = payload.get(key)
        if isinstance(v, str) and "instagram.com" in v.lower():
            return True

    return False


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
            "has_instagram": extract_has_instagram(item),
        }

        if lead["nome"]:
            leads.append(lead)

    return leads


def scrape_all(
    nichos: list[str],
    cidades: list[str],
    max_results: int | None = None,
    fontes: list[str] | None = None,
) -> tuple[list[dict], list[str]]:
    """Scrape all enabled sources for every niche×city combination.

    fontes: subset of ["google_maps", "cnpj"]. Defaults to both.
    Each source failure is isolated — logged to errors, never crashes the job.
    Leads are deduplicated by phone number (digits) or CNPJ across sources.
    Returns (leads, errors).
    """
    if max_results is None:
        max_results = settings.max_results_per_search
    if fontes is None:
        fontes = ["google_maps", "cnpj"]

    all_leads: list[dict] = []
    errors: list[str] = []
    seen: set[str] = set()

    def _dedup_key(lead: dict) -> str | None:
        tel = re.sub(r"\D", "", lead.get("telefone") or "")
        cnpj = re.sub(r"\D", "", lead.get("cnpj") or "")
        return tel or cnpj or None

    def _add_lead(lead: dict) -> None:
        key = _dedup_key(lead)
        if key:
            if key in seen:
                return
            seen.add(key)
        else:
            # No phone or CNPJ — dedup by name to avoid exact duplicates
            name_key = (lead.get("nome") or "").strip().lower()
            if name_key in seen:
                return
            if name_key:
                seen.add(name_key)
        all_leads.append(lead)

    for niche in nichos:
        for city in cidades:
            if "google_maps" in fontes:
                try:
                    for lead in scrape_google_maps(niche, city, max_results):
                        _add_lead(lead)
                except Exception as exc:
                    errors.append(f"[google_maps] {niche} em {city}: {str(exc)[:200]}")

            if "cnpj" in fontes:
                try:
                    for lead in scrape_cnpj(niche, city, max_results):
                        _add_lead(lead)
                except Exception as exc:
                    errors.append(f"[cnpj] {niche} em {city}: {str(exc)[:200]}")

    return all_leads, errors
