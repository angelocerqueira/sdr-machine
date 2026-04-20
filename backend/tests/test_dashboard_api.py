from app.models import Job, Lead


def test_dashboard_stats_includes_profile_and_nicho_distribution(client, db):
    db.add(Lead(nome="A", telefone="1", perfil_lead="hot_no_site", nicho_canonico="dentista"))
    db.add(Lead(nome="B", telefone="2", perfil_lead="warm", nicho_canonico="restaurante"))
    db.add(Lead(nome="C", telefone="3", perfil_lead="hot_no_site", nicho_canonico="dentista"))
    db.commit()

    resp = client.get("/api/dashboard/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["profile_distribution"]["hot_no_site"] == 2
    assert body["profile_distribution"]["warm"] == 1
    assert body["nicho_distribution"]["dentista"] == 2
    assert body["nicho_distribution"]["restaurante"] == 1


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
