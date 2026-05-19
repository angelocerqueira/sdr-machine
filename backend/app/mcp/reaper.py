"""Reaper de pending_actions expiradas — marca cancelled_at sem deletar."""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import PendingAction

logger = logging.getLogger(__name__)


def reap_expired_actions(db: Session) -> int:
    rows = (
        db.query(PendingAction)
        .filter(PendingAction.expires_at <= datetime.utcnow())
        .filter(PendingAction.committed_at.is_(None))
        .filter(PendingAction.cancelled_at.is_(None))
        .all()
    )
    now = datetime.utcnow()
    for r in rows:
        r.cancelled_at = now
    if rows:
        db.commit()
        logger.info("mcp.reaper.reaped count=%d", len(rows))
    return len(rows)
