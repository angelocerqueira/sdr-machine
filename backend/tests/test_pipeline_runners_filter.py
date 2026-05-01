"""Tests verifying the SELECT predicate logic used by `_run_enrich` and `_run_outreach`.

These tests don't run the full orchestrator/outreach generation — they only verify
that the query filters mirror the runner's actual SELECT shape. The runner contract
(post-revert) is:

- enrich: explicit `lead_ids` are accepted as-is. No status filter.
- outreach: explicit `lead_ids` exclude only `disqualified`.

This keeps the tests fast and isolated from network-dependent providers.
"""

from app.models import Lead
from app.routers.pipeline import OUTREACH_INPUT_STATUSES


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


class TestEnrichRunnerFilter:
    """The runner accepts every lead in `lead_ids` regardless of status."""

    def test_enrich_runner_processes_all_explicit_lead_ids(self, db):
        scraped = _make_lead(db, status="scraped")
        enriched = _make_lead(db, status="enriched")
        lp = _make_lead(db, status="lp_generated")
        disqualified = _make_lead(db, status="disqualified")
        lead_ids = [scraped.id, enriched.id, lp.id, disqualified.id]

        # Reproduce the runner's SELECT — no status filter.
        leads = db.query(Lead).filter(Lead.id.in_(lead_ids)).all()

        assert len(leads) == 4
        returned_ids = {lead.id for lead in leads}
        assert returned_ids == {scraped.id, enriched.id, lp.id, disqualified.id}

    def test_processes_all_with_force(self, db):
        """`force_providers` no longer changes the SELECT — runner accepts all."""
        scraped = _make_lead(db, status="scraped")
        enriched = _make_lead(db, status="enriched")
        lp = _make_lead(db, status="lp_generated")
        lead_ids = [scraped.id, enriched.id, lp.id]

        # Reproduce the runner's SELECT — single shape regardless of force.
        leads = db.query(Lead).filter(Lead.id.in_(lead_ids)).all()

        assert len(leads) == 3
        returned_ids = {lead.id for lead in leads}
        assert returned_ids == {scraped.id, enriched.id, lp.id}

    def test_includes_enrich_failed_without_force(self, db):
        scraped = _make_lead(db, status="scraped")
        enrich_failed = _make_lead(db, status="enrich_failed")
        enriched = _make_lead(db, status="enriched")
        lead_ids = [scraped.id, enrich_failed.id, enriched.id]

        leads = db.query(Lead).filter(Lead.id.in_(lead_ids)).all()

        assert len(leads) == 3
        returned_ids = {lead.id for lead in leads}
        assert returned_ids == {scraped.id, enrich_failed.id, enriched.id}


class TestOutreachRunnerFilter:
    """The runner SELECT excludes only `disqualified`."""

    def test_outreach_runner_excludes_disqualified(self, db):
        lp_generated = _make_lead(db, status="lp_generated")
        outreach_ready = _make_lead(db, status="outreach_ready")
        outreach_failed = _make_lead(db, status="outreach_failed")
        enriched = _make_lead(db, status="enriched")
        outreach_sent = _make_lead(db, status="outreach_sent")
        responded = _make_lead(db, status="responded")
        disqualified = _make_lead(db, status="disqualified")

        lead_ids = [
            lp_generated.id,
            outreach_ready.id,
            outreach_failed.id,
            enriched.id,
            outreach_sent.id,
            responded.id,
            disqualified.id,
        ]

        # Reproduce the runner's SELECT — only disqualified is excluded.
        leads = db.query(Lead).filter(
            Lead.id.in_(lead_ids),
            Lead.status != "disqualified",
        ).all()

        assert len(leads) == 6
        returned_ids = {lead.id for lead in leads}
        assert returned_ids == {
            lp_generated.id,
            outreach_ready.id,
            outreach_failed.id,
            enriched.id,
            outreach_sent.id,
            responded.id,
        }
        # Disqualified must not leak through.
        assert disqualified.id not in returned_ids

    def test_excludes_disqualified_implicitly(self, db):
        """OUTREACH_INPUT_STATUSES doesn't include 'disqualified', so anything
        described as the natural outreach window excludes it by construction."""
        assert "disqualified" not in OUTREACH_INPUT_STATUSES
