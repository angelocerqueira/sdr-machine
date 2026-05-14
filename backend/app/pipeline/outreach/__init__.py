"""Outreach package — WhatsApp cold cadence (5 toques).

Re-exports the public API (and a few internals consumed by existing tests)
from :mod:`app.pipeline.outreach.generator` so existing callers continue to
import ``from app.pipeline.outreach import generate_messages`` unchanged.

Subsequent refactor PRs (PR1.2+) will split ``generator.py`` into sibling
modules (validators, cadence_specs, prompts, …) without touching this surface.
"""

from app.pipeline.outreach.generator import (
    CADENCE_ORDER,
    GenerationResult,
    _build_context,
    _clean_phone,
    _empresa_idade_anos,
    _fallback,
    _format_ctx_facts,
    _format_diag_block,
    _generate_ai_message,
    _get_diagnostic,
    _hook_calibration_block,
    _lp_url,
    _parse_llm_response,
    _persona_block,
    generate_messages,
    logger,
    requests,
    settings,
)

__all__ = [
    "CADENCE_ORDER",
    "GenerationResult",
    "generate_messages",
]
