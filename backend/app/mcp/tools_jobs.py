"""MCP READ tools — Jobs."""
from __future__ import annotations

from typing import Any, Optional

from app.mcp.context import get_workspace_id
from app.mcp.db import db_session
from app.mcp.schemas import JobFull, JobSummary
from app.models import Job


async def list_jobs(
    ctx: Any,
    status: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = 10,
) -> list[JobSummary]:
    workspace_id = get_workspace_id(ctx)  # noqa: F841

    with db_session() as db:
        q = db.query(Job)
        if status:
            q = q.filter(Job.status == status)
        if type:
            q = q.filter(Job.type == type)
        rows = q.order_by(Job.id.desc()).limit(limit).all()
        return [
            JobSummary(
                id=r.id, type=r.type, status=r.status,
                progress=getattr(r, "progress", None),
                started_at=r.started_at, finished_at=r.finished_at,
                error_message=r.error_message,
            )
            for r in rows
        ]


async def get_job(ctx: Any, id: int) -> Optional[JobFull]:
    workspace_id = get_workspace_id(ctx)  # noqa: F841

    with db_session() as db:
        r = db.get(Job, id)
        if r is None:
            return None
        return JobFull(
            id=r.id, type=r.type, status=r.status,
            progress=getattr(r, "progress", None),
            started_at=r.started_at, finished_at=r.finished_at,
            error_message=r.error_message,
            params=r.params, result_summary=r.result_summary,
        )


def register_jobs_tools(server) -> None:
    server.tool(name="list_jobs")(list_jobs)
    server.tool(name="get_job")(get_job)
