import pytest

from app.models import Job, Lead


def test_classify_job_endpoint_creates_job(client, db_session):
    # Setup: 3 unclassified leads
    for i in range(3):
        db_session.add(Lead(
            nome=f"Lead {i}", telefone="11999", rating=4.5, reviews_count=50,
            nicho="Pizzaria",
        ))
    db_session.commit()

    resp = client.post("/api/pipeline/classify", json={"scope": "unclassified"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["type"] == "classification"
    assert "id" in body


def test_run_classify_processes_unclassified_leads(db_session, classify_sessionlocal_patch):
    """Direct invocation of _run_classify to verify persistence path."""
    from app.routers.pipeline import _run_classify

    job = Job(type="classification", status="pending", params={"scope": "unclassified"})
    db_session.add(job)
    for i in range(3):
        db_session.add(Lead(
            nome=f"Pizzaria {i}", telefone="1199", rating=4.5, reviews_count=60,
            nicho="Pizzaria",
        ))
    db_session.commit()
    job_id = job.id

    with classify_sessionlocal_patch:
        _run_classify(job_id, {"scope": "unclassified", "force": False})

    db_session.expire_all()
    job_fresh = db_session.get(Job, job_id)
    assert job_fresh.status in ("done", "done_with_errors")
    leads = db_session.query(Lead).all()
    for l in leads:
        assert l.perfil_lead is not None
        assert l.nicho_canonico is not None


def test_run_classify_isolates_lead_failures(db_session, classify_sessionlocal_patch):
    """A lead that crashes consolidation should not take the whole job down."""
    from app.routers.pipeline import _run_classify

    job = Job(type="classification", status="pending", params={})
    db_session.add(job)
    # 2 valid leads + 1 edge-case lead (empty nome, no other data)
    db_session.add(Lead(nome="", telefone=None))  # likely DISQUALIFIED, but classify() handles it
    db_session.add(Lead(
        nome="A", telefone="1", rating=4.5, reviews_count=50, nicho="Pizzaria",
    ))
    db_session.add(Lead(
        nome="B", telefone="2", rating=4.5, reviews_count=50, nicho="Pizzaria",
    ))
    db_session.commit()
    job_id = job.id

    with classify_sessionlocal_patch:
        _run_classify(job_id, {"scope": "unclassified"})

    db_session.expire_all()
    job_fresh = db_session.get(Job, job_id)
    # Even with an edge-case lead, job completes (not failed/stalled)
    assert job_fresh.status in ("done", "done_with_errors")


def test_classify_job_returns_409_when_one_is_running(client, db_session):
    from app.models import Job
    running_job = Job(type="classification", status="running")
    db_session.add(running_job)
    db_session.commit()

    resp = client.post("/api/pipeline/classify", json={"scope": "unclassified"})
    assert resp.status_code == 409
    assert "already" in resp.json()["detail"].lower()


def test_classify_job_rejects_unknown_scope(client, db_session):
    """scope not in Literal → 422 from Pydantic validation."""
    resp = client.post("/api/pipeline/classify", json={"scope": "byJob"})
    assert resp.status_code == 422
