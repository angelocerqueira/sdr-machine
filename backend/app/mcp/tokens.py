"""Token utilities pro MCP server: generate, hash (SHA-256), verify, revoke.

Plain token nunca é persistido — só seu hash. Apenas o user vê o plain UMA VEZ
no momento de criação (UI mostra modal "copie agora").
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from app.models import McpToken


def generate_token() -> str:
    """32 random bytes em hex = 64 chars. Crypto-strong via secrets module."""
    return secrets.token_hex(32)


def hash_token(plain: str) -> str:
    """SHA-256 hex digest. Plain nunca volta ao banco."""
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def verify_token(db: Session, plain: str) -> McpToken | None:
    """Localiza token ativo (não-revogado). Atualiza last_used_at e retorna row.
    Retorna None se: token desconhecido, revogado, ou hash inválido.
    """
    if not plain or len(plain) != 64:
        return None
    h = hash_token(plain)
    row = (
        db.query(McpToken)
        .filter_by(token_hash=h)
        .filter(McpToken.revoked_at.is_(None))
        .first()
    )
    if row is None:
        return None
    row.last_used_at = datetime.utcnow()
    db.commit()
    return row


def revoke_token(db: Session, token_hash: str) -> bool:
    """Marca como revogado. Retorna True se afetou linha."""
    row = db.query(McpToken).filter_by(token_hash=token_hash).first()
    if row is None or row.revoked_at is not None:
        return False
    row.revoked_at = datetime.utcnow()
    db.commit()
    return True


def list_tokens(
    db: Session, *, workspace_id: int, include_revoked: bool = False,
) -> List[McpToken]:
    """Lista tokens do workspace. Exclui revogados por default."""
    q = db.query(McpToken).filter_by(workspace_id=workspace_id)
    if not include_revoked:
        q = q.filter(McpToken.revoked_at.is_(None))
    return q.order_by(McpToken.created_at.desc()).all()
