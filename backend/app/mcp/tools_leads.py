"""MCP READ tools — Leads domain."""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import or_

from app.mcp.context import get_workspace_id
from app.mcp.db import db_session
from app.mcp.schemas import (
    LandingPageSummary,
    LeadFull,
    LeadListResult,
    LeadSummary,
)
from app.models import LandingPage, Lead


async def list_leads(
    ctx: Any,
    filter: Optional[dict] = None,
    limit: int = 20,
    offset: int = 0,
) -> LeadListResult:
    """Lista leads do workspace com filtros opcionais."""
    workspace_id = get_workspace_id(ctx)  # noqa: F841 — pra quando Lead.workspace_id existir
    f = filter or {}

    with db_session() as db:
        q = db.query(Lead)
        if f.get("status"):
            q = q.filter(Lead.status == f["status"])
        if f.get("nicho"):
            q = q.filter(Lead.nicho == f["nicho"])
        if f.get("cidade"):
            q = q.filter(Lead.cidade == f["cidade"])
        if f.get("score_min") is not None:
            q = q.filter(Lead.opportunity_score >= f["score_min"])
        if f.get("has_email") is True:
            q = q.filter(Lead.email.isnot(None), Lead.email != "")
        if f.get("search"):
            pat = f"%{f['search']}%"
            q = q.filter(or_(Lead.nome.ilike(pat), Lead.telefone.ilike(pat)))

        total = q.count()
        rows = q.order_by(Lead.id.desc()).limit(limit).offset(offset).all()

        return LeadListResult(
            items=[LeadSummary.from_lead(r) for r in rows],
            total=total,
            page=offset // max(limit, 1) + 1 if limit > 0 else 1,
            per_page=limit,
        )


async def get_lead(ctx: Any, id: int) -> Optional[LeadFull]:
    workspace_id = get_workspace_id(ctx)  # noqa: F841

    with db_session() as db:
        lead = db.get(Lead, id)
        if lead is None:
            return None
        return LeadFull.model_validate(lead)


async def list_landing_pages(
    ctx: Any, lead_id: int, limit: int = 50,
) -> list[LandingPageSummary]:
    workspace_id = get_workspace_id(ctx)  # noqa: F841

    with db_session() as db:
        rows = (
            db.query(LandingPage)
            .filter_by(lead_id=lead_id)
            .order_by(LandingPage.version.desc())
            .limit(limit)
            .all()
        )
        return [
            LandingPageSummary(
                id=r.id, lead_id=r.lead_id, version=r.version,
                is_active=r.is_active, created_at=r.created_at,
            )
            for r in rows
        ]


async def get_lp_html(ctx: Any, lp_id: int) -> Optional[dict]:
    workspace_id = get_workspace_id(ctx)  # noqa: F841

    with db_session() as db:
        lp = db.get(LandingPage, lp_id)
        if lp is None:
            return None
        from app.config import settings as app_settings
        lead = db.get(Lead, lp.lead_id)
        public_url = None
        if lead and getattr(lead, "public_id", None):
            base = (app_settings.api_url or "http://localhost:8000").rstrip("/")
            public_url = f"{base}/api/leads/p/{lead.public_id}/lp"
        return {
            "html": lp.html,
            "public_url": public_url,
            "version": lp.version,
            "is_active": lp.is_active,
        }


def register_leads_tools(server) -> None:
    """Registra tools no FastMCP server."""
    server.tool(name="list_leads")(list_leads)
    server.tool(name="get_lead")(get_lead)
    server.tool(name="list_landing_pages")(list_landing_pages)
    server.tool(name="get_lp_html")(get_lp_html)
