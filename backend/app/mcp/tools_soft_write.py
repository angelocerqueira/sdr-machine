"""MCP soft-write tools — execute direct, Claude confirma via prompt antes."""
from __future__ import annotations

from typing import Any

from app.mcp.context import get_workspace_id
from app.mcp.db import db_session
from app.models import (
    Conversation, Lead, WorkspaceProfile, WorkspaceTargeting,
)


_LEAD_ALLOWED_FIELDS = {
    "nome", "telefone", "email", "perfil_lead", "nicho_canonico",
    "endereco", "cidade", "categoria", "rating", "opportunity_score",
}


async def update_lead_status(ctx: Any, id: int, new_status: str) -> dict:
    workspace_id = get_workspace_id(ctx)  # noqa: F841  # TODO(multi-tenant): Lead has no workspace_id column; all lead operations are workspace-global. See spec §11.
    with db_session() as db:
        lead = db.get(Lead, id)
        if lead is None:
            return {"ok": False, "error": "Lead not found"}
        old_status = lead.status
        lead.status = new_status
        db.commit()
        return {
            "ok": True, "lead_id": id,
            "old_status": old_status, "new_status": new_status,
        }


async def update_lead_fields(ctx: Any, id: int, patch: dict) -> dict:
    workspace_id = get_workspace_id(ctx)  # noqa: F841  # TODO(multi-tenant): Lead has no workspace_id column; all lead operations are workspace-global. See spec §11.
    with db_session() as db:
        lead = db.get(Lead, id)
        if lead is None:
            return {"ok": False, "error": "Lead not found"}
        applied = {}
        for k, v in patch.items():
            if k in _LEAD_ALLOWED_FIELDS:
                setattr(lead, k, v)
                applied[k] = v
        db.commit()
        return {"ok": True, "lead_id": id, "applied": applied}


async def mark_conversation_read(ctx: Any, conv_id: int) -> dict:
    workspace_id = get_workspace_id(ctx)
    with db_session() as db:
        conv = db.query(Conversation).filter_by(
            id=conv_id, workspace_id=workspace_id,
        ).first()
        if conv is None:
            return {"ok": False, "error": "Conversation not found"}
        previous = conv.unread_count
        conv.unread_count = 0
        db.commit()
        return {
            "ok": True, "conversation_id": conv_id, "previous_unread": previous,
        }


async def update_workspace_profile(ctx: Any, patch: dict) -> dict:
    workspace_id = get_workspace_id(ctx)
    with db_session() as db:
        row = db.query(WorkspaceProfile).filter_by(workspace_id=workspace_id).first()
        if row is None:
            row = WorkspaceProfile(workspace_id=workspace_id)
            db.add(row)
        for k, v in patch.items():
            if hasattr(row, k):
                setattr(row, k, v)
        db.commit()
        return {"ok": True, "workspace_id": workspace_id, "applied": list(patch.keys())}


async def update_workspace_targeting(ctx: Any, patch: dict) -> dict:
    workspace_id = get_workspace_id(ctx)
    with db_session() as db:
        row = db.query(WorkspaceTargeting).filter_by(workspace_id=workspace_id).first()
        if row is None:
            row = WorkspaceTargeting(
                workspace_id=workspace_id, target_niches=[], target_cities=[],
            )
            db.add(row)
        for k, v in patch.items():
            if hasattr(row, k):
                setattr(row, k, v)
        db.commit()
        return {"ok": True, "workspace_id": workspace_id, "applied": list(patch.keys())}


def register_soft_write_tools(server) -> None:
    server.tool(name="update_lead_status")(update_lead_status)
    server.tool(name="update_lead_fields")(update_lead_fields)
    server.tool(name="mark_conversation_read")(mark_conversation_read)
    server.tool(name="update_workspace_profile")(update_workspace_profile)
    server.tool(name="update_workspace_targeting")(update_workspace_targeting)
