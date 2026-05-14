"""Outreach config loader (angulos + CTAs + glossario + compliance + cases).

Pure config package: no LLM, no DB, no side effects. Loads JSON files
co-located in this directory and caches results module-wide via
``functools.lru_cache`` so tests can verify the cache by identity.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_CONFIG_DIR = Path(__file__).parent


def _load_json(filename: str) -> dict:
    path = _CONFIG_DIR / filename
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def load_angulos() -> dict[str, str]:
    """Return the angulos taxonomy (key -> human label)."""
    return _load_json("angulos.json")


@lru_cache(maxsize=1)
def load_ctas() -> dict[str, list[str]]:
    """Return the CTA pool keyed by cadence message type."""
    return _load_json("ctas.json")


def ctas_for(msg_type: str) -> list[str]:
    """Return the CTA pool for ``msg_type``, or ``[]`` if unknown."""
    return load_ctas().get(msg_type, [])


@lru_cache(maxsize=1)
def load_glossario() -> dict[str, dict]:
    """Return the glossario taxonomy keyed by nicho_canonico."""
    return _load_json("glossario_por_nicho.json")


@lru_cache(maxsize=1)
def load_compliance() -> dict[str, dict]:
    """Return the compliance taxonomy keyed by nicho_canonico."""
    return _load_json("compliance_por_nicho.json")


@lru_cache(maxsize=1)
def load_cases() -> dict[str, list[dict]]:
    """Return the anonymous cases keyed by nicho_canonico."""
    return _load_json("cases_por_nicho.json")


def glossario_for(nicho: str) -> dict[str, str]:
    """Return the 'evitar' mapping for the given nicho (lowercased), or {} if unknown."""
    cfg = load_glossario().get((nicho or "").strip().lower(), {})
    return cfg.get("evitar", {})


def compliance_for(nicho: str) -> dict:
    """Return compliance config {regulacao, bloqueantes, preferir} for the given nicho, or {}."""
    return load_compliance().get((nicho or "").strip().lower(), {})


def cases_for(nicho: str) -> list[dict]:
    """Return list of anonymous cases for the given nicho, or [] if no cases."""
    return load_cases().get((nicho or "").strip().lower(), [])


__all__ = [
    "load_angulos",
    "load_ctas",
    "ctas_for",
    "load_glossario",
    "load_compliance",
    "load_cases",
    "glossario_for",
    "compliance_for",
    "cases_for",
]
