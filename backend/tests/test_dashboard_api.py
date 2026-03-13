from app.models import Job, Lead


class TestDashboardStats:
    def test_empty(self, client):
        resp = client.get("/api/dashboard/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_leads"] == 0
        assert data["leads_by_status"] == {}
        assert data["avg_score"] is None
        assert data["total_jobs"] == 0
        assert data["conversion_rate"] is None

    def test_with_data(self, client, db, sample_lead):
        # Add a closed lead
        closed_lead = Lead(
            nome="Clinica Boa",
            cidade="Chapecó SC",
            nicho="dentista",
            status="closed",
            opportunity_score=80,
        )
        db.add(closed_lead)

        # Add a job
        job = Job(type="scrape", status="completed")
        db.add(job)
        db.commit()

        resp = client.get("/api/dashboard/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_leads"] == 2
        assert data["leads_by_status"]["scraped"] == 1
        assert data["leads_by_status"]["closed"] == 1
        assert data["avg_score"] is not None
        assert data["total_jobs"] == 1
        # conversion_rate = 1 closed / 2 total * 100 = 50.0
        assert data["conversion_rate"] == 50.0
