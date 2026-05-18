import pytest
from pydantic import ValidationError


def test_provider_schemas_registry_has_all_eight():
    from app.integrations.schemas import PROVIDER_SCHEMAS
    expected = {"resend", "telegram", "apify", "llm", "hunter", "apollo", "evolution", "langsmith"}
    assert set(PROVIDER_SCHEMAS.keys()) == expected


def test_resend_requires_api_key_and_from_email():
    from app.integrations.schemas import ResendConfig
    with pytest.raises(ValidationError):
        ResendConfig(from_email="x@y.com", from_name="X")  # missing api_key
    with pytest.raises(ValidationError):
        ResendConfig(api_key="re_x", from_name="X")  # missing from_email
    cfg = ResendConfig(api_key="re_x", from_email="x@y.com", from_name="X")
    assert cfg.api_key.get_secret_value() == "re_x"


def test_telegram_requires_bot_token_and_chat_id():
    from app.integrations.schemas import TelegramConfig
    with pytest.raises(ValidationError):
        TelegramConfig(chat_id="-100123")  # missing bot_token
    cfg = TelegramConfig(bot_token="abc", chat_id="-100123")
    assert cfg.bot_token.get_secret_value() == "abc"


def test_apify_minimal():
    from app.integrations.schemas import ApifyConfig
    cfg = ApifyConfig(token="apify_xxx")
    assert cfg.token.get_secret_value() == "apify_xxx"


def test_llm_requires_three_fields():
    from app.integrations.schemas import LlmConfig
    with pytest.raises(ValidationError):
        LlmConfig(api_key="k", model="m")  # missing base_url
    cfg = LlmConfig(api_key="k", model="claude-x", base_url="https://api.x")
    assert cfg.model == "claude-x"


def test_secret_fields_set():
    """Campos cifrados devem estar declarados em SECRET_FIELDS por provider."""
    from app.integrations.schemas import SECRET_FIELDS
    assert SECRET_FIELDS["resend"] == {"api_key", "webhook_secret"}
    assert SECRET_FIELDS["telegram"] == {"bot_token"}
    assert SECRET_FIELDS["apify"] == {"token"}
    assert SECRET_FIELDS["llm"] == {"api_key"}
    assert SECRET_FIELDS["hunter"] == {"api_key"}
    assert SECRET_FIELDS["apollo"] == {"api_key"}
    assert SECRET_FIELDS["langsmith"] == {"api_key"}
