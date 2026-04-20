"""Pure classification function — no DB, no I/O dependencies.

Never raises: every failure mode lowers confidence or returns a safe
fallback (DISQUALIFIED / OUTROS / failed). See spec section 7.1.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, asdict
from typing import Any

from app.pipeline.enrichment.classifier_enums import (
    LeadProfile, NichoCanonico, NichoSource, PacoteSugerido, Prioridade,
)
from tenacity import (
    Retrying, stop_after_attempt, wait_exponential_jitter,
    retry_if_exception_type,
)

from app.pipeline.enrichment.classifier_prompts import (
    build_nicho_prompt, NICHO_TOOL_SCHEMA,
)
from app.pipeline.enrichment.classifier_rules import (
    PROFILE_THRESHOLDS, PROFILE_TO_DERIVED, fuzzy_match_nicho,
)


_VALID_NICHOS = {n.value for n in NichoCanonico}

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    perfil_lead: LeadProfile
    nicho_canonico: NichoCanonico
    nicho_source: NichoSource
    nicho_confidence: float
    pacote_sugerido: PacoteSugerido
    prioridade: Prioridade
    classification_hash: str
    error_reason: str | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        # Convert enums to their string values
        for k in (
            "perfil_lead", "nicho_canonico", "nicho_source",
            "pacote_sugerido", "prioridade",
        ):
            d[k] = d[k].value if hasattr(d[k], "value") else d[k]
        return d


# Defaults for missing inputs
_DEFAULTS = {
    "has_website": False,
    "score": 50,
    "rating": 0.0,
    "review_count": 0,
    "has_ssl": False,
    "has_analytics": False,
    "has_chatbot": False,
    "has_whatsapp_cta": False,
    "has_instagram": False,
}


def _coerce_num(v: Any, default: float) -> float:
    if v is None:
        return default
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _coerce_bool(v: Any, default: bool) -> bool:
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "sim", "t")
    return default


def _compute_hash(lead_data: dict) -> str:
    key = "|".join([
        str(_coerce_bool(lead_data.get("has_website"), _DEFAULTS["has_website"])),
        str(_coerce_num(lead_data.get("score"), _DEFAULTS["score"])),
        str(_coerce_num(lead_data.get("rating"), _DEFAULTS["rating"])),
        str(_coerce_num(lead_data.get("review_count"), _DEFAULTS["review_count"])),
        str(_coerce_bool(lead_data.get("has_ssl"), False)),
        str(_coerce_bool(lead_data.get("has_analytics"), False)),
        str(_coerce_bool(lead_data.get("has_chatbot"), False)),
        str(_coerce_bool(lead_data.get("has_instagram"), False)),
        str(lead_data.get("nicho_raw") or ""),
        str(lead_data.get("nome") or ""),
    ])
    return hashlib.md5(key.encode("utf-8")).hexdigest()


def _classify_profile(lead_data: dict) -> LeadProfile:
    """Cascade of deterministic rules — first match wins. Never raises."""
    has_website = _coerce_bool(lead_data.get("has_website"), _DEFAULTS["has_website"])
    score = _coerce_num(lead_data.get("score"), _DEFAULTS["score"])
    rating = _coerce_num(lead_data.get("rating"), _DEFAULTS["rating"])
    review_count = _coerce_num(lead_data.get("review_count"), _DEFAULTS["review_count"])
    has_ssl = _coerce_bool(lead_data.get("has_ssl"), False)
    has_analytics = _coerce_bool(lead_data.get("has_analytics"), False)
    has_chatbot = _coerce_bool(lead_data.get("has_chatbot"), False)
    has_whatsapp_cta = _coerce_bool(lead_data.get("has_whatsapp_cta"), False)
    has_instagram = _coerce_bool(lead_data.get("has_instagram"), False)
    telefone = lead_data.get("telefone")

    t = PROFILE_THRESHOLDS

    # Rule 1: DISQUALIFIED
    if rating and rating < t["disqualified_min_rating"]:
        return LeadProfile.DISQUALIFIED
    if review_count < t["disqualified_min_reviews_without_phone"] and not telefone:
        return LeadProfile.DISQUALIFIED
    if not (lead_data.get("nome") or telefone or lead_data.get("endereco")):
        return LeadProfile.DISQUALIFIED

    # Rule 2: HOT_NO_SITE
    if (not has_website
            and rating >= t["hot_no_site_min_rating"]
            and review_count >= t["hot_no_site_min_reviews"]):
        return LeadProfile.HOT_NO_SITE

    # Rule 3: HOT_BAD_SITE
    if (has_website
            and score >= t["hot_bad_site_min_score"]
            and (has_instagram or review_count >= t["hot_bad_site_min_reviews_when_no_instagram"])):
        return LeadProfile.HOT_BAD_SITE

    # Rule 4: COLD
    if (has_website
            and score < t["cold_max_score"]
            and has_ssl and has_analytics
            and (has_chatbot or has_whatsapp_cta)):
        return LeadProfile.COLD

    # Rule 5: WARM (catch-all)
    return LeadProfile.WARM


def classify(lead_data: dict, *, llm_client=None) -> ClassificationResult:
    """Main entry point: classify a lead by profile and nicho.

    Contract:
      - Never raises.
      - Always returns a ClassificationResult.
      - On any failure path, returns a fallback with error_reason populated.
    """
    # Guard against non-dict input
    if not isinstance(lead_data, dict):
        lead_data = {}

    try:
        profile = _classify_profile(lead_data)
    except Exception as exc:
        logger.exception("profile classification crashed: %s", exc)
        profile = LeadProfile.DISQUALIFIED

    # Nicho: fuzzy first, LLM fallback comes in next task (stub for now)
    try:
        nicho, source, confidence = _classify_nicho(lead_data, llm_client=llm_client)
        error_reason = None
    except Exception as exc:
        logger.exception("nicho classification crashed: %s", exc)
        nicho = NichoCanonico.OUTROS
        source = NichoSource.FAILED
        confidence = 0.0
        error_reason = str(exc)[:200]

    pacote, prioridade = PROFILE_TO_DERIVED[profile]

    return ClassificationResult(
        perfil_lead=profile,
        nicho_canonico=nicho,
        nicho_source=source,
        nicho_confidence=confidence,
        pacote_sugerido=pacote,
        prioridade=prioridade,
        classification_hash=_compute_hash(lead_data),
        error_reason=error_reason,
    )


def _call_llm_for_nicho(llm_client, lead_data: dict) -> tuple[NichoCanonico, float]:
    """Single LLM call with retry on transient failures.

    Returns (bucket, confidence). Raises on hard failure after retries.
    """
    prompt = build_nicho_prompt(
        nome=lead_data.get("nome") or "",
        nicho_raw=lead_data.get("nicho_raw") or "",
        descricao=lead_data.get("descricao") or "",
        reviews=lead_data.get("reviews") or [],
    )

    retryer = Retrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=8),
        retry=retry_if_exception_type((TimeoutError, ConnectionError, OSError)),
        reraise=True,
    )

    last_response = None
    for attempt in retryer:
        with attempt:
            last_response = llm_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=256,
                tools=[NICHO_TOOL_SCHEMA],
                tool_choice={"type": "tool", "name": "classify_nicho"},
                messages=[{"role": "user", "content": prompt}],
                timeout=15,
            )

    # Parse response
    tool_blocks = [b for b in last_response.content if getattr(b, "type", None) == "tool_use"]
    if not tool_blocks:
        raise ValueError("no tool_use block in response")

    data = tool_blocks[0].input or {}
    nicho_raw = data.get("nicho_canonico")
    if nicho_raw not in _VALID_NICHOS:
        raise ValueError(f"invalid enum value: {nicho_raw!r}")

    confidence = data.get("confidence", 0.5)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    return (NichoCanonico(nicho_raw), confidence)


def _classify_nicho(
    lead_data: dict, *, llm_client=None,
) -> tuple[NichoCanonico, NichoSource, float]:
    """3-layer nicho inference."""
    raw = lead_data.get("nicho_raw") or ""

    # Layers 1 + 2: fuzzy match (exact substring = 1.0, fuzzy ratio >= 0.75)
    match = fuzzy_match_nicho(raw)
    if match is not None:
        bucket, conf = match
        if conf >= 0.999:
            return (bucket, NichoSource.APIFY_CATEGORY, 1.0)
        return (bucket, NichoSource.FUZZY_MATCH, conf)

    # Layer 3: LLM
    if llm_client is None:
        return (NichoCanonico.OUTROS, NichoSource.FAILED, 0.0)

    try:
        bucket, conf = _call_llm_for_nicho(llm_client, lead_data)
        return (bucket, NichoSource.LLM_INFERRED, conf)
    except Exception as exc:
        logger.warning("LLM nicho classification failed: %s", exc)
        return (NichoCanonico.OUTROS, NichoSource.FAILED, 0.0)
