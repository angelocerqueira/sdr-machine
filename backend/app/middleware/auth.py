"""Better Auth session-cookie middleware for FastAPI.

Validates the ``better-auth.session_token`` cookie against the ``session``
table managed by Better Auth in PostgreSQL (or SQLite in tests).
"""
from __future__ import annotations

import datetime
from typing import Sequence

from sqlalchemy import create_engine, text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

COOKIE_NAME = "better-auth.session_token"

_VALIDATE_SQL = text('SELECT "expiresAt" FROM "session" WHERE "token" = :token')


class AuthMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that enforces Better Auth sessions.

    Parameters
    ----------
    app:
        The ASGI application.
    database_url:
        SQLAlchemy connection string used to query the ``session`` table.
    public_paths:
        Path prefixes that skip authentication (e.g. ``["/api/health"]``).
    """

    def __init__(
        self,
        app,
        database_url: str,
        public_paths: Sequence[str] = (),
    ):
        super().__init__(app)
        self.public_paths = tuple(public_paths)

        connect_args = {}
        if database_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        self._engine = create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)

    def _is_public(self, path: str) -> bool:
        return any(path.startswith(p) for p in self.public_paths)

    async def dispatch(self, request: Request, call_next):
        # OPTIONS preflight requests always pass through
        if request.method == "OPTIONS":
            return await call_next(request)

        # Public paths skip auth
        if self._is_public(request.url.path):
            return await call_next(request)

        # Extract session token from cookie
        token = request.cookies.get(COOKIE_NAME)
        if not token:
            return JSONResponse(
                status_code=401,
                content={"detail": "Nao autenticado"},
            )

        # Validate token against the session table
        engine = self._engine
        try:
            with engine.connect() as conn:
                row = conn.execute(_VALIDATE_SQL, {"token": token}).fetchone()
        except Exception:
            return JSONResponse(
                status_code=401,
                content={"detail": "Nao autenticado"},
            )

        if row is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "Nao autenticado"},
            )

        expires_at = row[0]
        # Handle both timezone-aware and naive datetimes
        if isinstance(expires_at, str):
            expires_at = datetime.datetime.fromisoformat(expires_at)

        now = datetime.datetime.now(datetime.timezone.utc)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)

        if expires_at <= now:
            return JSONResponse(
                status_code=401,
                content={"detail": "Nao autenticado"},
            )

        # Auth passed — continue
        return await call_next(request)
