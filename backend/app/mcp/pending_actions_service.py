"""Pending Actions service — CRUD + handler registry pra two-phase commit."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

from sqlalchemy.orm import Session

from app.models import PendingAction

logger = logging.getLogger(__name__)

ACTION_TTL = timedelta(minutes=5)

HandlerFn = Callable[[Session, dict, str], Dict[str, Any]]
HANDLERS: Dict[str, HandlerFn] = {}


def register_handler(action_type: str):
    def decorator(fn: HandlerFn) -> HandlerFn:
        if action_type in HANDLERS:
            logger.warning("mcp.handler.override action_type=%s", action_type)
        HANDLERS[action_type] = fn
        return fn
    return decorator


def create_action(
    db: Session,
    *,
    workspace_id: int,
    action_type: str,
    params: dict,
    preview: dict,
    token_hash: str,
    ttl: timedelta = ACTION_TTL,
) -> PendingAction:
    pa = PendingAction(
        id=uuid.uuid4().hex[:32],
        workspace_id=workspace_id,
        action_type=action_type,
        params=params,
        preview=preview,
        created_by_token_hash=token_hash,
        expires_at=datetime.utcnow() + ttl,
    )
    db.add(pa)
    db.commit()
    db.refresh(pa)
    return pa


def get_action(
    db: Session,
    *,
    action_id: str,
    workspace_id: int,
    token_hash: str,
) -> Optional[PendingAction]:
    row = db.query(PendingAction).filter_by(id=action_id).first()
    if row is None:
        return None
    if row.workspace_id != workspace_id:
        return None
    if row.created_by_token_hash != token_hash:
        return None
    if row.cancelled_at is not None:
        return None
    if row.committed_at is None and row.expires_at <= datetime.utcnow():
        return None
    return row


def commit_action_row(
    db: Session, *, action_id: str, result: dict,
) -> None:
    row = db.query(PendingAction).filter_by(id=action_id).first()
    if row is None:
        return
    if row.committed_at is not None:
        return
    row.committed_at = datetime.utcnow()
    row.result = result
    db.commit()


def cancel_action_row(db: Session, *, action_id: str) -> bool:
    row = db.query(PendingAction).filter_by(id=action_id).first()
    if row is None or row.committed_at is not None or row.cancelled_at is not None:
        return False
    row.cancelled_at = datetime.utcnow()
    db.commit()
    return True
