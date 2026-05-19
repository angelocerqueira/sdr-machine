"""Handlers executados pelo commit_action — 1 por action_type.

Registrados via `@register_handler("xxx")`. Importar este módulo dispara
auto-registro (side effect).

Signature comum: `handler(db, params, action_id) -> dict`. O `action_id`
é usado para idempotency_key estável (send_message) — handlers que não
precisam dele simplesmente ignoram o parâmetro.
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.mcp.pending_actions_service import register_handler
from app.models import (
    Conversation, Job, Lead,
)
from app.whatsapp.registry import (
    ProviderNotConfigured,
    UnknownProviderError,
    get_provider,
)
from app.whatsapp.services import append_message

logger = logging.getLogger(__name__)


@register_handler("send_message")
def handle_send_message(db: Session, params: dict, action_id: str) -> dict:
    conv_id = params["conversation_id"]
    body = params["body"]

    conv = db.get(Conversation, conv_id)
    if conv is None:
        return {"ok": False, "error": "Conversation not found"}

    try:
        adapter = get_provider(db, workspace_id=conv.workspace_id, provider=conv.provider)
    except (UnknownProviderError, ProviderNotConfigured) as exc:
        return {"ok": False, "error": f"provider unavailable: {exc}"}

    # Idempotency_key vinculado ao action_id: retry após crash entre send +
    # persist usa MESMA key → Evolution dedupa (não duplica msg).
    idem = f"mcp_action_{action_id}"
    try:
        sent = adapter.send_text(
            to_phone=conv.phone, body=body, idempotency_key=idem,
        )
    except Exception as exc:
        logger.exception("mcp.send_message.failed conv=%s", conv.id)
        return {"ok": False, "error": f"send failed: {exc}"}

    msg = append_message(
        db, conversation_id=conv.id, direction="out",
        provider_message_id=sent.provider_message_id, body=body,
        timestamp=sent.sent_at,
    )

    return {
        "ok": True,
        "message_id": msg.id,
        "provider_message_id": sent.provider_message_id,
        "sent_at": sent.sent_at.isoformat() if sent.sent_at else None,
    }


@register_handler("bulk_send")
def handle_bulk_send(db: Session, params: dict, action_id: str) -> dict:
    template = params["template"]
    recipients = params["recipient_lead_ids"]

    job = Job(
        type="mcp_bulk_send", status="pending",
        params={"template": template, "lead_ids": recipients},
        started_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    _spawn_bulk_send(job.id)
    return {"ok": True, "job_id": job.id, "recipient_count": len(recipients)}


@register_handler("delete_lead")
def handle_delete_lead(db: Session, params: dict, action_id: str) -> dict:
    # TODO(multi-tenant): Lead has no workspace_id column; deleting by id is workspace-global.
    # Workspace isolation is enforced at the prepare/get_action layer via token ownership.
    lead_id = params["lead_id"]
    lead = db.get(Lead, lead_id)
    if lead is None:
        return {"ok": False, "error": "Lead not found"}
    db.delete(lead)
    db.commit()
    return {"ok": True, "deleted_lead_id": lead_id}


@register_handler("delete_conversations")
def handle_delete_conversations(db: Session, params: dict, action_id: str) -> dict:
    ids = params["conversation_ids"]
    workspace_id = params.get("workspace_id")
    if not ids:
        return {"ok": True, "deleted_count": 0}
    q = db.query(Conversation).filter(Conversation.id.in_(ids))
    if workspace_id is not None:
        # Defense-in-depth: prepare/get_action já validam workspace via token,
        # mas filtramos aqui também pra fechar o vector de cross-tenant delete
        # caso params sejam manipulados.
        q = q.filter(Conversation.workspace_id == workspace_id)
    rows = q.all()
    for r in rows:
        db.delete(r)
    db.commit()
    return {"ok": True, "deleted_count": len(rows)}


@register_handler("run_pipeline")
def handle_run_pipeline(db: Session, params: dict, action_id: str) -> dict:
    stage = params["stage"]
    stage_params = params.get("params", {})

    job = Job(
        type=stage, status="pending", params=stage_params,
        started_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    _spawn_pipeline_stage(stage, job.id, stage_params)
    return {"ok": True, "job_id": job.id, "stage": stage}


@register_handler("classify_leads")
def handle_classify_leads(db: Session, params: dict, action_id: str) -> dict:
    job = Job(
        type="classify", status="pending", params=params,
        started_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    _spawn_classify(job.id, params)
    return {"ok": True, "job_id": job.id}


@register_handler("generate_lps")
def handle_generate_lps(db: Session, params: dict, action_id: str) -> dict:
    job = Job(
        type="generate", status="pending", params=params,
        started_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    _spawn_generate_lps(job.id, params)
    return {"ok": True, "job_id": job.id}


# ─── Spawners ───

def _spawn_pipeline_stage(stage: str, job_id: int, params: dict) -> None:
    from app.routers.pipeline import (
        _run_scrape, _run_enrich, _run_generate, _run_outreach,
        _spawn_job_thread,
    )
    runners = {
        "scrape": _run_scrape, "enrich": _run_enrich,
        "generate": _run_generate, "outreach": _run_outreach,
    }
    fn = runners.get(stage)
    if fn is None:
        return
    # Reusa _spawn_job_thread do pipeline router → pega _job_semaphore +
    # crash recovery sem reimplementar.
    _spawn_job_thread(fn, job_id, params)


def _spawn_bulk_send(job_id: int) -> None:
    logger.info("mcp.bulk_send.spawned job=%s (no-op stub)", job_id)


def _spawn_classify(job_id: int, params: dict) -> None:
    try:
        from app.routers.pipeline import _run_classify, _spawn_job_thread
    except ImportError:
        logger.warning("mcp.classify.no_runner job=%s", job_id)
        return
    _spawn_job_thread(_run_classify, job_id, params)


def _spawn_generate_lps(job_id: int, params: dict) -> None:
    from app.routers.pipeline import _run_generate, _spawn_job_thread
    _spawn_job_thread(_run_generate, job_id, params)
