"""Builder do FastMCP server pro SDR Machine.

M-1 retorna server vazio (sem tools nem resources). M-2 adiciona READ tools,
M-3 adiciona write tools, etc.
"""
from __future__ import annotations

import logging

from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

from app.config import settings as app_settings
from app.database import SessionLocal
from app.mcp.auth import BearerTokenVerifier

logger = logging.getLogger(__name__)


def build_mcp_server() -> FastMCP:
    """Constrói o FastMCP server. Idempotente."""
    verifier = BearerTokenVerifier(session_factory=SessionLocal)

    # SDK 1.27 exige AuthSettings quando token_verifier é passado. Operamos
    # como Resource Server puro — não emitimos tokens, só validamos. issuer_url
    # e resource_server_url apontam pro próprio backend pra satisfazer o schema.
    api_url = getattr(app_settings, "api_url", None) or "http://localhost:8000"
    auth_settings = AuthSettings(
        issuer_url=api_url,
        resource_server_url=api_url,
    )

    server = FastMCP(
        "sdr-machine",
        instructions=(
            "Servidor MCP do SDR Machine — plataforma de automação de prospecção. "
            "Use tools para listar leads, conversas e jobs. Ações que enviam mensagens "
            "ou deletam dados usam two-phase commit (prepare_* + commit_action) — "
            "sempre revise o preview com o usuário antes de chamar commit_action."
        ),
        token_verifier=verifier,
        auth=auth_settings,
        json_response=True,
        streamable_http_path="/",
    )

    # M-2/3/4/5 adicionarão tools/resources/prompts aqui

    return server
