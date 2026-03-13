import pytest
from unittest.mock import patch, MagicMock

from app.models import Job, Lead


@pytest.fixture(autouse=True)
def mock_runners():
    """Mock the _RUNNERS dict so background tasks become no-ops."""
    noop = MagicMock()
    fake_runners = {
        "scrape": noop,
        "enrich": noop,
        "generate": noop,
        "outreach": noop,
    }
    with patch("app.routers.pipeline._RUNNERS", fake_runners):
        yield fake_runners


class TestPipelineEndpoints:
    """Tests for POST /api/pipeline/* endpoints."""

    def test_run_scrape_creates_job(self, client, db):
        resp = client.post("/api/pipeline/scrape", json={"nichos": ["dentista"], "cidades": ["Chapecó SC"], "max_results": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "scrape"
        assert data["status"] == "pending"
        assert data["params"]["nichos"] == ["dentista"]
        # Verify in DB
        job = db.get(Job, data["id"])
        assert job is not None

    def test_run_enrich_creates_job(self, client, db):
        resp = client.post("/api/pipeline/enrich", json={"lead_ids": [1, 2]})
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "enrich"
        assert data["status"] == "pending"
        assert data["params"]["lead_ids"] == [1, 2]

    def test_run_generate_creates_job(self, client, db):
        resp = client.post("/api/pipeline/generate", json={"lead_ids": [1], "max_count": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "generate"
        assert data["status"] == "pending"

    def test_run_outreach_creates_job(self, client, db):
        resp = client.post("/api/pipeline/outreach", json={"lead_ids": [1]})
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "outreach"
        assert data["status"] == "pending"


class TestJobEndpoints:
    """Tests for GET /api/jobs endpoints."""

    def test_list_jobs(self, client, db):
        # Create some jobs
        for jtype in ("scrape", "enrich", "generate"):
            db.add(Job(type=jtype, params={}))
        db.commit()

        resp = client.get("/api/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 3
        assert len(data["items"]) >= 3
        assert data["page"] == 1

    def test_get_job(self, client, db):
        job = Job(type="scrape", params={"nichos": ["dentista"]})
        db.add(job)
        db.commit()
        db.refresh(job)

        resp = client.get(f"/api/jobs/{job.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == job.id
        assert data["type"] == "scrape"

    def test_get_job_not_found(self, client):
        resp = client.get("/api/jobs/99999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Job not found"
