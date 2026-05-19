"""Pydantic schemas validando shape do `config` por provider.

`SECRET_FIELDS[provider]` mapeia quais campos são criptografados
antes de gravar e mascarados na resposta.
"""
from pydantic import BaseModel, EmailStr, Field, SecretStr


class ResendConfig(BaseModel):
    api_key: SecretStr
    from_email: EmailStr
    from_name: str
    reply_to: EmailStr | None = None
    webhook_secret: SecretStr | None = None


class TelegramConfig(BaseModel):
    bot_token: SecretStr
    chat_id: str


class ApifyConfig(BaseModel):
    token: SecretStr


class LlmConfig(BaseModel):
    api_key: SecretStr
    model: str
    base_url: str


class HunterConfig(BaseModel):
    api_key: SecretStr


class ApolloConfig(BaseModel):
    api_key: SecretStr


class EvolutionConfig(BaseModel):
    base_url: str = Field(min_length=8)         # ex: https://evo.example.com
    instance: str = Field(min_length=1)         # nome da instância — required
    api_key: SecretStr                          # apikey header + auth de webhook (Evolution v2 não tem HMAC)
    webhook_secret: SecretStr | None = None     # não usado por Evolution v2; reservado pra futuro provider com HMAC


class LangsmithConfig(BaseModel):
    api_key: SecretStr
    project: str
    tracing: bool = False


PROVIDER_SCHEMAS: dict[str, type[BaseModel]] = {
    "resend": ResendConfig,
    "telegram": TelegramConfig,
    "apify": ApifyConfig,
    "llm": LlmConfig,
    "hunter": HunterConfig,
    "apollo": ApolloConfig,
    "evolution": EvolutionConfig,
    "langsmith": LangsmithConfig,
}

SECRET_FIELDS: dict[str, set[str]] = {
    "resend": {"api_key", "webhook_secret"},
    "telegram": {"bot_token"},
    "apify": {"token"},
    "llm": {"api_key"},
    "hunter": {"api_key"},
    "apollo": {"api_key"},
    "evolution": {"api_key", "webhook_secret"},
    "langsmith": {"api_key"},
}
