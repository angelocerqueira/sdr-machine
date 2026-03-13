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
