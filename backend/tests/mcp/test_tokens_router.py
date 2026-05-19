from app.models import McpToken
from app.mcp.tokens import generate_token, hash_token


def test_list_tokens_empty(client):
    r = client.get("/api/workspace/mcp-tokens")
    assert r.status_code == 200
    assert r.json() == []


def test_create_token_returns_plain_once(client, db):
    r = client.post("/api/workspace/mcp-tokens", json={"name": "claude-laptop"})
    assert r.status_code == 201
    body = r.json()
    assert "token" in body
    assert len(body["token"]) == 64
    assert body["last4"] == body["token"][-4:]
    assert body["name"] == "claude-laptop"
    assert body["revoked_at"] is None

    row = db.query(McpToken).filter_by(name="claude-laptop").first()
    assert row is not None
    assert row.token_hash == hash_token(body["token"])
    assert row.workspace_id == 1


def test_create_token_requires_name(client):
    r = client.post("/api/workspace/mcp-tokens", json={})
    assert r.status_code == 422


def test_list_tokens_shows_last4_not_full(client, db):
    plain = generate_token()
    db.add(McpToken(
        workspace_id=1, name="existing", token_hash=hash_token(plain),
        last4=plain[-4:],
    ))
    db.commit()

    r = client.get("/api/workspace/mcp-tokens")
    items = r.json()
    assert len(items) == 1
    item = items[0]
    assert item["name"] == "existing"
    assert item["last4"] == plain[-4:]
    assert "token" not in item
    assert "token_hash" not in item


def test_revoke_token_marks_revoked(client, db):
    plain = generate_token()
    db.add(McpToken(
        workspace_id=1, name="revokeme", token_hash=hash_token(plain), last4="abcd",
    ))
    db.commit()
    tok = db.query(McpToken).filter_by(name="revokeme").first()

    r = client.delete(f"/api/workspace/mcp-tokens/{tok.id}")
    assert r.status_code == 204

    db.refresh(tok)
    assert tok.revoked_at is not None


def test_revoke_unknown_token_returns_404(client):
    r = client.delete("/api/workspace/mcp-tokens/9999")
    assert r.status_code == 404


def test_list_excludes_revoked_by_default(client, db):
    from datetime import datetime
    plain_a = generate_token()
    plain_b = generate_token()
    db.add_all([
        McpToken(workspace_id=1, name="active", token_hash=hash_token(plain_a), last4="aaaa"),
        McpToken(workspace_id=1, name="revoked", token_hash=hash_token(plain_b), last4="bbbb",
                 revoked_at=datetime.utcnow()),
    ])
    db.commit()

    r = client.get("/api/workspace/mcp-tokens")
    items = r.json()
    assert len(items) == 1
    assert items[0]["name"] == "active"


def test_list_isolates_by_workspace(client, db):
    """Token de outro workspace não aparece na lista do workspace atual (=1)."""
    db.add(McpToken(
        workspace_id=2, name="other-ws",
        token_hash=hash_token(generate_token()), last4="zzzz",
    ))
    db.commit()

    r = client.get("/api/workspace/mcp-tokens")
    names = [t["name"] for t in r.json()]
    assert "other-ws" not in names


def test_revoke_cross_workspace_returns_404(client, db):
    """DELETE em token de outro workspace retorna 404 (não 403, não revela existência)."""
    plain = generate_token()
    db.add(McpToken(
        workspace_id=2, name="other-ws",
        token_hash=hash_token(plain), last4="zzzz",
    ))
    db.commit()
    tok = db.query(McpToken).filter_by(name="other-ws").first()

    r = client.delete(f"/api/workspace/mcp-tokens/{tok.id}")
    assert r.status_code == 404

    db.refresh(tok)
    assert tok.revoked_at is None  # não foi revogado
