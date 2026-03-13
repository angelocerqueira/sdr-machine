"""
Módulo 2: Enriquecimento e Análise de Gaps
Analisa o site de cada lead e gera um score de oportunidade.
Score alto = site ruim = MAIS oportunidade pra você.
"""

import time

import requests
from bs4 import BeautifulSoup


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
        }

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text().lower()
    html_lower = html.lower()

    meta_desc_tag = soup.find("meta", {"name": "description"})
    description = ""
    if meta_desc_tag:
        description = (meta_desc_tag.get("content") or "")[:200]

    return {
        "has_responsive_meta": "viewport" in html_lower,
        "has_whatsapp_link": any(x in html_lower for x in ["wa.me", "whatsapp", "api.whatsapp"]),
        "has_analytics": any(x in html_lower for x in ["gtag", "analytics", "gtm", "google-analytics", "facebook pixel", "fbq("]),
        "has_chatbot": any(x in html_lower for x in ["tidio", "intercom", "crisp", "zendesk", "jivochat", "tawk", "drift", "chatbot"]),
        "has_cta": any(x in text for x in ["agende", "entre em contato", "fale conosco", "solicite", "orçamento", "whatsapp", "ligar"]),
        "has_social_links": any(x in html_lower for x in ["instagram.com", "facebook.com", "linkedin.com"]),
        "title": (soup.title.string.strip() if soup.title and soup.title.string else "")[:100],
        "description": description,
        "word_count": len(text.split()),
        "image_count": len(soup.find_all("img")),
        "is_template": any(x in html_lower for x in ["wix.com", "squarespace", "wordpress.com", "webnode", "site123"]),
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
        return {
            "performance_score": int((score or 0) * 100),
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


def enrich_lead_data(website: str, skip_pagespeed: bool = False) -> dict:
    """
    Pipeline completo de enriquecimento para 1 lead.
    Retorna dict com opportunity_score, opportunity_reasons, site_analysis.
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

    # 4. Score
    score, reasons = calculate_score(site_data, html_analysis, pagespeed)

    return {
        "opportunity_score": score,
        "opportunity_reasons": reasons,
        "site_analysis": {
            "status": site_data.get("status"),
            "has_ssl": site_data.get("has_ssl"),
            "title": html_analysis.get("title", ""),
            "description": html_analysis.get("description", ""),
            **html_analysis,
            "pagespeed": pagespeed.get("performance_score"),
        },
    }
