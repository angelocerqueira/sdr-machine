from unittest.mock import patch, MagicMock
from app.pipeline.cnpj_scraper import scrape_cnpj, _build_lead, _search_minhareceita


# ── _build_lead ───────────────────────────────────────────────────────────────

def test_build_lead_active_company():
    company = {
        "cnpj": "00000000000100",
        "razao_social": "CLINICA TESTE LTDA",
        "nome_fantasia": "Clínica Teste",
        "situacao_cadastral": "ATIVA",
        "cnae_fiscal_descricao": "Atividades de odontologia",
        "ddd_telefone_1": "49",
        "telefone_1": "33334444",
        "email": "contato@clinicateste.com.br",
        "website": "https://clinicateste.com.br",
        "logradouro": "Rua das Flores",
        "numero": "100",
        "complemento": "",
        "bairro": "Centro",
    }
    lead = _build_lead(company, "dentista", "Chapecó SC")
    assert lead is not None
    assert lead["nome"] == "Clínica Teste"
    assert lead["telefone"] == "4933334444"
    assert lead["cnpj"] == "00000000000100"
    assert lead["cidade"] == "Chapecó SC"
    assert lead["fonte"] == "cnpj"


def test_build_lead_inactive_returns_none():
    company = {
        "cnpj": "00000000000100",
        "razao_social": "EMPRESA BAIXADA LTDA",
        "situacao_cadastral": "BAIXADA",
    }
    assert _build_lead(company, "dentista", "SP") is None


def test_build_lead_no_nome_fantasia_uses_razao_social():
    company = {
        "cnpj": "00000000000200",
        "razao_social": "EMPRESA SEM FANTASIA LTDA",
        "nome_fantasia": "",
        "situacao_cadastral": "ATIVA",
        "ddd_telefone_1": "",
        "telefone_1": "",
    }
    lead = _build_lead(company, "restaurante", "SP")
    assert lead is not None
    assert "Empresa Sem Fantasia" in lead["nome"]


def test_build_lead_no_phone_is_none():
    company = {
        "cnpj": "00000000000300",
        "razao_social": "SEM TELEFONE LTDA",
        "situacao_cadastral": "ATIVA",
        "ddd_telefone_1": None,
        "telefone_1": None,
    }
    lead = _build_lead(company, "academia", "RJ")
    assert lead is not None
    assert lead["telefone"] is None


# ── scrape_cnpj resilience ────────────────────────────────────────────────────

def test_scrape_cnpj_unknown_niche_returns_empty():
    result = scrape_cnpj("nicho_inexistente_xyz", "São Paulo SP", 10)
    assert result == []


def test_scrape_cnpj_unknown_city_returns_empty():
    with patch("app.pipeline.cnpj_scraper.city_to_ibge", return_value=None):
        result = scrape_cnpj("dentista", "Cidade Inexistente XY", 10)
    assert result == []


def test_scrape_cnpj_minhareceita_error_returns_empty():
    with patch("app.pipeline.cnpj_scraper.city_to_ibge", return_value=("4204202", "SC")):
        with patch("app.pipeline.cnpj_scraper._search_minhareceita", side_effect=Exception("timeout")):
            result = scrape_cnpj("dentista", "Chapecó SC", 10)
    assert result == []  # resilient: error logged, empty list returned


def test_scrape_cnpj_deduplicates_by_cnpj():
    dup_company = {
        "cnpj": "00000000000100",
        "razao_social": "CLINICA LTDA",
        "situacao_cadastral": "ATIVA",
        "ddd_telefone_1": "49",
        "telefone_1": "33334444",
    }
    with patch("app.pipeline.cnpj_scraper.city_to_ibge", return_value=("4204202", "SC")):
        # MinhaReceita returns the same company twice (two CNAE queries)
        with patch("app.pipeline.cnpj_scraper._search_minhareceita", return_value=[dup_company, dup_company]):
            result = scrape_cnpj("clinica", "Chapecó SC", 10)
    assert len(result) == 1


def test_scrape_cnpj_filters_inactive():
    companies = [
        {"cnpj": "00000000000101", "razao_social": "ATIVA LTDA", "situacao_cadastral": "ATIVA",
         "ddd_telefone_1": "49", "telefone_1": "11111111"},
        {"cnpj": "00000000000102", "razao_social": "BAIXADA LTDA", "situacao_cadastral": "BAIXADA",
         "ddd_telefone_1": "49", "telefone_1": "22222222"},
    ]
    with patch("app.pipeline.cnpj_scraper.city_to_ibge", return_value=("4204202", "SC")):
        with patch("app.pipeline.cnpj_scraper._search_minhareceita", return_value=companies):
            result = scrape_cnpj("dentista", "Chapecó SC", 10)
    assert len(result) == 1
    assert result[0]["cnpj"] == "00000000000101"


def test_scrape_cnpj_respects_max_results():
    companies = [
        {"cnpj": f"0000000000{i:04d}", "razao_social": f"EMPRESA {i} LTDA",
         "situacao_cadastral": "ATIVA", "ddd_telefone_1": "49", "telefone_1": f"3333{i:04d}"}
        for i in range(1, 21)
    ]
    with patch("app.pipeline.cnpj_scraper.city_to_ibge", return_value=("4204202", "SC")):
        with patch("app.pipeline.cnpj_scraper._search_minhareceita", return_value=companies):
            result = scrape_cnpj("dentista", "Chapecó SC", max_results=5)
    assert len(result) <= 5
