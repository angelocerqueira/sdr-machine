import asyncio
from datetime import datetime

from app.mcp.auth import BearerTokenVerifier
from app.mcp.tokens import generate_token, hash_token
from app.models import McpToken


def _factory(session):
    """Retorna callable que devolve a session de teste."""
    def _f():
        return session
    return _f


def test_verifier_accepts_valid_token(db):
    plain = generate_token()
    db.add(McpToken(
        workspace_id=42, name="x", token_hash=hash_token(plain), last4=plain[-4:],
    ))
    db.commit()

    verifier = BearerTokenVerifier(session_factory=_factory(db))
    result = asyncio.run(verifier.verify_token(plain))

    assert result is not None
    assert result.scopes == ["mcp:workspace:42"]


def test_verifier_rejects_unknown_token(db):
    plain = generate_token()
    verifier = BearerTokenVerifier(session_factory=_factory(db))
    result = asyncio.run(verifier.verify_token(plain))
    assert result is None


def test_verifier_rejects_malformed(db):
    verifier = BearerTokenVerifier(session_factory=_factory(db))
    assert asyncio.run(verifier.verify_token("short")) is None
    assert asyncio.run(verifier.verify_token("")) is None


def test_verifier_rejects_revoked(db):
    plain = generate_token()
    db.add(McpToken(
        workspace_id=1, name="x", token_hash=hash_token(plain), last4="abcd",
        revoked_at=datetime.utcnow(),
    ))
    db.commit()

    verifier = BearerTokenVerifier(session_factory=_factory(db))
    assert asyncio.run(verifier.verify_token(plain)) is None
