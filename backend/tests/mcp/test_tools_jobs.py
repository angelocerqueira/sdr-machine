import asyncio
from datetime import datetime
from unittest.mock import Mock

from mcp.server.auth.provider import AccessToken

from app.models import Job
from app.mcp.tools_jobs import list_jobs, get_job


def _ctx():
    ctx = Mock()
    user = Mock()
    user.access_token = AccessToken(
        token="x" * 64, client_id="mcp-1",
        scopes=["mcp:workspace:1"], expires_at=None, resource=None,
    )
    ctx.request_context.request.user = user
    return ctx


def test_list_jobs_empty(db):
    result = asyncio.run(list_jobs(_ctx(), status=None, type=None, limit=10))
    assert result == []


def test_list_jobs_filter_status(db):
    db.add_all([
        Job(type="scrape", status="done", params={}, started_at=datetime.utcnow()),
        Job(type="enrich", status="running", params={}, started_at=datetime.utcnow()),
    ])
    db.commit()
    result = asyncio.run(list_jobs(_ctx(), status="running", type=None, limit=10))
    assert len(result) == 1
    assert result[0].status == "running"


def test_get_job_returns_full(db):
    job = Job(
        type="scrape", status="done", params={"nichos": ["dentista"]},
        result_summary={"total": 10}, started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    result = asyncio.run(get_job(_ctx(), id=job.id))
    assert result is not None
    assert result.params == {"nichos": ["dentista"]}
    assert result.result_summary == {"total": 10}


def test_get_job_not_found(db):
    result = asyncio.run(get_job(_ctx(), id=9999))
    assert result is None
