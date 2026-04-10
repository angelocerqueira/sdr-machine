"""Opportunity score calculation — replaces the algorithm in enricher.py.

Score is additive (higher = worse site = more opportunity) and capped at 100.
See docs/superpowers/specs/2026-04-10-smart-enrichment-pipeline-design.md §5.
"""
from datetime import date


_GENERIC_EMAIL_DOMAINS = {
    "gmail.com", "hotmail.com", "yahoo.com", "outlook.com", "yahoo.com.br",
    "bol.com.br", "uol.com.br", "live.com", "icloud.com",
}


_DATED_TECH_NAMES = {"adobe flash", "flash", "silverlight", "jquery 1", "jquery 2"}


def _is_generic_email(email: str | None) -> bool:
    if not email or "@" not in email:
        return False
    domain = email.split("@", 1)[1].strip().lower()
    return domain in _GENERIC_EMAIL_DOMAINS


def _has_dated_tech(tech_stack: list[dict] | None) -> bool:
    if not tech_stack:
        return False
    for tech in tech_stack:
        name = (tech.get("name") or "").lower()
        if any(dated in name for dated in _DATED_TECH_NAMES):
            return True
    return False


def calculate_score(
    lead_data: dict,
    site_analysis: dict,
    tech_stack: list[dict] | None = None,
    data_fundacao: date | None = None,
) -> tuple[int, list[str]]:
    """Calculate opportunity score from all enrichment data.

    Args:
        lead_data: dict with Lead fields (website, email, ...)
        site_analysis: dict produced by WebsiteCrawlerProvider
        tech_stack: list of {name, category} detected by TechStackProvider
        data_fundacao: company founding date from CNPJ provider

    Returns:
        (score, reasons) — score capped at 100
    """
    score = 0
    reasons: list[str] = []

    website = lead_data.get("website")
    status = site_analysis.get("status")

    # Base: no website
    if not website or status == "no_website":
        score += 40
        reasons.append("Sem website — oportunidade alta")

    # Site down / broken
    if status in ("connection_error", "timeout", "ssl_error"):
        score += 30
        reasons.append(f"Site com problemas técnicos: {status}")

    if website and status == "ok":
        if not site_analysis.get("has_ssl"):
            score += 15
            reasons.append("Sem HTTPS/SSL")

        if not site_analysis.get("has_responsive_meta"):
            score += 15
            reasons.append("Site não é responsivo (mobile)")

        if not site_analysis.get("has_cta"):
            score += 10
            reasons.append("Sem CTA claro (call-to-action)")

        if not site_analysis.get("has_social_links"):
            score += 5
            reasons.append("Sem links para redes sociais")

        pagespeed = site_analysis.get("pagespeed")
        if pagespeed is not None and pagespeed < 50:
            score += 10
            reasons.append(f"PageSpeed baixo ({pagespeed}/100)")

        if not site_analysis.get("structured_data"):
            score += 3
            reasons.append("Sem dados estruturados (schema.org)")

    # Tech stack signals
    if _has_dated_tech(tech_stack):
        score += 5
        reasons.append("Tech stack defasado detectado")

    # Email quality signal
    if _is_generic_email(lead_data.get("email")):
        score += 5
        reasons.append("Email não profissional (gmail/hotmail/etc)")

    # Established company with bad score
    if data_fundacao and score >= 50:
        try:
            years_old = date.today().year - data_fundacao.year
            if years_old >= 5:
                score += 2
                reasons.append(f"Empresa com {years_old} anos mas presença digital fraca")
        except Exception:
            pass

    return min(score, 100), reasons
