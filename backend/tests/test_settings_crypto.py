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


def test_crypto_module_imports_without_key(monkeypatch):
    """Container deve subir mesmo sem SETTINGS_ENC_KEY — só falha em uso.

    setenv("SETTINGS_ENC_KEY", "") força string vazia mesmo com .env local
    setado (env vars têm precedência sobre .env file no pydantic-settings).
    """
    monkeypatch.setenv("SETTINGS_ENC_KEY", "")
    import importlib
    from app import config
    importlib.reload(config)
    from app.integrations import crypto
    importlib.reload(crypto)
    # Module-level state: _fernet ainda None, sem crash
    assert crypto._fernet is None
    assert config.settings.settings_enc_key == ""


def test_crypto_raises_settings_enc_key_missing_on_use(monkeypatch):
    """Tentar cifrar/decifrar sem key levanta erro tipado, não Fernet/ValueError."""
    monkeypatch.setenv("SETTINGS_ENC_KEY", "")
    import importlib
    from app import config
    importlib.reload(config)
    from app.integrations import crypto
    importlib.reload(crypto)
    from app.integrations.crypto import SettingsEncKeyMissing, encrypt, decrypt

    with pytest.raises(SettingsEncKeyMissing):
        encrypt("anything")
    with pytest.raises(SettingsEncKeyMissing):
        decrypt("gAAAAAB-x")
