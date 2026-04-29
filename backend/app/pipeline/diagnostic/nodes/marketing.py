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


def _extract_balanced_json(text: str) -> str | None:
    """Return the first balanced ``{...}`` block in ``text``, or None.

    Tracks string boundaries so braces inside JSON string values don't break the
    balance. Lets us recover a valid JSON object when the LLM wraps its
    response in prose ("Here's the analysis: {...}\\n\\nHope it helps!").
    """
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def _parse_response(text: str) -> MarketingDiagnostic:
    """Parse LLM response into MarketingDiagnostic.

    Tolerates: ``<think>`` blocks, ```` ```json ``` ```` fences, and prose
    surrounding the JSON object.
    """
    cleaned = _THINK_RE.sub("", text).strip()
    match = _JSON_BLOCK_RE.search(cleaned)
    if match:
        cleaned = match.group(1).strip()
    else:
        balanced = _extract_balanced_json(cleaned)
        if balanced:
            cleaned = balanced
    return MarketingDiagnostic(**json.loads(cleaned))


def analyze_marketing(state: GraphState) -> dict:
    """Run marketing diagnostic LLM call and parse JSON."""
    response_text: str | None = None
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
        response_text = response.content
        result = _parse_response(response_text)
        return {"marketing_result": result}
    except Exception:
        if response_text is None:
            logger.exception("Marketing analyzer failed (no response captured)")
        else:
            head = response_text[:200].replace("\n", " ")
            tail = response_text[-200:].replace("\n", " ")
            logger.exception(
                "Marketing analyzer failed | resp_len=%d | head=%r | tail=%r",
                len(response_text), head, tail,
            )
        return {"marketing_result": None}
