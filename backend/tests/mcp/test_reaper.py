from datetime import datetime, timedelta

from app.models import PendingAction
from app.mcp.reaper import reap_expired_actions


def test_reaper_marks_expired_as_cancelled(db):
    past = datetime.utcnow() - timedelta(minutes=10)
    future = datetime.utcnow() + timedelta(minutes=5)
    db.add_all([
        PendingAction(
            id="exp1", workspace_id=1, action_type="x",
            params={}, preview={}, created_by_token_hash="h",
            expires_at=past,
        ),
        PendingAction(
            id="exp2", workspace_id=1, action_type="x",
            params={}, preview={}, created_by_token_hash="h",
            expires_at=past,
        ),
        PendingAction(
            id="active", workspace_id=1, action_type="x",
            params={}, preview={}, created_by_token_hash="h",
            expires_at=future,
        ),
    ])
    db.commit()

    reaped = reap_expired_actions(db)
    assert reaped == 2

    rows = {r.id: r for r in db.query(PendingAction).all()}
    assert rows["exp1"].cancelled_at is not None
    assert rows["exp2"].cancelled_at is not None
    assert rows["active"].cancelled_at is None


def test_reaper_ignores_already_committed(db):
    past = datetime.utcnow() - timedelta(minutes=10)
    db.add(PendingAction(
        id="commited-but-expired", workspace_id=1, action_type="x",
        params={}, preview={}, created_by_token_hash="h",
        expires_at=past, committed_at=datetime.utcnow(),
    ))
    db.commit()
    reaped = reap_expired_actions(db)
    assert reaped == 0


def test_reaper_ignores_already_cancelled(db):
    past = datetime.utcnow() - timedelta(minutes=10)
    db.add(PendingAction(
        id="cancelled-and-expired", workspace_id=1, action_type="x",
        params={}, preview={}, created_by_token_hash="h",
        expires_at=past, cancelled_at=datetime.utcnow(),
    ))
    db.commit()
    reaped = reap_expired_actions(db)
    assert reaped == 0
