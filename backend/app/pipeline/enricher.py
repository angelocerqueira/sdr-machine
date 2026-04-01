"""
Módulo 2: Enriquecimento e Análise de Gaps
Analisa o site de cada lead e gera um score de oportunidade.
Score alto = site ruim = MAIS oportunidade pra você.
Inclui diagnóstico de marketing via Claude API com avaliação de potencial IA/automação.
"""

import json
import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from app.config import settings

logger = logging.getLogger(__name__)


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
        "social_urls": _extract_social_urls(soup),
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


# ---------------------------------------------------------------------------
# Diagnóstico de Marketing via Claude API
# ---------------------------------------------------------------------------

DIAGNOSTIC_JSON_SCHEMA = """{
  "qualificado": true,
  "motivo_desqualificacao": null,
  "potencial_ia_automacao": {
    "score": 75,
    "oportunidades": ["Chatbot IA para agendamento", "Automação de follow-up por WhatsApp"],
    "justificativa": "Explicação de por que este negócio tem potencial para IA/automação..."
  },
  "momento_funil": "descoberta",
  "funil": {
    "descoberta": {
      "diagnostico": "Análise do estado atual do negócio nesta etapa...",
      "acoes_top2": [
        {"acao": "Ação concreta 1", "resultado_esperado": "Resultado mensurável", "kpi": "Métrica de acompanhamento"},
        {"acao": "Ação concreta 2", "resultado_esperado": "Resultado mensurável", "kpi": "Métrica de acompanhamento"}
      ]
    },
    "atracao": {"diagnostico": "...", "acoes_top2": [{"acao": "...", "resultado_esperado": "...", "kpi": "..."}, {"acao": "...", "resultado_esperado": "...", "kpi": "..."}]},
    "consideracao": {"diagnostico": "...", "acoes_top2": [{"acao": "...", "resultado_esperado": "...", "kpi": "..."}, {"acao": "...", "resultado_esperado": "...", "kpi": "..."}]},
    "acao": {"diagnostico": "...", "acoes_top2": [{"acao": "...", "resultado_esperado": "...", "kpi": "..."}, {"acao": "...", "resultado_esperado": "...", "kpi": "..."}]},
    "apologia": {"diagnostico": "...", "acoes_top2": [{"acao": "...", "resultado_esperado": "...", "kpi": "..."}, {"acao": "...", "resultado_esperado": "...", "kpi": "..."}]}
  },
  "resumo_executivo": "2-3 frases sobre o estado geral do marketing digital do negócio",
  "prioridades_top3": ["Prioridade 1", "Prioridade 2", "Prioridade 3"]
}"""


def _extract_visible_text(html: str) -> str:
    """Extrai texto visível do HTML, limitado a 2000 chars pra economizar tokens."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return text[:2000]


def _format_social_context(lead_info: dict) -> str:
    """Formata dados de redes sociais pro prompt de diagnóstico."""
    profiles = lead_info.get("social_profiles", {})
    if not profiles:
        return "REDES SOCIAIS: Nenhum perfil encontrado."

    lines = ["REDES SOCIAIS:"]
    ig = profiles.get("instagram")
    if ig and isinstance(ig, dict) and ig.get("followers") is not None:
        lines.append(f"- Instagram: @{ig.get('username', '?')} | {ig.get('followers', 0)} seguidores | {ig.get('posts_count', 0)} posts | {'Conta comercial' if ig.get('is_business') else 'Conta pessoal'}")
        if ig.get("bio"):
            lines.append(f"  Bio: {ig['bio'][:200]}")

    li = profiles.get("linkedin")
    if li and isinstance(li, dict) and li.get("name"):
        lines.append(f"- LinkedIn: {li.get('name', '?')} | {li.get('followers', 0)} seguidores | {li.get('employees_range', '?')} funcionários | Setor: {li.get('industry', '?')}")

    for platform in ("facebook", "tiktok", "youtube"):
        p = profiles.get(platform)
        if p and isinstance(p, dict):
            lines.append(f"- {platform.capitalize()}: {p.get('url', 'perfil encontrado')}")

    return "\n".join(lines) if len(lines) > 1 else "REDES SOCIAIS: Nenhum perfil encontrado."


def _build_diagnostic_prompt(
    lead_info: dict,
    site_data: dict,
    html_analysis: dict,
    pagespeed: dict,
    visible_text: str,
) -> str:
    """Monta o prompt de diagnóstico de marketing."""
    reviews_text = ""
    if lead_info.get("top_reviews"):
        reviews_text = "\n".join(f'- "{r}"' for r in lead_info["top_reviews"][:3])

    site_status = site_data.get("status", "unknown")
    has_site = site_status == "ok"

    return f"""Você é um consultor de marketing digital especializado em negócios locais brasileiros.
Sua especialidade é identificar oportunidades de aplicação de IA e automação em operações comerciais.

Analise os dados abaixo e gere um diagnóstico de marketing estruturado.

DADOS DO NEGÓCIO:
- Nome: {lead_info.get('nome', 'N/A')}
- Nicho/Categoria: {lead_info.get('nicho', 'N/A')} / {lead_info.get('categoria', 'N/A')}
- Cidade: {lead_info.get('cidade', 'N/A')}
- Nota Google: {lead_info.get('rating', 'N/A')} ({lead_info.get('reviews_count', 0)} avaliações)
- Avaliações destaque:
{reviews_text or 'Sem avaliações disponíveis'}

ANÁLISE TÉCNICA DO SITE:
- Status: {"Site funcional" if has_site else f"Problemas: {site_status}"}
- SSL/HTTPS: {"Sim" if html_analysis.get("has_ssl", site_data.get("has_ssl")) else "Não"}
- Responsivo (mobile): {"Sim" if html_analysis.get("has_responsive_meta") else "Não"}
- Link WhatsApp: {"Sim" if html_analysis.get("has_whatsapp_link") else "Não"}
- Google Analytics/Tracking: {"Sim" if html_analysis.get("has_analytics") else "Não"}
- Chatbot/Atendimento online: {"Sim" if html_analysis.get("has_chatbot") else "Não"}
- CTA (call-to-action): {"Sim" if html_analysis.get("has_cta") else "Não"}
- Redes sociais: {"Sim" if html_analysis.get("has_social_links") else "Não"}
- Conteúdo: {html_analysis.get("word_count", 0)} palavras, {html_analysis.get("image_count", 0)} imagens
- Template genérico: {"Sim" if html_analysis.get("is_template") else "Não"}
- PageSpeed (mobile): {pagespeed.get("performance_score", "N/A")}/100
- Título do site: {html_analysis.get("title", "N/A")}
- Descrição: {html_analysis.get("description", "N/A")}

{"CONTEÚDO VISÍVEL DO SITE (trecho):" + chr(10) + visible_text if visible_text else "SEM WEBSITE — o negócio não possui site."}

{_format_social_context(lead_info)}

INSTRUÇÕES:
1. QUALIFICAÇÃO: Avalie se este negócio tem potencial real para serviços de IA e automação.
   - Negócios com operação que envolve agendamento, atendimento ao cliente, follow-up, gestão de leads, CRM = ALTO potencial
   - Negócios muito informais, sem escala, sem operação repetitiva = BAIXO potencial
   - Seja honesto: nem todo negócio se beneficia. Se não faz sentido, marque qualificado=false

2. MOMENTO NO FUNIL: Identifique em qual estágio o negócio se encontra predominantemente:
   - descoberta: quase não é encontrado online, presença digital mínima
   - atracao: é encontrado mas não converte visitantes em interessados
   - consideracao: atrai visitantes mas não gera confiança/diferenciação suficiente
   - acao: gera interesse mas perde na conversão (sem CTA claro, sem automação, processo manual)
   - apologia: converte bem mas não fideliza nem gera indicações sistemáticas

3. RECOMENDAÇÕES: Para CADA etapa do funil, dê exatamente 2 ações CONCRETAS e IMPLEMENTÁVEIS com resultado rápido.
   As ações devem ser específicas para este negócio (não genéricas). Foque em ações que o dono pode implementar em 1-2 semanas.

4. POTENCIAL IA/AUTOMAÇÃO: Score de 0 a 100.
   - 0-25: Sem potencial relevante (desqualifica)
   - 26-50: Potencial básico (automações simples)
   - 51-75: Bom potencial (chatbot, CRM, automações de marketing)
   - 76-100: Alto potencial (múltiplas oportunidades de IA na operação)

Responda EXCLUSIVAMENTE com JSON válido no formato abaixo. Sem texto antes ou depois, sem markdown.

{DIAGNOSTIC_JSON_SCHEMA}"""


def _parse_diagnostic_response(text: str) -> dict | None:
    """Parse da resposta do Claude. Retorna dict ou None se inválido."""
    text = text.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Diagnóstico: falha ao parsear JSON da resposta")
        return None

    # Validação básica de keys obrigatórias
    required_keys = {"qualificado", "potencial_ia_automacao", "momento_funil", "funil", "resumo_executivo"}
    if not required_keys.issubset(data.keys()):
        missing = required_keys - data.keys()
        logger.warning("Diagnóstico: keys faltando no JSON: %s", missing)
        return None

    valid_stages = {"descoberta", "atracao", "consideracao", "acao", "apologia"}
    if data.get("momento_funil") not in valid_stages:
        logger.warning("Diagnóstico: momento_funil inválido: %s", data.get("momento_funil"))
        return None

    pot = data.get("potencial_ia_automacao", {})
    pot_score = pot.get("score") if isinstance(pot, dict) else None
    if pot_score is None or not isinstance(pot_score, (int, float)) or not (0 <= pot_score <= 100):
        logger.warning("Diagnóstico: score de potencial inválido: %s", pot_score)
        return None

    return data


def generate_diagnostic(
    lead_info: dict,
    site_data: dict,
    html_analysis: dict,
    pagespeed: dict,
    html: str,
) -> dict | None:
    """
    Gera diagnóstico de marketing via Claude API.
    Retorna dict com o diagnóstico ou None em caso de falha.
    """
    if settings.skip_ai_diagnostic:
        return None

    if not settings.anthropic_api_key:
        logger.warning("Diagnóstico: ANTHROPIC_API_KEY não configurada")
        return None

    visible_text = _extract_visible_text(html)
    prompt = _build_diagnostic_prompt(lead_info, site_data, html_analysis, pagespeed, visible_text)

    model = settings.diagnostic_model or settings.claude_model

    headers = {
        "Content-Type": "application/json",
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
    }

    payload = {
        "model": model,
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=90,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["content"][0]["text"].strip()
        return _parse_diagnostic_response(text)

    except Exception as exc:
        logger.error("Diagnóstico: erro na API Claude: %s", str(exc)[:200])
        return None


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

    # 6. Diagnóstico de marketing via IA
    qualified = True
    diagnostic = None
    if lead_info:
        # Incluir dados sociais no lead_info pro diagnóstico
        lead_info_with_social = {**lead_info, "social_profiles": social_profiles}
        diagnostic = generate_diagnostic(
            lead_info=lead_info_with_social,
            site_data=site_data,
            html_analysis=html_analysis,
            pagespeed=pagespeed,
            html=site_data.get("html", ""),
        )

    if diagnostic:
        site_analysis["diagnostico_marketing"] = diagnostic

        # Qualificação baseada no score de potencial IA
        ai_score = diagnostic.get("potencial_ia_automacao", {}).get("score", 0)
        if not diagnostic.get("qualificado") or ai_score < settings.ai_potential_threshold:
            qualified = False

        # Adicionar razões do diagnóstico às opportunity_reasons
        prioridades = diagnostic.get("prioridades_top3") or []
        if prioridades:
            reasons.extend(prioridades)

    return {
        "opportunity_score": score,
        "opportunity_reasons": reasons,
        "site_analysis": site_analysis,
        "social_profiles": social_profiles,
        "qualified": qualified,
    }
