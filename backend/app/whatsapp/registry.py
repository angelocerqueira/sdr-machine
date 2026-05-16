"""Resolve adapter WhatsApp por workspace.

Lê `IntegrationSettings` via padrão de `integrations/resolver.py`:
DB primeiro, env fallback NÃO se aplica (WhatsApp não tem credencial
em `.env` legado — workspace tem que configurar via UI).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.integrations.resolver import get_provider_config
from app.whatsapp.evolution_adapter import EvolutionAdapter
from app.whatsapp.provider import WhatsAppProvider


class ProviderNotConfigured(Exception):
    """Workspace não tem provider WhatsApp configurado/habilitado."""


class UnknownProviderError(Exception):
    """Provider name desconhecido (typo, ou ainda não implementado)."""


# Map name → factory(cfg_dict) → WhatsAppProvider
_REGISTRY = {
    "evolution": lambda cfg: EvolutionAdapter(
        base_url=cfg["base_url"],
        instance=cfg["instance"],
        api_key=cfg["api_key"],
    ),
}


def get_provider(
    db: Session, workspace_id: int, provider: str = "evolution"
) -> WhatsAppProvider:
    """Resolve adapter conforme `IntegrationSettings` do workspace.

    Args:
        provider: nome do provider. Default "evolution" (único MVP).

    Raises:
        UnknownProviderError: se `provider` não existe no registry.
        ProviderNotConfigured: se workspace não tem row habilitada com
            secrets decifráveis pra esse provider.
    """
    factory = _REGISTRY.get(provider)
    if factory is None:
        raise UnknownProviderError(
            f"Unknown WhatsApp provider: {provider!r}. "
            f"Available: {list(_REGISTRY)}"
        )
    cfg = get_provider_config(db, workspace_id=workspace_id, provider=provider)
    if cfg is None:
        raise ProviderNotConfigured(
            f"No active {provider!r} integration for workspace {workspace_id}"
        )
    return factory(cfg)
