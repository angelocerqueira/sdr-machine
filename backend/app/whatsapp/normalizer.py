"""Helpers compartilhados entre adapters WhatsApp.

Foco: normalização de telefone BR + parsing de chat_id WhatsApp.
"""
from __future__ import annotations

import re

_DIGITS = re.compile(r"\D+")


def normalize_phone_br(raw: str | None) -> str:
    """Normaliza telefone BR pro formato WhatsApp internacional (55 + DDD + número).

    Aceita máscaras comuns: "(44) 99999-0000", "+55 44 9 9999-0000",
    "44999990000", etc. Garante DDI 55. Rejeita strings sem dígitos ou
    com menos de 10 dígitos efetivos (DDD + 8 dígitos mínimos).
    """
    if not raw:
        raise ValueError("Phone is empty")
    digits = _DIGITS.sub("", raw)
    if len(digits) < 10:
        raise ValueError(f"Phone too short: {raw!r} → {digits!r}")
    # Adiciona DDI 55 se ausente
    if not digits.startswith("55") or len(digits) <= 11:
        digits = "55" + digits
    return digits


def to_chat_id(phone: str) -> str:
    """Telefone normalizado → chat_id WhatsApp individual."""
    return f"{phone}@s.whatsapp.net"


def parse_chat_id(chat_id: str) -> str:
    """chat_id individual → telefone normalizado. Rejeita grupos."""
    if chat_id.endswith("@g.us"):
        raise ValueError(f"Group chats not supported in P1: {chat_id}")
    if chat_id.endswith("@s.whatsapp.net"):
        return chat_id.split("@", 1)[0]
    # Tolera chat_id sem sufixo (puro phone)
    return chat_id
