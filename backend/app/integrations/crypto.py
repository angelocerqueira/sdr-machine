"""Fernet symmetric encryption for storing provider secrets at rest.

Master key comes from SETTINGS_ENC_KEY env var (loaded by app.config).
Rotation = re-encrypt every row with a new key (script utility, not in v1).
"""
from cryptography.fernet import Fernet

from app.config import settings

_fernet = Fernet(settings.settings_enc_key.encode())


def encrypt(plain: str) -> str:
    """Cifra string em UTF-8 -> Fernet token (URL-safe base64)."""
    return _fernet.encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt(cipher: str) -> str:
    """Decifra Fernet token. Raises InvalidToken se tampered/expired."""
    return _fernet.decrypt(cipher.encode("utf-8")).decode("utf-8")


def mask(plain: str | None, keep: int = 4) -> str:
    """Retorna placeholder pra exibir credencial mascarada na UI.

    `keep` últimos chars expostos quando string é maior que `keep`.
    Strings curtas/vazias retornam apenas dots.
    """
    if not plain or len(plain) <= keep:
        return "•" * 8
    return "•" * 8 + plain[-keep:]
