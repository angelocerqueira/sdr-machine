import pytest
from cryptography.fernet import Fernet


@pytest.fixture(autouse=True)
def _enc_key(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("SETTINGS_ENC_KEY", key)
    import importlib
    from app import config
    importlib.reload(config)
    from app.integrations import crypto
    importlib.reload(crypto)


def test_resolver_returns_db_when_present(db):
    from app.integrations.crypto import encrypt
    from app.integrations.resolver import get_provider_config
    from app.models import IntegrationSettings

    db.add(IntegrationSettings(
        workspace_id=1,
        provider="resend",
        config={"api_key": encrypt("re_real"), "from_email": "x@y.com", "from_name": "X"},
        enabled=True,
    ))
    db.commit()

    cfg = get_provider_config(db, 1, "resend")
    assert cfg["api_key"] == "re_real"  # decrypted
    assert cfg["from_email"] == "x@y.com"


def test_resolver_falls_back_to_env_when_no_db_row(db, monkeypatch):
    from app.integrations.resolver import get_provider_config
    monkeypatch.setenv("APIFY_TOKEN", "apify_env_token")
    import importlib
    from app import config
    importlib.reload(config)

    cfg = get_provider_config(db, 1, "apify")
    assert cfg == {"token": "apify_env_token"}


def test_resolver_returns_none_when_disabled_and_no_env(db, monkeypatch):
    from app.integrations.resolver import get_provider_config
    from app.models import IntegrationSettings

    db.add(IntegrationSettings(
        workspace_id=1, provider="resend", config={"api_key": "x"},
        enabled=False,
    ))
    db.commit()
    # resend nunca teve env fallback
    assert get_provider_config(db, 1, "resend") is None


def test_resolver_returns_none_when_no_db_no_env(db, monkeypatch):
    from app.integrations.resolver import get_provider_config
    monkeypatch.delenv("HUNTER_API_KEY", raising=False)
    import importlib
    from app import config
    importlib.reload(config)
    assert get_provider_config(db, 1, "hunter") is None


def test_decrypt_secrets_strict_default_raises_on_corrupt():
    """strict=True (default) propaga InvalidToken pro caller (router path)."""
    from cryptography.fernet import InvalidToken
    from app.integrations.resolver import _decrypt_secrets
    raw = {
        "api_key": "gAAAAAB-not-a-valid-fernet-token",
        "from_email": "x@y.com",
    }
    with pytest.raises(InvalidToken):
        _decrypt_secrets("resend", raw)


def test_decrypt_secrets_strict_false_returns_none_on_corrupt():
    """strict=False retorna None — usado pelo pipeline path pra fallback."""
    from app.integrations.resolver import _decrypt_secrets
    raw = {
        "api_key": "gAAAAAB-not-a-valid-fernet-token",
        "from_email": "x@y.com",
    }
    assert _decrypt_secrets("resend", raw, strict=False) is None


def test_get_provider_config_falls_back_to_env_when_db_secret_corrupt(db, monkeypatch):
    """Row com secret corrompido + env válido → retorna env (graceful degrade)."""
    from app.integrations.resolver import get_provider_config
    from app.models import IntegrationSettings

    db.add(IntegrationSettings(
        workspace_id=1, provider="apify",
        config={"token": "gAAAAAB-corrupt-cipher"},
        enabled=True,
    ))
    db.commit()

    monkeypatch.setenv("APIFY_TOKEN", "apify_env_fallback")
    import importlib
    from app import config
    importlib.reload(config)

    cfg = get_provider_config(db, 1, "apify")
    assert cfg == {"token": "apify_env_fallback"}


def test_get_provider_config_returns_none_when_corrupt_and_no_env(db, monkeypatch):
    """Row corrompido + env vazio → None (não retorna config quebrado)."""
    from app.integrations.resolver import get_provider_config
    from app.models import IntegrationSettings

    db.add(IntegrationSettings(
        workspace_id=1, provider="hunter",
        config={"api_key": "gAAAAAB-corrupt-cipher"},
        enabled=True,
    ))
    db.commit()

    monkeypatch.delenv("HUNTER_API_KEY", raising=False)
    import importlib
    from app import config
    importlib.reload(config)

    assert get_provider_config(db, 1, "hunter") is None
