import os
import pytest
from cryptography.fernet import Fernet, InvalidToken


@pytest.fixture(autouse=True)
def _enc_key(monkeypatch):
    """Gera key fresca por teste e injeta em settings."""
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("SETTINGS_ENC_KEY", key)
    # Re-import pra pegar key nova
    import importlib
    from app import config
    importlib.reload(config)
    from app.integrations import crypto
    importlib.reload(crypto)
    yield


def test_encrypt_decrypt_roundtrip():
    from app.integrations.crypto import encrypt, decrypt
    plain = "re_test_abc123"
    cipher = encrypt(plain)
    assert cipher != plain
    assert decrypt(cipher) == plain


def test_decrypt_tampered_raises():
    from app.integrations.crypto import encrypt, decrypt
    cipher = encrypt("hello")
    tampered = cipher[:-2] + "XX"
    with pytest.raises(InvalidToken):
        decrypt(tampered)


def test_mask_keeps_last_four():
    from app.integrations.crypto import mask
    assert mask("re_test_abc1234") == "••••••••1234"


def test_mask_short_string():
    from app.integrations.crypto import mask
    assert mask("abc") == "••••••••"


def test_mask_empty():
    from app.integrations.crypto import mask
    assert mask("") == "••••••••"
    assert mask(None) == "••••••••"
