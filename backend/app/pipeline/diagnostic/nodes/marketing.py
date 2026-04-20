"""Marketing diagnostic node — produces full funnel analysis via LLM."""

import json
import logging
import re

from langchain_openai import ChatOpenAI

from app.config import settings
from app.pipeline.diagnostic.state import GraphState, MarketingDiagnostic
from app.pipeline.diagnostic.prompts.shared import format_lead_context
from app.pipeline.diagnostic.prompts.marketing import (
    MARKETING_SYSTEM_PROMPT,
    build_marketing_prompt,
)
from app.pipeline.html_utils import _extract_visible_text

logger = logging.getLogger(__name__)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def _get_llm() -> ChatOpenAI:
    """Create a ChatOpenAI instance pointing at the configured LLM provider."""
    model = settings.diagnostic_model or settings.llm_model
    return ChatOpenAI(
        model=model,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        max_tokens=6000,
        timeout=90,
    )


def _parse_response(text: str) -> MarketingDiagnostic:
    """Parse LLM response into MarketingDiagnostic."""
    cleaned = _THINK_RE.sub("", text).strip()
    match = _JSON_BLOCK_RE.search(cleaned)
    if match:
        cleaned = match.group(1).strip()
    return MarketingDiagnostic(**json.loads(cleaned))


def analyze_marketing(state: GraphState) -> dict:
    """Run marketing diagnostic LLM call and parse JSON."""
    try:
        llm = _get_llm()
        visible_text = _extract_visible_text(state.html)
        context = format_lead_context(
            lead_info=state.lead_info,
            site_data=state.site_data,
            html_analysis=state.html_analysis,
            pagespeed=state.pagespeed,
            visible_text=visible_text,
            social_profiles=state.social_profiles,
        )
        user_prompt = build_marketing_prompt(context)
        response = llm.invoke([
            {"role": "system", "content": MARKETING_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ])
        result = _parse_response(response.content)
        return {"marketing_result": result}
    except Exception:
        logger.exception("Marketing analyzer failed")
        return {"marketing_result": None}
