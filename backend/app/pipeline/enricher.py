"""
Módulo 2: Enriquecimento e Análise de Gaps
Analisa o site de cada lead e gera um score de oportunidade.
Score alto = site ruim = MAIS oportunidade pra você.
Inclui diagnóstico de marketing via Claude API com avaliação de potencial IA/automação.
"""

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from app.config import settings
from app.pipeline.html_utils import _extract_visible_text  # noqa: F401 — re-exported for diagnostic nodes
from app.pipeline.diagnostic import run_diagnostic

logger = logging.getLogger(__name__)


_BOOKING_PATTERNS = [
    "calendly.com", "setmore.com", "cal.com", "agendor",
    "tidycal", "book.stripe", "simplybook",
]
_PAYMENT_PATTERNS = [
    "mercadopago", "pagseguro", "stripe.com", "paypal.com",
    "picpay", "getnet", "cielo",
]
_VIDEO_PATTERNS = [
    "youtube.com/embed", "vimeo.com/video", "<video", "youtu.be/",
]

_SOCIAL_NON_PROFILE_PATHS = {
    "instagram": {"p", "reel", "reels", "stories", "explore", "accounts", "about", "legal", "developer"},
    "facebook": {"sharer", "sharer.php", "share", "dialog", "plugins", "login.php", "groups"},
    "linkedin": {"sharearticle", "share", "cws", "pub", "pulse"},
    "tiktok": {"embed"},
    "youtube": {"watch", "results", "feed"},
}


def _is_profile_url(platform: str, href: str) -> bool:
    """Verifica se a URL é realmente um perfil e não um link de compartilhamento/post."""
    # Extract the first path segment after the domain (stop at /, ? or #)
    match = re.search(rf"{platform}\.com/([^/?#]+)", href.lower())
    if not match:
        return False
    first_segment = match.group(1).strip("/")
    if not first_segment:
        return False
    blocked = _SOCIAL_NON_PROFILE_PATHS.get(platform, set())
    return first_segment not in blocked


def _extract_social_urls(soup: BeautifulSoup) -> dict:
    """Extrai URLs de redes sociais dos links do site, filtrando links de compartilhamento."""
    social = {}
    platforms = ["instagram", "facebook", "linkedin", "tiktok", "youtube"]
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        href_lower = href.lower()
        for platform in platforms:
            if platform not in social and f"{platform}.com/" in href_lower and _is_profile_url(platform, href_lower):
                social[platform] = href
                break
    return social


def _scrape_instagram_profile(url: str) -> dict | None:
    """
    Busca dados públicos de um perfil do Instagram via Apify.
    Retorna dict com followers, posts, bio, etc. ou None se falhar.
    """
    if not settings.apify_token or not url:
        return None

    # Extrair username da URL
    match = re.search(r"instagram\.com/([^/?#]+)", url)
    if not match:
        return None
    username = match.group(1).strip("/")
    if username in ("p", "reel", "stories", "explore"):
        return None

    api_url = "https://api.apify.com/v2/acts/apify~instagram-profile-scraper/run-sync-get-dataset-items"
    payload = {
        "usernames": [username],
    }
    params = {
        "token": settings.apify_token,
        "timeout": 30,
        "memory": 256,
    }

    try:
        resp = requests.post(api_url, json=payload, params=params, timeout=60)
        resp.raise_for_status()
        results = resp.json()
        if not results:
            return None

        profile = results[0]
        return {
            "platform": "instagram",
            "username": username,
            "full_name": profile.get("fullName", ""),
            "bio": (profile.get("biography", "") or "")[:300],
            "followers": profile.get("followersCount", 0),
            "following": profile.get("followsCount", 0),
            "posts_count": profile.get("postsCount", 0),
            "is_business": profile.get("isBusinessAccount", False),
            "category": profile.get("businessCategoryName", ""),
            "external_url": profile.get("externalUrl", ""),
            "is_verified": profile.get("verified", False),
        }
    except Exception as exc:
        logger.warning("Instagram scrape failed for %s: %s", username, str(exc)[:100])
        return None


def _search_linkedin_company(company_name: str, city: str) -> dict | None:
    """
    Busca perfil de empresa no LinkedIn via Apify.
    Retorna dict com dados básicos ou None se não encontrar.
    """
    if not settings.apify_token or not company_name:
        return None

    api_url = "https://api.apify.com/v2/acts/apify~linkedin-company-scraper/run-sync-get-dataset-items"
    payload = {
        "queries": [f"{company_name} {city}"],
        "maxResults": 1,
    }
    params = {
        "token": settings.apify_token,
        "timeout": 30,
        "memory": 256,
    }

    try:
        resp = requests.post(api_url, json=payload, params=params, timeout=60)
        resp.raise_for_status()
        results = resp.json()
        if not results:
            return None

        company = results[0]
        return {
            "platform": "linkedin",
            "name": company.get("name", ""),
            "description": (company.get("description", "") or "")[:500],
            "followers": company.get("followersCount", 0),
            "employees_range": company.get("employeeCountRange", ""),
            "industry": company.get("industry", ""),
            "website": company.get("website", ""),
            "specialties": company.get("specialties", []),
            "url": company.get("url", ""),
        }
    except Exception as exc:
        logger.warning("LinkedIn scrape failed for %s: %s", company_name, str(exc)[:100])
        return None


def scrape_social_profiles(lead_info: dict, social_urls: dict) -> dict:
    """
    Busca dados de redes sociais do lead.
    Usa URLs encontradas no site + busca por nome no LinkedIn.
    Retorna dict com dados de cada plataforma encontrada.
    """
    profiles: dict = {}

    # Instagram (se encontrou URL no site)
    ig_url = social_urls.get("instagram")
    if ig_url:
        ig_data = _scrape_instagram_profile(ig_url)
        if ig_data:
            profiles["instagram"] = ig_data
            time.sleep(1)  # Rate limit

    # LinkedIn (only if URL found on site)
    li_url = social_urls.get("linkedin")
    if li_url:
        nome = lead_info.get("nome", "")
        cidade = lead_info.get("cidade", "")
        li_data = _search_linkedin_company(nome, cidade)
        if li_data:
            profiles["linkedin"] = li_data
            time.sleep(1)

    # Preservar URLs encontradas mesmo sem scraping
    for platform, url in social_urls.items():
        if platform not in profiles:
            profiles[platform] = {"platform": platform, "url": url}

    return profiles


def fetch_website(url: str, timeout: int = 10) -> dict:
    """
    Faz o crawl básico do site do lead.
    Retorna HTML, status, headers básicos.
    """
    if not url:
        return {"status": "no_website", "html": "", "error": "Sem website"}

    if not url.startswith("http"):
        url = "https://" + url

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)

        return {
            "status": "ok",
            "status_code": resp.status_code,
            "html": resp.text[:15000],
            "final_url": resp.url,
            "has_ssl": resp.url.startswith("https"),
            "content_length": len(resp.text),
        }
    except requests.exceptions.SSLError:
        return {"status": "ssl_error", "html": "", "has_ssl": False}
    except requests.exceptions.ConnectionError:
        return {"status": "connection_error", "html": "", "error": "Site fora do ar"}
    except requests.exceptions.Timeout:
        return {"status": "timeout", "html": "", "error": "Site muito lento"}
    except Exception as e:
        return {"status": "error", "html": "", "error": str(e)[:100]}


def analyze_html(html: str) -> dict:
    """
    Análise técnica básica do HTML sem precisar de IA.
    """
    if not html:
        return {
            "has_responsive_meta": False,
            "has_whatsapp_link": False,
            "has_analytics": False,
            "has_chatbot": False,
            "has_cta": False,
            "has_social_links": False,
            "title": "",
            "description": "",
            "word_count": 0,
            "image_count": 0,
            "is_template": False,
            "has_booking_link": False,
            "has_payment_link": False,
            "has_contact_form": False,
            "form_count": 0,
            "has_video": False,
            "contact_channels_count": 0,
        }

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text().lower()
    html_lower = html.lower()

    meta_desc_tag = soup.find("meta", {"name": "description"})
    description = ""
    if meta_desc_tag:
        description = (meta_desc_tag.get("content") or "")[:200]

    # ── Automation signals ──────────────────────────────────────────────────
    has_booking_link = any(p in html_lower for p in _BOOKING_PATTERNS)
    has_payment_link = any(p in html_lower for p in _PAYMENT_PATTERNS)
    has_contact_form = "<form" in html_lower
    form_count = html_lower.count("<form")
    has_video = any(p in html_lower for p in _VIDEO_PATTERNS)

    contact_channels = 0
    if "tel:" in html_lower:
        contact_channels += 1
    if "mailto:" in html_lower:
        contact_channels += 1
    if "wa.me" in html_lower or "api.whatsapp" in html_lower:
        contact_channels += 1
    if has_contact_form:
        contact_channels += 1
    if any(c in html_lower for c in ["tidio", "crisp", "intercom", "tawk", "zendesk", "drift"]):
        contact_channels += 1

    return {
        "has_responsive_meta": "viewport" in html_lower,
        "has_whatsapp_link": any(x in html_lower for x in ["wa.me", "whatsapp", "api.whatsapp"]),
        "has_analytics": any(x in html_lower for x in ["gtag", "analytics", "gtm", "google-analytics", "facebook pixel", "fbq("]),
        "has_chatbot": any(x in html_lower for x in ["tidio", "intercom", "crisp", "zendesk", "jivochat", "tawk", "drift", "chatbot"]),
        "has_cta": any(x in text for x in ["agende", "entre em contato", "fale conosco", "solicite", "orçamento", "whatsapp", "ligar"]),
        "has_social_links": any(x in html_lower for x in ["instagram.com", "facebook.com", "linkedin.com"]),
        "social_urls": _extract_social_urls(soup),
        "title": (soup.title.string.strip() if soup.title and soup.title.string else "")[:100],
        "description": description,
        "word_count": len(text.split()),
        "image_count": len(soup.find_all("img")),
        "is_template": any(x in html_lower for x in ["wix.com", "squarespace", "wordpress.com", "webnode", "site123"]),
        "has_booking_link": has_booking_link,
        "has_payment_link": has_payment_link,
        "has_contact_form": has_contact_form,
        "form_count": form_count,
        "has_video": has_video,
        "contact_channels_count": contact_channels,
    }


def check_pagespeed(url: str) -> dict:
    """
    Usa a API gratuita do Google PageSpeed Insights.
    """
    if not url:
        return {"performance_score": 0, "error": "no_url"}

    try:
        api_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
        params = {
            "url": url if url.startswith("http") else f"https://{url}",
            "strategy": "mobile",
            "category": "performance",
        }
        resp = requests.get(api_url, params=params, timeout=30)
        data = resp.json()

        score = data.get("lighthouseResult", {}).get("categories", {}).get("performance", {}).get("score", 0)
        perf_score = max(0, int((score or 0) * 100))
        return {
            "performance_score": perf_score,
            "first_contentful_paint": data.get("lighthouseResult", {}).get("audits", {}).get("first-contentful-paint", {}).get("displayValue", "N/A"),
        }
    except Exception:
        return {"performance_score": 0, "error": "api_failed"}


def calculate_score(site_data: dict, html_analysis: dict, pagespeed: dict) -> tuple[int, list[str]]:
    """
    Calcula o score de oportunidade (0-100).
    Quanto MAIOR, pior o site, MAIS oportunidade.
    Retorna (score, reasons).
    """
    score = 0
    reasons: list[str] = []

    if site_data.get("status") == "no_website":
        return 95, ["Sem website — oportunidade máxima"]

    if site_data.get("status") in ("connection_error", "timeout", "ssl_error"):
        return 85, [f"Site com problemas: {site_data.get('status')}"]

    if not site_data.get("has_ssl"):
        score += 15
        reasons.append("Sem HTTPS/SSL")

    if not html_analysis.get("has_responsive_meta"):
        score += 15
        reasons.append("Não é responsivo (mobile)")

    if not html_analysis.get("has_whatsapp_link"):
        score += 10
        reasons.append("Sem link de WhatsApp")

    if not html_analysis.get("has_analytics"):
        score += 8
        reasons.append("Sem Google Analytics/tracking")

    if not html_analysis.get("has_chatbot"):
        score += 8
        reasons.append("Sem chatbot/atendimento online")

    if not html_analysis.get("has_cta"):
        score += 10
        reasons.append("Sem CTA claro (call-to-action)")

    if pagespeed.get("performance_score", 100) < 50:
        score += 10
        reasons.append(f"PageSpeed lento ({pagespeed.get('performance_score', '?')}/100)")

    if html_analysis.get("word_count", 500) < 200:
        score += 10
        reasons.append("Conteúdo muito escasso")

    if html_analysis.get("is_template"):
        score += 5
        reasons.append("Usa template genérico (Wix/WordPress.com)")

    if html_analysis.get("image_count", 5) < 2:
        score += 5
        reasons.append("Quase sem imagens")

    return min(score, 100), reasons


def enrich_lead_data(website: str, lead_info: dict | None = None, skip_pagespeed: bool = False) -> dict:
    """
    Pipeline completo de enriquecimento para 1 lead.
    Retorna dict com opportunity_score, opportunity_reasons, site_analysis, qualified.
    """
    # 1. Fetch site
    site_data = fetch_website(website)

    # 2. Análise HTML
    html_analysis = analyze_html(site_data.get("html", ""))

    # 3. PageSpeed (opcional - tem rate limit)
    pagespeed: dict = {}
    if not skip_pagespeed and website and site_data.get("status") == "ok":
        pagespeed = check_pagespeed(website)
        time.sleep(1)  # Rate limit

    # 4. Score técnico
    score, reasons = calculate_score(site_data, html_analysis, pagespeed)

    site_analysis = {
        "status": site_data.get("status"),
        "has_ssl": site_data.get("has_ssl"),
        "title": html_analysis.get("title", ""),
        "description": html_analysis.get("description", ""),
        **html_analysis,
        "pagespeed": pagespeed.get("performance_score"),
    }

    # 5. Scrape redes sociais
    social_profiles: dict = {}
    social_urls = html_analysis.get("social_urls", {})
    if lead_info and settings.apify_token and not settings.skip_social_scraping:
        social_profiles = scrape_social_profiles(lead_info, social_urls)

    # 6. Service Level Analysis via LangGraph
    qualified = True
    if lead_info:
        service_levels = run_diagnostic(
            lead_info=lead_info,
            site_data=site_data,
            html_analysis=html_analysis,
            pagespeed=pagespeed,
            html=site_data.get("html", ""),
            social_profiles=social_profiles,
        )

        if service_levels:
            site_analysis["service_levels"] = service_levels.model_dump()
            if service_levels.diagnostico_marketing:
                site_analysis["diagnostico_marketing"] = service_levels.diagnostico_marketing.model_dump()
            qualified = service_levels.qualificado

    return {
        "opportunity_score": score,
        "opportunity_reasons": reasons,
        "site_analysis": site_analysis,
        "social_profiles": social_profiles,
        "qualified": qualified,
    }


def enrich_lead_via_orchestrator(
    lead,
    skip_providers: list[str] | None = None,
    force_providers: list[str] | None = None,
) -> dict:
    """New entry point — uses the orchestrator.

    Takes a Lead-like object directly (not the legacy website+lead_info dict).
    Returns a dict compatible with what _run_enrich applies to the Lead row.
    """
    # Lazy import to avoid circular dependency:
    # enricher -> orchestrator -> website_crawler -> enricher
    from app.pipeline.enrichment.orchestrator import EnrichmentOrchestrator

    orch = EnrichmentOrchestrator()
    return orch.run(lead, skip_providers=skip_providers, force_providers=force_providers)
