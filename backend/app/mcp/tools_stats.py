"""MCP READ tools — dashboard stats + conversion funnel."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Literal

from sqlalchemy import func

from app.mcp.context import get_workspace_id
from app.mcp.db import db_session
from app.mcp.schemas import DashboardStats
from app.models import Lead


async def dashboard_stats(ctx: Any) -> DashboardStats:
    workspace_id = get_workspace_id(ctx)  # noqa: F841

    with db_session() as db:
        total = db.query(Lead).count()
        if total == 0:
            return DashboardStats(
                total_leads=0, by_status={}, avg_score=None,
                conversion_rate=None, leads_by_day=[],
            )
        by_status = dict(
            db.query(Lead.status, func.count(Lead.id)).group_by(Lead.status).all()
        )
        avg = db.query(func.avg(Lead.opportunity_score)).scalar()
        since = datetime.utcnow() - timedelta(days=14)
        by_day_rows = (
            db.query(
                func.date(Lead.created_at).label("day"),
                func.count(Lead.id).label("count"),
            )
            .filter(Lead.created_at >= since)
            .group_by(func.date(Lead.created_at))
            .order_by("day")
            .all()
        )
        leads_by_day = [{"day": str(r.day), "count": r.count} for r in by_day_rows]
        won_count = db.query(Lead).filter(
            Lead.status.in_(["closed", "won", "delivered"])
        ).count()
        conv_rate = (won_count / total) if total > 0 else None
        return DashboardStats(
            total_leads=total, by_status=by_status,
            avg_score=float(avg) if avg is not None else None,
            conversion_rate=conv_rate, leads_by_day=leads_by_day,
        )


async def conversion_funnel(
    ctx: Any, period: Literal["7d", "30d", "90d"] = "30d",
) -> dict:
    workspace_id = get_workspace_id(ctx)  # noqa: F841
    days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
    since = datetime.utcnow() - timedelta(days=days)

    with db_session() as db:
        rows = (
            db.query(Lead.status, func.count(Lead.id))
            .filter(Lead.created_at >= since)
            .group_by(Lead.status)
            .all()
        )
        return {
            "period": period, "since": since.isoformat(),
            "by_status": dict(rows),
        }


def register_stats_tools(server) -> None:
    server.tool(name="dashboard_stats")(dashboard_stats)
    server.tool(name="conversion_funnel")(conversion_funnel)
