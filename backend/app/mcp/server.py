"""Builder do FastMCP server pro SDR Machine.

M-1 retornou server vazio. M-2 adicionou READ tools + resources.
M-3 adicionará write tools, M-5 prompts + subscriptions.
"""
from __future__ import annotations

import logging

from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from app.config import settings as app_settings
from app.database import SessionLocal
from app.mcp.auth import BearerTokenVerifier
from app.mcp.resources import register_resources
from app.mcp.tools_commit import register_commit_tools
from app.mcp.tools_conversations import register_conversations_tools
from app.mcp.tools_jobs import register_jobs_tools
from app.mcp.tools_leads import register_leads_tools
from app.mcp.tools_pending import register_pending_tools
from app.mcp.tools_prepare import register_prepare_tools
from app.mcp.tools_soft_write import register_soft_write_tools
from app.mcp.tools_stats import register_stats_tools
from app.mcp.tools_workspace import register_workspace_tools
import app.mcp.action_handlers  # noqa: F401 — força registro dos handlers

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

    # DNS rebinding protection desabilitada: backend roda atrás de Railway TLS,
    # default do SDK 1.27 (allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*"])
    # retorna 421 "Invalid Host header" em qualquer host externo.
    transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
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
        stateless_http=True,
        streamable_http_path="/",
        transport_security=transport_security,
    )

    # READ tools (M-2)
    register_leads_tools(server)
    register_conversations_tools(server)
    register_jobs_tools(server)
    register_stats_tools(server)
    register_workspace_tools(server)
    register_pending_tools(server)

    # Resources (M-2)
    register_resources(server)

    # M-3 write tools
    register_soft_write_tools(server)
    register_prepare_tools(server)
    register_commit_tools(server)

    # M-5 vai adicionar prompts + subscriptions

    return server
