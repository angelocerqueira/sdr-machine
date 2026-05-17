"""HMAC SHA256 signature verification para webhooks WhatsApp.

Strategy: compute HMAC-SHA256(secret, raw_body) hex-encoded.
Verify usa comparação constant-time (`hmac.compare_digest`) pra prevenir
timing attacks. Aceita assinatura com ou sem prefixo `sha256=`.
"""
from __future__ import annotations

import hashlib
import hmac as _hmac

_PREFIX = "sha256="


def compute_signature(secret: str, body: bytes) -> str:
    """Retorna assinatura prefixada com `sha256=` (formato GitHub-style)."""
    digest = _hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"{_PREFIX}{digest}"


def verify_signature(secret: str, body: bytes, signature: str | None) -> bool:
    """Constant-time verify. Tolera `sha256=` ausente.

    Retorna False se signature for None/vazia ou se hash não bater.
    """
    if not signature:
        return False
    expected = compute_signature(secret, body)
    candidate = signature if signature.startswith(_PREFIX) else f"{_PREFIX}{signature}"
    return _hmac.compare_digest(expected, candidate)
