from app.pipeline.enrichment.classifier_enums import (
    LeadProfile, NichoCanonico, NichoSource, PacoteSugerido, Prioridade,
)


def test_all_enums_are_string_enums():
    assert LeadProfile.HOT_NO_SITE.value == "hot_no_site"
    assert LeadProfile.HOT_BAD_SITE.value == "hot_bad_site"
    assert LeadProfile.WARM.value == "warm"
    assert LeadProfile.COLD.value == "cold"
    assert LeadProfile.DISQUALIFIED.value == "disqualified"


def test_nicho_canonico_has_15_buckets():
    assert len(list(NichoCanonico)) == 15
    assert NichoCanonico.OUTROS.value == "outros"


def test_nicho_source_values():
    expected = {"apify_category", "fuzzy_match", "llm_inferred", "manual", "failed"}
    assert {s.value for s in NichoSource} == expected


def test_pacote_sugerido_values():
    expected = {"essencial", "profissional", "premium", "skip"}
    assert {p.value for p in PacoteSugerido} == expected


def test_prioridade_values():
    expected = {"maxima", "alta", "media", "baixa", "pular"}
    assert {p.value for p in Prioridade} == expected
