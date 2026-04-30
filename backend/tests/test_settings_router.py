"""Tests for GET/PUT /api/workspace/{profile,targeting}.

Parcial — só profile + targeting nesta task.
"""


def test_profile_get_empty_returns_defaults(client):
    res = client.get("/api/workspace/profile")
    assert res.status_code == 200
    body = res.json()
    assert body["business_name"] is None
    assert body["legal_basis"] == "legitimo_interesse_b2b"


def test_profile_put_upsert(client):
    res = client.put("/api/workspace/profile", json={
        "business_name": "Acme",
        "your_name": "Angelo",
        "your_email": "a@a.com",
        "your_whatsapp": "5549999",
        "your_website": "https://a.com",
    })
    assert res.status_code == 200
    assert res.json()["business_name"] == "Acme"

    # second PUT updates
    res = client.put("/api/workspace/profile", json={"business_name": "Acme 2"})
    assert res.json()["business_name"] == "Acme 2"
    # other fields preserved
    assert res.json()["your_name"] == "Angelo"


def test_targeting_get_empty(client):
    res = client.get("/api/workspace/targeting")
    assert res.status_code == 200
    body = res.json()
    assert body["target_niches"] == []
    assert body["target_cities"] == []


def test_targeting_put(client):
    res = client.put("/api/workspace/targeting", json={
        "target_niches": ["dentista", "pet shop"],
        "target_cities": ["Chapecó SC"],
        "min_rating": 4.0,
        "max_results_per_search": 50,
        "opportunity_score_threshold": 40,
    })
    assert res.status_code == 200
    assert res.json()["min_rating"] == 4.0


def test_integrations_list_empty(client):
    res = client.get("/api/workspace/integrations")
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body, list)
    # Cada provider conhecido aparece como "desconectado" se sem row
    providers = [i["provider"] for i in body]
    for p in ["resend", "telegram", "apify", "llm", "hunter", "apollo", "langsmith"]:
        assert p in providers


def test_integration_put_creates_with_encrypted_secret(client, db):
    res = client.put("/api/workspace/integrations/resend", json={
        "config": {
            "api_key": "re_real_secret",
            "from_email": "x@y.com",
            "from_name": "X",
        }
    })
    assert res.status_code == 200
    body = res.json()
    # Resposta nunca vaza secret em texto
    assert "api_key" not in body["config"] or body["config"].get("api_key") is None
    assert body["config"]["has_api_key"] is True
    assert body["config"]["api_key_last4"] == "cret"
    # DB grava cifrado
    from app.models import IntegrationSettings
    row = db.query(IntegrationSettings).filter_by(provider="resend").first()
    assert row.config["api_key"] != "re_real_secret"


def test_integration_put_partial_keeps_secret(client, db):
    # Setup: cria com secret
    client.put("/api/workspace/integrations/resend", json={
        "config": {"api_key": "re_first", "from_email": "x@y.com", "from_name": "X"}
    })
    # PUT sem api_key — mantém o atual
    res = client.put("/api/workspace/integrations/resend", json={
        "config": {"from_email": "novo@y.com"}
    })
    assert res.status_code == 200
    assert res.json()["config"]["from_email"] == "novo@y.com"
    assert res.json()["config"]["has_api_key"] is True
    assert res.json()["config"]["api_key_last4"] == "irst"


def test_integration_put_empty_secret_ignored(client, db):
    client.put("/api/workspace/integrations/resend", json={
        "config": {"api_key": "re_first", "from_email": "x@y.com", "from_name": "X"}
    })
    res = client.put("/api/workspace/integrations/resend", json={
        "config": {"api_key": "", "from_email": "nu@y.com"}
    })
    assert res.json()["config"]["api_key_last4"] == "irst"  # mantido


def test_integration_delete(client):
    client.put("/api/workspace/integrations/resend", json={
        "config": {"api_key": "re_x", "from_email": "x@y.com", "from_name": "X"}
    })
    res = client.delete("/api/workspace/integrations/resend")
    assert res.status_code == 204
    res = client.get("/api/workspace/integrations/resend")
    assert res.json()["enabled"] is False


def test_integration_test_endpoint(client, httpx_mock):
    httpx_mock.add_response(
        url="https://api.resend.com/domains",
        json={"data": []}, status_code=200,
    )
    client.put("/api/workspace/integrations/resend", json={
        "config": {"api_key": "re_x", "from_email": "x@y.com", "from_name": "X"}
    })
    res = client.post("/api/workspace/integrations/resend/test")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["latency_ms"] >= 0


def test_integration_test_without_config_fails(client):
    res = client.post("/api/workspace/integrations/resend/test")
    assert res.status_code == 400


def test_integration_get_with_corrupt_secret_does_not_500(client, db):
    """Linha com ciphertext inválido (key rotation, corrupção) não pode quebrar
    GET /integrations — deve marcar needs_reencrypt e seguir."""
    from app.models import IntegrationSettings

    db.add(IntegrationSettings(
        workspace_id=1, provider="resend",
        config={
            "api_key": "gAAAAAB-not-a-valid-fernet-token",  # cifra inválida
            "from_email": "x@y.com",
            "from_name": "X",
        },
        enabled=True,
    ))
    db.commit()

    # GET single
    res = client.get("/api/workspace/integrations/resend")
    assert res.status_code == 200
    body = res.json()
    assert body["config"]["has_api_key"] is True
    assert "api_key_last4" not in body["config"]
    assert body["config"]["needs_reencrypt"] is True

    # GET list — não pode 500 mesmo com 1 linha corrompida
    res = client.get("/api/workspace/integrations")
    assert res.status_code == 200
    items = res.json()
    resend = next(i for i in items if i["provider"] == "resend")
    assert resend["config"]["needs_reencrypt"] is True


def test_integration_put_with_corrupt_secret_returns_422(client, db):
    """PUT preservando secret corrompido (sem re-paste) retorna 422 claro,
    não 500."""
    from app.models import IntegrationSettings

    db.add(IntegrationSettings(
        workspace_id=1, provider="resend",
        config={
            "api_key": "gAAAAAB-not-a-valid-fernet-token",
            "from_email": "x@y.com",
            "from_name": "X",
        },
        enabled=True,
    ))
    db.commit()

    # PUT só de campo plain — secret corrompido permanece
    res = client.put("/api/workspace/integrations/resend", json={
        "config": {"from_email": "novo@y.com"}
    })
    assert res.status_code == 422
    assert "corrupted" in res.json()["detail"].lower()


def test_integration_put_overwrites_corrupt_secret_with_new_value(client, db):
    """User re-paste de secret novo deve sobrescrever ciphertext corrompido."""
    from app.models import IntegrationSettings

    db.add(IntegrationSettings(
        workspace_id=1, provider="resend",
        config={
            "api_key": "gAAAAAB-not-a-valid-fernet-token",
            "from_email": "x@y.com",
            "from_name": "X",
        },
        enabled=True,
    ))
    db.commit()

    res = client.put("/api/workspace/integrations/resend", json={
        "config": {"api_key": "re_new_valid_value", "from_email": "x@y.com", "from_name": "X"}
    })
    assert res.status_code == 200
    body = res.json()
    assert body["config"]["has_api_key"] is True
    assert body["config"]["api_key_last4"] == "alue"
    assert "needs_reencrypt" not in body["config"]


def test_integration_test_with_corrupt_secret_returns_422(client, db):
    """POST /test em linha com secret corrompido retorna 422 claro."""
    from app.models import IntegrationSettings

    db.add(IntegrationSettings(
        workspace_id=1, provider="resend",
        config={"api_key": "gAAAAAB-not-a-valid-fernet-token",
                "from_email": "x@y.com", "from_name": "X"},
        enabled=True,
    ))
    db.commit()

    res = client.post("/api/workspace/integrations/resend/test")
    assert res.status_code == 422
    assert "corrupted" in res.json()["detail"].lower()
