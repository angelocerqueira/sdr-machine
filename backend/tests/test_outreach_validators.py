"""Tests for backend/app/pipeline/outreach/validators.py (PR1.2)."""

from app.pipeline.outreach.validators import (
    ValidationResult,
    detect_placeholders,
    fix_capitalization,
    fix_punctuation_spacing,
    validate_hard,
)


# ---------------------------------------------------------------------------
# detect_placeholders
# ---------------------------------------------------------------------------

class TestDetectPlaceholders:
    def test_finds_xxxx_run(self):
        assert "XXXX" in detect_placeholders("(51) 99606-XXXX")

    def test_finds_bracketed_placeholder(self):
        assert "[Nome]" in detect_placeholders("Oi [Nome]")

    def test_finds_braced_placeholder(self):
        assert "{empresa}" in detect_placeholders("olá {empresa}")

    def test_finds_todo(self):
        assert "TODO" in detect_placeholders("TODO: finalizar")

    def test_clean_text_returns_empty(self):
        assert detect_placeholders("texto limpo") == []

    def test_placeholder_word_case_insensitive(self):
        # The literal word "placeholder" (case-insensitive)
        matches = detect_placeholders("placeholder aqui")
        assert any(m.lower() == "placeholder" for m in matches)

    def test_uppercase_placeholder_word(self):
        matches = detect_placeholders("PLACEHOLDER no meio")
        assert any(m.upper() == "PLACEHOLDER" for m in matches)

    def test_mixed_case_todo(self):
        matches = detect_placeholders("Todo: implementar")
        assert any(m.upper() == "TODO" for m in matches)

    def test_finds_multiple_placeholders(self):
        matches = detect_placeholders("[nome] e {empresa} TODO XXXX")
        # Expect at least 4 separate detections
        assert len(matches) >= 4

    def test_single_x_not_match(self):
        # "X" alone (not 2+) should not match the XXXX rule
        # (other rules also shouldn't fire on plain text without brackets etc.)
        assert detect_placeholders("um X solitário") == []


# ---------------------------------------------------------------------------
# fix_capitalization
# ---------------------------------------------------------------------------

class TestFixCapitalization:
    def test_uppercases_first_letter(self):
        assert fix_capitalization("oi tudo bem") == "Oi tudo bem"

    def test_uppercases_after_period_space(self):
        assert fix_capitalization("olá mundo. tudo certo.") == "Olá mundo. Tudo certo."

    def test_already_capitalized_unchanged(self):
        assert fix_capitalization("Já capitalizado") == "Já capitalizado"

    def test_empty_string(self):
        assert fix_capitalization("") == ""

    def test_whitespace_only_unchanged(self):
        assert fix_capitalization("   ") == "   "

    def test_does_not_uppercase_inside_url(self):
        # "wa.me/123" — period not followed by space, should not trigger
        # (and even if it did, the next char is a digit, not lowercase)
        out = fix_capitalization("link wa.me/123 aqui")
        assert "wa.me/123" in out

    def test_does_not_uppercase_decimal(self):
        # "R$1.500" — period not followed by space
        out = fix_capitalization("custou R$1.500 reais")
        assert "R$1.500" in out

    def test_multiple_sentences(self):
        result = fix_capitalization("primeiro. segundo. terceiro.")
        assert result == "Primeiro. Segundo. Terceiro."

    def test_accented_first_letter(self):
        # First letter accented should still get uppercased
        result = fix_capitalization("ótimo trabalho")
        # Python's str.upper() handles unicode
        assert result[0] == "Ó"


# ---------------------------------------------------------------------------
# fix_punctuation_spacing
# ---------------------------------------------------------------------------

class TestFixPunctuationSpacing:
    def test_inserts_space_after_period(self):
        assert fix_punctuation_spacing("olá.tudo bem") == "olá. tudo bem"

    def test_already_spaced_unchanged(self):
        assert fix_punctuation_spacing("olá. tudo bem") == "olá. tudo bem"

    def test_decimal_unchanged(self):
        assert fix_punctuation_spacing("R$1.500") == "R$1.500"

    def test_multiple_glued_sentences(self):
        result = fix_punctuation_spacing("uma.outra.terceira")
        assert result == "uma. outra. terceira"

    def test_period_then_uppercase_also_gets_space(self):
        # Common LLM bug: ".Achei" (period followed by capital)
        assert fix_punctuation_spacing("bom.Achei") == "bom. Achei"

    def test_accented_letter_after_period(self):
        assert fix_punctuation_spacing("oi.ótimo") == "oi. ótimo"

    def test_period_at_end_unchanged(self):
        # Period at the very end (no following char) should not break
        assert fix_punctuation_spacing("final.") == "final."

    def test_wa_me_url_unchanged(self):
        # wa.me is the primary URL emitted by the outreach module — must NOT
        # be split by punctuation glue ('manda no wa. me/5551999' would break
        # the link).
        assert (
            fix_punctuation_spacing("manda no wa.me/5551999")
            == "manda no wa.me/5551999"
        )

    def test_wa_me_after_space_unchanged(self):
        # Full https://wa.me/... URL surrounded by spaces, with a trailing
        # sentence-final period (period followed by nothing — also untouched).
        assert (
            fix_punctuation_spacing("acesse https://wa.me/123 hoje.")
            == "acesse https://wa.me/123 hoje."
        )


# ---------------------------------------------------------------------------
# validate_hard
# ---------------------------------------------------------------------------

class TestValidateHard:
    def test_placeholder_fails(self):
        result = validate_hard(
            "Oi João, ligamos pro (51) 99606-XXXX mas não atendeu. Podemos conversar?",
            "initial",
        )
        assert isinstance(result, ValidationResult)
        assert result.passed is False
        assert any(e.startswith("placeholder:") for e in result.errors)

    def test_too_short_for_initial(self):
        # 50 chars, well below 180 min for "initial"
        text = "Oi! Achei seu site e queria conversar com você."
        result = validate_hard(text, "initial")
        assert result.passed is False
        assert any(
            e.startswith("too_short:") and "180" in e
            for e in result.errors
        )

    def test_too_short_explicit_format(self):
        # 50 chars exactly
        text = "x" * 50 + "."  # 51 chars, with punctuation
        result = validate_hard(text, "initial")
        assert any("too_short:51<180" in e for e in result.errors)

    def test_no_sentence_punctuation(self):
        # No . ? !
        text = "Olá tudo bem com sua loja " + ("a" * 200)
        result = validate_hard(text, "initial")
        assert result.passed is False
        assert "no_sentence_punctuation" in result.errors

    def test_forbidden_pattern_clima(self):
        text = (
            "Oi, bom dia. Tá gelado aí? "
            "Queria conversar sobre seu site, vi que está com alguns gaps "
            "que podem estar custando leads. Topa uma análise rápida sem compromisso?"
        )
        result = validate_hard(text, "initial")
        assert result.passed is False
        assert any(e.startswith("forbidden:") for e in result.errors)

    def test_forbidden_pattern_tudo_bem(self):
        text = (
            "Oi João, tudo bem com você? "
            "Passando aqui pra falar sobre o site da sua empresa. "
            "Achei alguns pontos que podem estar travando conversão. Topa conversar?"
        )
        result = validate_hard(text, "initial")
        assert result.passed is False
        assert any(e.startswith("forbidden:") for e in result.errors)

    def test_multiple_errors_collected(self):
        # Short + placeholder + no punctuation
        text = "Oi [Nome] XXXX"  # short, has placeholders, no . ? !
        result = validate_hard(text, "initial")
        assert result.passed is False
        # Expect at least 3 distinct errors: placeholder(s), too_short, no_sentence_punctuation
        assert any(e.startswith("placeholder:") for e in result.errors)
        assert any(e.startswith("too_short:") for e in result.errors)
        assert "no_sentence_punctuation" in result.errors

    def test_clean_initial_passes(self):
        # ≥180 chars, has period, no placeholders, no forbidden patterns
        text = (
            "Oi João, vi a página da sua clínica no Google e reparei que "
            "ela está sem HTTPS e o site não abre direito no celular. "
            "Faço um diagnóstico rápido e sem compromisso, se topar te mando aqui."
        )
        assert len(text) >= 180
        result = validate_hard(text, "initial")
        assert result.passed is True, f"unexpected errors: {result.errors}"
        assert result.errors == []

    def test_unknown_msg_type_uses_default_60(self):
        # 50 chars, unknown type → min becomes 60
        text = "x" * 50 + "."  # 51 chars, has punctuation
        result = validate_hard(text, "weird_type")
        assert any("too_short:51<60" in e for e in result.errors)

    def test_short_type_bump_d2_passes_when_above_min(self):
        # bump_d2 min is 25 — short message that fits
        text = "Oi, ainda faz sentido conversar?"  # >25 chars with punctuation
        assert len(text) >= 25
        result = validate_hard(text, "bump_d2")
        assert result.passed is True, f"unexpected errors: {result.errors}"

    def test_validation_result_is_dataclass(self):
        result = validate_hard("texto limpo demais.", "bump_d2")
        # dataclass exposes fields directly
        assert hasattr(result, "passed")
        assert hasattr(result, "errors")
        assert isinstance(result.errors, list)

    def test_calculo_hipotetico_blocks_hypothetical_percentage(self):
        text = "Oi! Olhei o site da Odonto Sorriso. Se 10% dos seus leads do Google fechassem, seriam 5 clientes a mais por mês. " * 3  # pad to min_length
        result = validate_hard(text, "initial")
        assert not result.passed
        assert any(err == "forbidden:calculo_hipotetico" for err in result.errors)

    def test_calculo_hipotetico_does_not_block_real_data(self):
        # "123 avaliações" doesn't match \bse\s+\d+\s*%
        text = "Oi! Vi a Odonto Sorriso no Google com 123 avaliações e rating 4.7 estrelas — presença local clara. " * 4
        result = validate_hard(text, "initial")
        # might fail OTHER hard validators, but NOT calculo_hipotetico
        assert not any(err == "forbidden:calculo_hipotetico" for err in result.errors)
