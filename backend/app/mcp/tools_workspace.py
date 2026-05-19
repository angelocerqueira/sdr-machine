"""MCP READ tools — workspace profile + targeting."""
from __future__ import annotations

from typing import Any

from app.mcp.context import get_workspace_id
from app.mcp.db import db_session
from app.mcp.schemas import WorkspaceProfileOut, WorkspaceTargetingOut
from app.models import WorkspaceProfile, WorkspaceTargeting


async def workspace_profile(ctx: Any) -> WorkspaceProfileOut:
    ws = get_workspace_id(ctx)
    with db_session() as db:
        row = db.query(WorkspaceProfile).filter_by(workspace_id=ws).first()
        if row is None:
            return WorkspaceProfileOut(
                business_name=None, your_name=None, your_email=None,
                your_whatsapp=None, your_website=None, legal_basis=None,
            )
        return WorkspaceProfileOut(
            business_name=row.business_name, your_name=row.your_name,
            your_email=row.your_email, your_whatsapp=row.your_whatsapp,
            your_website=row.your_website, legal_basis=row.legal_basis,
        )


async def workspace_targeting(ctx: Any) -> WorkspaceTargetingOut:
    ws = get_workspace_id(ctx)
    with db_session() as db:
        row = db.query(WorkspaceTargeting).filter_by(workspace_id=ws).first()
        if row is None:
            return WorkspaceTargetingOut(
                target_niches=[], target_cities=[], min_rating=None,
                max_results_per_search=None, opportunity_score_threshold=None,
            )
        return WorkspaceTargetingOut(
            target_niches=row.target_niches or [],
            target_cities=row.target_cities or [],
            min_rating=row.min_rating,
            max_results_per_search=row.max_results_per_search,
            opportunity_score_threshold=row.opportunity_score_threshold,
        )


def register_workspace_tools(server) -> None:
    server.tool(name="workspace_profile")(workspace_profile)
    server.tool(name="workspace_targeting")(workspace_targeting)
