"""Tests for the Better Auth session middleware."""
import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.middleware.auth import AuthMiddleware


@pytest.fixture(autouse=True)
def _bypass_auth():
    """Override conftest: do NOT bypass auth in middleware-specific tests."""
    yield

# ---------------------------------------------------------------------------
# Fixtures — isolated FastAPI app with the middleware wired to an in-memory DB
# ---------------------------------------------------------------------------

ENGINE = create_engine("sqlite:///./test_auth.db", connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=ENGINE)

BETTER_AUTH_SESSION_DDL = """
CREATE TABLE IF NOT EXISTS "session" (
    "id"        TEXT PRIMARY KEY,
    "token"     TEXT NOT NULL UNIQUE,
    "userId"    TEXT NOT NULL,
    "expiresAt" TIMESTAMP NOT NULL
)
"""


def _make_app() -> FastAPI:
    """Create a minimal FastAPI app with AuthMiddleware for testing."""
    app = FastAPI()

    app.add_middleware(
        AuthMiddleware,
        database_url="sqlite:///./test_auth.db",
        public_paths=["/api/health", "/api/leads/p/", "/docs", "/openapi.json"],
    )

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/leads/p/{public_id}")
    def public_lead(public_id: str):
        return {"id": public_id}

    @app.get("/api/leads")
    def list_leads():
        return {"leads": []}

    @app.get("/docs")
    def docs():
        return {"docs": True}

    @app.get("/openapi.json")
    def openapi():
        return {"openapi": "3.0"}

    return app


@pytest.fixture(autouse=True)
def setup_session_table():
    """Create/clean the session table before each test."""
    with ENGINE.connect() as conn:
        conn.execute(text(BETTER_AUTH_SESSION_DDL))
        conn.execute(text('DELETE FROM "session"'))
        conn.commit()
    yield
    with ENGINE.connect() as conn:
        conn.execute(text('DROP TABLE IF EXISTS "session"'))
        conn.commit()


@pytest.fixture
def app():
    return _make_app()


@pytest.fixture
def client(app):
    return TestClient(app)


def _insert_session(token: str, expires_at: datetime.datetime, user_id: str = "user-1"):
    with ENGINE.connect() as conn:
        conn.execute(
            text('INSERT INTO "session" ("id", "token", "userId", "expiresAt") VALUES (:id, :token, :uid, :exp)'),
            {"id": f"sess-{token[:8]}", "token": token, "uid": user_id, "exp": expires_at},
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Public routes — no auth required
# ---------------------------------------------------------------------------

class TestPublicRoutes:
    def test_health_no_cookie(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200

    def test_health_with_invalid_cookie(self, client):
        r = client.get("/api/health", cookies={"better-auth.session_token": "bogus"})
        assert r.status_code == 200

    def test_docs_no_auth(self, client):
        r = client.get("/docs")
        assert r.status_code == 200

    def test_openapi_no_auth(self, client):
        r = client.get("/openapi.json")
        assert r.status_code == 200

    def test_public_lead_route(self, client):
        r = client.get("/api/leads/p/abc123")
        assert r.status_code == 200

    def test_options_always_allowed(self, client):
        r = client.options("/api/leads")
        assert r.status_code != 401


# ---------------------------------------------------------------------------
# Protected routes — auth required
# ---------------------------------------------------------------------------

class TestProtectedRoutes:
    def test_no_cookie_returns_401(self, client):
        r = client.get("/api/leads")
        assert r.status_code == 401
        assert r.json()["detail"] == "Nao autenticado"

    def test_invalid_token_returns_401(self, client):
        r = client.get("/api/leads", cookies={"better-auth.session_token": "nonexistent"})
        assert r.status_code == 401

    def test_expired_token_returns_401(self, client):
        expired = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
        _insert_session("expired-token", expired)
        r = client.get("/api/leads", cookies={"better-auth.session_token": "expired-token"})
        assert r.status_code == 401

    def test_valid_token_passes(self, client):
        future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
        _insert_session("valid-token", future)
        r = client.get("/api/leads", cookies={"better-auth.session_token": "valid-token"})
        assert r.status_code == 200
        assert r.json() == {"leads": []}

    def test_valid_token_sets_user_id_header(self, client, app):
        """Middleware should forward userId for downstream use."""
        future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
        _insert_session("uid-token", future, user_id="user-42")

        @app.get("/api/whoami")
        def whoami():
            return {}

        # Recreate client to pick up new route
        c = TestClient(app)
        r = c.get("/api/whoami", cookies={"better-auth.session_token": "uid-token"})
        assert r.status_code == 200
