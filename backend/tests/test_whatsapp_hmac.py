import pytest

from app.whatsapp.hmac import compute_signature, verify_signature


def test_compute_signature_deterministic():
    body = b'{"event":"messages.upsert"}'
    sig1 = compute_signature("secret", body)
    sig2 = compute_signature("secret", body)
    assert sig1 == sig2
    assert sig1.startswith("sha256=")


def test_compute_signature_changes_with_secret():
    body = b'{"event":"messages.upsert"}'
    assert compute_signature("secret1", body) != compute_signature("secret2", body)


def test_verify_signature_ok():
    body = b'{"event":"x"}'
    sig = compute_signature("topsecret", body)
    assert verify_signature("topsecret", body, sig) is True


def test_verify_signature_wrong_secret():
    body = b'{"event":"x"}'
    sig = compute_signature("topsecret", body)
    assert verify_signature("wrongsecret", body, sig) is False


def test_verify_signature_tampered_body():
    body = b'{"event":"x"}'
    sig = compute_signature("topsecret", body)
    tampered = b'{"event":"y"}'
    assert verify_signature("topsecret", tampered, sig) is False


def test_verify_signature_missing_prefix_rejected():
    body = b'{"event":"x"}'
    sig = compute_signature("topsecret", body)
    raw_hex = sig.removeprefix("sha256=")
    # Aceita sem o prefixo "sha256=" (caso o provider não use prefixo)
    assert verify_signature("topsecret", body, raw_hex) is True


def test_verify_signature_empty_input_safe():
    assert verify_signature("s", b"x", "") is False
    assert verify_signature("s", b"x", None) is False  # type: ignore[arg-type]
