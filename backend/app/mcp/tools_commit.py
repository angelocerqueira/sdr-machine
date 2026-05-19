"""MCP commit_action + cancel_action — phase 2 do two-phase commit."""
from __future__ import annotations

import logging
from typing import Any

from app.mcp.context import get_workspace_id
from app.mcp.db import db_session
from app.mcp.pending_actions_service import (
    HANDLERS,
    cancel_action_row,
    commit_action_row,
    get_action,
)
from app.mcp.tokens import hash_token

logger = logging.getLogger(__name__)


def _token_hash_from_ctx(ctx: Any) -> str:
    try:
        user = ctx.request_context.request.user
        plain = user.access_token.token if user else ""
    except AttributeError:
        plain = ""
    return hash_token(plain) if plain else ""


async def commit_action(ctx: Any, action_id: str) -> dict:
    workspace_id = get_workspace_id(ctx)
    token_hash = _token_hash_from_ctx(ctx)

    with db_session() as db:
        row = get_action(
            db, action_id=action_id, workspace_id=workspace_id, token_hash=token_hash,
        )
        if row is None:
            return {"ok": False, "error": "Action not found or invalid"}

        if row.committed_at is not None:
            return {
                "ok": True, "already_committed": True,
                "committed_at": row.committed_at.isoformat(),
                "result": row.result,
            }

        handler = HANDLERS.get(row.action_type)
        if handler is None:
            logger.error("mcp.commit.no_handler action_type=%s id=%s", row.action_type, action_id)
            return {"ok": False, "error": f"No handler for {row.action_type}"}

        try:
            result = handler(db, row.params, row.id)
        except Exception as exc:
            logger.exception("mcp.commit.handler_failed id=%s", action_id)
            return {"ok": False, "error": f"Handler failed: {exc}"}

        commit_action_row(db, action_id=action_id, result=result)

        return {"ok": True, "action_id": action_id, "result": result}


async def cancel_action(ctx: Any, action_id: str) -> dict:
    workspace_id = get_workspace_id(ctx)
    token_hash = _token_hash_from_ctx(ctx)

    with db_session() as db:
        row = get_action(
            db, action_id=action_id, workspace_id=workspace_id, token_hash=token_hash,
        )
        if row is None:
            return {"ok": False, "error": "Action not found or invalid"}
        ok = cancel_action_row(db, action_id=action_id)
        return {"ok": ok, "action_id": action_id}


def register_commit_tools(server) -> None:
    server.tool(name="commit_action")(commit_action)
    server.tool(name="cancel_action")(cancel_action)
