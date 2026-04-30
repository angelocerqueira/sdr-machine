"""Resolve config de provider: DB primeiro, env fallback.

Permite migração progressiva: enquanto user não configurar via UI,
pipelines continuam lendo .env como antes.
"""
from __future__ import annotations

import logging

from cryptography.fernet import InvalidToken
from sqlalchemy.orm import Session

from app import config as _config_module
from app.integrations.crypto import SettingsEncKeyMissing, decrypt
from app.integrations.schemas import SECRET_FIELDS
from app.models import IntegrationSettings

logger = logging.getLogger(__name__)


def get_provider_config(
    db: Session, workspace_id: int, provider: str
) -> dict | None:
    """Retorna dict pronto pra uso (secrets já decifrados) ou None.

    Se o row existir mas algum secret estiver corrompido (key rotation,
    restore parcial), trata como "não configurado via UI" e cai pro env
    fallback — pipeline degrada graciosamente em vez de crashar a stage.
    Router endpoints continuam usando _decrypt_secrets(strict=True) pra
    devolver 422 explícito ao user.
    """
    row = (
        db.query(IntegrationSettings)
        .filter_by(workspace_id=workspace_id, provider=provider, enabled=True)
        .first()
    )
    if row:
        decrypted = _decrypt_secrets(provider, row.config, strict=False)
        if decrypted is not None:
            return decrypted
    return _env_fallback(provider)


def _decrypt_secrets(provider: str, raw: dict, *, strict: bool = True) -> dict | None:
    """Aplica decrypt nos campos listados em SECRET_FIELDS pro provider.

    Args:
        strict: True (default) → propaga InvalidToken / SettingsEncKeyMissing
                pra caller (usado pelo router pra retornar 422/503 e pedir
                ação ao user).
                False → log warning + retorna None se houver corrupção ou
                key ausente (usado por get_provider_config pra cair no env
                fallback sem crashar pipeline).
    """
    secret_fields = SECRET_FIELDS.get(provider, set())
    out = {}
    for k, v in raw.items():
        if k in secret_fields and isinstance(v, str) and v:
            try:
                out[k] = decrypt(v)
            except (InvalidToken, SettingsEncKeyMissing) as exc:
                if strict:
                    raise
                logger.warning(
                    "Cannot decrypt provider=%s field=%s (%s); "
                    "treating row as unconfigured and falling back to env",
                    provider, k, type(exc).__name__,
                )
                return None
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


from app.database import SessionLocal
from app.integrations.tenant import DEFAULT_WORKSPACE_ID


def provider_config_for(provider: str) -> dict | None:
    """Conveniência pra call sites de pipeline (sync, sem request).

    Hoje single-workspace. Quando virar multi-tenant, call sites de
    background passam workspace_id explícito.
    """
    db = SessionLocal()
    try:
        return get_provider_config(db, DEFAULT_WORKSPACE_ID, provider)
    finally:
        db.close()
