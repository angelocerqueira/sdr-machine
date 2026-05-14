"""Tests for the tratamento_formal inference helpers (PR3.2).

Pure heuristic — no LLM, no DB. Lives module-level in
``app.pipeline.enrichment.providers.cnpj_enricher``.
"""
from __future__ import annotations

from app.pipeline.enrichment.providers.cnpj_enricher import (
    _extract_socio_names,
    _is_female_first_name,
    _is_regulated_nicho,
    infer_tratamento_formal,
)


# ---------------------------------------------------------------------------
# Decision matrix (rule #3 in the outreach quality spec)
# ---------------------------------------------------------------------------


def test_single_socio_male_advocacia_returns_dr():
    assert (
        infer_tratamento_formal("advocacia", None, [{"nome": "João Silva"}])
        == "Dr"
    )


def test_single_socio_female_advocacia_returns_dra():
    assert (
        infer_tratamento_formal("advocacia", None, [{"nome": "Maria Silva"}])
        == "Dra"
    )


def test_two_socios_returns_none():
    assert (
        infer_tratamento_formal(
            "advocacia", None, [{"nome": "A Silva"}, {"nome": "B Souza"}]
        )
        is None
    )


def test_not_regulated_nicho_returns_none():
    assert (
        infer_tratamento_formal(
            "restaurante", None, [{"nome": "Maria Silva"}]
        )
        is None
    )


def test_zero_socios_returns_none():
    assert infer_tratamento_formal("odontologia", None, []) is None


def test_unknown_first_name_defaults_to_dr():
    # "Lana" is not in our female list — heuristic defaults to Dr to avoid
    # false positives from -a ending names (e.g. Luca, Cassia ambiguity).
    assert (
        infer_tratamento_formal(
            "odontologia", None, [{"nome": "Lana Silva"}]
        )
        == "Dr"
    )


def test_nicho_canonico_match_enables_inference():
    # nicho is None but nicho_canonico is regulated.
    assert (
        infer_tratamento_formal(
            None, "dentista", [{"nome": "Fernanda Souza"}]
        )
        == "Dra"
    )


def test_no_nicho_returns_none():
    assert (
        infer_tratamento_formal(None, None, [{"nome": "Maria Silva"}])
        is None
    )


# ---------------------------------------------------------------------------
# Socio shape variants
# ---------------------------------------------------------------------------


def test_socio_as_plain_string():
    assert (
        infer_tratamento_formal("advocacia", None, ["João Silva"])
        == "Dr"
    )


def test_socio_with_english_name_key():
    assert (
        infer_tratamento_formal(
            "advocacia", None, [{"name": "Maria Silva"}]
        )
        == "Dra"
    )


def test_socio_with_razao_social_key():
    assert (
        infer_tratamento_formal(
            "medicina", None, [{"razao_social": "Patricia Lima"}]
        )
        == "Dra"
    )


def test_socio_with_descricao_key():
    assert (
        infer_tratamento_formal(
            "medicina", None, [{"descricao": "Joao Souza"}]
        )
        == "Dr"
    )


def test_empty_or_whitespace_name_is_ignored():
    socios = [{"nome": "   "}, {"nome": ""}, {"nome": "Maria"}]
    # Two ignored, only one valid → effectively single sócio → Dra.
    assert (
        infer_tratamento_formal("advocacia", None, socios) == "Dra"
    )


def test_mixed_socio_types_and_ignored_entries():
    # Non-string non-dict entries (e.g. None, ints) silently dropped.
    socios = [None, 42, {"nome": ""}, "Fernanda Souza"]
    assert (
        infer_tratamento_formal("odontologia", None, socios) == "Dra"
    )


def test_extract_socio_names_skips_empties_and_invalid_types():
    socios = [
        {"nome": "Alice"},
        {"nome": "  "},
        {"name": "Bob"},
        None,
        12345,
        "Carla",
    ]
    assert _extract_socio_names(socios) == ["Alice", "Bob", "Carla"]


# ---------------------------------------------------------------------------
# Helper edge cases
# ---------------------------------------------------------------------------


def test_is_regulated_nicho_case_insensitive():
    assert _is_regulated_nicho("Advocacia") is True
    assert _is_regulated_nicho("ODONTOLOGIA") is True
    assert _is_regulated_nicho("  Dentista  ") is True
    assert _is_regulated_nicho("padaria") is False
    assert _is_regulated_nicho(None, None) is False


def test_is_regulated_nicho_accent_variants():
    # Both "veterinaria" and "veterinária" are recognised.
    assert _is_regulated_nicho("veterinaria") is True
    assert _is_regulated_nicho("veterinária") is True


def test_is_regulated_via_either_nicho_or_canonico():
    assert _is_regulated_nicho(None, "psicologia") is True
    assert _is_regulated_nicho("padaria", "fisioterapia") is True
    assert _is_regulated_nicho("padaria", "salgaderia") is False


def test_is_female_first_name_uses_first_token_only():
    # Second token "Maria" doesn't matter — only first token counts.
    assert _is_female_first_name("João Maria") is False
    assert _is_female_first_name("Maria João") is True


def test_is_female_first_name_handles_accents():
    assert _is_female_first_name("Patrícia Souza") is True
    assert _is_female_first_name("Patricia Souza") is True
    assert _is_female_first_name("Mônica Lima") is True


def test_is_female_first_name_empty_or_unknown():
    assert _is_female_first_name("") is False
    assert _is_female_first_name("   ") is False
    assert _is_female_first_name("Roberto") is False
