from unittest.mock import patch
from app.pipeline.cnpj_lookup import niche_to_cnaes, city_to_ibge


def test_exact_niche_match():
    assert "8630504" in niche_to_cnaes("dentista")


def test_partial_niche_match():
    codes = niche_to_cnaes("clínica odontológica")
    assert len(codes) > 0


def test_unknown_niche_returns_empty():
    assert niche_to_cnaes("submarino nuclear") == []


def test_niche_case_insensitive():
    assert niche_to_cnaes("DENTISTA") == niche_to_cnaes("dentista")


def test_city_with_uf_resolves():
    municipios_sc = [
        {"nome": "Chapecó", "codigo_ibge": 4204202},
        {"nome": "Florianópolis", "codigo_ibge": 4205407},
    ]
    with patch("app.pipeline.cnpj_lookup._get_municipalities", return_value=municipios_sc):
        result = city_to_ibge("Chapecó SC")
    assert result == ("4204202", "SC")


def test_city_accent_insensitive():
    municipios_sc = [{"nome": "Chapecó", "codigo_ibge": 4204202}]
    with patch("app.pipeline.cnpj_lookup._get_municipalities", return_value=municipios_sc):
        result = city_to_ibge("Chapeco SC")
    assert result is not None
    assert result[0] == "4204202"


def test_unknown_city_returns_none():
    with patch("app.pipeline.cnpj_lookup._get_municipalities", return_value=[]):
        result = city_to_ibge("Cidade Inexistente XY")
    assert result is None


def test_brasilapi_failure_returns_none():
    with patch("app.pipeline.cnpj_lookup._get_municipalities", return_value=None):
        result = city_to_ibge("Chapecó SC")
    assert result is None
