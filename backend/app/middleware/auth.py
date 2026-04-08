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

# Better Auth uses __Secure- prefix on HTTPS, plain name on HTTP
COOKIE_NAME = "better-auth.session_token"
COOKIE_NAME_SECURE = "__Secure-better-auth.session_token"

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

        # Extract session token: try Authorization header first, then cookies
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            raw_token = auth_header[7:]
        else:
            raw_token = request.cookies.get(COOKIE_NAME_SECURE) or request.cookies.get(COOKIE_NAME)

        if not raw_token:
            return JSONResponse(
                status_code=401,
                content={"detail": "Nao autenticado"},
            )

        # Better Auth cookie format: "token.signature" — extract token part only
        token = raw_token.split(".")[0] if "." in raw_token else raw_token

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
