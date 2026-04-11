import io
import pytest
from unittest.mock import MagicMock, patch

from app.pipeline.csv_importer import parse_csv
from app.models import Job


class TestParseCSV:
    def test_basic_import(self):
        csv_content = "nome,telefone,website\nPadaria Dona Maria,11999999999,www.padaria.com\nAcougue Boi Gordo,11888888888,"
        leads, errors = parse_csv(csv_content)
        assert len(leads) == 2
        assert len(errors) == 0
        assert leads[0]["nome"] == "Padaria Dona Maria"
        assert leads[0]["telefone"] == "11999999999"
        assert leads[0]["website"] == "www.padaria.com"
        # empty strings are skipped, so website won't be in dict
        assert "website" not in leads[1]

    def test_english_headers(self):
        csv_content = "name,phone,address,email\nJohn Bakery,555-1234,123 Main St,john@bakery.com"
        leads, errors = parse_csv(csv_content)
        assert len(leads) == 1
        assert leads[0]["nome"] == "John Bakery"
        assert leads[0]["telefone"] == "555-1234"
        assert leads[0]["endereco"] == "123 Main St"
        assert leads[0]["email"] == "john@bakery.com"

    def test_missing_nome_column(self):
        csv_content = "telefone,website\n11999999999,www.site.com"
        leads, errors = parse_csv(csv_content)
        assert len(leads) == 0
        assert len(errors) == 1
        assert "nome" in errors[0].lower()

    def test_empty_nome_skipped(self):
        csv_content = "nome,telefone\n,11999999999\nPadaria OK,11888888888"
        leads, errors = parse_csv(csv_content)
        assert len(leads) == 1
        assert leads[0]["nome"] == "Padaria OK"
        assert len(errors) == 1

    def test_rating_parsed(self):
        csv_content = "nome,rating\nPadaria,4.5"
        leads, errors = parse_csv(csv_content)
        assert leads[0]["rating"] == 4.5

    def test_invalid_rating_ignored(self):
        csv_content = "nome,rating\nPadaria,abc"
        leads, errors = parse_csv(csv_content)
        assert "rating" not in leads[0]

    def test_empty_csv(self):
        leads, errors = parse_csv("")
        assert len(leads) == 0
        assert len(errors) == 1

    def test_extra_columns_ignored(self):
        csv_content = "nome,unknown_col,telefone\nPadaria,blah,111"
        leads, errors = parse_csv(csv_content)
        assert len(leads) == 1
        assert leads[0]["nome"] == "Padaria"
        assert leads[0]["telefone"] == "111"
        assert "unknown_col" not in leads[0]

    def test_pt_br_headers(self):
        csv_content = "nome,cidade,nicho,categoria\nMercado Central,São Paulo,mercado,Supermercado"
        leads, errors = parse_csv(csv_content)
        assert len(leads) == 1
        assert leads[0]["cidade"] == "São Paulo"
        assert leads[0]["nicho"] == "mercado"
        assert leads[0]["categoria"] == "Supermercado"

    def test_whitespace_trimmed(self):
        csv_content = "nome,telefone\n  Padaria Bela  ,  11999999999  "
        leads, errors = parse_csv(csv_content)
        assert leads[0]["nome"] == "Padaria Bela"
        assert leads[0]["telefone"] == "11999999999"


@pytest.fixture(autouse=True)
def mock_runners():
    """Mock the _RUNNERS dict so background tasks become no-ops."""
    noop = MagicMock()
    fake_runners = {
        "scrape": noop,
        "enrich": noop,
        "generate": noop,
        "outreach": noop,
        "csv_import": noop,
    }
    with patch("app.routers.pipeline._RUNNERS", fake_runners):
        yield fake_runners


class TestCSVImportEndpoint:
    def test_csv_import_creates_job(self, client, db):
        csv_content = "nome,telefone\nPadaria Teste,11999999999"
        files = {"file": ("leads.csv", io.BytesIO(csv_content.encode()), "text/csv")}
        data = {"nicho": "padaria", "cidade": "São Paulo"}
        response = client.post("/api/pipeline/csv-import", files=files, data=data)
        assert response.status_code == 200
        body = response.json()
        assert body["type"] == "csv_import"
        assert body["status"] in ("pending", "running", "done")

    def test_csv_import_stores_params(self, client, db):
        csv_content = "nome,telefone\nPadaria Teste,11999999999"
        files = {"file": ("leads.csv", io.BytesIO(csv_content.encode()), "text/csv")}
        data = {"nicho": "restaurante", "cidade": "Recife"}
        response = client.post("/api/pipeline/csv-import", files=files, data=data)
        assert response.status_code == 200
        body = response.json()
        job = db.get(Job, body["id"])
        assert job is not None
        assert job.params["nicho"] == "restaurante"
        assert job.params["cidade"] == "Recife"
        assert "file_content" in job.params

    def test_csv_import_rejects_non_csv(self, client):
        files = {"file": ("data.txt", io.BytesIO(b"not csv"), "text/plain")}
        response = client.post("/api/pipeline/csv-import", files=files)
        assert response.status_code == 400
        assert "CSV" in response.json()["detail"]

    def test_csv_import_rejects_large_file(self, client):
        large = b"nome\n" + b"x" * (6 * 1024 * 1024)
        files = {"file": ("big.csv", io.BytesIO(large), "text/csv")}
        response = client.post("/api/pipeline/csv-import", files=files)
        assert response.status_code == 400
        assert "5MB" in response.json()["detail"]

    def test_csv_import_defaults_nicho_cidade_empty(self, client, db):
        csv_content = "nome\nLoja Teste"
        files = {"file": ("leads.csv", io.BytesIO(csv_content.encode()), "text/csv")}
        response = client.post("/api/pipeline/csv-import", files=files)
        assert response.status_code == 200
        body = response.json()
        assert body["params"]["nicho"] == ""
        assert body["params"]["cidade"] == ""
