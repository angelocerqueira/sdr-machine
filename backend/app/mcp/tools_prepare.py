"""MCP prepare_* tools — montam preview + persistem pending_action."""
from __future__ import annotations

from typing import Any, Literal, Optional

from app.mcp.context import get_workspace_id
from app.mcp.db import db_session
from app.mcp.pending_actions_service import create_action
from app.mcp.tokens import hash_token
from app.models import Conversation, ConversationMessage, Lead


def _token_hash_from_ctx(ctx: Any) -> str:
    try:
        user = ctx.request_context.request.user
        plain = user.access_token.token if user else ""
    except AttributeError:
        plain = ""
    return hash_token(plain) if plain else ""


def _result(action_id: str, preview: dict, row) -> dict:
    return {
        "action_id": action_id,
        "preview": preview,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
    }


async def prepare_send_message(
    ctx: Any, conversation_id: int, body: str,
) -> dict:
    workspace_id = get_workspace_id(ctx)
    token_hash = _token_hash_from_ctx(ctx)

    with db_session() as db:
        conv = db.query(Conversation).filter_by(
            id=conversation_id, workspace_id=workspace_id,
        ).first()
        if conv is None:
            return {"error": "Conversation not found"}
        lead = db.get(Lead, conv.lead_id)
        preview = {
            "to_phone": conv.phone,
            "body_rendered": body,
            "lead_nome": lead.nome if lead else None,
            "conversation_id": conversation_id,
        }
        params = {"conversation_id": conversation_id, "body": body}
        row = create_action(
            db, workspace_id=workspace_id, action_type="send_message",
            params=params, preview=preview, token_hash=token_hash,
        )
        return _result(row.id, preview, row)


async def prepare_bulk_send(
    ctx: Any, recipient_lead_ids: list[int], template: str,
) -> dict:
    workspace_id = get_workspace_id(ctx)
    token_hash = _token_hash_from_ctx(ctx)

    with db_session() as db:
        sample_leads = (
            db.query(Lead).filter(Lead.id.in_(recipient_lead_ids)).limit(5).all()
        )
        preview = {
            "count": len(recipient_lead_ids),
            "recipients_sample": [
                {"id": l.id, "nome": l.nome, "telefone": l.telefone}
                for l in sample_leads
            ],
            "template": template,
            "estimated_minutes": max(1, len(recipient_lead_ids) // 30),
        }
        row = create_action(
            db, workspace_id=workspace_id, action_type="bulk_send",
            params={"recipient_lead_ids": recipient_lead_ids, "template": template},
            preview=preview, token_hash=token_hash,
        )
        return _result(row.id, preview, row)


async def prepare_delete_lead(ctx: Any, lead_id: int) -> dict:
    # TODO(multi-tenant): Lead has no workspace_id column; lookup is workspace-global.
    # Workspace isolation is enforced at the get_action layer via token ownership. See spec §11.
    workspace_id = get_workspace_id(ctx)
    token_hash = _token_hash_from_ctx(ctx)

    with db_session() as db:
        lead = db.get(Lead, lead_id)
        if lead is None:
            return {"error": "Lead not found"}

        msgs_count = (
            db.query(ConversationMessage)
            .join(Conversation, Conversation.id == ConversationMessage.conversation_id)
            .filter(Conversation.lead_id == lead_id)
            .count()
        )
        from app.models import LandingPage, OutreachMessage
        lps_count = db.query(LandingPage).filter_by(lead_id=lead_id).count()
        outreach_count = db.query(OutreachMessage).filter_by(lead_id=lead_id).count()
        convs_count = db.query(Conversation).filter_by(lead_id=lead_id).count()

        preview = {
            "lead_summary": {
                "id": lead.id, "nome": lead.nome, "telefone": lead.telefone,
                "status": lead.status, "score": lead.opportunity_score,
            },
            "related_data": {
                "conversations": convs_count,
                "messages": msgs_count,
                "landing_pages": lps_count,
                "outreach_messages": outreach_count,
            },
        }
        row = create_action(
            db, workspace_id=workspace_id, action_type="delete_lead",
            params={"lead_id": lead_id}, preview=preview, token_hash=token_hash,
        )
        return _result(row.id, preview, row)


async def prepare_delete_conversations(
    ctx: Any, conversation_ids: list[int],
) -> dict:
    workspace_id = get_workspace_id(ctx)
    token_hash = _token_hash_from_ctx(ctx)

    with db_session() as db:
        rows = (
            db.query(Conversation)
            .filter(
                Conversation.id.in_(conversation_ids),
                Conversation.workspace_id == workspace_id,
            )
            .limit(3)
            .all()
        )
        preview = {
            "count": len(conversation_ids),
            "sample": [
                {"id": c.id, "phone": c.phone, "lead_id": c.lead_id} for c in rows
            ],
        }
        row = create_action(
            db, workspace_id=workspace_id, action_type="delete_conversations",
            params={"conversation_ids": conversation_ids, "workspace_id": workspace_id},
            preview=preview, token_hash=token_hash,
        )
        return _result(row.id, preview, row)


async def prepare_run_pipeline(
    ctx: Any, stage: Literal["scrape", "enrich", "generate", "outreach"],
    params: Optional[dict] = None,
) -> dict:
    workspace_id = get_workspace_id(ctx)
    token_hash = _token_hash_from_ctx(ctx)
    stage_params = params or {}

    with db_session() as db:
        if stage == "enrich":
            count = db.query(Lead).filter(Lead.status == "scraped").count()
        elif stage == "generate":
            count = db.query(Lead).filter(Lead.status == "enriched").count()
        elif stage == "outreach":
            count = db.query(Lead).filter(Lead.status == "lp_generated").count()
        else:
            count = None

        preview = {
            "stage": stage,
            "estimated_eligible_count": count,
            "params": stage_params,
            "estimated_minutes": (count or 50) // 30 if count else 5,
            "estimated_cost_usd": None,
        }
        row = create_action(
            db, workspace_id=workspace_id, action_type="run_pipeline",
            params={"stage": stage, "params": stage_params},
            preview=preview, token_hash=token_hash,
        )
        return _result(row.id, preview, row)


async def prepare_classify_leads(
    ctx: Any, filter: Optional[dict] = None,
    level: Literal["light", "full"] = "full",
) -> dict:
    workspace_id = get_workspace_id(ctx)
    token_hash = _token_hash_from_ctx(ctx)
    f = filter or {}

    with db_session() as db:
        q = db.query(Lead)
        if f.get("status"):
            q = q.filter(Lead.status == f["status"])
        count = q.count()
        cost_estimate = round(count * 0.005, 2)

        preview = {
            "count": count, "level": level, "filter": f,
            "estimated_llm_calls": count,
            "estimated_cost_usd": cost_estimate,
        }
        row = create_action(
            db, workspace_id=workspace_id, action_type="classify_leads",
            params={"filter": f, "level": level},
            preview=preview, token_hash=token_hash,
        )
        return _result(row.id, preview, row)


async def prepare_generate_lps(
    ctx: Any, filter: Optional[dict] = None,
) -> dict:
    workspace_id = get_workspace_id(ctx)
    token_hash = _token_hash_from_ctx(ctx)
    f = filter or {}

    with db_session() as db:
        q = db.query(Lead)
        if f.get("status"):
            q = q.filter(Lead.status == f["status"])
        else:
            q = q.filter(Lead.status == "enriched")
        count = q.count()
        cost_estimate = round(count * 0.03, 2)

        preview = {
            "count": count, "filter": f,
            "estimated_cost_usd": cost_estimate,
        }
        row = create_action(
            db, workspace_id=workspace_id, action_type="generate_lps",
            params={"filter": f}, preview=preview, token_hash=token_hash,
        )
        return _result(row.id, preview, row)


def register_prepare_tools(server) -> None:
    server.tool(name="prepare_send_message")(prepare_send_message)
    server.tool(name="prepare_bulk_send")(prepare_bulk_send)
    server.tool(name="prepare_delete_lead")(prepare_delete_lead)
    server.tool(name="prepare_delete_conversations")(prepare_delete_conversations)
    server.tool(name="prepare_run_pipeline")(prepare_run_pipeline)
    server.tool(name="prepare_classify_leads")(prepare_classify_leads)
    server.tool(name="prepare_generate_lps")(prepare_generate_lps)
