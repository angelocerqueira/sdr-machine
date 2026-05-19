"""Conftest pra testes MCP — alinha db_session() com a SQLite test engine."""
from unittest.mock import patch

import pytest

from tests.conftest import TestSession


@pytest.fixture(autouse=True)
def _patch_mcp_session_local():
    """O helper db_session() em app.mcp.db usa app.database.SessionLocal,
    que aponta pra Postgres. Em testes precisamos redirecionar pra TestSession
    (SQLite in-memory) pra os tools enxergarem os mesmos dados que a fixture `db`.
    """
    with patch("app.mcp.db.SessionLocal", new=TestSession):
        yield
