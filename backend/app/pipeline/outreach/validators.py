"""
Hard validators + fixers for outreach LLM output (PR1.2).

Pure leaf module — no imports from generator.py, no LLM calls, no DB.
Used by the generator's post-LLM pipeline to gate / repair output.

Public surface
--------------
- ValidationResult           — dataclass(passed, errors)
- detect_placeholders(text)  — regex/heuristic detector
- fix_capitalization(text)   — capitalizes first letter + after period+space
- fix_punctuation_spacing()  — inserts space after stuck-together periods
- validate_hard(text, type)  — runs all hard validators, collects all errors

Error code convention
---------------------
- "placeholder:<match>"             e.g. "placeholder:XXXX", "placeholder:[Nome]"
- "too_short:<n><min>"              e.g. "too_short:55<180"
- "no_sentence_punctuation"
- "forbidden:<short_label>"         e.g. "forbidden:clima", "forbidden:tudo_bem"

`validate_hard` gathers ALL errors (does NOT short-circuit) so callers get
the full picture for debugging / logging.
"""

import re
from dataclasses import dataclass, field

from app.pipeline.outreach.config import compliance_for, glossario_for

# ---------------------------------------------------------------------------
# Public dataclass
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    passed: bool
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Length thresholds (ported from generator._MIN_LENGTHS)
# ---------------------------------------------------------------------------

_MIN_LENGTHS: dict[str, int] = {
    "initial": 180,
    "bump_d2": 25,
    "insight_d5": 100,
    "angle_d9": 90,
    "breakup_d14": 80,
}
_DEFAULT_MIN_LENGTH = 60


# ---------------------------------------------------------------------------
# Forbidden patterns (ported from generator._FORBIDDEN_PATTERNS)
#
# Each entry is (label, regex). Label feeds the "forbidden:<label>" error code.
# ---------------------------------------------------------------------------

_FORBIDDEN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "clima_estado",
        re.compile(
            r"\b(?:t[aá]|est[aá])\s+(?:gelado|quente|frio|chovendo|ensolarado|nublado)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "clima",
        re.compile(r"\bclima\s+(?:d[ae]|aí|por\s+aí|em)\b", re.IGNORECASE),
    ),
    (
        "tempo",
        re.compile(r"\btempo\s+(?:aí|por\s+aí|t[aá]\b)", re.IGNORECASE),
    ),
    (
        "tudo_bem",
        re.compile(r"\btudo\s+bem\s+com\s+(?:voc[eê]|tu)\b", re.IGNORECASE),
    ),
    (
        "venho_por_meio",
        re.compile(r"\bvenho\s+por\s+meio", re.IGNORECASE),
    ),
    (
        "espero_que_esta",
        re.compile(r"\bespero\s+que\s+esta", re.IGNORECASE),
    ),
    (
        "prezado",
        re.compile(r"\bprezad[oa]\b", re.IGNORECASE),
    ),
    (
        "dia_semana_adjetivo",
        re.compile(
            r"\b(?:sexta|segunda|terça|quarta|quinta|sábado|domingo)\s+"
            r"(?:linda|chegou|abençoada|tranquila)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "bom_dia_sexta",
        re.compile(r"\bbom\s+dia.*sexta", re.IGNORECASE),
    ),
    (
        "range_dias",
        re.compile(r"\b\d+\s*[-–]\s*\d+\s+dias\b", re.IGNORECASE),
    ),
    (
        "percent_inventado",
        re.compile(
            r"\b(?:aumenta|aumentou|cresce|cresceu)\s+\d+\s*%",
            re.IGNORECASE,
        ),
    ),
    (
        "multiplicador_inventado",
        re.compile(r"\b\d+\s*x\s+(?:mais|menos)\b", re.IGNORECASE),
    ),
    ("calculo_hipotetico", re.compile(r"\bse\s+\d+\s*%", re.IGNORECASE)),
]


# ---------------------------------------------------------------------------
# Placeholder detection
# ---------------------------------------------------------------------------

# X{2,}             → unsubstituted XXXX runs
# \[[^\]]*\]        → [Nome], [empresa], …
# \{[^}]*\}         → {nome}, {empresa}, …
# TODO              → literal TODO marker
# PLACEHOLDER       → literal placeholder marker
_PLACEHOLDER_RE = re.compile(
    r"X{2,}|\[[^\]]*\]|\{[^}]*\}|TODO|PLACEHOLDER",
    re.IGNORECASE,
)


def detect_placeholders(text: str) -> list[str]:
    """
    Find unsubstituted placeholders in `text`.

    Detects (case-insensitive):
      - XX, XXX, XXXX… runs (e.g. phone "99606-XXXX")
      - [bracketed] tokens (e.g. "[Nome]", "[empresa]")
      - {braced} tokens (e.g. "{nome}")
      - The literal markers "TODO" and "PLACEHOLDER"

    Returns the list of raw matches (in original casing). Empty list = clean.
    """
    if not text:
        return []
    return _PLACEHOLDER_RE.findall(text)


# ---------------------------------------------------------------------------
# Fixers (deterministic, pure)
# ---------------------------------------------------------------------------

# Period followed by an alphabetic letter (lowercase or uppercase, incl. accented)
# → likely missing space (the '.achei' / '.Achei' LLM bug).
#
# URL-preservation: the negative lookahead `(?![a-záéíóúâêôãõçA-Záéíóúâêôãõç]+/)`
# ensures we DO NOT split inside domain-like fragments such as `wa.me/...`,
# where the alphabetic chars after the period are followed by `/` (with no
# intervening whitespace). This is critical because `wa.me/...` is the primary
# URL emitted by the outreach generator.
#
# Decimals ("R$1.500") are already safe because we only match alphabetic chars
# after the period — digits don't fire the rule.
_PUNCT_GLUE_RE = re.compile(
    r"\.(?=[a-záéíóúâêôãõçA-Záéíóúâêôãõç])"
    r"(?![a-záéíóúâêôãõçA-Záéíóúâêôãõç]+/)"
)

# Lowercase letter (possibly accented) at the start of a sentence after period+space.
# We look for ". x" or ".\nx" / multiple spaces, and uppercase the first char.
_AFTER_PERIOD_RE = re.compile(r"(\.\s+)([a-záéíóúâêôãõç])")


def fix_punctuation_spacing(text: str) -> str:
    """
    Insert a space after '.' when it's immediately followed by an alphabetic
    letter (covers the '.achei' / '.Achei' bug LLMs produce when merging
    sentences without spacing).

    Caveats / behaviour:
      - We only match alphabetic letters after the period; digits ("R$1.500")
        and other punctuation are left untouched, so decimals are safe.
      - URLs of the `wa.me/...` shape (and any other `<letters>.<letters>/`
        domain fragment) are preserved via a negative lookahead in
        `_PUNCT_GLUE_RE`. This is required because `wa.me/...` is THE
        primary URL emitted by the outreach module.
      - Trade-off: a hypothetical sentence-internal `.End/` would also be
        skipped (treated as URL-ish). Acceptable — real prose never produces
        that pattern.
    """
    if not text:
        return text
    return _PUNCT_GLUE_RE.sub(". ", text)


def _upper_first_alpha(s: str) -> str:
    """Uppercase the first alphabetic char in `s`, preserving leading whitespace."""
    for i, ch in enumerate(s):
        if ch.isalpha():
            return s[:i] + ch.upper() + s[i + 1 :]
    return s


def fix_capitalization(text: str) -> str:
    """
    Uppercase the first letter of the message and the first letter after every
    period+space combo.

    Rules:
      - Empty / whitespace-only string → unchanged.
      - Existing uppercase letters are preserved.
      - We ONLY uppercase when the period is followed by whitespace + a
        lowercase alphabetic letter — this avoids touching URLs ("wa.me/x")
        and decimals ("R$1.500") because neither has whitespace after the
        period.
    """
    if not text or not text.strip():
        return text

    # 1) First alpha char of the whole message.
    out = _upper_first_alpha(text)

    # 2) After period+space: uppercase the next lowercase letter.
    def _repl(m: re.Match[str]) -> str:
        return m.group(1) + m.group(2).upper()

    out = _AFTER_PERIOD_RE.sub(_repl, out)
    return out


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

_SENTENCE_PUNCT_RE = re.compile(r"[.?!]")


# ---------------------------------------------------------------------------
# AI cliché soft detector (PR3.3)
#
# Soft signals (NOT in validate_hard). Caller decides whether to reject based
# on count (current policy: 2+ matches → reject, 0-1 tolerated).
#
# Opening patterns ("notei que", "vi que vocês") use ^ + re.MULTILINE so they
# match at the start of ANY line. Message bodies are short (~5-8 lines max),
# and any line-start "notei que" is a clichê signature in practice.
# ---------------------------------------------------------------------------

_AI_CLICHE_PATTERNS = [
    ("achei_curioso", re.compile(r"\bachei\s+curios[oa]\b", re.IGNORECASE)),
    ("espero_tudo_bem", re.compile(r"\bespero\s+que\s+esteja\s+tudo\s+bem\b", re.IGNORECASE)),
    ("notei_que_abertura", re.compile(r"^[^.!?\n]*\bnotei\s+que\b", re.IGNORECASE | re.MULTILINE)),
    ("vi_que_voces_abertura", re.compile(r"^\s*vi\s+que\s+voc[eê]s\b", re.IGNORECASE | re.MULTILINE)),
    ("faz_sentido_conversarmos_x_min", re.compile(r"\bfaz\s+sentido\s+conversarmos\s+\d+\s*min", re.IGNORECASE)),
]


def detect_ai_cliches(text: str) -> list[str]:
    """Return list of cliché labels found (with 'cliche:' prefix).

    Soft signal — caller decides whether to reject.
    """
    if not text:
        return []
    return [f"cliche:{label}" for label, pat in _AI_CLICHE_PATTERNS if pat.search(text)]


# ---------------------------------------------------------------------------
# Glossário + Compliance soft validators (PR4.2)
#
# Both run AFTER `validate_hard` + cliché detection. They consume per-nicho
# config from ``app.pipeline.outreach.config``:
#   - ``glossario_for(nicho)`` → {evitar: substituto} mapping (style guide).
#   - ``compliance_for(nicho)`` → {regulacao, bloqueantes, preferir} (regulatory).
#
# Substring match, case-insensitive — terms are short Portuguese phrases that
# need to be caught regardless of casing. Empty list means no config for that
# nicho (graceful no-op rather than KeyError).
# ---------------------------------------------------------------------------


def check_glossario(text: str, nicho: str) -> list[str]:
    """Return list of ``glossario:<term>`` codes for terms found in text.

    Substring search, case-insensitive. Returns ``[]`` if ``nicho`` has no
    glossario config (unknown / falsy).
    """
    if not text:
        return []
    terms = glossario_for(nicho)  # {evitar: substituto}
    if not terms:
        return []
    text_lower = text.lower()
    return [f"glossario:{term}" for term in terms if term.lower() in text_lower]


def check_compliance(text: str, nicho: str) -> list[str]:
    """Return list of ``compliance:<term>`` codes for ``bloqueantes`` found.

    Substring search, case-insensitive. Returns ``[]`` if ``nicho`` has no
    compliance config OR no ``bloqueantes`` list.
    """
    if not text:
        return []
    cfg = compliance_for(nicho)
    bloqueantes = cfg.get("bloqueantes", [])
    if not bloqueantes:
        return []
    text_lower = text.lower()
    return [f"compliance:{term}" for term in bloqueantes if term.lower() in text_lower]


# ---------------------------------------------------------------------------
# Negative review salvaguarda (PR4.2)
#
# Heuristic detection — case-insensitive substring of explicit negative
# markers. "mal" alone is too broad (matches "normal", "mal-"-anything that
# isn't actually negative), so we require compound markers ("mal educad",
# "mal-educad") or distinct words ("ruim", "péssimo", "horrível").
#
# When detected, ``wrap_negative_review`` swaps the original text for a neutral
# framing so the LLM never sees the raw negative review (and can't quote it).
# ---------------------------------------------------------------------------


_NEGATIVE_REVIEW_MARKERS = (
    "ruim", "péssimo", "péssima", "pessimo", "pessima",
    "horrível", "horrivel", "horrendo", "decepcionante",
    "grosseir",  # grosseiro, grosseira, grosseiros, grosseiras
    "mal educad",  # mal educado(s), mal educada(s)
    "mal-educad",
    "descaso", "demorou", "atraso",
    "não recomendo", "nao recomendo",
    "perdi tempo", "perda de tempo",
    "experiência ruim", "experiencia ruim",
)

_NEUTRAL_REVIEW_FRAMING = (
    "vi que apareceu uma avaliação no Google que pode não refletir o trabalho de vocês"
)


def is_review_negative(review_text: str) -> bool:
    """Return True if the review text contains any negative marker.

    Case-insensitive substring search. Compound markers (e.g. ``"mal educad"``)
    intentionally avoid the "mal" / "normal" overreach.
    """
    if not review_text:
        return False
    lower = review_text.lower()
    return any(marker in lower for marker in _NEGATIVE_REVIEW_MARKERS)


def wrap_negative_review(review_text: str) -> str:
    """Replace a negative review with a neutral framing; passthrough otherwise.

    If ``is_review_negative(review_text)`` is True, return the neutral framing
    string. Otherwise return ``review_text`` unchanged.
    """
    if is_review_negative(review_text):
        return _NEUTRAL_REVIEW_FRAMING
    return review_text


def validate_hard(text: str, msg_type: str) -> ValidationResult:
    """
    Run all hard validators in order and return a ValidationResult collecting
    EVERY error (does not short-circuit).

    Order of checks (each independent):
      1. placeholder detection      → "placeholder:<match>"
      2. min length per msg_type    → "too_short:<n><min>"
      3. sentence punctuation       → "no_sentence_punctuation"
      4. forbidden patterns         → "forbidden:<label>"

    `passed` is True iff `errors` is empty.
    """
    errors: list[str] = []
    safe = text or ""
    text_clean = safe.strip()

    # 1) Placeholders
    for match in detect_placeholders(text_clean):
        errors.append(f"placeholder:{match}")

    # 2) Min length
    min_len = _MIN_LENGTHS.get(msg_type, _DEFAULT_MIN_LENGTH)
    if len(text_clean) < min_len:
        errors.append(f"too_short:{len(text_clean)}<{min_len}")

    # 3) Sentence punctuation
    if not _SENTENCE_PUNCT_RE.search(text_clean):
        errors.append("no_sentence_punctuation")

    # 4) Forbidden patterns
    for label, pattern in _FORBIDDEN_PATTERNS:
        if pattern.search(text_clean):
            errors.append(f"forbidden:{label}")

    return ValidationResult(passed=not errors, errors=errors)


__all__ = [
    "ValidationResult",
    "check_compliance",
    "check_glossario",
    "detect_ai_cliches",
    "detect_placeholders",
    "fix_capitalization",
    "fix_punctuation_spacing",
    "is_review_negative",
    "validate_hard",
    "wrap_negative_review",
]
