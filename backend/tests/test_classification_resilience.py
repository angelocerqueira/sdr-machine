"""End-to-end resilience tests for classification pipeline.

Validates spec section 7 guarantees:
- classify() never raises
- Circuit breaker fires at >50% failures after 20 leads
- Batch tolerates per-lead failures
- Idempotency via hash
"""
from unittest.mock import patch

import pytest

from app.models import Job, Lead


# ---------------------------------------------------------------------------
# 1. classify() never raises — pure function contract
# ---------------------------------------------------------------------------

def test_classify_never_raises_with_random_garbage():
    from app.pipeline.enrichment.classifier import classify, ClassificationResult

    garbage_inputs = [
        None,
        {},
        {"score": "banana"},
        {"rating": [1, 2, 3]},
        {"has_website": object()},
        {"review_count": -999},
        {"nome": None, "telefone": None, "rating": None},
        {"nicho_raw": b"bytes-are-not-str"},
        {"reviews": "not a list"},
    ]
    for g in garbage_inputs:
        result = classify(g)
        assert isinstance(result, ClassificationResult)
        assert result.perfil_lead is not None


# ---------------------------------------------------------------------------
# 2. Batch tolerates per-lead failures
# ---------------------------------------------------------------------------

def test_batch_job_tolerates_individual_failures(
    client, db_session, classify_sessionlocal_patch
):
    """30 leads with mixed-quality data. Job should complete (not stall) and
    process all leads (each either ok or failed, no crash stops the loop).

    Uses classify_sessionlocal_patch so the background task runner (_run_classify)
    shares the same test DB as the fixture that inserted the leads.
    """
    for i in range(30):
        db_session.add(Lead(
            nome=f"Lead {i}" if i % 3 else "",  # empty string is allowed (no empty-check constraint)
            telefone=f"11999{i}",
            rating=4.5 if i % 2 else None,
            reviews_count=50 if i % 2 else 0,
            nicho="Pizzaria" if i % 4 else "Clinica Odontologica",
        ))
    db_session.commit()

    with classify_sessionlocal_patch:
        resp = client.post("/api/pipeline/classify", json={"scope": "unclassified"})

    assert resp.status_code == 200
    job_id = resp.json()["id"]

    # FastAPI TestClient runs BackgroundTasks inline — job is already done
    db_session.expire_all()
    job = db_session.get(Job, job_id)
    assert job.status in ("done", "done_with_errors"), (
        f"Expected done/done_with_errors, got {job.status}. "
        f"Summary: {job.result_summary}"
    )
    # All 30 leads should have been processed (ok + failed + skipped)
    total_processed = (
        job.result_summary["ok"]
        + job.result_summary["failed"]
        + job.result_summary["skipped"]
    )
    assert total_processed == 30


# ---------------------------------------------------------------------------
# 3. Circuit breaker fires on high failure rate
# ---------------------------------------------------------------------------

def test_circuit_breaker_fires_on_high_failure_rate(
    db_session, classify_sessionlocal_patch
):
    """Inject classify() to raise for every lead.
    After 20 leads with 100% failure rate, circuit breaker trips → stalled."""
    from app.routers.pipeline import _run_classify

    # Add 25 leads (more than the 20-lead threshold)
    for i in range(25):
        db_session.add(Lead(
            nome=f"L{i}", telefone="11", rating=4.0, reviews_count=30,
        ))
    db_session.commit()

    job = Job(type="classification", status="pending", params={})
    db_session.add(job)
    db_session.commit()
    job_id = job.id

    with classify_sessionlocal_patch:
        with patch(
            "app.pipeline.enrichment.classifier.classify",
            side_effect=Exception("boom"),
        ):
            _run_classify(job_id, {"scope": "unclassified"})

    db_session.expire_all()
    job_fresh = db_session.get(Job, job_id)
    assert job_fresh.status == "stalled"
    assert job_fresh.result_summary.get("reason") == "too_many_failures"


def test_circuit_breaker_does_not_fire_below_threshold(
    db_session, classify_sessionlocal_patch
):
    """Below the 20-lead minimum, circuit breaker MUST NOT fire even with 100% failures."""
    from app.routers.pipeline import _run_classify

    # Only 10 leads — below threshold
    for i in range(10):
        db_session.add(Lead(nome=f"L{i}", telefone="11"))
    db_session.commit()

    job = Job(type="classification", status="pending", params={})
    db_session.add(job)
    db_session.commit()
    job_id = job.id

    with classify_sessionlocal_patch:
        with patch(
            "app.pipeline.enrichment.classifier.classify",
            side_effect=Exception("boom"),
        ):
            _run_classify(job_id, {"scope": "unclassified"})

    db_session.expire_all()
    job_fresh = db_session.get(Job, job_id)
    # All 10 failed but circuit breaker didn't fire (below 20 threshold)
    assert job_fresh.status == "done_with_errors"
    assert job_fresh.result_summary["failed"] == 10


# ---------------------------------------------------------------------------
# 4. Idempotency via hash
# ---------------------------------------------------------------------------

def test_idempotency_via_hash(client, db_session, classify_sessionlocal_patch):
    """Running classification twice over the same lead → second run skips it.

    Uses classify_sessionlocal_patch so the inline background task shares the
    test DB and can read/write the lead data inserted by db_session.
    """
    db_session.add(Lead(
        nome="Pizzaria Idem", telefone="11", rating=4.5, reviews_count=50,
        nicho="Pizzaria",
    ))
    db_session.commit()

    # Run 1 — classifies the lead
    with classify_sessionlocal_patch:
        resp1 = client.post("/api/pipeline/classify", json={"scope": "unclassified"})
    assert resp1.status_code == 200
    job1_id = resp1.json()["id"]

    db_session.expire_all()
    job1 = db_session.get(Job, job1_id)
    assert job1.result_summary["ok"] == 1

    # Run 2 — scope=all reaches the same lead; hash unchanged → skipped
    with classify_sessionlocal_patch:
        resp2 = client.post("/api/pipeline/classify", json={"scope": "all", "force": False})
    assert resp2.status_code == 200
    job2_id = resp2.json()["id"]

    db_session.expire_all()
    job2 = db_session.get(Job, job2_id)
    assert job2.result_summary["skipped"] == 1
    assert job2.result_summary["ok"] == 0
