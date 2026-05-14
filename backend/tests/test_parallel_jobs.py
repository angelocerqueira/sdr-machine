"""Tests for parallel job execution + orphan reaping.

The autouse `_sync_job_threads` fixture from conftest forces inline execution
in most tests. Tests here use @pytest.mark.real_threads to opt into the real
threading.Thread path.
"""
import datetime
import threading
import time
from unittest.mock import patch

import pytest

from tests.conftest import TestSession


@pytest.mark.real_threads
def test_two_runners_execute_concurrently(client, db_session):
    """Two different-type jobs dispatched in quick succession should overlap."""
    import app.routers.pipeline as pipeline_module
    from app.models import Job

    started = threading.Event()
    proceed = threading.Event()
    results: dict[str, float | bool] = {}

    def slow_runner_a(job_id: int, params: dict):
        results["a_start"] = time.monotonic()
        started.set()
        proceed.wait(timeout=5)
        results["a_end"] = time.monotonic()
        db = TestSession()
        try:
            job = db.get(Job, job_id)
            job.status = "done"
            db.commit()
        finally:
            db.close()

    def fast_runner_b(job_id: int, params: dict):
        assert started.wait(timeout=5), "runner A never started"
        results["b_ran_while_a_blocked"] = True
        results["b_time"] = time.monotonic()
        db = TestSession()
        try:
            job = db.get(Job, job_id)
            job.status = "done"
            db.commit()
        finally:
            db.close()

    with patch.dict(pipeline_module._RUNNERS, {"scrape": slow_runner_a, "enrich": fast_runner_b}):
        with patch("app.routers.pipeline.SessionLocal", new=TestSession):
            r1 = client.post("/api/pipeline/scrape", json={})
            assert r1.status_code == 200
            r2 = client.post("/api/pipeline/enrich", json={})
            assert r2.status_code == 200

            assert started.wait(timeout=3), "runner A never started"
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and "b_ran_while_a_blocked" not in results:
                time.sleep(0.05)
            proceed.set()  # release A
            # Wait for A's thread to finish recording a_end before asserting.
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and "a_end" not in results:
                time.sleep(0.05)

    assert results.get("b_ran_while_a_blocked") is True
    assert isinstance(results.get("a_end"), float)
    # B should have completed strictly before A — proves they overlapped.
    assert results["b_time"] < results["a_end"]


@pytest.mark.real_threads
def test_runner_crash_marks_job_failed(client, db_session):
    """If a runner raises, the spawned thread must flip the Job to failed."""
    import app.routers.pipeline as pipeline_module
    from app.models import Job

    def crashing_runner(job_id: int, params: dict):
        raise RuntimeError("boom")

    with patch.dict(pipeline_module._RUNNERS, {"scrape": crashing_runner}):
        with patch("app.routers.pipeline.SessionLocal", new=TestSession):
            r = client.post("/api/pipeline/scrape", json={})
            assert r.status_code == 200
            job_id = r.json()["id"]

            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                db_session.expire_all()
                job = db_session.get(Job, job_id)
                if job and job.status == "failed":
                    break
                time.sleep(0.05)

    db_session.expire_all()
    job = db_session.get(Job, job_id)
    assert job.status == "failed"
    assert "crashed" in (job.error_message or "")


def test_startup_reaps_orphaned_jobs(db_session):
    """Jobs left running/pending from a previous process should be marked failed."""
    from app.models import Job
    from app.main import _reap_orphaned_jobs

    db_session.add(Job(type="scrape", status="running", started_at=datetime.datetime.utcnow()))
    db_session.add(Job(type="enrich", status="pending"))
    db_session.add(Job(type="generate", status="done"))  # untouched
    db_session.commit()

    with patch("app.main.SessionLocal", new=TestSession):
        _reap_orphaned_jobs()

    db_session.expire_all()
    statuses = {j.type: j.status for j in db_session.query(Job).all()}
    assert statuses["scrape"] == "failed"
    assert statuses["enrich"] == "failed"
    assert statuses["generate"] == "done"
