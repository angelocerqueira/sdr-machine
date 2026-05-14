"""Outreach config loader (angulos + CTAs).

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


__all__ = ["load_angulos", "load_ctas", "ctas_for"]
