"""Helpers pra extrair info do Context injetado pelo FastMCP."""
from __future__ import annotations

from typing import Any

DEFAULT_WORKSPACE_ID = 1


_SCOPE_PREFIX = "mcp:workspace:"


def get_workspace_id(ctx: Any) -> int:
    """Deriva workspace_id do AccessToken associado à request.
    Cai pra DEFAULT_WORKSPACE_ID se ausente.
    """
    try:
        user = ctx.request_context.request.user
    except AttributeError:
        return DEFAULT_WORKSPACE_ID
    if user is None:
        return DEFAULT_WORKSPACE_ID
    token = getattr(user, "access_token", None)
    if token is None:
        return DEFAULT_WORKSPACE_ID
    for scope in (token.scopes or []):
        if scope.startswith(_SCOPE_PREFIX):
            try:
                return int(scope[len(_SCOPE_PREFIX):])
            except ValueError:
                continue
    return DEFAULT_WORKSPACE_ID
