from app.mcp.db import db_session
from app.models import Lead


def test_db_session_yields_session():
    with db_session() as db:
        count = db.query(Lead).count()
        assert isinstance(count, int)


def test_db_session_rollback_on_exception():
    try:
        with db_session() as db:
            db.add(Lead(nome="rollback-test", telefone="x", status="scraped"))
            raise RuntimeError("force rollback")
    except RuntimeError:
        pass

    with db_session() as db:
        count = db.query(Lead).filter_by(nome="rollback-test").count()
        assert count == 0
