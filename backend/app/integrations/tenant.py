"""Resolve workspace_id do request.

Hoje retorna constante DEFAULT_WORKSPACE_ID = 1 (single-tenant).
Quando virar multi-tenant pra valer, esta função consulta membership
via session do Better Auth — call sites não mudam.
"""
from fastapi import Request

DEFAULT_WORKSPACE_ID = 1


def get_current_workspace_id(request: Request) -> int:
    # Multi-tenant futuro: lookup user_id em workspace_users.
    # Hoje single-workspace global.
    return DEFAULT_WORKSPACE_ID
