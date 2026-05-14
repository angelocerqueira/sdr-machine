"""Tests for CnpjProvider."""
from unittest.mock import patch, MagicMock

from app.pipeline.enrichment.base_provider import EnrichmentContext
from app.pipeline.enrichment.providers.cnpj_enricher import CnpjProvider


class FakeLead:
    def __init__(
        self,
        cnpj=None,
        nome="Test",
        cidade=None,
        website=None,
        nicho=None,
        nicho_canonico=None,
        tratamento_formal=None,
    ):
        self.cnpj = cnpj
        self.nome = nome
        self.cidade = cidade
        self.website = website
        self.nicho = nicho
        self.nicho_canonico = nicho_canonico
        self.tratamento_formal = tratamento_formal


def test_can_run_with_cnpj():
    provider = CnpjProvider()
    assert provider.can_run(FakeLead(cnpj="12.345.678/0001-90")) is True


def test_cannot_run_without_cnpj():
    provider = CnpjProvider()
    assert provider.can_run(FakeLead(nome="Clinica XYZ", cidade="Chapeco SC")) is False
    assert provider.can_run(FakeLead(nome="", cidade=None)) is False


@patch("app.pipeline.enrichment.providers.cnpj_enricher.requests.get")
def test_enrich_from_cnpj(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "razao_social": "CLINICA XYZ LTDA",
        "nome_fantasia": "Clinica XYZ",
        "cnae_fiscal_descricao": "Atividades odontologicas",
        "porte": "ME",
        "data_inicio_atividade": "2018-05-10",
        "qsa": [{"nome_socio": "Fulano da Silva"}],
        "logradouro": "RUA X",
        "numero": "100",
        "municipio": "CHAPECO",
    }
    mock_get.return_value = mock_resp

    provider = CnpjProvider()
    lead = FakeLead(cnpj="12345678000190")
    ctx = EnrichmentContext()
    result = provider.run(lead, ctx)

    assert result.success is True
    assert result.data["razao_social"] == "CLINICA XYZ LTDA"
    assert result.data["porte"] == "ME"
    assert "Atividades odontologicas" in (result.data.get("cnae") or "")
    assert result.data["socios"] == [{"nome": "Fulano da Silva"}]


@patch("app.pipeline.enrichment.providers.cnpj_enricher.requests.get")
def test_handles_cnpj_not_found(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_get.return_value = mock_resp

    provider = CnpjProvider()
    lead = FakeLead(cnpj="99999999999999")
    ctx = EnrichmentContext()
    result = provider.run(lead, ctx)

    assert result.success is False
    assert result.data == {}


# --- EC4: CNPJ accepts masked and unmasked ---

@patch("app.pipeline.enrichment.providers.cnpj_enricher.requests.get")
def test_accepts_masked_cnpj(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"razao_social": "ACME LTDA"}
    mock_get.return_value = mock_resp

    provider = CnpjProvider()
    lead = FakeLead(cnpj="12.345.678/0001-90")
    result = provider.run(lead, EnrichmentContext())

    called_url = mock_get.call_args[0][0]
    assert "12345678000190" in called_url
    assert result.success is True


# --- EC15: BrasilAPI 200 with empty body ---

@patch("app.pipeline.enrichment.providers.cnpj_enricher.requests.get")
def test_handles_empty_body(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {}
    mock_get.return_value = mock_resp

    provider = CnpjProvider()
    lead = FakeLead(cnpj="12345678000190")
    result = provider.run(lead, EnrichmentContext())
    assert result.success is True
    assert result.data == {}


# --- EC18: CNPJ timeout ---

@patch("app.pipeline.enrichment.providers.cnpj_enricher.requests.get")
def test_handles_timeout(mock_get):
    import requests
    mock_get.side_effect = requests.exceptions.Timeout("slow")
    provider = CnpjProvider()
    result = provider.run(FakeLead(cnpj="12345678000190"), EnrichmentContext())
    assert result.success is False
    assert any("error" in e.lower() or "timeout" in e.lower() for e in result.errors)


# --- PR3.2: tratamento_formal inference inside CnpjProvider.run ---

@patch("app.pipeline.enrichment.providers.cnpj_enricher.requests.get")
def test_run_infers_tratamento_formal_for_regulated_single_socio(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "razao_social": "ESCRITORIO ADV LTDA",
        "qsa": [{"nome_socio": "Maria Silva"}],
    }
    mock_get.return_value = mock_resp

    provider = CnpjProvider()
    lead = FakeLead(cnpj="12345678000190", nicho="advocacia")
    result = provider.run(lead, EnrichmentContext())

    assert result.success is True
    assert result.data.get("tratamento_formal") == "Dra"


@patch("app.pipeline.enrichment.providers.cnpj_enricher.requests.get")
def test_run_skips_tratamento_formal_for_non_regulated_nicho(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "razao_social": "PADARIA DO CENTRO LTDA",
        "qsa": [{"nome_socio": "Maria Silva"}],
    }
    mock_get.return_value = mock_resp

    provider = CnpjProvider()
    lead = FakeLead(cnpj="12345678000190", nicho="padaria")
    result = provider.run(lead, EnrichmentContext())

    assert result.success is True
    assert "tratamento_formal" not in result.data


@patch("app.pipeline.enrichment.providers.cnpj_enricher.requests.get")
def test_run_skips_tratamento_formal_for_multiple_socios(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "razao_social": "CLINICA ODONTO LTDA",
        "qsa": [
            {"nome_socio": "Maria Silva"},
            {"nome_socio": "João Souza"},
        ],
    }
    mock_get.return_value = mock_resp

    provider = CnpjProvider()
    lead = FakeLead(cnpj="12345678000190", nicho="odontologia")
    result = provider.run(lead, EnrichmentContext())

    assert result.success is True
    assert "tratamento_formal" not in result.data


@patch("app.pipeline.enrichment.providers.cnpj_enricher.requests.get")
def test_run_uses_nicho_canonico_when_nicho_missing(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "razao_social": "CONSULTORIO DR FULANO",
        "qsa": [{"nome_socio": "Fernanda Souza"}],
    }
    mock_get.return_value = mock_resp

    provider = CnpjProvider()
    lead = FakeLead(cnpj="12345678000190", nicho=None, nicho_canonico="dentista")
    result = provider.run(lead, EnrichmentContext())

    assert result.success is True
    assert result.data.get("tratamento_formal") == "Dra"


@patch("app.pipeline.enrichment.providers.cnpj_enricher.requests.get")
def test_discovers_website_via_cnpj(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "razao_social": "EMPRESA Y LTDA",
        "website": "https://empresay.com.br",
        "cnae_fiscal_descricao": "...",
        "porte": "EPP",
    }
    mock_get.return_value = mock_resp

    provider = CnpjProvider()
    lead = FakeLead(cnpj="12345678000190")
    ctx = EnrichmentContext()
    result = provider.run(lead, ctx)

    assert result.success is True
    assert ctx.discovered_website == "https://empresay.com.br"
