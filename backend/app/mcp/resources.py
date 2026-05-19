"""MCP Resources — URI-style read-only endpoints."""
from __future__ import annotations

import json

from mcp.server.fastmcp import Context

from app.mcp.context import get_workspace_id
from app.mcp.db import db_session
from app.mcp.tools_conversations import get_conversation, list_conversations
from app.mcp.tools_jobs import get_job, list_jobs
from app.mcp.tools_leads import get_lead, list_landing_pages, list_leads
from app.mcp.tools_pending import list_pending_actions
from app.mcp.tools_workspace import workspace_profile, workspace_targeting
from app.models import IntegrationSettings


def _json(data) -> str:
    if hasattr(data, "model_dump_json"):
        return data.model_dump_json(indent=2)
    if hasattr(data, "model_dump"):
        return json.dumps(data.model_dump(), default=str, indent=2)
    return json.dumps(data, default=str, indent=2)


async def leads_list_resource(ctx: Context) -> str:
    result = await list_leads(ctx, filter=None, limit=50, offset=0)
    return _json(result)


async def lead_detail_resource(ctx: Context, lead_id: int) -> str:
    result = await get_lead(ctx, id=lead_id)
    if result is None:
        return json.dumps({"not_found": True, "id": lead_id})
    return _json(result)


async def lead_landing_pages_resource(ctx: Context, lead_id: int) -> str:
    result = await list_landing_pages(ctx, lead_id=lead_id)
    return _json([r.model_dump() for r in result])


async def conversations_list_resource(ctx: Context) -> str:
    result = await list_conversations(ctx, filter=None)
    return _json([r.model_dump() for r in result])


async def conversation_detail_resource(ctx: Context, conv_id: int) -> str:
    result = await get_conversation(ctx, id=conv_id)
    if result is None:
        return json.dumps({"not_found": True, "id": conv_id})
    return _json(result)


async def jobs_list_resource(ctx: Context) -> str:
    result = await list_jobs(ctx, status=None, type=None, limit=20)
    return _json([r.model_dump() for r in result])


async def job_detail_resource(ctx: Context, job_id: int) -> str:
    result = await get_job(ctx, id=job_id)
    if result is None:
        return json.dumps({"not_found": True, "id": job_id})
    return _json(result)


async def workspace_profile_resource(ctx: Context) -> str:
    result = await workspace_profile(ctx)
    return _json(result)


async def workspace_targeting_resource(ctx: Context) -> str:
    result = await workspace_targeting(ctx)
    return _json(result)


async def workspace_integrations_resource(ctx: Context) -> str:
    """NUNCA retorna secrets em plain."""
    workspace_id = get_workspace_id(ctx)
    with db_session() as db:
        rows = db.query(IntegrationSettings).filter_by(workspace_id=workspace_id).all()
        out = []
        for r in rows:
            cfg = r.config or {}
            from app.integrations.schemas import SECRET_FIELDS
            secrets = SECRET_FIELDS.get(r.provider, set())
            masked = {k: v for k, v in cfg.items() if k not in secrets}
            for field in secrets:
                cipher = cfg.get(field)
                masked[f"has_{field}"] = bool(cipher)
                if cipher:
                    try:
                        from app.integrations.crypto import decrypt
                        val = decrypt(cipher)
                        masked[f"{field}_last4"] = val[-4:] if val and len(val) >= 4 else None
                    except Exception:
                        masked[f"{field}_decrypt_error"] = True
            out.append({
                "provider": r.provider,
                "enabled": r.enabled,
                "config": masked,
                "last_tested_at": r.last_tested_at.isoformat() if r.last_tested_at else None,
            })
        return json.dumps(out, default=str, indent=2)


async def pending_actions_list_resource(ctx: Context) -> str:
    result = await list_pending_actions(ctx, include_expired=False)
    return _json([r.model_dump() for r in result])


def register_resources(server) -> None:
    """Registra resources no FastMCP server."""
    server.resource("leads://list")(leads_list_resource)
    server.resource("leads://{lead_id}")(lead_detail_resource)
    server.resource("leads://{lead_id}/landing-pages")(lead_landing_pages_resource)
    server.resource("conversations://list")(conversations_list_resource)
    server.resource("conversations://{conv_id}")(conversation_detail_resource)
    server.resource("jobs://list")(jobs_list_resource)
    server.resource("jobs://{job_id}")(job_detail_resource)
    server.resource("workspace://profile")(workspace_profile_resource)
    server.resource("workspace://targeting")(workspace_targeting_resource)
    server.resource("workspace://integrations")(workspace_integrations_resource)
    server.resource("pending_actions://list")(pending_actions_list_resource)
