"""Resolve config de provider: DB primeiro, env fallback.

Permite migração progressiva: enquanto user não configurar via UI,
pipelines continuam lendo .env como antes.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app import config as _config_module
from app.integrations.crypto import decrypt
from app.integrations.schemas import SECRET_FIELDS
from app.models import IntegrationSettings


def get_provider_config(
    db: Session, workspace_id: int, provider: str
) -> dict | None:
    """Retorna dict pronto pra uso (secrets já decifrados) ou None."""
    row = (
        db.query(IntegrationSettings)
        .filter_by(workspace_id=workspace_id, provider=provider, enabled=True)
        .first()
    )
    if row:
        return _decrypt_secrets(provider, row.config)
    return _env_fallback(provider)


def _decrypt_secrets(provider: str, raw: dict) -> dict:
    """Aplica decrypt nos campos listados em SECRET_FIELDS pro provider."""
    secret_fields = SECRET_FIELDS.get(provider, set())
    out = {}
    for k, v in raw.items():
        if k in secret_fields and isinstance(v, str) and v:
            out[k] = decrypt(v)
        else:
            out[k] = v
    return out


def _env_fallback(provider: str) -> dict | None:
    """Lê config legado de env vars antigas — só pra integrações pré-existentes."""
    # Access settings via module attribute so reloads in tests are picked up.
    s = _config_module.settings
    if provider == "apify":
        return {"token": s.apify_token} if s.apify_token else None
    if provider == "llm":
        if s.llm_api_key:
            return {
                "api_key": s.llm_api_key,
                "model": s.llm_model,
                "base_url": s.llm_base_url,
            }
        return None
    if provider == "hunter":
        return {"api_key": s.hunter_api_key} if s.hunter_api_key else None
    if provider == "apollo":
        return {"api_key": s.apollo_api_key} if s.apollo_api_key else None
    if provider == "langsmith":
        if s.langsmith_api_key:
            return {
                "api_key": s.langsmith_api_key,
                "project": s.langsmith_project,
                "tracing": s.langsmith_tracing,
            }
        return None
    return None  # resend, telegram nunca tiveram env
