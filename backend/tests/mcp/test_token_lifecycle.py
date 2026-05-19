from datetime import datetime

import pytest

from app.models import McpToken
from app.mcp.tokens import (
    generate_token,
    hash_token,
    verify_token,
    revoke_token,
    list_tokens,
)


def test_generate_token_format():
    plain = generate_token()
    assert len(plain) == 64
    assert all(c in "0123456789abcdef" for c in plain)


def test_generate_token_unique():
    a = generate_token()
    b = generate_token()
    assert a != b


def test_hash_token_deterministic():
    plain = "deadbeef" * 8
    h1 = hash_token(plain)
    h2 = hash_token(plain)
    assert h1 == h2
    assert len(h1) == 64


def test_hash_token_different_for_different_inputs():
    a = hash_token("aaaaaaaa" * 8)
    b = hash_token("bbbbbbbb" * 8)
    assert a != b


def test_verify_token_finds_valid(db):
    plain = generate_token()
    h = hash_token(plain)
    db.add(McpToken(workspace_id=1, name="laptop", token_hash=h, last4=plain[-4:]))
    db.commit()
    row = verify_token(db, plain)
    assert row is not None
    assert row.name == "laptop"
    assert row.workspace_id == 1


def test_verify_token_returns_none_for_unknown(db):
    plain = generate_token()
    row = verify_token(db, plain)
    assert row is None


def test_verify_token_rejects_revoked(db):
    plain = generate_token()
    h = hash_token(plain)
    tok = McpToken(
        workspace_id=1, name="x", token_hash=h, last4="abcd",
        revoked_at=datetime.utcnow(),
    )
    db.add(tok)
    db.commit()
    row = verify_token(db, plain)
    assert row is None


def test_verify_token_updates_last_used_at(db):
    plain = generate_token()
    h = hash_token(plain)
    db.add(McpToken(workspace_id=1, name="x", token_hash=h, last4="abcd"))
    db.commit()
    before = datetime.utcnow()
    verify_token(db, plain)
    tok = db.query(McpToken).filter_by(token_hash=h).first()
    assert tok.last_used_at is not None
    assert tok.last_used_at >= before


def test_revoke_token_sets_revoked_at(db):
    plain = generate_token()
    h = hash_token(plain)
    db.add(McpToken(workspace_id=1, name="x", token_hash=h, last4="abcd"))
    db.commit()
    revoke_token(db, h)
    tok = db.query(McpToken).filter_by(token_hash=h).first()
    assert tok.revoked_at is not None


def test_list_tokens_excludes_revoked_by_default(db):
    h1 = hash_token(generate_token())
    h2 = hash_token(generate_token())
    db.add_all([
        McpToken(workspace_id=1, name="active", token_hash=h1, last4="aaaa"),
        McpToken(workspace_id=1, name="revoked", token_hash=h2, last4="bbbb",
                 revoked_at=datetime.utcnow()),
    ])
    db.commit()
    rows = list_tokens(db, workspace_id=1)
    assert len(rows) == 1
    assert rows[0].name == "active"


def test_list_tokens_workspace_scoped(db):
    h1 = hash_token(generate_token())
    h2 = hash_token(generate_token())
    db.add_all([
        McpToken(workspace_id=1, name="ws1", token_hash=h1, last4="aaaa"),
        McpToken(workspace_id=2, name="ws2", token_hash=h2, last4="bbbb"),
    ])
    db.commit()
    rows = list_tokens(db, workspace_id=1)
    assert len(rows) == 1
    assert rows[0].name == "ws1"
