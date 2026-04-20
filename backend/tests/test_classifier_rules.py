from app.pipeline.enrichment.classifier_enums import LeadProfile, NichoCanonico
from app.pipeline.enrichment.classifier_rules import (
    NICHO_ALIASES, PROFILE_THRESHOLDS, PROFILE_TO_DERIVED, fuzzy_match_nicho,
)


def test_aliases_cover_all_15_buckets():
    assert set(NICHO_ALIASES.keys()) == {n for n in NichoCanonico if n != NichoCanonico.OUTROS}


def test_fuzzy_match_obvious_cases():
    assert fuzzy_match_nicho("Dentist") == (NichoCanonico.DENTISTA, 1.0)
    assert fuzzy_match_nicho("Clinica Odontologica Dr Silva") == (NichoCanonico.DENTISTA, 1.0)
    assert fuzzy_match_nicho("Pizzaria da Nonna") == (NichoCanonico.RESTAURANTE, 1.0)


def test_fuzzy_match_misspelled_uses_ratio_path():
    # "akademia" contains no alias substring; ratio vs "academia" is ~0.88
    result = fuzzy_match_nicho("akademia")
    assert result is not None
    bucket, conf = result
    assert bucket == NichoCanonico.ACADEMIA
    assert 0.75 <= conf < 1.0  # ratio path, not exact-substring


def test_fuzzy_match_returns_none_when_no_match():
    assert fuzzy_match_nicho("Consultoria de Fusões e Aquisições") is None


def test_fuzzy_match_handles_empty():
    assert fuzzy_match_nicho("") is None
    assert fuzzy_match_nicho(None) is None


def test_profile_thresholds_keys():
    assert "hot_no_site_min_rating" in PROFILE_THRESHOLDS
    assert "hot_no_site_min_reviews" in PROFILE_THRESHOLDS
    assert "hot_bad_site_min_score" in PROFILE_THRESHOLDS
    assert "cold_max_score" in PROFILE_THRESHOLDS
    assert "disqualified_min_rating" in PROFILE_THRESHOLDS


def test_profile_to_derived_complete():
    for profile in LeadProfile:
        assert profile in PROFILE_TO_DERIVED
        pacote, prioridade = PROFILE_TO_DERIVED[profile]
        assert pacote is not None
        assert prioridade is not None
