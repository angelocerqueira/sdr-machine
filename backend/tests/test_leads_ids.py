from app.models import Lead


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


class TestLeadIdsHappy:
    def test_returns_all_ids(self, client, db):
        ids = [_make_lead(db, nome=f"Lead {i}").id for i in range(5)]

        resp = client.get("/api/leads/ids")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert sorted(body["ids"]) == sorted(ids)
        assert body["total"] == 5
        assert body["truncated"] is False

    def test_truncates_at_5000(self, client, db):
        # Bulk insert 5001 leads (single commit) for speed
        leads = [
            Lead(
                nome=f"Lead {i}",
                telefone=f"4999900{i:04d}",
                status="scraped",
                cidade="Chapecó",
                nicho="dentista",
            )
            for i in range(5001)
        ]
        db.add_all(leads)
        db.commit()

        resp = client.get("/api/leads/ids")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert len(body["ids"]) == 5000
        assert body["total"] == 5001
        assert body["truncated"] is True

    def test_empty(self, client, db):
        resp = client.get("/api/leads/ids")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["ids"] == []
        assert body["total"] == 0
        assert body["truncated"] is False


class TestLeadIdsFilters:
    def test_filter_status(self, client, db):
        for i in range(3):
            _make_lead(db, nome=f"S{i}", status="scraped")
        for i in range(2):
            _make_lead(db, nome=f"E{i}", status="enriched")

        resp = client.get("/api/leads/ids?status=scraped")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert len(body["ids"]) == 3
        assert body["total"] == 3
        assert body["truncated"] is False

    def test_filter_nicho(self, client, db):
        _make_lead(db, nome="A", nicho="dentista")
        _make_lead(db, nome="B", nicho="dentista")
        _make_lead(db, nome="C", nicho="restaurante")

        resp = client.get("/api/leads/ids?nicho=dentista")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert len(body["ids"]) == 2
        assert body["total"] == 2

    def test_filter_cidade(self, client, db):
        _make_lead(db, nome="A", cidade="Chapecó")
        _make_lead(db, nome="B", cidade="Florianópolis")
        _make_lead(db, nome="C", cidade="Florianópolis")

        resp = client.get("/api/leads/ids?cidade=Florian%C3%B3polis")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert len(body["ids"]) == 2

    def test_filter_score_min_max(self, client, db):
        _make_lead(db, nome="A", opportunity_score=30)
        b = _make_lead(db, nome="B", opportunity_score=50)
        c = _make_lead(db, nome="C", opportunity_score=70)
        _make_lead(db, nome="D", opportunity_score=90)

        resp = client.get("/api/leads/ids?score_min=40&score_max=80")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert sorted(body["ids"]) == sorted([b.id, c.id])
        assert body["total"] == 2

    def test_filter_has_telefone_true(self, client, db):
        _make_lead(db, nome="A", telefone="111")
        _make_lead(db, nome="B", telefone="222")
        _make_lead(db, nome="C", telefone=None)

        resp = client.get("/api/leads/ids?has_telefone=true")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert len(body["ids"]) == 2

    def test_filter_has_telefone_false(self, client, db):
        _make_lead(db, nome="A", telefone="111")
        _make_lead(db, nome="B", telefone="222")
        c = _make_lead(db, nome="C", telefone=None)

        resp = client.get("/api/leads/ids?has_telefone=false")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["ids"] == [c.id]

    def test_filter_has_email_true_and_false(self, client, db):
        a = _make_lead(db, nome="A", email="a@example.com")
        b = _make_lead(db, nome="B", email="b@example.com")
        c = _make_lead(db, nome="C", email=None)

        resp_true = client.get("/api/leads/ids?has_email=true")
        assert resp_true.status_code == 200, resp_true.text
        body_true = resp_true.json()
        assert sorted(body_true["ids"]) == sorted([a.id, b.id])

        resp_false = client.get("/api/leads/ids?has_email=false")
        assert resp_false.status_code == 200, resp_false.text
        body_false = resp_false.json()
        assert body_false["ids"] == [c.id]

    def test_filter_search(self, client, db):
        a = _make_lead(db, nome="Odonto Sorriso")
        _make_lead(db, nome="Pizzaria Roma")
        _make_lead(db, nome="Padaria Central")

        resp = client.get("/api/leads/ids?search=Odonto")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["ids"] == [a.id]

    def test_filter_combined(self, client, db):
        # Match: cidade=Chapecó + score>=50 + has_telefone=true
        a = _make_lead(
            db,
            nome="Match A",
            cidade="Chapecó",
            opportunity_score=60,
            telefone="111",
        )
        b = _make_lead(
            db,
            nome="Match B",
            cidade="Chapecó",
            opportunity_score=80,
            telefone="222",
        )
        # Wrong cidade
        _make_lead(
            db,
            nome="No match cidade",
            cidade="Florianópolis",
            opportunity_score=90,
            telefone="333",
        )
        # Wrong score
        _make_lead(
            db,
            nome="No match score",
            cidade="Chapecó",
            opportunity_score=20,
            telefone="444",
        )
        # No telefone
        _make_lead(
            db,
            nome="No match phone",
            cidade="Chapecó",
            opportunity_score=70,
            telefone=None,
        )

        resp = client.get(
            "/api/leads/ids?cidade=Chapec%C3%B3&score_min=50&has_telefone=true"
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert sorted(body["ids"]) == sorted([a.id, b.id])
        assert body["total"] == 2


class TestLeadIdsExistingFiltersNotBroken:
    """Regression tests for the _apply_lead_filters refactor — confirm the new
    score_max / has_telefone filters work on the legacy list_leads + counts
    endpoints, and that existing behavior wasn't changed."""

    def test_list_leads_score_max(self, client, db):
        _make_lead(db, nome="A", opportunity_score=30)
        _make_lead(db, nome="B", opportunity_score=60)
        _make_lead(db, nome="C", opportunity_score=90)

        resp = client.get("/api/leads?score_max=70")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] == 2
        names = {item["nome"] for item in body["items"]}
        assert names == {"A", "B"}

    def test_list_leads_has_telefone(self, client, db):
        _make_lead(db, nome="A", telefone="111")
        _make_lead(db, nome="B", telefone="222")
        _make_lead(db, nome="C", telefone=None)

        resp_true = client.get("/api/leads?has_telefone=true")
        assert resp_true.status_code == 200, resp_true.text
        assert resp_true.json()["total"] == 2

        resp_false = client.get("/api/leads?has_telefone=false")
        assert resp_false.status_code == 200, resp_false.text
        body_false = resp_false.json()
        assert body_false["total"] == 1
        assert body_false["items"][0]["nome"] == "C"

    def test_lead_counts_score_max(self, client, db):
        _make_lead(db, nome="A", status="scraped", opportunity_score=30)
        _make_lead(db, nome="B", status="scraped", opportunity_score=60)
        _make_lead(db, nome="C", status="scraped", opportunity_score=90)
        _make_lead(db, nome="D", status="enriched", opportunity_score=40)

        resp = client.get("/api/leads/counts?score_max=70")
        assert resp.status_code == 200, resp.text
        counts = resp.json()
        assert counts.get("scraped", 0) == 2
        assert counts.get("enriched", 0) == 1
