"""BearerTokenVerifier — implementa o protocolo TokenVerifier do MCP SDK.

O SDK chama `verify_token(plain) -> AccessToken | None` em cada request.
Retornamos um AccessToken com scope `mcp:workspace:<id>` codificado, que
o downstream usa pra derivar workspace_id sem 2nd lookup.
"""
from __future__ import annotations

import logging
from typing import Callable

from mcp.server.auth.provider import AccessToken, TokenVerifier
from sqlalchemy.orm import Session

from app.mcp.tokens import verify_token

logger = logging.getLogger(__name__)


SessionFactory = Callable[[], Session]


class BearerTokenVerifier(TokenVerifier):
    """Valida Bearer tokens contra tabela mcp_tokens."""

    def __init__(self, session_factory: SessionFactory):
        self._session_factory = session_factory

    async def verify_token(self, token: str) -> AccessToken | None:
        db = self._session_factory()
        try:
            try:
                row = verify_token(db, token)
            except Exception:
                logger.exception("mcp.auth.verify_failed")
                return None

            if row is None:
                return None

            return AccessToken(
                token=token,
                client_id=f"mcp-token-{row.id}",
                scopes=[f"mcp:workspace:{row.workspace_id}"],
                expires_at=None,
                resource=None,
            )
        finally:
            db.close()
