"""Smoke test: MCP server mounted respondendo no path correto."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_mcp_path_not_404():
    """MCP endpoint deve responder (não 404). Sem auth → não importa o status,
    desde que não seja 404 do FastAPI por rota não registrada."""
    r = client.post("/api/mcp/", json={"jsonrpc": "2.0", "method": "initialize", "id": 1})
    assert r.status_code != 404, (
        f"MCP endpoint not mounted (got 404). Headers: {dict(r.headers)}"
    )


def test_mcp_rejects_no_auth():
    """Sem Bearer token, server deve rejeitar (401/403/400 ou JSON-RPC error)."""
    r = client.post("/api/mcp/", json={"jsonrpc": "2.0", "method": "initialize", "id": 1})
    assert r.status_code in (401, 403, 400, 406) or (
        r.status_code == 200 and isinstance(r.json(), dict) and "error" in r.json()
    )
