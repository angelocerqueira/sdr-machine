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


def test_get_webhook_url_evolution(client):
    r = client.get("/api/workspace/integrations/evolution/webhook-url")
    assert r.status_code == 200
    j = r.json()
    assert "/api/webhooks/whatsapp/1/evolution" in j["url"]


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


def test_evolution_connect_no_config(client, db):
    """No IntegrationSettings row → 422."""
    r = client.post("/api/workspace/integrations/evolution/connect")
    assert r.status_code == 422


def test_evolution_status_no_config(client, db):
    r = client.get("/api/workspace/integrations/evolution/status")
    assert r.status_code == 422


def test_evolution_connect_returns_qr(client, db, httpx_mock):
    from app.integrations.crypto import encrypt
    from app.models import IntegrationSettings

    db.add(IntegrationSettings(
        workspace_id=1, provider="evolution", enabled=True,
        config={
            "base_url": "https://evo.example.com",
            "instance": "sdr",
            "api_key": encrypt("KEY"),
            "webhook_secret": encrypt("SEC"),
        },
    ))
    db.commit()

    httpx_mock.add_response(
        url="https://evo.example.com/instance/connect/sdr",
        json={"base64": "data:image/png;base64,iVBORw0K", "code": "2@abc"},
    )
    httpx_mock.add_response(
        url="https://evo.example.com/instance/connectionState/sdr",
        json={"instance": {"state": "connecting"}},
    )

    r = client.post("/api/workspace/integrations/evolution/connect")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["qr_base64"] == "data:image/png;base64,iVBORw0K"
    assert body["code"] == "2@abc"
    assert body["state"] == "connecting"


def test_evolution_status_returns_state(client, db, httpx_mock):
    from app.integrations.crypto import encrypt
    from app.models import IntegrationSettings

    db.add(IntegrationSettings(
        workspace_id=1, provider="evolution", enabled=True,
        config={
            "base_url": "https://evo.example.com",
            "instance": "sdr",
            "api_key": encrypt("KEY"),
            "webhook_secret": encrypt("SEC"),
        },
    ))
    db.commit()

    httpx_mock.add_response(
        url="https://evo.example.com/instance/connectionState/sdr",
        json={"instance": {"state": "open"}},
    )

    r = client.get("/api/workspace/integrations/evolution/status")
    assert r.status_code == 200
    body = r.json()
    assert body["state"] == "open"
    assert body["ok"] is True


def test_evolution_logout_no_config(client, db):
    """Logout sem config → 422."""
    r = client.post("/api/workspace/integrations/evolution/logout")
    assert r.status_code == 422


def test_evolution_logout_success(client, db, httpx_mock):
    from app.integrations.crypto import encrypt
    from app.models import IntegrationSettings

    db.add(IntegrationSettings(
        workspace_id=1, provider="evolution", enabled=True,
        config={
            "base_url": "https://evo.example.com",
            "instance": "sdr",
            "api_key": encrypt("KEY"),
        },
    ))
    db.commit()

    httpx_mock.add_response(
        url="https://evo.example.com/instance/logout/sdr",
        method="DELETE",
        json={"status": "SUCCESS"},
    )

    r = client.post("/api/workspace/integrations/evolution/logout")
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True


def test_evolution_logout_502_when_upstream_fails(client, db, httpx_mock):
    from app.integrations.crypto import encrypt
    from app.models import IntegrationSettings

    db.add(IntegrationSettings(
        workspace_id=1, provider="evolution", enabled=True,
        config={
            "base_url": "https://evo.example.com",
            "instance": "sdr",
            "api_key": encrypt("KEY"),
        },
    ))
    db.commit()

    httpx_mock.add_response(
        url="https://evo.example.com/instance/logout/sdr",
        method="DELETE",
        status_code=500, text="evolution down",
    )

    r = client.post("/api/workspace/integrations/evolution/logout")
    assert r.status_code == 502


def test_evolution_put_caches_instance_token(client, db, httpx_mock):
    """Save Evolution dispara fetch_instance_token e persiste cifrado."""
    from app.integrations.crypto import decrypt
    from app.models import IntegrationSettings

    httpx_mock.add_response(
        url="https://evo.example.com/instance/fetchInstances?instanceName=sdr",
        json=[{"name": "sdr", "token": "INSTANCE-TOKEN-XYZ"}],
    )

    r = client.put("/api/workspace/integrations/evolution", json={
        "config": {
            "base_url": "https://evo.example.com",
            "instance": "sdr",
            "api_key": "GLOBAL-KEY",
        }
    })
    assert r.status_code == 200, r.text

    row = db.query(IntegrationSettings).filter_by(provider="evolution").first()
    assert row.config.get("instance_token"), "instance_token deveria estar cacheado"
    assert decrypt(row.config["instance_token"]) == "INSTANCE-TOKEN-XYZ"


def test_evolution_put_no_crash_when_fetch_fails(client, db, httpx_mock):
    """Fetch falha (Evolution offline / instance ainda não criada) → save OK sem cache."""
    from app.models import IntegrationSettings

    httpx_mock.add_response(
        url="https://evo.example.com/instance/fetchInstances?instanceName=sdr",
        status_code=502,
        text="upstream error",
    )

    r = client.put("/api/workspace/integrations/evolution", json={
        "config": {
            "base_url": "https://evo.example.com",
            "instance": "sdr",
            "api_key": "GLOBAL-KEY",
        }
    })
    assert r.status_code == 200, r.text

    row = db.query(IntegrationSettings).filter_by(provider="evolution").first()
    assert "instance_token" not in row.config


def test_evolution_test_refreshes_instance_token(client, db, httpx_mock):
    """POST /test resyncs instance_token — caso instance recriada com mesmo nome."""
    from app.integrations.crypto import decrypt, encrypt
    from app.models import IntegrationSettings

    # Estado inicial: token antigo cacheado
    db.add(IntegrationSettings(
        workspace_id=1, provider="evolution", enabled=True,
        config={
            "base_url": "https://evo.example.com",
            "instance": "sdr",
            "api_key": encrypt("GLOBAL-KEY"),
            "instance_token": encrypt("OLD-TOKEN"),
        },
    ))
    db.commit()

    # run_test do tester chama health_check; fetch_instance_token roda em seguida
    httpx_mock.add_response(
        url="https://evo.example.com/instance/connectionState/sdr",
        json={"instance": {"state": "open"}},
    )
    httpx_mock.add_response(
        url="https://evo.example.com/instance/fetchInstances?instanceName=sdr",
        json=[{"name": "sdr", "token": "NEW-TOKEN-AFTER-RECREATE"}],
    )

    r = client.post("/api/workspace/integrations/evolution/test")
    assert r.status_code == 200, r.text

    db.expire_all()
    row = db.query(IntegrationSettings).filter_by(provider="evolution").first()
    assert decrypt(row.config["instance_token"]) == "NEW-TOKEN-AFTER-RECREATE"
