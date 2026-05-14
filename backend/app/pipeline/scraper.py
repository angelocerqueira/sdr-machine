"""
Módulo 1: Scraping de negócios locais.
Fontes: Google Maps (Apify) e CNPJ (MinhaReceita).
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

import requests

from app.config import settings
from app.integrations.resolver import provider_config_for
from app.pipeline.cnpj_scraper import scrape_cnpj

logger = logging.getLogger(__name__)


@dataclass
class SourceResult:
    """Telemetry from a single (source, niche, city) scrape pass."""
    source: str
    nicho: str
    cidade: str
    returned: int = 0
    rating_filtered: int = 0
    no_name_filtered: int = 0
    inactive_filtered: int = 0
    accepted: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {
            "source": self.source,
            "nicho": self.nicho,
            "cidade": self.cidade,
            "returned": self.returned,
            "accepted": self.accepted,
        }
        if self.rating_filtered:
            d["rating_filtered"] = self.rating_filtered
        if self.no_name_filtered:
            d["no_name_filtered"] = self.no_name_filtered
        if self.inactive_filtered:
            d["inactive_filtered"] = self.inactive_filtered
        if self.error:
            d["error"] = self.error
        return d


@dataclass
class ScrapeReport:
    """Aggregate telemetry across the whole scrape job."""
    leads: list[dict] = field(default_factory=list)
    per_search: list[SourceResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    apify_returned: int = 0
    rating_filtered: int = 0
    no_name_filtered: int = 0
    inactive_filtered: int = 0
    dedup_filtered: int = 0
    min_rating_used: float = 0.0


def extract_place_id(url: str | None) -> str | None:
    """Extract the Google place_id from a Google Maps URL."""
    if not url:
        return None
    match = re.search(r"[?&]query_place_id=([^&]+)", url)
    if match:
        return match.group(1)
    match = re.search(r"!1s([^!]+)", url)
    return match.group(1) if match else None


def extract_has_instagram(payload: dict | None) -> bool:
    """Check if Apify Google Maps payload indicates Instagram presence."""
    if not payload or not isinstance(payload, dict):
        return False

    if payload.get("instagramUrl"):
        return True

    social = payload.get("socialLinks") or []
    if isinstance(social, list):
        for entry in social:
            if not isinstance(entry, dict):
                continue
            service = (entry.get("service") or entry.get("platform") or "").lower()
            url = (entry.get("url") or "").lower()
            if "instagram" in service or "instagram.com" in url:
                return True

    for key in ("website", "websiteUri", "url", "description"):
        v = payload.get(key)
        if isinstance(v, str) and "instagram.com" in v.lower():
            return True

    return False


def scrape_google_maps(niche: str, city: str, max_results: int | None = None) -> SourceResult:
    """
    Scrape Google Maps via Apify Actor 'compass/crawler-google-places'.
    Returns SourceResult with the leads and per-search telemetry.
    """
    if max_results is None:
        max_results = settings.max_results_per_search

    result = SourceResult(source="google_maps", nicho=niche, cidade=city)
    leads: list[dict] = []

    _apify_cfg = provider_config_for("apify") or {}
    _apify_token = _apify_cfg.get("token", "")
    if not _apify_token:
        result.error = "apify_token_missing"
        logger.warning("scrape.google_maps.no_token niche=%r city=%r", niche, city)
        return result

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
    headers = {"Content-Type": "application/json"}
    params = {"token": _apify_token, "timeout": 120, "memory": 1024}

    try:
        resp = requests.post(url, json=payload, headers=headers, params=params, timeout=180)
        resp.raise_for_status()
        items = resp.json() or []
    except Exception as exc:
        result.error = str(exc)[:200]
        logger.exception("scrape.google_maps.fail niche=%r city=%r", niche, city)
        return result

    result.returned = len(items)

    for item in items:
        rating = item.get("totalScore", 0) or 0
        if rating < settings.min_rating:
            result.rating_filtered += 1
            continue

        google_maps_url = item.get("url", "")
        lead = {
            "nome": item.get("title", "").strip(),
            "telefone": item.get("phone", ""),
            "website": item.get("website", ""),
            "endereco": item.get("address", ""),
            "cidade": city,
            "nicho": niche,
            "rating": rating,
            "reviews_count": item.get("reviewsCount", 0),
            "google_maps_url": google_maps_url,
            "place_id": item.get("placeId") or extract_place_id(google_maps_url),
            "categoria": item.get("categoryName", ""),
            "top_reviews": [
                r.get("text", "")[:200]
                for r in (item.get("reviews", []) or [])[:3]
                if r.get("text")
            ],
            "has_instagram": extract_has_instagram(item),
        }

        if not lead["nome"]:
            result.no_name_filtered += 1
            continue

        leads.append(lead)
        result.accepted += 1

    logger.info(
        "scrape.google_maps.done niche=%r city=%r returned=%d accepted=%d "
        "rating_filtered=%d no_name=%d min_rating=%s",
        niche, city, result.returned, result.accepted,
        result.rating_filtered, result.no_name_filtered, settings.min_rating,
    )

    # Attach leads via attribute (not part of dataclass to_dict telemetry)
    result._leads = leads  # type: ignore[attr-defined]
    return result


def scrape_all(
    nichos: list[str],
    cidades: list[str],
    max_results: int | None = None,
    fontes: list[str] | None = None,
) -> ScrapeReport:
    """Scrape all enabled sources for every niche×city combination.

    Returns a ScrapeReport with leads, per-search telemetry and aggregated counters.
    Each source failure is isolated — captured per-search, never crashes the job.
    Leads are deduplicated by place_id, phone, CNPJ or name across sources.
    """
    if max_results is None:
        max_results = settings.max_results_per_search
    if fontes is None:
        fontes = ["google_maps", "cnpj"]

    report = ScrapeReport(min_rating_used=settings.min_rating)
    seen: set[str] = set()

    def _dedup_key(lead: dict) -> str | None:
        place_id = lead.get("place_id")
        if place_id:
            return f"pid:{place_id}"
        tel = re.sub(r"\D", "", lead.get("telefone") or "")
        cnpj = re.sub(r"\D", "", lead.get("cnpj") or "")
        return tel or cnpj or None

    def _add_lead(lead: dict) -> bool:
        key = _dedup_key(lead)
        if key:
            if key in seen:
                return False
            seen.add(key)
        else:
            name_key = (lead.get("nome") or "").strip().lower()
            if name_key in seen:
                return False
            if name_key:
                seen.add(name_key)
        report.leads.append(lead)
        return True

    for niche in nichos:
        for city in cidades:
            if "google_maps" in fontes:
                gm_result = scrape_google_maps(niche, city, max_results)
                gm_leads = getattr(gm_result, "_leads", [])
                report.apify_returned += gm_result.returned
                report.rating_filtered += gm_result.rating_filtered
                report.no_name_filtered += gm_result.no_name_filtered
                if gm_result.error:
                    report.errors.append(
                        f"[google_maps] {niche} em {city}: {gm_result.error}"
                    )
                for lead in gm_leads:
                    if not _add_lead(lead):
                        report.dedup_filtered += 1
                report.per_search.append(gm_result)

            if "cnpj" in fontes:
                cnpj_result = SourceResult(source="cnpj", nicho=niche, cidade=city)
                try:
                    cnpj_leads = scrape_cnpj(niche, city, max_results)
                    cnpj_result.returned = len(cnpj_leads)
                    cnpj_result.accepted = cnpj_result.returned
                    for lead in cnpj_leads:
                        if not _add_lead(lead):
                            report.dedup_filtered += 1
                    logger.info(
                        "scrape.cnpj.done niche=%r city=%r returned=%d",
                        niche, city, cnpj_result.returned,
                    )
                except Exception as exc:
                    cnpj_result.error = str(exc)[:200]
                    report.errors.append(f"[cnpj] {niche} em {city}: {str(exc)[:200]}")
                    logger.exception("scrape.cnpj.fail niche=%r city=%r", niche, city)
                report.per_search.append(cnpj_result)

    logger.info(
        "scrape.summary nichos=%d cidades=%d apify_returned=%d "
        "rating_filtered=%d dedup=%d accepted=%d errors=%d",
        len(nichos), len(cidades), report.apify_returned,
        report.rating_filtered, report.dedup_filtered, len(report.leads),
        len(report.errors),
    )
    return report
