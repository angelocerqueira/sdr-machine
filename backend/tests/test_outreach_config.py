"""Tests for app.pipeline.outreach.config (PR2.1 + PR4.1)."""

from __future__ import annotations

import re

from app.pipeline.outreach.config import (
    cases_for,
    compliance_for,
    ctas_for,
    glossario_for,
    load_angulos,
    load_cases,
    load_compliance,
    load_ctas,
    load_glossario,
)

_SNAKE_CASE = re.compile(r"^[a-z][a-z0-9_]*$")

_EXPECTED_NICHOS = {
    "advocacia",
    "medicina",
    "odontologia",
    "contabilidade",
    "arquitetura",
    "engenharia",
}


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


# --- PR4.1: glossario / compliance / cases ---------------------------------


def test_load_glossario_returns_six_nicho_keys() -> None:
    assert set(load_glossario().keys()) == _EXPECTED_NICHOS


def test_load_compliance_returns_six_nicho_keys() -> None:
    assert set(load_compliance().keys()) == _EXPECTED_NICHOS


def test_load_cases_returns_six_nicho_keys() -> None:
    assert set(load_cases().keys()) == _EXPECTED_NICHOS


def test_glossario_for_advocacia_contains_captacao_de_clientes() -> None:
    mapping = glossario_for("advocacia")
    assert isinstance(mapping, dict)
    assert "captação de clientes" in mapping


def test_glossario_for_unknown_returns_empty_dict() -> None:
    assert glossario_for("unknown") == {}
    assert glossario_for("") == {}


def test_compliance_for_medicina_has_cfm_and_garantia_de_resultado() -> None:
    cfg = compliance_for("medicina")
    assert "CFM" in cfg["regulacao"]
    assert "garantia de resultado" in cfg["bloqueantes"]


def test_compliance_for_unknown_returns_empty_dict() -> None:
    assert compliance_for("unknown") == {}
    assert compliance_for("") == {}


def test_cases_for_odontologia_has_at_least_one_with_descricao() -> None:
    cases = cases_for("odontologia")
    assert isinstance(cases, list)
    assert len(cases) >= 1
    assert "descricao" in cases[0]


def test_cases_for_unknown_returns_empty_list() -> None:
    assert cases_for("unknown") == []
    assert cases_for("") == []


def test_load_glossario_is_cached() -> None:
    assert load_glossario() is load_glossario()
