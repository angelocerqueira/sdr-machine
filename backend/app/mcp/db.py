"""DB session helper pras tools MCP."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy.orm import Session

from app.database import SessionLocal


@contextmanager
def db_session() -> Iterator[Session]:
    """Session per call. Auto-rollback em exception, sempre close."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
