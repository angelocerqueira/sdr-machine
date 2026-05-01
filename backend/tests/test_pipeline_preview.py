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


class TestPreviewEnrich:
    def test_all_scraped_eligible(self, client, db):
        l1 = _make_lead(db, status="scraped")
        l2 = _make_lead(db, status="scraped")
        l3 = _make_lead(db, status="scraped")

        resp = client.post(
            "/api/pipeline/preview",
            json={"action": "enrich", "lead_ids": [l1.id, l2.id, l3.id]},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["action"] == "enrich"
        assert body["total_leads"] == 3
        assert body["eligible"] == 3
        assert body["skipped"] == 0
        assert body["skipped_reasons"] == {}
        assert body["warnings"] == []

    def test_already_enriched_warned_not_skipped(self, client, db):
        l1 = _make_lead(db, status="scraped")
        l2 = _make_lead(db, status="scraped")
        l3 = _make_lead(db, status="enriched")
        l4 = _make_lead(db, status="enriched")

        resp = client.post(
            "/api/pipeline/preview",
            json={"action": "enrich", "lead_ids": [l1.id, l2.id, l3.id, l4.id]},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total_leads"] == 4
        # Runner accepts all leads regardless of status — no skips.
        assert body["eligible"] == 4
        assert body["skipped"] == 0
        assert body["skipped_reasons"] == {}
        # Out-of-natural-input leads are reported as a warning instead.
        assert len(body["warnings"]) == 1
        assert "2 leads" in body["warnings"][0]
        assert "reprocessados" in body["warnings"][0]

    def test_already_enriched_with_force_all_eligible(self, client, db):
        """`force_providers` is no longer special at the preview layer — runner
        already accepts every explicit lead_id, so eligibility is always total."""
        l1 = _make_lead(db, status="scraped")
        l2 = _make_lead(db, status="scraped")
        l3 = _make_lead(db, status="enriched")
        l4 = _make_lead(db, status="enriched")

        resp = client.post(
            "/api/pipeline/preview",
            json={
                "action": "enrich",
                "lead_ids": [l1.id, l2.id, l3.id, l4.id],
                "options": {"force_providers": ["website_crawler"]},
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total_leads"] == 4
        assert body["eligible"] == 4
        assert body["skipped"] == 0
        assert body["skipped_reasons"] == {}
        # Warning still emitted — the 2 enriched leads will be reprocessed.
        assert len(body["warnings"]) == 1

    def test_enrich_failed_treated_as_scraped(self, client, db):
        l1 = _make_lead(db, status="scraped")
        l2 = _make_lead(db, status="enrich_failed")

        resp = client.post(
            "/api/pipeline/preview",
            json={"action": "enrich", "lead_ids": [l1.id, l2.id]},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total_leads"] == 2
        assert body["eligible"] == 2
        assert body["skipped"] == 0
        assert body["skipped_reasons"] == {}
        assert body["warnings"] == []


class TestPreviewGenerate:
    def test_disqualified_excluded(self, client, db):
        l1 = _make_lead(db, status="enriched")
        l2 = _make_lead(db, status="enriched")
        l3 = _make_lead(db, status="disqualified")

        resp = client.post(
            "/api/pipeline/preview",
            json={"action": "generate", "lead_ids": [l1.id, l2.id, l3.id]},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total_leads"] == 3
        assert body["eligible"] == 2
        assert body["skipped"] == 1
        assert body["skipped_reasons"] == {"disqualified": 1}

    def test_all_eligible(self, client, db):
        l1 = _make_lead(db, status="enriched")
        l2 = _make_lead(db, status="enriched")
        l3 = _make_lead(db, status="enriched")

        resp = client.post(
            "/api/pipeline/preview",
            json={"action": "generate", "lead_ids": [l1.id, l2.id, l3.id]},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total_leads"] == 3
        assert body["eligible"] == 3
        assert body["skipped"] == 0
        assert body["skipped_reasons"] == {}


class TestPreviewOutreach:
    def test_out_of_window_warned_not_skipped(self, client, db):
        l1 = _make_lead(db, status="lp_generated")
        l2 = _make_lead(db, status="outreach_ready")
        l3 = _make_lead(db, status="outreach_failed")
        l4 = _make_lead(db, status="enriched")

        resp = client.post(
            "/api/pipeline/preview",
            json={"action": "outreach", "lead_ids": [l1.id, l2.id, l3.id, l4.id]},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total_leads"] == 4
        # Runner only excludes disqualified — enriched is processed.
        assert body["eligible"] == 4
        assert body["skipped"] == 0
        assert body["skipped_reasons"] == {}
        assert len(body["warnings"]) == 1
        assert "1 leads fora do estágio de outreach" in body["warnings"][0]

    def test_outreach_disqualified_skipped(self, client, db):
        l1 = _make_lead(db, status="lp_generated")
        l2 = _make_lead(db, status="outreach_ready")
        l3 = _make_lead(db, status="disqualified")

        resp = client.post(
            "/api/pipeline/preview",
            json={"action": "outreach", "lead_ids": [l1.id, l2.id, l3.id]},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total_leads"] == 3
        assert body["eligible"] == 2
        assert body["skipped"] == 1
        assert body["skipped_reasons"] == {"disqualified": 1}
        # Warning for disqualified; no out-of-window warning since the others
        # are within OUTREACH_INPUT_STATUSES.
        assert any("desqualificados" in w for w in body["warnings"])

    def test_all_have_lp(self, client, db):
        l1 = _make_lead(db, status="lp_generated")
        l2 = _make_lead(db, status="lp_generated")
        l3 = _make_lead(db, status="lp_generated")

        resp = client.post(
            "/api/pipeline/preview",
            json={"action": "outreach", "lead_ids": [l1.id, l2.id, l3.id]},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total_leads"] == 3
        assert body["eligible"] == 3
        assert body["skipped"] == 0
        assert body["skipped_reasons"] == {}
        assert body["warnings"] == []


class TestPreviewClassify:
    def test_all_eligible(self, client, db):
        l1 = _make_lead(db, status="scraped")
        l2 = _make_lead(db, status="enriched")
        l3 = _make_lead(db, status="lp_generated")

        resp = client.post(
            "/api/pipeline/preview",
            json={"action": "classify", "lead_ids": [l1.id, l2.id, l3.id]},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total_leads"] == 3
        assert body["eligible"] == 3
        assert body["skipped"] == 0
        assert body["skipped_reasons"] == {}


class TestPreviewValidation:
    def test_5001_ids_rejected(self, client):
        resp = client.post(
            "/api/pipeline/preview",
            json={"action": "enrich", "lead_ids": list(range(1, 5002))},
        )
        assert resp.status_code == 422

    def test_empty_lead_ids_rejected(self, client):
        resp = client.post(
            "/api/pipeline/preview",
            json={"action": "enrich", "lead_ids": []},
        )
        assert resp.status_code == 422

    def test_invalid_action_rejected(self, client):
        resp = client.post(
            "/api/pipeline/preview",
            json={"action": "bogus", "lead_ids": [1, 2, 3]},
        )
        assert resp.status_code == 422

    def test_missing_leads_counted_as_zero(self, client):
        resp = client.post(
            "/api/pipeline/preview",
            json={"action": "enrich", "lead_ids": [9999, 8888]},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total_leads"] == 0
        assert body["eligible"] == 0
        assert body["skipped"] == 0


class TestPreviewResponse:
    def test_cost_estimate_and_quota_are_null_v1(self, client, db):
        l1 = _make_lead(db, status="scraped")

        resp = client.post(
            "/api/pipeline/preview",
            json={"action": "enrich", "lead_ids": [l1.id]},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["cost_estimate"] is None
        assert body["quota_status"] is None
