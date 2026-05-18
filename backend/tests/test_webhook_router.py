import json

import pytest

from app.integrations.crypto import encrypt
from app.models import IntegrationSettings, Lead, OutreachMessage
from app.whatsapp.hmac import compute_signature

WEBHOOK_SECRET = "hmac-secret-xyz"


@pytest.fixture
def seeded(db):
    db.add(IntegrationSettings(
        workspace_id=1, provider="evolution", enabled=True,
        config={
            "base_url": "https://evo.example.com",
            "instance": "sdr", "api_key": encrypt("X"),
            "webhook_secret": encrypt(WEBHOOK_SECRET),
        },
    ))
    db.add(Lead(nome="Acme", telefone="5544999990000", status="outreach_sent"))
    db.commit()


def _payload_inbound() -> dict:
    return {
        "event": "messages.upsert",
        "data": {
            "key": {
                "id": "EVO-WH-1",
                "remoteJid": "5544999990000@s.whatsapp.net",
                "fromMe": False,
            },
            "message": {"conversation": "test reply"},
            "messageTimestamp": 1715000000,
        },
    }


def test_webhook_200_with_valid_hmac(client, db, seeded):
    body = json.dumps(_payload_inbound()).encode("utf-8")
    sig = compute_signature(WEBHOOK_SECRET, body)
    r = client.post(
        "/api/webhooks/whatsapp/1/evolution",
        content=body,
        headers={"Content-Type": "application/json", "X-Sdr-Signature": sig},
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ok"] is True
    assert j["summary"]["inbound_processed"] == 1


def test_webhook_401_without_signature(client, db, seeded):
    body = json.dumps(_payload_inbound()).encode("utf-8")
    r = client.post(
        "/api/webhooks/whatsapp/1/evolution", content=body,
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 401


def test_webhook_401_with_wrong_signature(client, db, seeded):
    body = json.dumps(_payload_inbound()).encode("utf-8")
    r = client.post(
        "/api/webhooks/whatsapp/1/evolution", content=body,
        headers={"Content-Type": "application/json", "X-Sdr-Signature": "sha256=deadbeef"},
    )
    assert r.status_code == 401


def test_webhook_404_unknown_provider(client, db, seeded):
    body = json.dumps({"event": "x"}).encode("utf-8")
    sig = compute_signature(WEBHOOK_SECRET, body)
    r = client.post(
        "/api/webhooks/whatsapp/1/bogus", content=body,
        headers={"X-Sdr-Signature": sig, "Content-Type": "application/json"},
    )
    assert r.status_code in (401, 404)


def test_webhook_idempotent_retry(client, db, seeded):
    body = json.dumps(_payload_inbound()).encode("utf-8")
    sig = compute_signature(WEBHOOK_SECRET, body)
    headers = {"Content-Type": "application/json", "X-Sdr-Signature": sig}

    r1 = client.post("/api/webhooks/whatsapp/1/evolution", content=body, headers=headers)
    r2 = client.post("/api/webhooks/whatsapp/1/evolution", content=body, headers=headers)
    assert r1.status_code == 200
    assert r2.status_code == 200

    from app.models import ConversationMessage
    count = db.query(ConversationMessage).filter_by(provider_message_id="EVO-WH-1").count()
    assert count == 1
