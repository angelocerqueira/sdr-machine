"""CNPJ-based lead discovery via MinhaReceita (primary) + BrasilAPI (fallback).

scrape_cnpj(niche, city, max_results) -> list[dict]

Never raises — any HTTP failure is caught, logged, and returns partial/empty list.
MinhaReceita API: GET https://minhareceita.org/?cnae={code}&municipio={ibge}&uf={uf}
BrasilAPI fallback: GET https://brasilapi.com.br/api/cnpj/v1/{cnpj}
"""
from __future__ import annotations

import logging
import re
import time

import requests

from app.pipeline.cnpj_lookup import niche_to_cnaes, city_to_ibge

logger = logging.getLogger(__name__)

MINHARECEITA_URL = "https://minhareceita.org"
BRASILAPI_CNPJ_URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"

_ACTIVE_STATUSES = {"ATIVA"}


# ── Internals ─────────────────────────────────────────────────────────────────

def _clean_digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def _build_lead(company: dict, niche: str, city: str) -> dict | None:
    """Convert MinhaReceita company dict to a lead dict.

    Returns None if company is inactive or has no name.
    """
    status = (company.get("situacao_cadastral") or "").upper()
    if status not in _ACTIVE_STATUSES:
        return None

    nome = (
        (company.get("nome_fantasia") or "").strip()
        or (company.get("razao_social") or "").strip()
    )
    if not nome:
        return None

    # Title-case avoids ALL-CAPS from Receita Federal
    nome = nome.title()

    ddd = company.get("ddd_telefone_1") or ""
    tel = company.get("telefone_1") or ""
    digits = _clean_digits(f"{ddd}{tel}")
    telefone = digits if digits else None

    address_parts = [
        company.get("logradouro"),
        company.get("numero"),
        company.get("complemento"),
        company.get("bairro"),
    ]
    endereco = " ".join(p for p in address_parts if p) or None

    return {
        "nome": nome,
        "telefone": telefone,
        "website": company.get("website") or None,
        "email": company.get("email") or None,
        "endereco": endereco,
        "cidade": city,
        "nicho": niche,
        "categoria": company.get("cnae_fiscal_descricao") or None,
        "cnpj": company.get("cnpj") or None,
        "razao_social": company.get("razao_social") or None,
        "porte": company.get("porte") or None,
        # Google Maps signals — not available from CNPJ source
        "rating": None,
        "reviews_count": 0,
        "google_maps_url": None,
        "top_reviews": [],
        "fonte": "cnpj",
    }


def _search_minhareceita(
    cnae: str,
    municipio: str,
    uf: str,
    max_results: int,
) -> list[dict]:
    """Paginate MinhaReceita results for a CNAE + municipality.

    Raises requests.RequestException on HTTP failure (caller handles).
    """
    results: list[dict] = []
    cursor: str | None = None

    while len(results) < max_results:
        params: dict[str, str] = {"cnae": cnae, "municipio": municipio, "uf": uf}
        if cursor:
            params["cursor"] = cursor

        resp = requests.get(MINHARECEITA_URL, params=params, timeout=15)
        resp.raise_for_status()
        body = resp.json()

        # Support both {"companies": [...]} and flat list responses
        companies: list[dict] = (
            body if isinstance(body, list)
            else body.get("companies") or body.get("data") or []
        )
        if not companies:
            break

        results.extend(companies)

        cursor = body.get("next") or body.get("cursor") if isinstance(body, dict) else None
        if not cursor:
            break

        time.sleep(0.3)  # gentle throttle

    return results[:max_results]


def _enrich_via_brasilapi(cnpj: str) -> dict | None:
    """Fetch full CNPJ data from BrasilAPI. Returns None on any error."""
    cleaned = _clean_digits(cnpj)
    if len(cleaned) != 14:
        return None
    try:
        resp = requests.get(BRASILAPI_CNPJ_URL.format(cnpj=cleaned), timeout=10)
        if resp.status_code == 200:
            return resp.json()
        logger.debug("BrasilAPI CNPJ %s returned %s", cleaned, resp.status_code)
    except Exception as exc:
        logger.debug("BrasilAPI fallback failed for CNPJ %s: %s", cleaned, exc)
    return None


# ── Public API ────────────────────────────────────────────────────────────────

def scrape_cnpj(niche: str, city: str, max_results: int = 50) -> list[dict]:
    """Discover leads from CNPJ data for a given niche + city.

    Primary source: MinhaReceita (search by CNAE + IBGE municipality).
    Fallback: BrasilAPI individual CNPJ lookup is NOT used for discovery
              (BrasilAPI has no search endpoint); it would be used by the
              existing CnpjProvider in the enrichment pipeline instead.

    Never raises — returns [] and logs on any error.
    """
    cnaes = niche_to_cnaes(niche)
    if not cnaes:
        logger.info("No CNAE mapping for niche '%s' — skipping CNPJ search", niche)
        return []

    ibge_result = city_to_ibge(city)
    if not ibge_result:
        logger.info("Could not resolve IBGE code for '%s' — skipping CNPJ search", city)
        return []

    municipio, uf = ibge_result
    per_cnae = max(1, max_results // len(cnaes))

    raw: list[dict] = []
    for cnae in cnaes:
        try:
            raw.extend(_search_minhareceita(cnae, municipio, uf, per_cnae))
        except Exception as exc:
            logger.warning(
                "MinhaReceita failed for cnae=%s city=%s: %s", cnae, city, exc
            )
            # Continue with remaining CNAEs — partial results are fine

    # Dedup by CNPJ, filter inactive, apply max_results
    leads: list[dict] = []
    seen_cnpj: set[str] = set()

    for company in raw:
        cnpj_digits = _clean_digits(company.get("cnpj") or "")
        if cnpj_digits and cnpj_digits in seen_cnpj:
            continue
        if cnpj_digits:
            seen_cnpj.add(cnpj_digits)

        lead = _build_lead(company, niche, city)
        if lead:
            leads.append(lead)

        if len(leads) >= max_results:
            break

    return leads
