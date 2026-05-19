"""MCP READ tool — pending actions."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.mcp.context import get_workspace_id
from app.mcp.db import db_session
from app.mcp.schemas import PendingActionOut
from app.models import PendingAction


async def list_pending_actions(
    ctx: Any, include_expired: bool = False,
) -> list[PendingActionOut]:
    ws = get_workspace_id(ctx)
    with db_session() as db:
        q = (
            db.query(PendingAction)
            .filter_by(workspace_id=ws)
            .filter(PendingAction.committed_at.is_(None))
            .filter(PendingAction.cancelled_at.is_(None))
        )
        if not include_expired:
            q = q.filter(PendingAction.expires_at > datetime.utcnow())
        rows = q.order_by(PendingAction.created_at.desc()).all()
        return [
            PendingActionOut(
                id=r.id, action_type=r.action_type, preview=r.preview,
                created_at=r.created_at, expires_at=r.expires_at,
                committed_at=r.committed_at, cancelled_at=r.cancelled_at,
            )
            for r in rows
        ]


def register_pending_tools(server) -> None:
    server.tool(name="list_pending_actions")(list_pending_actions)
