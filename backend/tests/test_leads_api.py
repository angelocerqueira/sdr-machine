from app.models import Lead


class TestListLeads:
    def test_empty(self, client):
        resp = client.get("/api/leads")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_with_data(self, client, sample_lead):
        resp = client.get("/api/leads")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["nome"] == "Odonto Sorriso"

    def test_filter_by_status(self, client, sample_lead):
        resp = client.get("/api/leads?status=scraped")
        assert resp.json()["total"] == 1

        resp = client.get("/api/leads?status=enriched")
        assert resp.json()["total"] == 0

    def test_filter_by_score(self, client, sample_lead):
        resp = client.get("/api/leads?score_min=60")
        assert resp.json()["total"] == 1

        resp = client.get("/api/leads?score_min=70")
        assert resp.json()["total"] == 0


class TestGetLead:
    def test_found(self, client, sample_lead):
        resp = client.get(f"/api/leads/{sample_lead.id}")
        assert resp.status_code == 200
        assert resp.json()["nome"] == "Odonto Sorriso"

    def test_not_found(self, client):
        resp = client.get("/api/leads/9999")
        assert resp.status_code == 404

    def test_lead_response_includes_enrichment_fields(self, client, sample_lead):
        """Verify the new smart-enrichment fields are serialized in lead responses."""
        resp = client.get(f"/api/leads/{sample_lead.id}")
        assert resp.status_code == 200
        data = resp.json()

        # Nullable string/date fields default to None
        for field in ("email", "cnpj", "razao_social", "porte", "cnae", "data_fundacao"):
            assert field in data, f"missing field: {field}"
            assert data[field] is None, f"expected {field} to be None, got {data[field]!r}"

        # List fields default to empty list
        for field in ("socios", "tech_stack", "enrichment_sources"):
            assert field in data, f"missing field: {field}"
            assert data[field] == [], f"expected {field} to be [], got {data[field]!r}"


class TestGetLeadLp:
    def test_lp_html(self, client, db, sample_lead):
        sample_lead.lp_html = "<html><body>Hello</body></html>"
        db.commit()
        resp = client.get(f"/api/leads/{sample_lead.id}/lp")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/html; charset=utf-8"
        assert "Hello" in resp.text

    def test_lp_not_generated(self, client, sample_lead):
        resp = client.get(f"/api/leads/{sample_lead.id}/lp")
        assert resp.status_code == 404


class TestUpdateLead:
    def test_update_status(self, client, sample_lead):
        resp = client.patch(
            f"/api/leads/{sample_lead.id}", json={"status": "enriched"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "enriched"

    def test_invalid_status(self, client, sample_lead):
        resp = client.patch(
            f"/api/leads/{sample_lead.id}", json={"status": "invalid_status"}
        )
        assert resp.status_code == 422


class TestDeleteLead:
    def test_delete(self, client, sample_lead):
        resp = client.delete(f"/api/leads/{sample_lead.id}")
        assert resp.status_code == 204

        resp = client.get(f"/api/leads/{sample_lead.id}")
        assert resp.status_code == 404

    def test_delete_not_found(self, client):
        resp = client.delete("/api/leads/9999")
        assert resp.status_code == 404


class TestSearchExpanded:
    def test_search_by_nicho(self, client, db):
        from app.models import Lead
        db.add_all([
            Lead(nome="Boiger Beauty", nicho="salão de beleza", cidade="Curitiba", telefone="1"),
            Lead(nome="Clinica XYZ", nicho="clínica estética", cidade="Curitiba", telefone="2"),
            Lead(nome="Bar do Zé", nicho="bar", cidade="Porto Alegre", telefone="3"),
        ])
        db.commit()

        resp = client.get("/api/leads?search=salão")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["nome"] == "Boiger Beauty"

    def test_search_by_cidade(self, client, db):
        from app.models import Lead
        db.add_all([
            Lead(nome="A", nicho="x", cidade="Porto Alegre", telefone="1"),
            Lead(nome="B", nicho="y", cidade="Curitiba", telefone="2"),
        ])
        db.commit()

        resp = client.get("/api/leads?search=porto")
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["cidade"] == "Porto Alegre"

    def test_search_by_email(self, client, db):
        from app.models import Lead
        db.add_all([
            Lead(nome="X", telefone="1", email="contato@loja.com"),
            Lead(nome="Y", telefone="2", email="outro@empresa.com"),
        ])
        db.commit()

        resp = client.get("/api/leads?search=loja.com")
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["email"] == "contato@loja.com"

    def test_search_by_razao_social(self, client, db):
        from app.models import Lead
        db.add_all([
            Lead(nome="X", telefone="1", razao_social="Empresa Alpha LTDA"),
            Lead(nome="Y", telefone="2", razao_social="Beta Comercio ME"),
        ])
        db.commit()

        resp = client.get("/api/leads?search=Alpha")
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["razao_social"] == "Empresa Alpha LTDA"
