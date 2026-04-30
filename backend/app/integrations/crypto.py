"""Fernet symmetric encryption for storing provider secrets at rest.

Master key vem de SETTINGS_ENC_KEY env var. Init é lazy: o módulo importa
mesmo sem a key (não trava startup do container). Apenas chamadas a
encrypt/decrypt levantam erro claro quando a key não está configurada,
permitindo que integrações via env fallback continuem funcionando até
o operador adicionar o secret.

Rotation = re-encrypt todas as linhas com nova key (script utility, não em v1).
"""
from cryptography.fernet import Fernet

from app.config import settings

_fernet: Fernet | None = None


class SettingsEncKeyMissing(RuntimeError):
    """Raised quando crypto é usado sem SETTINGS_ENC_KEY configurado."""


def _get_fernet() -> Fernet:
    """Lazy init do Fernet — só falha se alguém tentar usar sem key."""
    global _fernet
    if _fernet is not None:
        return _fernet
    key = settings.settings_enc_key
    if not key:
        raise SettingsEncKeyMissing(
            "SETTINGS_ENC_KEY env var não está configurada. "
            "Gere com: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\" "
            "e adicione aos secrets do deploy."
        )
    _fernet = Fernet(key.encode())
    return _fernet


def encrypt(plain: str) -> str:
    """Cifra string em UTF-8 -> Fernet token (URL-safe base64)."""
    return _get_fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt(cipher: str) -> str:
    """Decifra Fernet token. Raises InvalidToken se tampered/expired."""
    return _get_fernet().decrypt(cipher.encode("utf-8")).decode("utf-8")


def mask(plain: str | None, keep: int = 4) -> str:
    """Retorna placeholder pra exibir credencial mascarada na UI.

    `keep` últimos chars expostos quando string é maior que `keep`.
    Strings curtas/vazias retornam apenas dots.
    """
    if not plain or len(plain) <= keep:
        return "•" * 8
    return "•" * 8 + plain[-keep:]
