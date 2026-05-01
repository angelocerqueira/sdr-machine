"""Tests verifying the SELECT predicate logic used by `_run_enrich` and `_run_outreach`.

These tests don't run the full orchestrator/outreach generation — they only verify
that the query filters mirror the contract advertised by `/api/pipeline/preview`.
This keeps the tests fast and isolated from network-dependent providers.
"""

from app.models import Lead
from app.routers.pipeline import (
    ENRICH_INPUT_STATUSES,
    OUTREACH_INPUT_STATUSES,
)


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
    """The runner SELECT must match the preview's eligibility contract."""

    def test_skips_already_enriched_without_force(self, db):
        scraped = _make_lead(db, status="scraped")
        enriched = _make_lead(db, status="enriched")
        lead_ids = [scraped.id, enriched.id]

        # Reproduce the runner's SELECT for the no-force branch.
        query = db.query(Lead).filter(Lead.id.in_(lead_ids))
        force_providers: list[str] = []
        if not force_providers:
            query = query.filter(Lead.status.in_(ENRICH_INPUT_STATUSES))
        leads = query.all()

        assert len(leads) == 1
        assert leads[0].id == scraped.id

    def test_processes_all_with_force(self, db):
        scraped = _make_lead(db, status="scraped")
        enriched = _make_lead(db, status="enriched")
        lp = _make_lead(db, status="lp_generated")
        lead_ids = [scraped.id, enriched.id, lp.id]

        # Reproduce the runner's SELECT for the force branch.
        query = db.query(Lead).filter(Lead.id.in_(lead_ids))
        force_providers = ["website_crawler"]
        if not force_providers:
            query = query.filter(Lead.status.in_(ENRICH_INPUT_STATUSES))
        leads = query.all()

        assert len(leads) == 3
        returned_ids = {lead.id for lead in leads}
        assert returned_ids == {scraped.id, enriched.id, lp.id}

    def test_includes_enrich_failed_without_force(self, db):
        scraped = _make_lead(db, status="scraped")
        enrich_failed = _make_lead(db, status="enrich_failed")
        enriched = _make_lead(db, status="enriched")
        lead_ids = [scraped.id, enrich_failed.id, enriched.id]

        query = db.query(Lead).filter(Lead.id.in_(lead_ids))
        force_providers: list[str] = []
        if not force_providers:
            query = query.filter(Lead.status.in_(ENRICH_INPUT_STATUSES))
        leads = query.all()

        assert len(leads) == 2
        returned_ids = {lead.id for lead in leads}
        assert returned_ids == {scraped.id, enrich_failed.id}


class TestOutreachRunnerFilter:
    """The runner SELECT must match the preview's eligibility contract."""

    def test_only_processes_eligible_statuses(self, db):
        lp_generated = _make_lead(db, status="lp_generated")
        outreach_ready = _make_lead(db, status="outreach_ready")
        outreach_failed = _make_lead(db, status="outreach_failed")
        enriched = _make_lead(db, status="enriched")
        disqualified = _make_lead(db, status="disqualified")

        lead_ids = [
            lp_generated.id,
            outreach_ready.id,
            outreach_failed.id,
            enriched.id,
            disqualified.id,
        ]

        # Reproduce the runner's SELECT.
        leads = db.query(Lead).filter(
            Lead.id.in_(lead_ids),
            Lead.status.in_(OUTREACH_INPUT_STATUSES),
        ).all()

        assert len(leads) == 3
        returned_ids = {lead.id for lead in leads}
        assert returned_ids == {
            lp_generated.id,
            outreach_ready.id,
            outreach_failed.id,
        }
        # Disqualified must not leak through (was the legacy behavior already).
        assert disqualified.id not in returned_ids
        # Enriched is not yet eligible — needs LP first.
        assert enriched.id not in returned_ids

    def test_excludes_disqualified_implicitly(self, db):
        """OUTREACH_INPUT_STATUSES doesn't include 'disqualified', so it's
        excluded by construction without needing an extra `!= "disqualified"` clause."""
        assert "disqualified" not in OUTREACH_INPUT_STATUSES
