"""Opportunity score — multi-dimensional model (4 axes).

Axes:
  acessibilidade  — can we reach this lead? gate: < 40 = disqualify
  lp_site         — opportunity for landing page / site redesign
  automacao       — opportunity for automation services
  mapa_reputacao  — opportunity for Google Maps / reputation management

composite = max(lp_site, automacao, mapa_reputacao), gated by acessibilidade.
opportunity_score (legacy field) = composite — backward-compatible.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date


# ─────────────────────────────── Constants ────────────────────────────────────

_ACESSIBILIDADE_GATE = 40

_GENERIC_EMAIL_DOMAINS = {
    "gmail.com", "hotmail.com", "yahoo.com", "outlook.com", "yahoo.com.br",
    "bol.com.br", "uol.com.br", "live.com", "icloud.com",
}

_DATED_TECH_NAMES = {"adobe flash", "flash", "silverlight", "jquery 1", "jquery 2"}

_CRM_MARKETING_TOOLS = {
    "hubspot", "pipedrive", "rd station", "mailchimp", "klaviyo",
    "intercom", "activecampaign", "salesforce", "zoho",
}

_CONTACTABILITY_KEYWORDS = [
    "não atende", "não responde", "difícil contato", "difícil de achar",
    "não encontrei", "telefone não funciona", "sem whatsapp",
    "demora para responder", "nunca atendem", "não retornou",
]


# ─────────────────────────────── Helpers ──────────────────────────────────────

def _clean_phone(phone: str | None) -> str:
    if not phone:
        return ""
    return re.sub(r"\D", "", phone)


def _is_valid_br_phone(cleaned: str) -> bool:
    # 10 = fixo (DDD + 8 dígitos), 11 = celular (DDD + 9 dígitos)
    # 12/13 = com código do país 55
    return len(cleaned) in (10, 11, 12, 13)


def _is_mobile(cleaned: str) -> bool:
    if len(cleaned) == 11 and cleaned[2] == "9":
        return True
    if len(cleaned) == 13 and cleaned[4] == "9":
        return True
    return False


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


def _has_crm_tool(tech_stack: list[dict] | None) -> bool:
    if not tech_stack:
        return False
    stack_names = {(t.get("name") or "").lower() for t in tech_stack}
    return any(
        tool in name
        for tool in _CRM_MARKETING_TOOLS
        for name in stack_names
    )


# ─────────────────────────── DimensionalScore ─────────────────────────────────

@dataclass
class DimensionalScore:
    acessibilidade: int = 0
    lp_site: int = 0
    automacao: int = 0
    mapa_reputacao: int = 0
    reasons: dict = field(default_factory=lambda: {
        "acessibilidade": [],
        "lp_site": [],
        "automacao": [],
        "mapa_reputacao": [],
    })

    @property
    def composite(self) -> int:
        if self.acessibilidade < _ACESSIBILIDADE_GATE:
            return 0
        return min(100, max(self.lp_site, self.automacao, self.mapa_reputacao))

    @property
    def nivel_recomendado(self) -> str | None:
        if self.acessibilidade < _ACESSIBILIDADE_GATE:
            return None
        scores = {"lp": self.lp_site, "automacao": self.automacao, "mapa": self.mapa_reputacao}
        return max(scores, key=scores.get)

    @property
    def qualificado(self) -> bool:
        return self.acessibilidade >= _ACESSIBILIDADE_GATE and self.composite >= 40

    @property
    def flat_reasons(self) -> list[str]:
        """Flat list for backward compat with opportunity_reasons field."""
        result = []
        for dim, rs in self.reasons.items():
            for r in rs:
                result.append(f"[{dim.upper()}] {r}")
        return result


# ─────────────────────────── Dimension calculators ────────────────────────────

def _score_acessibilidade(lead_data: dict) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    cleaned = _clean_phone(lead_data.get("telefone"))
    if _is_valid_br_phone(cleaned):
        score += 50
        if _is_mobile(cleaned):
            score += 25
            reasons.append("Celular válido — WhatsApp provável")
        else:
            reasons.append("Telefone fixo válido — WhatsApp incerto")
    else:
        reasons.append("Sem telefone válido — canal WhatsApp comprometido")

    email = lead_data.get("email")
    if email and "@" in email:
        score += 15
        if not _is_generic_email(email):
            score += 10
            reasons.append("Email profissional disponível")
        else:
            reasons.append("Email genérico (gmail/hotmail)")

    if lead_data.get("social_profiles"):
        score += 10
        reasons.append("Perfis sociais encontrados")

    return min(score, 100), reasons


def _score_lp_site(
    lead_data: dict,
    site_analysis: dict,
    tech_stack: list[dict] | None,
    data_fundacao: date | None,
) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    website = lead_data.get("website")
    status = site_analysis.get("status")

    if not website or status == "no_website":
        return 95, ["Sem website — oportunidade máxima"]

    if status in ("connection_error", "timeout", "ssl_error"):
        return 85, [f"Site com problemas: {status}"]

    if status == "ok":
        if not site_analysis.get("has_ssl"):
            score += 15
            reasons.append("Sem HTTPS/SSL")
        if not site_analysis.get("has_responsive_meta"):
            score += 15
            reasons.append("Site não é responsivo (mobile)")
        if not site_analysis.get("has_whatsapp_link"):
            score += 10
            reasons.append("Sem link de WhatsApp")
        if not site_analysis.get("has_analytics"):
            score += 8
            reasons.append("Sem Google Analytics/tracking")
        if not site_analysis.get("has_chatbot"):
            score += 8
            reasons.append("Sem chatbot/atendimento online")
        if not site_analysis.get("has_cta"):
            score += 10
            reasons.append("Sem CTA claro (call-to-action)")
        pagespeed = site_analysis.get("pagespeed")
        if pagespeed is not None and pagespeed < 50:
            score += 10
            reasons.append(f"PageSpeed baixo ({pagespeed}/100)")
        if site_analysis.get("word_count", 500) < 200:
            score += 10
            reasons.append("Conteúdo muito escasso")
        if site_analysis.get("is_template"):
            score += 5
            reasons.append("Usa template genérico (Wix/WordPress.com)")
        if site_analysis.get("image_count", 5) < 2:
            score += 5
            reasons.append("Quase sem imagens")
        if not site_analysis.get("has_social_links"):
            score += 5
            reasons.append("Sem links para redes sociais")
        if not site_analysis.get("structured_data"):
            score += 3
            reasons.append("Sem dados estruturados (schema.org)")

    if _has_dated_tech(tech_stack):
        score += 5
        reasons.append("Tech stack defasado detectado")

    if _is_generic_email(lead_data.get("email")):
        score += 5
        reasons.append("Email não profissional (gmail/hotmail/etc)")

    if data_fundacao and score >= 50:
        try:
            years_old = date.today().year - data_fundacao.year
            if years_old >= 5:
                score += 2
                reasons.append(f"Empresa com {years_old} anos mas presença digital fraca")
        except Exception:
            pass

    return min(score, 100), reasons


def _score_mapa_reputacao(lead_data: dict) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    google_maps_url = lead_data.get("google_maps_url")
    if not google_maps_url:
        score += 25
        reasons.append("Sem presença no Google Maps")
        return min(score, 100), reasons

    rating = lead_data.get("rating")
    if rating is not None:
        r = float(rating)
        if r < 3.5:
            score += 30
            reasons.append(f"Avaliação baixa ({rating}★)")
        elif r < 4.0:
            score += 20
            reasons.append(f"Avaliação abaixo da média ({rating}★)")
        elif r < 4.5:
            score += 10
            reasons.append(f"Avaliação moderada ({rating}★) — tem espaço para melhorar")

    reviews_count = lead_data.get("reviews_count") or 0
    if reviews_count < 10:
        score += 25
        reasons.append(f"Pouquíssimas avaliações ({reviews_count}) — perfil subdesenvolvido")
    elif reviews_count < 30:
        score += 15
        reasons.append(f"Poucas avaliações ({reviews_count})")
    elif reviews_count < 100:
        score += 5
        reasons.append(f"Volume de avaliações mediano ({reviews_count})")

    top_reviews = lead_data.get("top_reviews") or []
    if top_reviews:
        texts = " ".join(
            r.get("text", "") if isinstance(r, dict) else str(r)
            for r in top_reviews[:5]
        ).lower()
        if any(kw in texts for kw in _CONTACTABILITY_KEYWORDS):
            score += 15
            reasons.append("Reviews mencionam problemas de contato/atendimento")

    return min(score, 100), reasons


def _score_automacao(
    site_analysis: dict,
    tech_stack: list[dict] | None,
    lead_data: dict,
) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    if not site_analysis.get("has_chatbot"):
        score += 15
        reasons.append("Sem chatbot — atendimento manual")

    if not site_analysis.get("has_booking_link"):
        score += 15
        reasons.append("Sem sistema de agendamento online")

    if not site_analysis.get("has_payment_link"):
        score += 15
        reasons.append("Sem integração de pagamento online")

    if not _has_crm_tool(tech_stack):
        score += 10
        reasons.append("Sem CRM ou ferramenta de marketing detectada")

    reviews_count = lead_data.get("reviews_count") or 0
    if reviews_count >= 100:
        score += 15
        reasons.append(f"Alto volume de clientes ({reviews_count} avaliações) — automação escalaria bem")
    elif reviews_count >= 50:
        score += 10
        reasons.append(f"Bom volume de clientes ({reviews_count} avaliações)")

    if not site_analysis.get("has_analytics"):
        score += 8
        reasons.append("Sem analytics — tomada de decisão manual")

    # Default 1 = lead sem site não tem fragmentação de canais para automatizar
    contact_channels = site_analysis.get("contact_channels_count", 1)
    if contact_channels >= 3:
        score += 10
        reasons.append(f"{contact_channels} canais de contato fragmentados — sem integração")

    return min(score, 100), reasons


# ─────────────────────────────── Public API ───────────────────────────────────

def calculate_score(
    lead_data: dict,
    site_analysis: dict,
    tech_stack: list[dict] | None = None,
    data_fundacao: date | None = None,
) -> DimensionalScore:
    """Calculate multi-dimensional opportunity score.

    Args:
        lead_data: dict with Lead fields. Keys used for full scoring:
            website, email, telefone, rating, reviews_count, top_reviews,
            google_maps_url, social_profiles
        site_analysis: dict from WebsiteCrawlerProvider (includes
            has_booking_link, has_payment_link, contact_channels_count)
        tech_stack: list of {name, category} from TechStackProvider
        data_fundacao: company founding date from CnpjProvider

    Returns:
        DimensionalScore with 4 axes + composite property
    """
    acess_score, acess_reasons = _score_acessibilidade(lead_data)
    lp_score, lp_reasons = _score_lp_site(lead_data, site_analysis, tech_stack, data_fundacao)
    mapa_score, mapa_reasons = _score_mapa_reputacao(lead_data)
    auto_score, auto_reasons = _score_automacao(site_analysis, tech_stack, lead_data)

    return DimensionalScore(
        acessibilidade=acess_score,
        lp_site=lp_score,
        automacao=auto_score,
        mapa_reputacao=mapa_score,
        reasons={
            "acessibilidade": acess_reasons,
            "lp_site": lp_reasons,
            "automacao": auto_reasons,
            "mapa_reputacao": mapa_reasons,
        },
    )
