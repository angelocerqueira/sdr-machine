"""Tests for app.pipeline.outreach.config (PR2.1)."""

from __future__ import annotations

import re

from app.pipeline.outreach.config import ctas_for, load_angulos, load_ctas

_SNAKE_CASE = re.compile(r"^[a-z][a-z0-9_]*$")


def test_load_angulos_returns_seven_snake_case_string_entries() -> None:
    angulos = load_angulos()
    assert len(angulos) == 7
    for key, value in angulos.items():
        assert _SNAKE_CASE.match(key), f"angulo key not snake_case: {key!r}"
        assert isinstance(value, str)
        assert value, f"angulo {key!r} has empty label"


def test_load_ctas_has_five_cadence_keys() -> None:
    ctas = load_ctas()
    assert set(ctas.keys()) == {
        "initial",
        "bump_d2",
        "insight_d5",
        "angle_d9",
        "breakup_d14",
    }


def test_ctas_for_initial_returns_four_entries() -> None:
    assert len(ctas_for("initial")) == 4


def test_ctas_for_bump_d2_returns_two_entries() -> None:
    assert len(ctas_for("bump_d2")) == 2


def test_ctas_for_unknown_returns_empty_list() -> None:
    assert ctas_for("unknown") == []
    assert ctas_for("") == []


def test_load_angulos_is_cached() -> None:
    assert load_angulos() is load_angulos()


def test_load_ctas_is_cached() -> None:
    assert load_ctas() is load_ctas()
