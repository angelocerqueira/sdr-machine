from app.models import LandingPage, Lead, OutreachMessage


def _make_lead(db, **overrides) -> Lead:
    defaults = {
        "nome": "Lead Teste",
        "telefone": "49999000000",
        "status": "scraped",
        "cidade": "Chapecó",
        "nicho": "dentista",
    }
    defaults.update(overrides)
    lead = Lead(**defaults)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


class TestBulkUpdate:
    def test_happy_path(self, client, db):
        l1 = _make_lead(db, nome="Lead A")
        l2 = _make_lead(db, nome="Lead B")
        l3 = _make_lead(db, nome="Lead C")

        resp = client.patch(
            "/api/leads/bulk",
            json={
                "lead_ids": [l1.id, l2.id, l3.id],
                "data": {"status": "enriched"},
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["updated"] == 3
        assert body["errors"] == []

        for lead_id in (l1.id, l2.id, l3.id):
            db.expire_all()
            lead = db.get(Lead, lead_id)
            assert lead.status == "enriched"

    def test_partial_with_missing_ids(self, client, db):
        l1 = _make_lead(db, nome="Lead A")
        l2 = _make_lead(db, nome="Lead B")

        resp = client.patch(
            "/api/leads/bulk",
            json={
                "lead_ids": [l1.id, l2.id, 9999],
                "data": {"status": "enriched"},
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["updated"] == 2
        assert len(body["errors"]) == 1
        assert body["errors"][0]["lead_id"] == 9999
        assert body["errors"][0]["error"] == "Lead not found"

        db.expire_all()
        assert db.get(Lead, l1.id).status == "enriched"
        assert db.get(Lead, l2.id).status == "enriched"

    def test_empty_lead_ids_rejected_by_pydantic(self, client):
        resp = client.patch(
            "/api/leads/bulk",
            json={"lead_ids": [], "data": {"status": "enriched"}},
        )
        assert resp.status_code == 422

    def test_5001_ids_rejected(self, client):
        resp = client.patch(
            "/api/leads/bulk",
            json={
                "lead_ids": list(range(1, 5002)),
                "data": {"status": "enriched"},
            },
        )
        assert resp.status_code == 422

    def test_invalid_status_rejected(self, client, db):
        lead = _make_lead(db)

        resp = client.patch(
            "/api/leads/bulk",
            json={"lead_ids": [lead.id], "data": {"status": "bogus"}},
        )
        assert resp.status_code == 422
        assert "Invalid status" in resp.json()["detail"]

        db.expire_all()
        assert db.get(Lead, lead.id).status == "scraped"

    def test_empty_data_returns_zero_updated(self, client, db):
        lead = _make_lead(db)

        resp = client.patch(
            "/api/leads/bulk",
            json={"lead_ids": [lead.id], "data": {}},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["updated"] == 0
        assert body["errors"] == []

        db.expire_all()
        assert db.get(Lead, lead.id).status == "scraped"

    def test_update_multiple_fields(self, client, db):
        lead = _make_lead(db, nome="Antigo")

        resp = client.patch(
            "/api/leads/bulk",
            json={
                "lead_ids": [lead.id],
                "data": {"status": "enriched", "nome": "Novo Nome"},
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["updated"] == 1
        assert body["errors"] == []

        db.expire_all()
        refreshed = db.get(Lead, lead.id)
        assert refreshed.status == "enriched"
        assert refreshed.nome == "Novo Nome"

    def test_nicho_canonico_marks_manual(self, client, db):
        """Mirrors single-lead PATCH invariant: setting nicho_canonico must set
        nicho_source='manual' + nicho_confidence=1.0 so a future reclassify
        won't overwrite the user's manual choice."""
        lead = _make_lead(
            db,
            nome="Lead X",
            nicho_canonico="outros",
            nicho_source="llm_inferred",
            nicho_confidence=0.4,
        )

        resp = client.patch(
            "/api/leads/bulk",
            json={
                "lead_ids": [lead.id],
                "data": {"nicho_canonico": "dentista"},
            },
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["updated"] == 1

        db.expire_all()
        refreshed = db.get(Lead, lead.id)
        assert refreshed.nicho_canonico == "dentista"
        assert refreshed.nicho_source == "manual"
        assert refreshed.nicho_confidence == 1.0


class TestBulkDelete:
    def test_happy_path(self, client, db):
        l1 = _make_lead(db, nome="Lead A")
        l2 = _make_lead(db, nome="Lead B")
        l3 = _make_lead(db, nome="Lead C")
        ids = [l1.id, l2.id, l3.id]

        resp = client.request(
            "DELETE",
            "/api/leads/bulk",
            json={"lead_ids": ids},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["deleted"] == 3
        assert body["errors"] == []

        db.expire_all()
        remaining = db.query(Lead).filter(Lead.id.in_(ids)).count()
        assert remaining == 0

    def test_partial_with_missing_ids(self, client, db):
        l1 = _make_lead(db, nome="Lead A")
        l2 = _make_lead(db, nome="Lead B")

        resp = client.request(
            "DELETE",
            "/api/leads/bulk",
            json={"lead_ids": [l1.id, l2.id, 9999]},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["deleted"] == 2
        assert len(body["errors"]) == 1
        assert body["errors"][0]["lead_id"] == 9999
        assert body["errors"][0]["error"] == "Lead not found"

        db.expire_all()
        assert db.get(Lead, l1.id) is None
        assert db.get(Lead, l2.id) is None

    def test_empty_lead_ids_rejected(self, client):
        resp = client.request(
            "DELETE",
            "/api/leads/bulk",
            json={"lead_ids": []},
        )
        assert resp.status_code == 422

    def test_5001_ids_rejected(self, client):
        resp = client.request(
            "DELETE",
            "/api/leads/bulk",
            json={"lead_ids": list(range(1, 5002))},
        )
        assert resp.status_code == 422

    def test_cascade_deletes_messages_and_lps(self, client, db):
        lead = _make_lead(db, nome="Cascade Lead")
        msg = OutreachMessage(
            lead_id=lead.id,
            type="initial",
            message_text="hello",
        )
        lp = LandingPage(
            lead_id=lead.id,
            public_id="lp-pub-id-123",
            html="<html></html>",
            version=1,
            is_active=True,
        )
        db.add(msg)
        db.add(lp)
        db.commit()
        msg_id = msg.id
        lp_id = lp.id

        resp = client.request(
            "DELETE",
            "/api/leads/bulk",
            json={"lead_ids": [lead.id]},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["deleted"] == 1
        assert body["errors"] == []

        db.expire_all()
        assert db.get(Lead, lead.id) is None
        assert db.get(OutreachMessage, msg_id) is None
        assert db.get(LandingPage, lp_id) is None
