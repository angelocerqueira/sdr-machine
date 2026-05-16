import pytest

from app.whatsapp.normalizer import (
    normalize_phone_br,
    to_chat_id,
    parse_chat_id,
)


@pytest.mark.parametrize("raw, expected", [
    ("(44) 99999-0000", "5544999990000"),
    ("44 99999-0000", "5544999990000"),
    ("+55 44 99999-0000", "5544999990000"),
    ("5544999990000", "5544999990000"),
    ("44999990000", "5544999990000"),  # sem 55
    ("  44 9 9999-0000  ", "5544999990000"),  # espaços + 9 dígitos
])
def test_normalize_phone_br_ok(raw, expected):
    assert normalize_phone_br(raw) == expected


@pytest.mark.parametrize("raw", ["", None, "abc", "12"])
def test_normalize_phone_br_invalid(raw):
    with pytest.raises(ValueError):
        normalize_phone_br(raw)


def test_to_chat_id_individual():
    assert to_chat_id("5544999990000") == "5544999990000@s.whatsapp.net"


def test_parse_chat_id_individual():
    assert parse_chat_id("5544999990000@s.whatsapp.net") == "5544999990000"


def test_parse_chat_id_group_raises():
    with pytest.raises(ValueError):
        parse_chat_id("12345-67890@g.us")  # grupo, não suportado P1
