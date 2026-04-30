# UI Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir superfície de configuração `/app/settings/*` com gerenciamento de credenciais cifradas (Fernet), perfil de remetente, preferências de targeting e teste de integrações — substituindo gradualmente env vars hoje em `app/config.py`. Schema multi-tenant-ready.

**Architecture:** 3 tabelas novas (`integration_settings` extensível por provider, `workspace_profile`, `workspace_targeting`) com `workspace_id` (constante 1 hoje). Resolver `DB → env fallback` no backend mantém zero breakage. Frontend usa sub-rotas com sidebar interna desktop e drill-in mobile. Replace pattern para edição de credenciais.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic + cryptography (Fernet) backend; Next.js 16 App Router + React 19 + Tailwind 4 + DS Instrumento frontend; pytest + SQLite in-memory.

**Spec:** `docs/superpowers/specs/2026-04-30-ui-settings-design.md`

---

## File Structure

### Backend novo
```
backend/
├── app/
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── crypto.py           # Fernet encrypt/decrypt/mask
│   │   ├── schemas.py          # Pydantic configs por provider + registry
│   │   ├── resolver.py         # get_provider_config() DB→env fallback
│   │   ├── testers.py          # 7 testers + dispatch
│   │   └── tenant.py           # get_current_workspace_id() helper
│   ├── routers/
│   │   └── workspace_settings.py  # 9 endpoints
│   └── models.py               # +3 modelos no fim
├── alembic/versions/
│   └── n07_workspace_settings.py
└── tests/
    ├── test_settings_crypto.py
    ├── test_settings_schemas.py
    ├── test_settings_resolver.py
    ├── test_settings_router.py
    └── test_settings_testers.py
```

### Backend modificado
- `app/config.py` — adiciona `settings_enc_key` obrigatório
- `app/main.py` — registra router novo
- `app/middleware/auth.py` — expõe `request.state.user_id` quando válido
- `app/pipeline/scraper.py` — usa resolver pra Apify
- `app/pipeline/generator.py` — usa resolver pra LLM
- `app/pipeline/enrichment/providers/email_discoverer.py` — Hunter
- `app/pipeline/enrichment/providers/apollo.py` — Apollo
- `app/pipeline/enrichment/__init__.py` ou call site Langsmith
- `requirements.txt` — adiciona `cryptography`
- `.env.example` — adiciona `SETTINGS_ENC_KEY`

### Frontend novo
```
frontend/src/
├── app/app/settings/
│   ├── layout.tsx              # SettingsLayout (sidebar interna + drill-in)
│   ├── settings.css            # estilos da seção
│   ├── page.tsx                # redirect → /perfil
│   ├── perfil/page.tsx
│   ├── targeting/page.tsx
│   ├── avancado/page.tsx       # placeholder "em breve"
│   └── integracoes/
│       ├── page.tsx            # grid de cards
│       ├── integration-card.tsx
│       └── [provider]/page.tsx # detalhe + replace pattern
├── components/settings/
│   ├── secret-field.tsx        # replace pattern reusável
│   ├── chips-input.tsx         # niches/cities chips
│   ├── status-badge.tsx        # ✓/⚠/✗
│   └── test-button.tsx         # botão Testar com loading + result inline
└── lib/
    ├── api-settings.ts         # 9 funções tipadas (api.ts já tem auth handling)
    └── settings-types.ts       # IntegrationDetail discriminated union etc.
```

### Frontend modificado
- `src/components/app-sidebar.tsx` — entry settings + dropdown item
- `src/lib/types.ts` — re-export tipos novos

---

## PR 1: Migration + Crypto + Schemas

Foundation. Sem PR2/3/4/5, este já merge limpo: tabelas existem, helpers prontos, mas ninguém usa.

### Task 1.1: Adicionar `cryptography` em requirements

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Adicionar dependência**

```diff
 sqlalchemy==2.0.35
 pydantic-settings==2.5.0
 httpx==0.27.0
+cryptography==44.0.0
```

- [ ] **Step 2: Instalar e verificar**

Run: `cd backend && pip install -r requirements.txt && python -c "from cryptography.fernet import Fernet; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "deps(backend): add cryptography for Fernet encryption"
```

### Task 1.2: `SETTINGS_ENC_KEY` obrigatório em config

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/.env.example`

- [ ] **Step 1: Adicionar campo obrigatório no Settings**

Edit `backend/app/config.py` adicionando linha **antes** de `model_config`:

```python
    settings_enc_key: str  # Fernet master key — obrigatório
```

- [ ] **Step 2: Adicionar default geração no .env.example**

Edit `backend/.env.example` (criar se não existir) adicionando:

```bash
# Master key para criptografar credenciais salvas via UI Settings.
# Gere com: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
SETTINGS_ENC_KEY=
```

- [ ] **Step 3: Adicionar key real no .env local**

Run: `cd backend && python -c "from cryptography.fernet import Fernet; print('SETTINGS_ENC_KEY=' + Fernet.generate_key().decode())" >> .env`

- [ ] **Step 4: Verificar startup**

Run: `cd backend && python -c "from app.config import settings; print(bool(settings.settings_enc_key))"`
Expected: `True`

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/.env.example
git commit -m "config: add required SETTINGS_ENC_KEY for Fernet master"
```

### Task 1.3: Crypto helper com TDD

**Files:**
- Create: `backend/app/integrations/__init__.py`
- Create: `backend/app/integrations/crypto.py`
- Create: `backend/tests/test_settings_crypto.py`

- [ ] **Step 1: Criar pacote**

Create `backend/app/integrations/__init__.py` com conteúdo vazio.

- [ ] **Step 2: Escrever testes failing**

Create `backend/tests/test_settings_crypto.py`:

```python
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
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `cd backend && pytest tests/test_settings_crypto.py -v`
Expected: ImportError, módulo `app.integrations.crypto` não existe.

- [ ] **Step 4: Implementar crypto.py**

Create `backend/app/integrations/crypto.py`:

```python
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
```

- [ ] **Step 5: Rodar testes**

Run: `cd backend && pytest tests/test_settings_crypto.py -v`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/integrations/__init__.py backend/app/integrations/crypto.py backend/tests/test_settings_crypto.py
git commit -m "feat(integrations): Fernet crypto helper with mask utility"
```

### Task 1.4: Pydantic schemas por provider

**Files:**
- Create: `backend/app/integrations/schemas.py`
- Create: `backend/tests/test_settings_schemas.py`

- [ ] **Step 1: Escrever testes failing**

Create `backend/tests/test_settings_schemas.py`:

```python
import pytest
from pydantic import ValidationError


def test_provider_schemas_registry_has_all_seven():
    from app.integrations.schemas import PROVIDER_SCHEMAS
    expected = {"resend", "telegram", "apify", "llm", "hunter", "apollo", "langsmith"}
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && pytest tests/test_settings_schemas.py -v`
Expected: ImportError.

- [ ] **Step 3: Implementar schemas.py**

Create `backend/app/integrations/schemas.py`:

```python
"""Pydantic schemas validando shape do `config` por provider.

`SECRET_FIELDS[provider]` mapeia quais campos são criptografados
antes de gravar e mascarados na resposta.
"""
from pydantic import BaseModel, EmailStr, SecretStr


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
    "langsmith": LangsmithConfig,
}

SECRET_FIELDS: dict[str, set[str]] = {
    "resend": {"api_key", "webhook_secret"},
    "telegram": {"bot_token"},
    "apify": {"token"},
    "llm": {"api_key"},
    "hunter": {"api_key"},
    "apollo": {"api_key"},
    "langsmith": {"api_key"},
}
```

- [ ] **Step 4: Rodar testes**

Run: `cd backend && pytest tests/test_settings_schemas.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/integrations/schemas.py backend/tests/test_settings_schemas.py
git commit -m "feat(integrations): pydantic schemas + secret-fields registry per provider"
```

### Task 1.5: Models SQLAlchemy

**Files:**
- Modify: `backend/app/models.py` (append)

- [ ] **Step 1: Adicionar 3 modelos no fim de models.py**

Append em `backend/app/models.py` (após `OutreachMessage`):

```python
class IntegrationSettings(Base):
    __tablename__ = "integration_settings"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, nullable=False, default=1, server_default="1")
    provider = Column(String(32), nullable=False)
    config = Column(JSON, nullable=False, default=dict, server_default="{}")
    enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    last_tested_at = Column(DateTime, nullable=True)
    last_test_result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("workspace_id", "provider", name="uq_integration_workspace_provider"),
        Index("idx_integration_settings_workspace", "workspace_id"),
    )


class WorkspaceProfile(Base):
    __tablename__ = "workspace_profile"

    workspace_id = Column(Integer, primary_key=True, default=1, server_default="1")
    business_name = Column(String(255), nullable=True)
    your_name = Column(String(255), nullable=True)
    your_email = Column(String(255), nullable=True)
    your_whatsapp = Column(String(50), nullable=True)
    your_website = Column(String(500), nullable=True)
    legal_basis = Column(String(64), nullable=True, default="legitimo_interesse_b2b",
                         server_default="legitimo_interesse_b2b")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class WorkspaceTargeting(Base):
    __tablename__ = "workspace_targeting"

    workspace_id = Column(Integer, primary_key=True, default=1, server_default="1")
    target_niches = Column(JSON, nullable=True, default=list, server_default="[]")
    target_cities = Column(JSON, nullable=True, default=list, server_default="[]")
    min_rating = Column(Float, nullable=True)
    max_results_per_search = Column(Integer, nullable=True)
    opportunity_score_threshold = Column(Integer, nullable=True)
    diagnostic_model = Column(String(64), nullable=True)
    skip_ai_diagnostic = Column(Boolean, nullable=True)
    skip_social_scraping = Column(Boolean, nullable=True)
    ai_potential_threshold = Column(Integer, nullable=True)
    disqualify_threshold = Column(Integer, nullable=True)
    skip_service_level_analysis = Column(Boolean, nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
```

- [ ] **Step 2: Verificar import**

Run: `cd backend && python -c "from app.models import IntegrationSettings, WorkspaceProfile, WorkspaceTargeting; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Verificar testes ainda passam**

Run: `cd backend && pytest tests/test_settings_crypto.py tests/test_settings_schemas.py -q`
Expected: 11 passed (não regrediu)

- [ ] **Step 4: Commit**

```bash
git add backend/app/models.py
git commit -m "feat(models): IntegrationSettings, WorkspaceProfile, WorkspaceTargeting"
```

### Task 1.6: Alembic migration

**Files:**
- Create: `backend/alembic/versions/n07_workspace_settings.py`

- [ ] **Step 1: Criar migration manualmente**

Create `backend/alembic/versions/n07_workspace_settings.py`:

```python
"""workspace settings — integrations, profile, targeting

Revision ID: k04
Revises: m06_place_id_unique
Create Date: 2026-04-30
"""
from alembic import op
import sqlalchemy as sa


revision = "n07"
down_revision = "m06_place_id_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integration_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_tested_at", sa.DateTime(), nullable=True),
        sa.Column("last_test_result", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "provider", name="uq_integration_workspace_provider"),
    )
    op.create_index("idx_integration_settings_workspace", "integration_settings", ["workspace_id"])

    op.create_table(
        "workspace_profile",
        sa.Column("workspace_id", sa.Integer(), primary_key=True, server_default="1"),
        sa.Column("business_name", sa.String(length=255), nullable=True),
        sa.Column("your_name", sa.String(length=255), nullable=True),
        sa.Column("your_email", sa.String(length=255), nullable=True),
        sa.Column("your_whatsapp", sa.String(length=50), nullable=True),
        sa.Column("your_website", sa.String(length=500), nullable=True),
        sa.Column("legal_basis", sa.String(length=64), nullable=True,
                  server_default="legitimo_interesse_b2b"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "workspace_targeting",
        sa.Column("workspace_id", sa.Integer(), primary_key=True, server_default="1"),
        sa.Column("target_niches", sa.JSON(), nullable=True, server_default="[]"),
        sa.Column("target_cities", sa.JSON(), nullable=True, server_default="[]"),
        sa.Column("min_rating", sa.Float(), nullable=True),
        sa.Column("max_results_per_search", sa.Integer(), nullable=True),
        sa.Column("opportunity_score_threshold", sa.Integer(), nullable=True),
        sa.Column("diagnostic_model", sa.String(length=64), nullable=True),
        sa.Column("skip_ai_diagnostic", sa.Boolean(), nullable=True),
        sa.Column("skip_social_scraping", sa.Boolean(), nullable=True),
        sa.Column("ai_potential_threshold", sa.Integer(), nullable=True),
        sa.Column("disqualify_threshold", sa.Integer(), nullable=True),
        sa.Column("skip_service_level_analysis", sa.Boolean(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("workspace_targeting")
    op.drop_table("workspace_profile")
    op.drop_index("idx_integration_settings_workspace", table_name="integration_settings")
    op.drop_table("integration_settings")
```

- [ ] **Step 2: Aplicar migration localmente**

Run: `cd backend && alembic upgrade head`
Expected: log mostra `Running upgrade m06 -> n07`. Sem erros.

- [ ] **Step 3: Verificar tabelas**

Run: `cd backend && python -c "from app.database import engine; from sqlalchemy import inspect; print(sorted(t for t in inspect(engine).get_table_names() if t.startswith(('integration', 'workspace'))))"`
Expected: `['integration_settings', 'workspace_profile', 'workspace_targeting']`

- [ ] **Step 4: Testar downgrade-upgrade**

Run: `cd backend && alembic downgrade -1 && alembic upgrade head`
Expected: ambos sem erro.

- [ ] **Step 5: Rodar todos testes pra checar não-regressão**

Run: `cd backend && pytest -q`
Expected: 390+ passed.

- [ ] **Step 6: Commit + abrir PR**

```bash
git add backend/alembic/versions/n07_workspace_settings.py
git commit -m "feat(db): migration n07 — integration_settings + workspace_profile + workspace_targeting"
git push -u origin feat/ui-settings-spec
gh pr create --title "feat(settings): foundation — migration + crypto + schemas" --body "$(cat <<'EOF'
## Summary
- Adiciona dependência \`cryptography\`
- \`SETTINGS_ENC_KEY\` obrigatório em config (Fernet master)
- Helper \`integrations/crypto.py\` (encrypt/decrypt/mask) com testes
- Pydantic schemas dos 7 providers + registry SECRET_FIELDS
- 3 models: IntegrationSettings, WorkspaceProfile, WorkspaceTargeting
- Alembic k04 com upgrade/downgrade

Spec: \`docs/superpowers/specs/2026-04-30-ui-settings-design.md\`

## Test plan
- [x] \`pytest tests/test_settings_crypto.py tests/test_settings_schemas.py\` 11 passed
- [x] \`alembic upgrade head\` aplica
- [x] \`alembic downgrade -1 && upgrade head\` reversível
- [x] \`pytest -q\` full suite verde
EOF
)"
```

---

## PR 2: Backend Router + Testers + Resolver

Endpoints REST + lógica de teste de credencial + resolver DB→env. Reusa foundation do PR 1.

**Pre-condition:** PR 1 mergeado, branch atualizada.

### Task 2.1: Branch nova

- [ ] **Step 1: Criar branch a partir de main**

```bash
git checkout main && git pull --ff-only
git checkout -b feat/ui-settings-backend
```

### Task 2.2: Tenant resolver

**Files:**
- Create: `backend/app/integrations/tenant.py`

- [ ] **Step 1: Criar helper**

Create `backend/app/integrations/tenant.py`:

```python
"""Resolve workspace_id do request.

Hoje retorna constante DEFAULT_WORKSPACE_ID = 1 (single-tenant).
Quando virar multi-tenant pra valer, esta função consulta membership
via session do Better Auth — call sites não mudam.
"""
from fastapi import Request

DEFAULT_WORKSPACE_ID = 1


def get_current_workspace_id(request: Request) -> int:
    # Multi-tenant futuro: lookup user_id em workspace_users.
    # Hoje single-workspace global.
    return DEFAULT_WORKSPACE_ID
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/integrations/tenant.py
git commit -m "feat(integrations): tenant resolver scaffold (single-workspace today)"
```

### Task 2.3: Resolver `get_provider_config` com TDD

**Files:**
- Create: `backend/app/integrations/resolver.py`
- Create: `backend/tests/test_settings_resolver.py`

- [ ] **Step 1: Escrever testes failing**

Create `backend/tests/test_settings_resolver.py`:

```python
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && pytest tests/test_settings_resolver.py -v`
Expected: ImportError no `app.integrations.resolver`

- [ ] **Step 3: Implementar resolver**

Create `backend/app/integrations/resolver.py`:

```python
"""Resolve config de provider: DB primeiro, env fallback.

Permite migração progressiva: enquanto user não configurar via UI,
pipelines continuam lendo .env como antes.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.integrations.crypto import decrypt
from app.integrations.schemas import SECRET_FIELDS
from app.models import IntegrationSettings


def get_provider_config(
    db: Session, workspace_id: int, provider: str
) -> dict | None:
    """Retorna dict pronto pra uso (secrets já decifrados) ou None."""
    row = (
        db.query(IntegrationSettings)
        .filter_by(workspace_id=workspace_id, provider=provider, enabled=True)
        .first()
    )
    if row:
        return _decrypt_secrets(provider, row.config)
    return _env_fallback(provider)


def _decrypt_secrets(provider: str, raw: dict) -> dict:
    """Aplica decrypt nos campos listados em SECRET_FIELDS pro provider."""
    secret_fields = SECRET_FIELDS.get(provider, set())
    out = {}
    for k, v in raw.items():
        if k in secret_fields and isinstance(v, str) and v:
            out[k] = decrypt(v)
        else:
            out[k] = v
    return out


def _env_fallback(provider: str) -> dict | None:
    """Lê config legado de env vars antigas — só pra integrações pré-existentes."""
    if provider == "apify":
        return {"token": settings.apify_token} if settings.apify_token else None
    if provider == "llm":
        if settings.llm_api_key:
            return {
                "api_key": settings.llm_api_key,
                "model": settings.llm_model,
                "base_url": settings.llm_base_url,
            }
        return None
    if provider == "hunter":
        return {"api_key": settings.hunter_api_key} if settings.hunter_api_key else None
    if provider == "apollo":
        return {"api_key": settings.apollo_api_key} if settings.apollo_api_key else None
    if provider == "langsmith":
        if settings.langsmith_api_key:
            return {
                "api_key": settings.langsmith_api_key,
                "project": settings.langsmith_project,
                "tracing": settings.langsmith_tracing,
            }
        return None
    return None  # resend, telegram nunca tiveram env
```

- [ ] **Step 4: Rodar testes**

Run: `cd backend && pytest tests/test_settings_resolver.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/integrations/resolver.py backend/tests/test_settings_resolver.py
git commit -m "feat(integrations): get_provider_config resolver (DB→env fallback)"
```

### Task 2.4: Testers dos 7 providers

**Files:**
- Create: `backend/app/integrations/testers.py`
- Create: `backend/tests/test_settings_testers.py`

- [ ] **Step 1: Adicionar `pytest-httpx` se não tiver**

Run: `cd backend && pip show pytest-httpx 2>/dev/null | head -1`
Se vazio, adiciona em `requirements.txt`: `pytest-httpx==0.32.0` e roda `pip install -r requirements.txt`.

- [ ] **Step 2: Escrever testes failing (cobertura mínima por tester)**

Create `backend/tests/test_settings_testers.py`:

```python
import pytest
from pytest_httpx import HTTPXMock


def test_resend_ok(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.resend.com/domains",
        json={"data": []},
        status_code=200,
    )
    from app.integrations.testers import test_resend
    res = test_resend({"api_key": "re_x"})
    assert res.ok is True
    assert res.error is None
    assert res.latency_ms >= 0


def test_resend_unauthorized(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.resend.com/domains",
        json={"name": "validation_error", "message": "API key is invalid"},
        status_code=401,
    )
    from app.integrations.testers import test_resend
    res = test_resend({"api_key": "re_bad"})
    assert res.ok is False
    assert "invalid" in res.error.lower()


def test_telegram_ok(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.telegram.org/bot123abc/getMe",
        json={"ok": True, "result": {"id": 1, "username": "bot"}},
        status_code=200,
    )
    from app.integrations.testers import test_telegram
    res = test_telegram({"bot_token": "123abc", "chat_id": "-100"})
    assert res.ok is True


def test_apify_ok(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.apify.com/v2/users/me?token=abc",
        json={"data": {"id": "1"}},
        status_code=200,
    )
    from app.integrations.testers import test_apify
    res = test_apify({"token": "abc"})
    assert res.ok is True


def test_dispatch_unknown_provider():
    from app.integrations.testers import run_test
    res = run_test("notarealthing", {})
    assert res.ok is False
    assert "unknown" in res.error.lower()
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `cd backend && pytest tests/test_settings_testers.py -v`
Expected: ImportError.

- [ ] **Step 4: Implementar testers**

Create `backend/app/integrations/testers.py`:

```python
"""Endpoints de validação por provider — chamada barata pra confirmar credencial."""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass

import httpx


@dataclass
class TestResult:
    ok: bool
    latency_ms: int
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _measure(fn, *args, **kwargs) -> TestResult:
    t0 = time.monotonic()
    try:
        return fn(*args, **kwargs, _t0=t0)
    except Exception as exc:
        return TestResult(
            ok=False,
            latency_ms=int((time.monotonic() - t0) * 1000),
            error=str(exc)[:200],
        )


def _result(ok: bool, t0: float, error: str | None = None) -> TestResult:
    return TestResult(
        ok=ok,
        latency_ms=int((time.monotonic() - t0) * 1000),
        error=error,
    )


def test_resend(cfg: dict, _t0: float | None = None) -> TestResult:
    t0 = _t0 if _t0 is not None else time.monotonic()
    r = httpx.get(
        "https://api.resend.com/domains",
        headers={"Authorization": f"Bearer {cfg['api_key']}"},
        timeout=10.0,
    )
    return _result(
        ok=r.status_code == 200, t0=t0,
        error=r.text[:200] if r.status_code != 200 else None,
    )


def test_telegram(cfg: dict, _t0: float | None = None) -> TestResult:
    t0 = _t0 if _t0 is not None else time.monotonic()
    r = httpx.get(
        f"https://api.telegram.org/bot{cfg['bot_token']}/getMe",
        timeout=10.0,
    )
    body = r.json() if r.status_code == 200 else {}
    return _result(
        ok=r.status_code == 200 and body.get("ok") is True, t0=t0,
        error=r.text[:200] if r.status_code != 200 else None,
    )


def test_apify(cfg: dict, _t0: float | None = None) -> TestResult:
    t0 = _t0 if _t0 is not None else time.monotonic()
    r = httpx.get(
        f"https://api.apify.com/v2/users/me?token={cfg['token']}",
        timeout=10.0,
    )
    return _result(ok=r.status_code == 200, t0=t0,
                   error=r.text[:200] if r.status_code != 200 else None)


def test_llm(cfg: dict, _t0: float | None = None) -> TestResult:
    t0 = _t0 if _t0 is not None else time.monotonic()
    r = httpx.post(
        f"{cfg['base_url']}/chat/completions",
        headers={"Authorization": f"Bearer {cfg['api_key']}",
                 "Content-Type": "application/json"},
        json={"model": cfg["model"], "messages": [{"role": "user", "content": "hi"}],
              "max_tokens": 5},
        timeout=15.0,
    )
    return _result(ok=r.status_code == 200, t0=t0,
                   error=r.text[:200] if r.status_code != 200 else None)


def test_hunter(cfg: dict, _t0: float | None = None) -> TestResult:
    t0 = _t0 if _t0 is not None else time.monotonic()
    r = httpx.get(
        f"https://api.hunter.io/v2/account?api_key={cfg['api_key']}",
        timeout=10.0,
    )
    return _result(ok=r.status_code == 200, t0=t0,
                   error=r.text[:200] if r.status_code != 200 else None)


def test_apollo(cfg: dict, _t0: float | None = None) -> TestResult:
    t0 = _t0 if _t0 is not None else time.monotonic()
    r = httpx.get(
        "https://api.apollo.io/v1/auth/health",
        headers={"X-Api-Key": cfg["api_key"]},
        timeout=10.0,
    )
    return _result(ok=r.status_code == 200, t0=t0,
                   error=r.text[:200] if r.status_code != 200 else None)


def test_langsmith(cfg: dict, _t0: float | None = None) -> TestResult:
    t0 = _t0 if _t0 is not None else time.monotonic()
    r = httpx.get(
        "https://api.smith.langchain.com/info",
        headers={"x-api-key": cfg["api_key"]},
        timeout=10.0,
    )
    return _result(ok=r.status_code == 200, t0=t0,
                   error=r.text[:200] if r.status_code != 200 else None)


TESTERS = {
    "resend": test_resend,
    "telegram": test_telegram,
    "apify": test_apify,
    "llm": test_llm,
    "hunter": test_hunter,
    "apollo": test_apollo,
    "langsmith": test_langsmith,
}


def run_test(provider: str, cfg: dict) -> TestResult:
    fn = TESTERS.get(provider)
    if fn is None:
        return TestResult(ok=False, latency_ms=0, error=f"unknown provider: {provider}")
    return _measure(fn, cfg)
```

- [ ] **Step 5: Rodar testes**

Run: `cd backend && pytest tests/test_settings_testers.py -v`
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/integrations/testers.py backend/tests/test_settings_testers.py
git commit -m "feat(integrations): testers for resend/telegram/apify/llm/hunter/apollo/langsmith"
```

### Task 2.5: Router workspace_settings (profile + targeting)

**Files:**
- Create: `backend/app/routers/workspace_settings.py`
- Create: `backend/tests/test_settings_router.py` (parcial)

- [ ] **Step 1: Escrever testes failing pra profile + targeting**

Create `backend/tests/test_settings_router.py`:

```python
def test_profile_get_empty_returns_defaults(client):
    res = client.get("/api/workspace/profile")
    assert res.status_code == 200
    body = res.json()
    assert body["business_name"] is None
    assert body["legal_basis"] == "legitimo_interesse_b2b"


def test_profile_put_upsert(client):
    res = client.put("/api/workspace/profile", json={
        "business_name": "Acme",
        "your_name": "Angelo",
        "your_email": "a@a.com",
        "your_whatsapp": "5549999",
        "your_website": "https://a.com",
    })
    assert res.status_code == 200
    assert res.json()["business_name"] == "Acme"

    # second PUT updates
    res = client.put("/api/workspace/profile", json={"business_name": "Acme 2"})
    assert res.json()["business_name"] == "Acme 2"
    # other fields preserved
    assert res.json()["your_name"] == "Angelo"


def test_targeting_get_empty(client):
    res = client.get("/api/workspace/targeting")
    assert res.status_code == 200
    body = res.json()
    assert body["target_niches"] == []
    assert body["target_cities"] == []


def test_targeting_put(client):
    res = client.put("/api/workspace/targeting", json={
        "target_niches": ["dentista", "pet shop"],
        "target_cities": ["Chapecó SC"],
        "min_rating": 4.0,
        "max_results_per_search": 50,
        "opportunity_score_threshold": 40,
    })
    assert res.status_code == 200
    assert res.json()["min_rating"] == 4.0
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && pytest tests/test_settings_router.py -v`
Expected: 404 (rota não existe).

- [ ] **Step 3: Implementar router (parcial — só profile + targeting)**

Create `backend/app/routers/workspace_settings.py`:

```python
"""Endpoints de configuração de workspace.

Hoje single-workspace (workspace_id=1). Quando virar multi-tenant
o helper get_current_workspace_id resolve do session — call sites não mudam.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database import get_db
from app.integrations.tenant import get_current_workspace_id
from app.models import WorkspaceProfile, WorkspaceTargeting

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


# ─────── Profile ───────

class ProfileIn(BaseModel):
    business_name: str | None = None
    your_name: str | None = None
    your_email: EmailStr | None = None
    your_whatsapp: str | None = None
    your_website: str | None = None
    legal_basis: str | None = None


class ProfileOut(BaseModel):
    business_name: str | None
    your_name: str | None
    your_email: str | None
    your_whatsapp: str | None
    your_website: str | None
    legal_basis: str | None

    class Config:
        from_attributes = True


def _get_or_create_profile(db: Session, ws: int) -> WorkspaceProfile:
    row = db.query(WorkspaceProfile).filter_by(workspace_id=ws).first()
    if row is None:
        row = WorkspaceProfile(workspace_id=ws, legal_basis="legitimo_interesse_b2b")
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("/profile", response_model=ProfileOut)
def get_profile(request: Request, db: Session = Depends(get_db)):
    ws = get_current_workspace_id(request)
    return _get_or_create_profile(db, ws)


@router.put("/profile", response_model=ProfileOut)
def put_profile(payload: ProfileIn, request: Request, db: Session = Depends(get_db)):
    ws = get_current_workspace_id(request)
    row = _get_or_create_profile(db, ws)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


# ─────── Targeting ───────

class TargetingIn(BaseModel):
    target_niches: list[str] | None = None
    target_cities: list[str] | None = None
    min_rating: float | None = None
    max_results_per_search: int | None = None
    opportunity_score_threshold: int | None = None
    diagnostic_model: str | None = None
    skip_ai_diagnostic: bool | None = None
    skip_social_scraping: bool | None = None
    ai_potential_threshold: int | None = None
    disqualify_threshold: int | None = None
    skip_service_level_analysis: bool | None = None


class TargetingOut(TargetingIn):
    class Config:
        from_attributes = True


def _get_or_create_targeting(db: Session, ws: int) -> WorkspaceTargeting:
    row = db.query(WorkspaceTargeting).filter_by(workspace_id=ws).first()
    if row is None:
        row = WorkspaceTargeting(workspace_id=ws, target_niches=[], target_cities=[])
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("/targeting", response_model=TargetingOut)
def get_targeting(request: Request, db: Session = Depends(get_db)):
    ws = get_current_workspace_id(request)
    return _get_or_create_targeting(db, ws)


@router.put("/targeting", response_model=TargetingOut)
def put_targeting(payload: TargetingIn, request: Request, db: Session = Depends(get_db)):
    ws = get_current_workspace_id(request)
    row = _get_or_create_targeting(db, ws)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row
```

- [ ] **Step 4: Registrar router em main.py**

Edit `backend/app/main.py`:

```diff
-from app.routers import dashboard, leads, pipeline, settings
+from app.routers import dashboard, leads, pipeline, settings, workspace_settings
@@
 app.include_router(settings.router)
 app.include_router(pipeline.router)
+app.include_router(workspace_settings.router)
```

- [ ] **Step 5: Rodar testes**

Run: `cd backend && pytest tests/test_settings_router.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/workspace_settings.py backend/app/main.py backend/tests/test_settings_router.py
git commit -m "feat(api): GET/PUT /api/workspace/{profile,targeting}"
```

### Task 2.6: Router — integrations CRUD + mascaramento

**Files:**
- Modify: `backend/app/routers/workspace_settings.py` (append)
- Modify: `backend/tests/test_settings_router.py` (append)

- [ ] **Step 1: Adicionar testes failing pra integrations**

Append em `backend/tests/test_settings_router.py`:

```python
def test_integrations_list_empty(client):
    res = client.get("/api/workspace/integrations")
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body, list)
    # Cada provider conhecido aparece como "desconectado" se sem row
    providers = [i["provider"] for i in body]
    for p in ["resend", "telegram", "apify", "llm", "hunter", "apollo", "langsmith"]:
        assert p in providers


def test_integration_put_creates_with_encrypted_secret(client, db):
    res = client.put("/api/workspace/integrations/resend", json={
        "config": {
            "api_key": "re_real_secret",
            "from_email": "x@y.com",
            "from_name": "X",
        }
    })
    assert res.status_code == 200
    body = res.json()
    # Resposta nunca vaza secret em texto
    assert "api_key" not in body["config"] or body["config"].get("api_key") is None
    assert body["config"]["has_api_key"] is True
    assert body["config"]["api_key_last4"] == "cret"
    # DB grava cifrado
    from app.models import IntegrationSettings
    row = db.query(IntegrationSettings).filter_by(provider="resend").first()
    assert row.config["api_key"] != "re_real_secret"


def test_integration_put_partial_keeps_secret(client, db):
    # Setup: cria com secret
    client.put("/api/workspace/integrations/resend", json={
        "config": {"api_key": "re_first", "from_email": "x@y.com", "from_name": "X"}
    })
    # PUT sem api_key — mantém o atual
    res = client.put("/api/workspace/integrations/resend", json={
        "config": {"from_email": "novo@y.com"}
    })
    assert res.status_code == 200
    assert res.json()["config"]["from_email"] == "novo@y.com"
    assert res.json()["config"]["has_api_key"] is True
    assert res.json()["config"]["api_key_last4"] == "irst"


def test_integration_put_empty_secret_ignored(client, db):
    client.put("/api/workspace/integrations/resend", json={
        "config": {"api_key": "re_first", "from_email": "x@y.com", "from_name": "X"}
    })
    res = client.put("/api/workspace/integrations/resend", json={
        "config": {"api_key": "", "from_email": "nu@y.com"}
    })
    assert res.json()["config"]["api_key_last4"] == "irst"  # mantido


def test_integration_delete(client):
    client.put("/api/workspace/integrations/resend", json={
        "config": {"api_key": "re_x", "from_email": "x@y.com", "from_name": "X"}
    })
    res = client.delete("/api/workspace/integrations/resend")
    assert res.status_code == 204
    res = client.get("/api/workspace/integrations/resend")
    assert res.json()["enabled"] is False


def test_integration_test_endpoint(client, httpx_mock):
    httpx_mock.add_response(
        url="https://api.resend.com/domains",
        json={"data": []}, status_code=200,
    )
    client.put("/api/workspace/integrations/resend", json={
        "config": {"api_key": "re_x", "from_email": "x@y.com", "from_name": "X"}
    })
    res = client.post("/api/workspace/integrations/resend/test")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["latency_ms"] >= 0


def test_integration_test_without_config_fails(client):
    res = client.post("/api/workspace/integrations/resend/test")
    assert res.status_code == 400
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && pytest tests/test_settings_router.py -v`
Expected: 7 falhas (rotas não existem).

- [ ] **Step 3: Implementar integrations endpoints**

Append em `backend/app/routers/workspace_settings.py`:

```python
# ─────── Integrations ───────
import datetime as _dt

from app.integrations.crypto import encrypt, mask
from app.integrations.resolver import _decrypt_secrets
from app.integrations.schemas import PROVIDER_SCHEMAS, SECRET_FIELDS
from app.integrations.testers import run_test
from app.models import IntegrationSettings

KNOWN_PROVIDERS = list(PROVIDER_SCHEMAS.keys())


def _mask_config(provider: str, raw: dict) -> dict:
    """Aplica mask em campos secretos e expõe flags has_*/last4 pra UI."""
    secrets = SECRET_FIELDS.get(provider, set())
    out = {}
    for k, v in raw.items():
        if k in secrets:
            continue  # secret nunca volta em plain
        out[k] = v
    # decifra (em memória) só pra calcular last4
    decrypted = _decrypt_secrets(provider, raw)
    for field in secrets:
        val = decrypted.get(field)
        out[f"has_{field}"] = bool(val)
        if val:
            out[f"{field}_last4"] = val[-4:] if len(val) >= 4 else val
    return out


def _serialize(row: IntegrationSettings) -> dict:
    return {
        "provider": row.provider,
        "enabled": row.enabled,
        "last_tested_at": row.last_tested_at.isoformat() if row.last_tested_at else None,
        "last_test_result": row.last_test_result,
        "config": _mask_config(row.provider, row.config or {}),
    }


def _stub(provider: str) -> dict:
    return {
        "provider": provider,
        "enabled": False,
        "last_tested_at": None,
        "last_test_result": None,
        "config": _mask_config(provider, {}),
    }


@router.get("/integrations")
def list_integrations(request: Request, db: Session = Depends(get_db)):
    ws = get_current_workspace_id(request)
    rows = {r.provider: r for r in db.query(IntegrationSettings).filter_by(workspace_id=ws).all()}
    return [_serialize(rows[p]) if p in rows else _stub(p) for p in KNOWN_PROVIDERS]


@router.get("/integrations/{provider}")
def get_integration(provider: str, request: Request, db: Session = Depends(get_db)):
    if provider not in PROVIDER_SCHEMAS:
        raise HTTPException(404, f"Unknown provider: {provider}")
    ws = get_current_workspace_id(request)
    row = db.query(IntegrationSettings).filter_by(workspace_id=ws, provider=provider).first()
    return _serialize(row) if row else _stub(provider)


class IntegrationPut(BaseModel):
    config: dict
    enabled: bool | None = None


@router.put("/integrations/{provider}")
def put_integration(provider: str, payload: IntegrationPut, request: Request, db: Session = Depends(get_db)):
    if provider not in PROVIDER_SCHEMAS:
        raise HTTPException(404, f"Unknown provider: {provider}")
    ws = get_current_workspace_id(request)
    row = db.query(IntegrationSettings).filter_by(workspace_id=ws, provider=provider).first()

    new_config = dict(row.config) if row else {}
    secrets = SECRET_FIELDS[provider]

    for k, v in payload.config.items():
        if k in secrets:
            # vazio = ignorado (mantém atual)
            if v is None or v == "":
                continue
            new_config[k] = encrypt(v)
        else:
            new_config[k] = v

    # Validar shape com Pydantic — testes só fazem sentido se schema completo
    # Pra PUT parcial inicial, exige schema completo apenas no primeiro put.
    schema = PROVIDER_SCHEMAS[provider]
    decrypted = _decrypt_secrets(provider, new_config)
    try:
        schema.model_validate(decrypted)
    except Exception as exc:
        raise HTTPException(400, f"Invalid config for {provider}: {exc}")

    if row is None:
        row = IntegrationSettings(
            workspace_id=ws, provider=provider,
            config=new_config, enabled=True,
        )
        db.add(row)
    else:
        row.config = new_config
        if payload.enabled is not None:
            row.enabled = payload.enabled

    db.commit()
    db.refresh(row)
    return _serialize(row)


@router.delete("/integrations/{provider}", status_code=204)
def delete_integration(provider: str, request: Request, db: Session = Depends(get_db)):
    if provider not in PROVIDER_SCHEMAS:
        raise HTTPException(404, f"Unknown provider: {provider}")
    ws = get_current_workspace_id(request)
    db.query(IntegrationSettings).filter_by(workspace_id=ws, provider=provider).delete()
    db.commit()
    return None


@router.post("/integrations/{provider}/test")
def test_integration(provider: str, request: Request, db: Session = Depends(get_db)):
    if provider not in PROVIDER_SCHEMAS:
        raise HTTPException(404, f"Unknown provider: {provider}")
    ws = get_current_workspace_id(request)
    row = db.query(IntegrationSettings).filter_by(workspace_id=ws, provider=provider).first()
    if row is None or not row.config:
        raise HTTPException(400, "Integration not configured")

    cfg = _decrypt_secrets(provider, row.config)
    res = run_test(provider, cfg)
    row.last_tested_at = _dt.datetime.utcnow()
    row.last_test_result = res.to_dict()
    db.commit()
    return res.to_dict()
```

- [ ] **Step 4: Rodar testes**

Run: `cd backend && pytest tests/test_settings_router.py -v`
Expected: 11 passed (4 anteriores + 7 novos).

- [ ] **Step 5: Rodar suíte completa**

Run: `cd backend && pytest -q`
Expected: 405+ passed.

- [ ] **Step 6: Commit + push + PR**

```bash
git add backend/app/routers/workspace_settings.py backend/tests/test_settings_router.py
git commit -m "feat(api): integrations CRUD + test endpoint with mask + Fernet"
git push -u origin feat/ui-settings-backend
gh pr create --title "feat(settings): backend router + testers + resolver" --body "$(cat <<'EOF'
## Summary
- Resolver \`get_provider_config(db, ws, provider)\` com DB→env fallback
- 7 testers (Resend/Telegram/Apify/LLM/Hunter/Apollo/Langsmith) + dispatch
- Router \`/api/workspace/{profile,targeting,integrations}\` com 9 endpoints
- Replace pattern: PUT parcial preserva secret; secret vazio = ignorado
- Mask na resposta: secret nunca volta em plain, retorna \`has_*\` + \`*_last4\`
- Validação Pydantic per-provider antes de gravar
- Tenant resolver scaffold (single-workspace hoje)

## Test plan
- [x] \`pytest tests/test_settings_router.py\` 11 passed
- [x] \`pytest tests/test_settings_testers.py\` 5 passed
- [x] \`pytest tests/test_settings_resolver.py\` 4 passed
- [x] \`pytest -q\` full suite verde
EOF
)"
```

---

## PR 3: Reaproveitar resolver em call sites existentes

Migrar Apify/LLM/Hunter/Apollo/Langsmith de `settings.x` direto pra `get_provider_config()`. Comportamento idêntico se ninguém configurar via UI (env fallback).

**Pre-condition:** PR 2 mergeado.

### Task 3.1: Branch nova

- [ ] **Step 1: Criar branch a partir de main**

```bash
git checkout main && git pull --ff-only
git checkout -b feat/ui-settings-resolver-callsites
```

### Task 3.2: Helper `provider_config_for(provider)` reusável

**Files:**
- Modify: `backend/app/integrations/resolver.py`

- [ ] **Step 1: Adicionar wrapper que abre session se não receber**

Append em `backend/app/integrations/resolver.py`:

```python
from app.database import SessionLocal
from app.integrations.tenant import DEFAULT_WORKSPACE_ID


def provider_config_for(provider: str) -> dict | None:
    """Conveniência pra call sites de pipeline (sync, sem request).

    Hoje single-workspace. Quando virar multi-tenant, call sites de
    background passam workspace_id explícito.
    """
    db = SessionLocal()
    try:
        return get_provider_config(db, DEFAULT_WORKSPACE_ID, provider)
    finally:
        db.close()
```

- [ ] **Step 2: Verificar import**

Run: `cd backend && python -c "from app.integrations.resolver import provider_config_for; print(provider_config_for('apify'))"`
Expected: dict ou None (depende se .env tem APIFY_TOKEN).

- [ ] **Step 3: Commit**

```bash
git add backend/app/integrations/resolver.py
git commit -m "feat(integrations): provider_config_for() helper for sync call sites"
```

### Task 3.3: Migrar `scraper.py` (Apify)

**Files:**
- Modify: `backend/app/pipeline/scraper.py`

- [ ] **Step 1: Localizar uso atual de `settings.apify_token`**

Run: `cd backend && grep -n "apify_token" app/pipeline/scraper.py`
Anotar linhas (provavelmente 1 ou 2 ocorrências).

- [ ] **Step 2: Substituir leitura direta**

No topo de `backend/app/pipeline/scraper.py` adicionar:

```python
from app.integrations.resolver import provider_config_for
```

Trocar cada `settings.apify_token` por:

```python
_apify_cfg = provider_config_for("apify")
_apify_token = _apify_cfg["token"] if _apify_cfg else ""
```

(definir `_apify_cfg` no início da função que faz a chamada — não em module scope, pra refletir mudanças em runtime).

- [ ] **Step 3: Rodar testes do scraper**

Run: `cd backend && pytest tests/test_scraper_multisource.py tests/test_scraper_instagram.py -q`
Expected: passes idênticos a antes (tests mockam Apify, não tocam env).

- [ ] **Step 4: Commit**

```bash
git add backend/app/pipeline/scraper.py
git commit -m "refactor(scraper): use provider_config_for('apify') instead of settings"
```

### Task 3.4: Migrar `generator.py` (LLM)

**Files:**
- Modify: `backend/app/pipeline/generator.py`

- [ ] **Step 1: Localizar usos**

Run: `cd backend && grep -n "settings.llm_" app/pipeline/generator.py`
Anotar (esperado: 3 vars — `llm_api_key`, `llm_base_url`, `llm_model`).

- [ ] **Step 2: Refatorar — em cada função que faz call (`_generate_creative_brief`, `_generate_html`)**

No topo de cada função, substituir leitura direta por:

```python
from app.integrations.resolver import provider_config_for
_llm_cfg = provider_config_for("llm") or {}
_api_key = _llm_cfg.get("api_key", "")
_base_url = _llm_cfg.get("base_url", "")
_model = _llm_cfg.get("model", "")
```

E trocar usos: `settings.llm_api_key` → `_api_key`, `settings.llm_base_url` → `_base_url`, `settings.llm_model` → `_model`.

- [ ] **Step 3: Rodar testes do generator**

Run: `cd backend && pytest tests/test_generator.py -q`
Expected: 7 passed.

- [ ] **Step 4: Commit**

```bash
git add backend/app/pipeline/generator.py
git commit -m "refactor(generator): use provider_config_for('llm') resolver"
```

### Task 3.5: Migrar Hunter + Apollo + Langsmith

**Files:**
- Modify: `backend/app/pipeline/enrichment/providers/email_discoverer.py`
- Modify: `backend/app/pipeline/enrichment/providers/apollo.py`

- [ ] **Step 1: Hunter**

Run: `cd backend && grep -n "hunter_api_key" app/pipeline/enrichment/providers/email_discoverer.py`

Trocar leitura direta por:

```python
from app.integrations.resolver import provider_config_for

# dentro do método que usa a key:
_cfg = provider_config_for("hunter") or {}
_api_key = _cfg.get("api_key", "")
if not _api_key:
    # comportamento atual quando não tem config — skip
    return ProviderResult(...)
```

Ajustar uso pra `_api_key`.

- [ ] **Step 2: Apollo (mesma operação)**

Run: `cd backend && grep -n "apollo_api_key" app/pipeline/enrichment/providers/apollo.py`

Trocar leitura por `provider_config_for("apollo")` análogo.

- [ ] **Step 3: Langsmith — encontrar call sites**

Run: `cd backend && grep -rn "langsmith_api_key\|langsmith_project\|langsmith_tracing" app/`

Pra cada arquivo, substituir leitura direta por:

```python
from app.integrations.resolver import provider_config_for
_ls_cfg = provider_config_for("langsmith") or {}
# usar _ls_cfg.get("api_key"), _ls_cfg.get("project"), _ls_cfg.get("tracing")
```

- [ ] **Step 4: Rodar testes de enrichment**

Run: `cd backend && pytest tests/enrichment/ tests/test_enricher.py -q`
Expected: passes existentes mantidos.

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/enrichment/
git commit -m "refactor(enrichment): hunter/apollo/langsmith use provider_config_for resolver"
```

### Task 3.6: Suite completa + push + PR

- [ ] **Step 1: Rodar tudo**

Run: `cd backend && pytest -q`
Expected: 405+ passed.

- [ ] **Step 2: Push + PR**

```bash
git push -u origin feat/ui-settings-resolver-callsites
gh pr create --title "refactor(pipeline): use provider_config_for resolver in call sites" --body "$(cat <<'EOF'
## Summary
- Helper \`provider_config_for(provider)\` pra sync call sites de pipeline
- scraper.py (Apify), generator.py (LLM), email_discoverer.py (Hunter), apollo.py, langsmith call sites
- Comportamento idêntico quando UI não tem config (env fallback)
- Zero breakage em testes existentes

Spec: \`docs/superpowers/specs/2026-04-30-ui-settings-design.md\`

## Test plan
- [x] \`pytest -q\` full suite verde
EOF
)"
```

---

## PR 4: Frontend layout + rotas + nav

Esqueleto navegável: SettingsLayout, sub-rotas vazias, entries no avatar dropdown e sidebar. Sem forms ainda.

**Pre-condition:** PR 3 mergeado (não bloqueante — frontend só consome API quando PR 5 chegar).

### Task 4.1: Branch nova

- [ ] **Step 1: Criar branch a partir de main**

```bash
git checkout main && git pull --ff-only
git checkout -b feat/ui-settings-frontend-skeleton
```

### Task 4.2: Tipos compartilhados

**Files:**
- Create: `frontend/src/lib/settings-types.ts`

- [ ] **Step 1: Criar arquivo de tipos**

Create `frontend/src/lib/settings-types.ts`:

```ts
export type ProviderId =
  | "resend" | "telegram" | "apify" | "llm"
  | "hunter" | "apollo" | "langsmith";

export interface TestResult {
  ok: boolean;
  latency_ms: number;
  error: string | null;
}

export interface IntegrationSummary {
  provider: ProviderId;
  enabled: boolean;
  last_tested_at: string | null;
  last_test_result: TestResult | null;
  config: IntegrationConfigMasked;
}

export type IntegrationConfigMasked = Record<string, unknown> & {
  // Per provider, has_<field> + <field>_last4 for secrets
  // resend: has_api_key, api_key_last4, has_webhook_secret, webhook_secret_last4
  // telegram: has_bot_token, bot_token_last4, chat_id
  // apify: has_token, token_last4
  // llm: has_api_key, api_key_last4, model, base_url
  // hunter, apollo: has_api_key, api_key_last4
  // langsmith: has_api_key, api_key_last4, project, tracing
};

export interface WorkspaceProfile {
  business_name: string | null;
  your_name: string | null;
  your_email: string | null;
  your_whatsapp: string | null;
  your_website: string | null;
  legal_basis: string | null;
}

export interface WorkspaceTargeting {
  target_niches: string[];
  target_cities: string[];
  min_rating: number | null;
  max_results_per_search: number | null;
  opportunity_score_threshold: number | null;
  diagnostic_model?: string | null;
  skip_ai_diagnostic?: boolean | null;
  skip_social_scraping?: boolean | null;
  ai_potential_threshold?: number | null;
  disqualify_threshold?: number | null;
  skip_service_level_analysis?: boolean | null;
}

export const PROVIDER_META: Record<ProviderId, { label: string; description: string; docs?: string }> = {
  resend:    { label: "Resend",    description: "Email transacional para cadência de outreach",    docs: "https://resend.com/docs" },
  telegram:  { label: "Telegram",  description: "Alertas de cadência (respostas, falhas)",         docs: "https://core.telegram.org/bots/api" },
  apify:     { label: "Apify",     description: "Scraping de Google Maps",                          docs: "https://docs.apify.com" },
  llm:       { label: "LLM",       description: "Geração de landing pages, copy e diagnósticos",   docs: "" },
  hunter:    { label: "Hunter",    description: "Descoberta de email por domínio",                  docs: "https://hunter.io/api-documentation" },
  apollo:    { label: "Apollo",    description: "Enriquecimento de contato",                        docs: "https://apolloio.github.io/apollo-api-docs/" },
  langsmith: { label: "LangSmith", description: "Tracing de chains LLM",                            docs: "https://docs.smith.langchain.com" },
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/settings-types.ts
git commit -m "feat(types): settings types and provider metadata"
```

### Task 4.3: SettingsLayout + rotas vazias

**Files:**
- Create: `frontend/src/app/app/settings/layout.tsx`
- Create: `frontend/src/app/app/settings/settings.css`
- Create: `frontend/src/app/app/settings/page.tsx`
- Create: `frontend/src/app/app/settings/perfil/page.tsx`
- Create: `frontend/src/app/app/settings/targeting/page.tsx`
- Create: `frontend/src/app/app/settings/avancado/page.tsx`
- Create: `frontend/src/app/app/settings/integracoes/page.tsx`
- Create: `frontend/src/app/app/settings/integracoes/[provider]/page.tsx`

- [ ] **Step 1: Layout**

Create `frontend/src/app/app/settings/layout.tsx`:

```tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon } from "@/components/ui";
import "./settings.css";

const SECTIONS = [
  { href: "/app/settings/perfil",       label: "Perfil",       icon: "user" as const },
  { href: "/app/settings/integracoes",  label: "Integrações",  icon: "settings" as const },
  { href: "/app/settings/targeting",    label: "Targeting",    icon: "target" as const },
  { href: "/app/settings/avancado",     label: "Avançado",     icon: "tool" as const },
];

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isIndex = pathname === "/app/settings";

  return (
    <div className="settings-shell">
      <aside className={`settings-sidebar ${isIndex ? "settings-sidebar--mobile-only" : ""}`}>
        <header className="settings-sidebar-header">
          <h1>Configurações</h1>
        </header>
        <nav className="settings-nav">
          {SECTIONS.map((s) => {
            const active = pathname.startsWith(s.href);
            return (
              <Link
                key={s.href}
                href={s.href}
                className={`settings-nav-item ${active ? "settings-nav-item--active" : ""}`}
              >
                <Icon name={s.icon} size={16} />
                <span>{s.label}</span>
                <Icon name="chevron-r" size={14} className="settings-nav-chevron" />
              </Link>
            );
          })}
        </nav>
      </aside>
      <section className="settings-content">{children}</section>
    </div>
  );
}
```

- [ ] **Step 2: CSS**

Create `frontend/src/app/app/settings/settings.css`:

```css
.settings-shell {
  display: grid;
  grid-template-columns: 1fr;
  min-height: calc(100vh - 48px);
}

.settings-sidebar {
  border-right: 1px solid var(--line-1);
  background: var(--surface);
  padding: 24px 16px;
}

.settings-sidebar-header h1 {
  font-size: 13px;
  font-weight: 460;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin: 0 0 16px 8px;
}

.settings-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.settings-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  color: var(--text);
  font-size: 14px;
  text-decoration: none;
  min-height: 48px; /* mobile touch target */
}

.settings-nav-item:hover {
  background: var(--bg-soft);
}

.settings-nav-item--active {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 480;
}

.settings-nav-chevron { margin-left: auto; opacity: 0.4; }

.settings-content {
  padding: 32px 24px;
  max-width: 720px;
}

/* Mobile: drill-in. Sidebar mostra só na rota índice. */
@media (max-width: 1023px) {
  .settings-shell { grid-template-columns: 1fr; }
  .settings-content { padding: 16px; }
  /* Em sub-rota: esconde sidebar interna (back fica no topbar interno do conteúdo) */
  .settings-shell:has(.settings-content > *):not(:has(.settings-index-tile)) .settings-sidebar { display: none; }
}

/* Desktop: 200 + flex */
@media (min-width: 1024px) {
  .settings-shell { grid-template-columns: 220px 1fr; }
  .settings-nav-chevron { display: none; }
}
```

- [ ] **Step 3: Index page (redirect mobile mostra tiles via layout sidebar)**

Create `frontend/src/app/app/settings/page.tsx`:

```tsx
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function SettingsIndex() {
  const router = useRouter();
  useEffect(() => {
    if (window.matchMedia("(min-width: 1024px)").matches) {
      router.replace("/app/settings/perfil");
    }
  }, [router]);
  return null;
}
```

- [ ] **Step 4: Sub-páginas placeholder**

Create `frontend/src/app/app/settings/perfil/page.tsx`:

```tsx
export default function PerfilPage() {
  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 480, marginBottom: 8 }}>Perfil</h2>
      <p style={{ color: "var(--text-muted)" }}>
        Em construção — implementação na Task 5.x.
      </p>
    </div>
  );
}
```

Create `frontend/src/app/app/settings/targeting/page.tsx`, `integracoes/page.tsx`, `integracoes/[provider]/page.tsx`, `avancado/page.tsx` análogos (com label apropriado).

Para `avancado/page.tsx`:

```tsx
export default function AvancadoPage() {
  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 480, marginBottom: 8 }}>Avançado</h2>
      <p style={{ color: "var(--text-muted)" }}>
        Em breve — tunables de pipeline (modelos de diagnóstico, thresholds de qualificação) serão configuráveis aqui.
      </p>
    </div>
  );
}
```

Para `integracoes/[provider]/page.tsx`:

```tsx
"use client";
import { use } from "react";

export default function IntegrationDetail({ params }: { params: Promise<{ provider: string }> }) {
  const { provider } = use(params);
  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 480 }}>{provider}</h2>
      <p style={{ color: "var(--text-muted)" }}>Em construção.</p>
    </div>
  );
}
```

- [ ] **Step 5: Verificar carrega**

Run: `cd frontend && npm run dev` (em background) e abrir http://localhost:3000/app/settings/perfil
Expected: layout com sidebar interna desktop, conteúdo "Em construção".

- [ ] **Step 6: Build sanity**

Run: `cd frontend && npm run build`
Expected: build success, sem erros TypeScript.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/app/app/settings/
git commit -m "feat(settings): SettingsLayout + sub-routes skeleton"
```

### Task 4.4: Avatar dropdown + sidebar entry

**Files:**
- Modify: `frontend/src/components/app-sidebar.tsx`

- [ ] **Step 1: Adicionar entry "Configurações" no avatar dropdown**

Edit `frontend/src/components/app-sidebar.tsx`. Localizar bloco do dropdown (após `Modo claro/escuro`, antes do `Sair`):

```diff
               <button className="avatar-menu-item" onClick={toggleTheme}>
                 <Icon name={theme === "dark" ? "sun" : "moon"} size={15} />
                 <span>{theme === "dark" ? "Modo claro" : "Modo escuro"}</span>
               </button>
+              <button
+                className="avatar-menu-item"
+                onClick={() => {
+                  setAvatarOpen(false);
+                  router.push("/app/settings");
+                }}
+              >
+                <Icon name="settings" size={15} />
+                <span>Configurações</span>
+              </button>
               <div className="avatar-menu-divider" />
               <button
                 className="avatar-menu-item avatar-menu-danger"
```

- [ ] **Step 2: Adicionar atalho na sidebar (acima do "Buscar"/avatar)**

Edit `frontend/src/components/app-sidebar.tsx`. Localizar `<div className="app-sidebar-sep" />` (linha ~175) e adicionar **antes** dele:

```diff
+        <div className="app-sidebar-sep" />
+        <button
+          className={`app-sidebar-btn ${pathname.startsWith("/app/settings") ? "active" : ""}`}
+          onClick={() => {
+            router.push("/app/settings");
+            setMobileOpen(false);
+          }}
+        >
+          <Icon name="settings" size={18} />
+          <span className="app-sidebar-label">Configurações</span>
+          <span className="app-sidebar-tip">Configurações</span>
+        </button>
         <div className="app-sidebar-sep" />
```

- [ ] **Step 3: Verificar dev**

Run: dev rodando — clicar avatar → "Configurações" → abre `/app/settings`. Sidebar mostrar gear embaixo, ativa quando em `/settings/*`.

- [ ] **Step 4: Build**

Run: `cd frontend && npm run build`
Expected: success.

- [ ] **Step 5: Commit + push + PR**

```bash
git add frontend/src/components/app-sidebar.tsx
git commit -m "feat(nav): settings entry in avatar dropdown + sidebar shortcut"
git push -u origin feat/ui-settings-frontend-skeleton
gh pr create --title "feat(settings): frontend skeleton — layout + routes + nav" --body "$(cat <<'EOF'
## Summary
- Tipos \`settings-types.ts\` (ProviderId, IntegrationSummary, etc.)
- \`SettingsLayout\` com sidebar interna desktop + drill-in mobile
- Sub-rotas vazias: /perfil, /integracoes, /integracoes/[provider], /targeting, /avancado
- Entry "Configurações" no avatar dropdown
- Atalho gear na sidebar (separado dos itens principais)

Forms e API calls vêm no PR 5.

## Smoke checklist
- [x] \`/app/settings/perfil\` carrega com sidebar interna desktop
- [x] Avatar dropdown → Configurações abre /app/settings
- [x] Sidebar gear ativa quando em /settings/*
- [x] Mobile (<1024px): index mostra tiles, sub-rota esconde sidebar interna
- [x] \`npm run build\` sem erros
EOF
)"
```

---

## PR 5: Frontend forms + integração com API

Conecta tudo: API client, forms, replace pattern, test button, masks.

**Pre-condition:** PRs 1-4 mergeados.

### Task 5.1: Branch nova

- [ ] **Step 1: Criar branch a partir de main**

```bash
git checkout main && git pull --ff-only
git checkout -b feat/ui-settings-frontend-forms
```

### Task 5.2: API client

**Files:**
- Create: `frontend/src/lib/api-settings.ts`
- Modify: `frontend/src/lib/api.ts` (re-export)

- [ ] **Step 1: Criar wrapper**

Create `frontend/src/lib/api-settings.ts`:

```ts
import type {
  WorkspaceProfile, WorkspaceTargeting,
  IntegrationSummary, ProviderId, TestResult,
} from "./settings-types";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function authedFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  // reuse same session token handling as api.ts
  const cookies = document.cookie.split("; ");
  let token: string | null = null;
  for (const c of cookies) {
    if (c.startsWith("__Secure-better-auth.session_data=") || c.startsWith("better-auth.session_data=")) {
      try {
        const val = decodeURIComponent(c.split("=").slice(1).join("="));
        const data = JSON.parse(atob(val));
        token = data?.session?.session?.token || null;
      } catch {}
    }
  }
  const res = await fetch(`${API}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers || {}),
    },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const getWorkspaceProfile  = () => authedFetch<WorkspaceProfile>("/api/workspace/profile");
export const updateWorkspaceProfile = (data: Partial<WorkspaceProfile>) =>
  authedFetch<WorkspaceProfile>("/api/workspace/profile", { method: "PUT", body: JSON.stringify(data) });

export const getWorkspaceTargeting = () => authedFetch<WorkspaceTargeting>("/api/workspace/targeting");
export const updateWorkspaceTargeting = (data: Partial<WorkspaceTargeting>) =>
  authedFetch<WorkspaceTargeting>("/api/workspace/targeting", { method: "PUT", body: JSON.stringify(data) });

export const listIntegrations  = () => authedFetch<IntegrationSummary[]>("/api/workspace/integrations");
export const getIntegration    = (provider: ProviderId) => authedFetch<IntegrationSummary>(`/api/workspace/integrations/${provider}`);
export const updateIntegration = (provider: ProviderId, config: Record<string, unknown>) =>
  authedFetch<IntegrationSummary>(`/api/workspace/integrations/${provider}`, {
    method: "PUT", body: JSON.stringify({ config }),
  });
export const deleteIntegration = (provider: ProviderId) =>
  authedFetch<void>(`/api/workspace/integrations/${provider}`, { method: "DELETE" });
export const testIntegration   = (provider: ProviderId) =>
  authedFetch<TestResult>(`/api/workspace/integrations/${provider}/test`, { method: "POST" });
```

- [ ] **Step 2: Build**

Run: `cd frontend && npm run build`
Expected: success.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/api-settings.ts
git commit -m "feat(api-client): typed wrappers for workspace settings endpoints"
```

### Task 5.3: SecretField (replace pattern)

**Files:**
- Create: `frontend/src/components/settings/secret-field.tsx`

- [ ] **Step 1: Criar componente**

Create `frontend/src/components/settings/secret-field.tsx`:

```tsx
"use client";

import { useState } from "react";
import { Icon } from "@/components/ui";

interface Props {
  label: string;
  hasValue: boolean;
  last4?: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}

export function SecretField({ label, hasValue, last4, value, onChange, placeholder }: Props) {
  const [editing, setEditing] = useState(!hasValue);

  if (!editing) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <div>
          <div style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 4 }}>{label}</div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14 }}>
            <Icon name="check" size={14} style={{ color: "var(--ok)" }} />
            <span>Configurado · termina em <code>{last4 ?? "????"}</code></span>
          </div>
        </div>
        <button
          type="button"
          className="settings-btn settings-btn-ghost"
          onClick={() => { setEditing(true); onChange(""); }}
        >
          Substituir
        </button>
      </div>
    );
  }

  return (
    <div>
      <label style={{ fontSize: 13, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>{label}</label>
      <div style={{ display: "flex", gap: 8 }}>
        <input
          type="password"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="settings-input"
          autoComplete="off"
          style={{ flex: 1 }}
        />
        {hasValue && (
          <button
            type="button"
            className="settings-btn settings-btn-ghost"
            onClick={() => { setEditing(false); onChange(""); }}
          >
            Cancelar
          </button>
        )}
      </div>
      {hasValue && (
        <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 6 }}>
          Vazio mantém a chave atual. Preencha pra substituir.
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Adicionar estilos genéricos `.settings-btn`/`.settings-input` em settings.css**

Append em `frontend/src/app/app/settings/settings.css`:

```css
.settings-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--line-1);
  border-radius: 8px;
  background: var(--bg);
  color: var(--text);
  font-size: 14px;
  font-family: inherit;
  min-height: 44px;
}

.settings-input:focus {
  outline: 2px solid var(--accent-soft);
  border-color: var(--accent);
}

.settings-btn {
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.settings-btn-primary { background: var(--accent); color: var(--accent-fg); }
.settings-btn-primary:hover { filter: brightness(1.1); }

.settings-btn-ghost { background: transparent; border-color: var(--line-1); color: var(--text); }
.settings-btn-ghost:hover { background: var(--bg-soft); }

.settings-btn-danger { background: transparent; border-color: var(--danger); color: var(--danger); }
.settings-btn-danger:hover { background: color-mix(in oklch, var(--danger) 12%, transparent); }

.settings-section {
  border-top: 1px solid var(--line-1);
  padding-top: 24px;
  margin-top: 24px;
}

.settings-section-title {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  margin-bottom: 16px;
}

.settings-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 16px;
}

.settings-field-label {
  font-size: 13px;
  color: var(--text-muted);
}

.settings-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid var(--line-1);
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/settings/secret-field.tsx frontend/src/app/app/settings/settings.css
git commit -m "feat(settings): SecretField component (replace pattern) + form styles"
```

### Task 5.4: ChipsInput (niches/cities)

**Files:**
- Create: `frontend/src/components/settings/chips-input.tsx`

- [ ] **Step 1: Criar componente**

Create `frontend/src/components/settings/chips-input.tsx`:

```tsx
"use client";

import { useState, type KeyboardEvent } from "react";

interface Props {
  values: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
}

export function ChipsInput({ values, onChange, placeholder }: Props) {
  const [draft, setDraft] = useState("");

  function add() {
    const v = draft.trim();
    if (!v || values.includes(v)) { setDraft(""); return; }
    onChange([...values, v]);
    setDraft("");
  }

  function remove(idx: number) {
    onChange(values.filter((_, i) => i !== idx));
  }

  function onKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      add();
    } else if (e.key === "Backspace" && !draft && values.length) {
      remove(values.length - 1);
    }
  }

  return (
    <div className="settings-input" style={{ display: "flex", flexWrap: "wrap", gap: 6, padding: 8, minHeight: 44 }}>
      {values.map((v, i) => (
        <span key={`${v}-${i}`} className="settings-chip">
          {v}
          <button type="button" onClick={() => remove(i)} aria-label={`Remover ${v}`}>×</button>
        </span>
      ))}
      <input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={onKey}
        onBlur={add}
        placeholder={values.length === 0 ? placeholder : ""}
        style={{ flex: 1, minWidth: 80, border: 0, background: "transparent", outline: "none", fontSize: 14 }}
      />
    </div>
  );
}
```

- [ ] **Step 2: Estilo do chip**

Append em `frontend/src/app/app/settings/settings.css`:

```css
.settings-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: var(--accent-soft);
  color: var(--accent);
  border-radius: 6px;
  font-size: 13px;
}

.settings-chip button {
  background: none; border: 0; cursor: pointer; color: inherit; opacity: 0.6;
  font-size: 16px; line-height: 1; padding: 0 2px;
}
.settings-chip button:hover { opacity: 1; }
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/settings/chips-input.tsx frontend/src/app/app/settings/settings.css
git commit -m "feat(settings): ChipsInput for niches/cities"
```

### Task 5.5: StatusBadge + TestButton

**Files:**
- Create: `frontend/src/components/settings/status-badge.tsx`
- Create: `frontend/src/components/settings/test-button.tsx`

- [ ] **Step 1: StatusBadge**

Create `frontend/src/components/settings/status-badge.tsx`:

```tsx
import type { IntegrationSummary } from "@/lib/settings-types";

export function StatusBadge({ integration }: { integration: IntegrationSummary }) {
  const isConfigured = Object.entries(integration.config).some(
    ([k, v]) => k.startsWith("has_") && v === true,
  );
  if (!isConfigured) return <span className="settings-badge settings-badge-muted">Desconectado</span>;
  if (!integration.last_test_result) return <span className="settings-badge settings-badge-warn">Não testado</span>;
  if (integration.last_test_result.ok) return <span className="settings-badge settings-badge-ok">Conectado</span>;
  return <span className="settings-badge settings-badge-danger">Falha</span>;
}
```

Append em settings.css:

```css
.settings-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 480;
  border: 1px solid;
}
.settings-badge-ok { color: var(--ok); border-color: color-mix(in oklch, var(--ok) 30%, transparent); background: color-mix(in oklch, var(--ok) 8%, transparent); }
.settings-badge-warn { color: var(--warn); border-color: color-mix(in oklch, var(--warn) 30%, transparent); background: color-mix(in oklch, var(--warn) 8%, transparent); }
.settings-badge-danger { color: var(--danger); border-color: color-mix(in oklch, var(--danger) 30%, transparent); background: color-mix(in oklch, var(--danger) 8%, transparent); }
.settings-badge-muted { color: var(--text-muted); border-color: var(--line-1); background: var(--surface); }
```

- [ ] **Step 2: TestButton**

Create `frontend/src/components/settings/test-button.tsx`:

```tsx
"use client";
import { useState } from "react";
import { testIntegration } from "@/lib/api-settings";
import type { ProviderId, TestResult } from "@/lib/settings-types";

export function TestButton({ provider, onResult }: { provider: ProviderId; onResult?: (r: TestResult) => void }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true); setError(null);
    try {
      const r = await testIntegration(provider);
      setResult(r);
      onResult?.(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <button type="button" className="settings-btn settings-btn-ghost" onClick={run} disabled={loading}>
        {loading ? "Testando…" : "Testar conexão"}
      </button>
      {result && (
        <span style={{ fontSize: 12, color: result.ok ? "var(--ok)" : "var(--danger)" }}>
          {result.ok ? `✓ OK · ${result.latency_ms}ms` : `✗ ${result.error || "Falhou"}`}
        </span>
      )}
      {error && <span style={{ fontSize: 12, color: "var(--danger)" }}>{error}</span>}
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/settings/status-badge.tsx frontend/src/components/settings/test-button.tsx frontend/src/app/app/settings/settings.css
git commit -m "feat(settings): StatusBadge + TestButton components"
```

### Task 5.6: Página Perfil

**Files:**
- Modify: `frontend/src/app/app/settings/perfil/page.tsx`

- [ ] **Step 1: Implementar**

Replace `frontend/src/app/app/settings/perfil/page.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { getWorkspaceProfile, updateWorkspaceProfile } from "@/lib/api-settings";
import type { WorkspaceProfile } from "@/lib/settings-types";

export default function PerfilPage() {
  const [data, setData] = useState<WorkspaceProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    getWorkspaceProfile().then(setData).finally(() => setLoading(false));
  }, []);

  if (loading || !data) return <div>Carregando…</div>;

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!data) return;
    setSaving(true);
    try {
      const next = await updateWorkspaceProfile(data);
      setData(next);
      setToast("Perfil atualizado");
      setTimeout(() => setToast(null), 2000);
    } finally {
      setSaving(false);
    }
  }

  function field<K extends keyof WorkspaceProfile>(key: K, label: string, type: string = "text") {
    return (
      <div className="settings-field" key={key}>
        <label className="settings-field-label">{label}</label>
        <input
          className="settings-input"
          type={type}
          value={(data?.[key] as string) ?? ""}
          onChange={(e) => setData(d => d ? ({ ...d, [key]: e.target.value }) : d)}
        />
      </div>
    );
  }

  return (
    <form onSubmit={save}>
      <h2 style={{ fontSize: 22, fontWeight: 480, marginBottom: 8 }}>Perfil de remetente</h2>
      <p style={{ color: "var(--text-muted)", marginBottom: 24, fontSize: 14 }}>
        Esses dados aparecem na LP gerada, no email de outreach e nos templates de mensagem.
      </p>

      {field("business_name", "Nome do negócio")}
      {field("your_name", "Seu nome")}
      {field("your_email", "Seu email", "email")}
      {field("your_whatsapp", "Seu WhatsApp", "tel")}
      {field("your_website", "Seu site", "url")}

      <div className="settings-actions">
        <button type="submit" className="settings-btn settings-btn-primary" disabled={saving}>
          {saving ? "Salvando…" : "Salvar"}
        </button>
        {toast && <span style={{ fontSize: 14, color: "var(--ok)", alignSelf: "center" }}>{toast}</span>}
      </div>
    </form>
  );
}
```

- [ ] **Step 2: Smoke test**

Dev rodando — abrir `/app/settings/perfil`, preencher, salvar. Reload, dados persistem. Backend dev rodando.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/app/settings/perfil/page.tsx
git commit -m "feat(settings): perfil form with persistence"
```

### Task 5.7: Página Targeting

**Files:**
- Modify: `frontend/src/app/app/settings/targeting/page.tsx`

- [ ] **Step 1: Implementar**

Replace `frontend/src/app/app/settings/targeting/page.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { getWorkspaceTargeting, updateWorkspaceTargeting } from "@/lib/api-settings";
import { ChipsInput } from "@/components/settings/chips-input";
import type { WorkspaceTargeting } from "@/lib/settings-types";

export default function TargetingPage() {
  const [data, setData] = useState<WorkspaceTargeting | null>(null);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    getWorkspaceTargeting().then(setData);
  }, []);

  if (!data) return <div>Carregando…</div>;

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!data) return;
    setSaving(true);
    try {
      const next = await updateWorkspaceTargeting(data);
      setData(next);
      setToast("Targeting atualizado");
      setTimeout(() => setToast(null), 2000);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={save}>
      <h2 style={{ fontSize: 22, fontWeight: 480, marginBottom: 8 }}>Targeting</h2>
      <p style={{ color: "var(--text-muted)", marginBottom: 24, fontSize: 14 }}>
        Defaults pra novos jobs de scraping. Pode ser sobrescrito por job individual.
      </p>

      <div className="settings-field">
        <label className="settings-field-label">Nichos-alvo</label>
        <ChipsInput
          values={data.target_niches || []}
          onChange={(v) => setData(d => d ? ({ ...d, target_niches: v }) : d)}
          placeholder="dentista, pet shop…"
        />
      </div>

      <div className="settings-field">
        <label className="settings-field-label">Cidades-alvo</label>
        <ChipsInput
          values={data.target_cities || []}
          onChange={(v) => setData(d => d ? ({ ...d, target_cities: v }) : d)}
          placeholder="Chapecó SC, Florianópolis SC…"
        />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
        <div className="settings-field">
          <label className="settings-field-label">Rating mínimo (Google)</label>
          <input className="settings-input" type="number" step="0.1" min="0" max="5"
            value={data.min_rating ?? ""}
            onChange={(e) => setData(d => d ? ({ ...d, min_rating: e.target.value ? Number(e.target.value) : null }) : d)} />
        </div>
        <div className="settings-field">
          <label className="settings-field-label">Resultados por busca</label>
          <input className="settings-input" type="number" min="1" max="500"
            value={data.max_results_per_search ?? ""}
            onChange={(e) => setData(d => d ? ({ ...d, max_results_per_search: e.target.value ? Number(e.target.value) : null }) : d)} />
        </div>
        <div className="settings-field">
          <label className="settings-field-label">Score mínimo qualificação</label>
          <input className="settings-input" type="number" min="0" max="100"
            value={data.opportunity_score_threshold ?? ""}
            onChange={(e) => setData(d => d ? ({ ...d, opportunity_score_threshold: e.target.value ? Number(e.target.value) : null }) : d)} />
        </div>
      </div>

      <div className="settings-actions">
        <button type="submit" className="settings-btn settings-btn-primary" disabled={saving}>
          {saving ? "Salvando…" : "Salvar"}
        </button>
        {toast && <span style={{ fontSize: 14, color: "var(--ok)", alignSelf: "center" }}>{toast}</span>}
      </div>
    </form>
  );
}
```

- [ ] **Step 2: Smoke test**

Abrir `/app/settings/targeting`, adicionar chip, salvar, reload, persiste.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/app/settings/targeting/page.tsx
git commit -m "feat(settings): targeting form with chips and numeric inputs"
```

### Task 5.8: Lista de integrações

**Files:**
- Modify: `frontend/src/app/app/settings/integracoes/page.tsx`

- [ ] **Step 1: Implementar**

Replace `frontend/src/app/app/settings/integracoes/page.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listIntegrations } from "@/lib/api-settings";
import { StatusBadge } from "@/components/settings/status-badge";
import { PROVIDER_META, type IntegrationSummary } from "@/lib/settings-types";

export default function IntegracoesPage() {
  const [items, setItems] = useState<IntegrationSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listIntegrations().then(setItems).finally(() => setLoading(false));
  }, []);

  if (loading) return <div>Carregando…</div>;

  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 480, marginBottom: 8 }}>Integrações</h2>
      <p style={{ color: "var(--text-muted)", marginBottom: 24, fontSize: 14 }}>
        Credenciais de APIs externas. Cada provider pode ser testado depois de configurado.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16 }}>
        {items.map((it) => {
          const meta = PROVIDER_META[it.provider];
          return (
            <Link
              key={it.provider}
              href={`/app/settings/integracoes/${it.provider}`}
              className="settings-card"
            >
              <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <strong>{meta.label}</strong>
                <StatusBadge integration={it} />
              </header>
              <p style={{ fontSize: 13, color: "var(--text-muted)", margin: 0, marginBottom: 12 }}>
                {meta.description}
              </p>
              {it.last_tested_at && (
                <p style={{ fontSize: 12, color: "var(--text-muted)", margin: 0 }}>
                  testado em {new Date(it.last_tested_at).toLocaleString("pt-BR")}
                </p>
              )}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: CSS card**

Append em settings.css:

```css
.settings-card {
  display: block;
  padding: 16px;
  border: 1px solid var(--line-1);
  border-radius: 12px;
  background: var(--surface);
  text-decoration: none;
  color: inherit;
  transition: border-color 0.15s, transform 0.15s;
}
.settings-card:hover { border-color: var(--accent); transform: translateY(-1px); }
```

- [ ] **Step 3: Smoke test**

Abrir `/app/settings/integracoes` — 7 cards, todos "Desconectado".

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/app/settings/integracoes/page.tsx frontend/src/app/app/settings/settings.css
git commit -m "feat(settings): integrations list grid with status badges"
```

### Task 5.9: Detalhe da integração

**Files:**
- Modify: `frontend/src/app/app/settings/integracoes/[provider]/page.tsx`

- [ ] **Step 1: Implementar (cobre os 7 providers via switch de campos)**

Replace `frontend/src/app/app/settings/integracoes/[provider]/page.tsx`:

```tsx
"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getIntegration, updateIntegration, deleteIntegration } from "@/lib/api-settings";
import { SecretField } from "@/components/settings/secret-field";
import { TestButton } from "@/components/settings/test-button";
import { StatusBadge } from "@/components/settings/status-badge";
import { PROVIDER_META, type IntegrationSummary, type ProviderId } from "@/lib/settings-types";

const PROVIDER_FIELDS: Record<ProviderId, { secrets: { key: string; label: string }[]; plain: { key: string; label: string; type?: string }[] }> = {
  resend:    { secrets: [{ key: "api_key", label: "API key" }, { key: "webhook_secret", label: "Webhook secret (opcional)" }],
               plain:   [{ key: "from_email", label: "From email", type: "email" }, { key: "from_name", label: "From name" }, { key: "reply_to", label: "Reply-to (opcional)", type: "email" }] },
  telegram:  { secrets: [{ key: "bot_token", label: "Bot token" }],
               plain:   [{ key: "chat_id", label: "Chat ID" }] },
  apify:     { secrets: [{ key: "token", label: "API token" }], plain: [] },
  llm:       { secrets: [{ key: "api_key", label: "API key" }],
               plain:   [{ key: "model", label: "Modelo" }, { key: "base_url", label: "Base URL", type: "url" }] },
  hunter:    { secrets: [{ key: "api_key", label: "API key" }], plain: [] },
  apollo:    { secrets: [{ key: "api_key", label: "API key" }], plain: [] },
  langsmith: { secrets: [{ key: "api_key", label: "API key" }],
               plain:   [{ key: "project", label: "Projeto" }] },
};

export default function IntegrationDetail({ params }: { params: Promise<{ provider: string }> }) {
  const router = useRouter();
  const { provider } = use(params) as { provider: ProviderId };
  const meta = PROVIDER_META[provider];
  const fields = PROVIDER_FIELDS[provider];

  const [data, setData] = useState<IntegrationSummary | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    getIntegration(provider).then((d) => {
      setData(d);
      const init: Record<string, string> = {};
      fields.plain.forEach((f) => { init[f.key] = (d.config[f.key] as string) ?? ""; });
      // langsmith.tracing é boolean — tratamos abaixo separado
      setDraft(init);
    });
  }, [provider]);

  if (!data || !meta) return <div>Carregando…</div>;

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!data) return;
    setSaving(true);
    try {
      // Compor payload: campos plain sempre, secrets só se preenchido
      const payload: Record<string, unknown> = {};
      for (const f of fields.plain) {
        const v = draft[f.key];
        if (v !== undefined) payload[f.key] = v;
      }
      for (const f of fields.secrets) {
        const v = draft[f.key];
        if (v) payload[f.key] = v;  // só envia se preenchido
      }
      const next = await updateIntegration(provider, payload);
      setData(next);
      setToast("Configuração salva");
      setTimeout(() => setToast(null), 2000);
    } catch (e) {
      setToast(e instanceof Error ? e.message : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  }

  async function onRemove() {
    if (!confirm(`Remover ${meta.label}? Cadências em andamento podem falhar.`)) return;
    await deleteIntegration(provider);
    router.push("/app/settings/integracoes");
  }

  return (
    <form onSubmit={save}>
      <Link href="/app/settings/integracoes" style={{ fontSize: 13, color: "var(--text-muted)" }}>
        ← Voltar pra integrações
      </Link>
      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 8, marginBottom: 8 }}>
        <h2 style={{ fontSize: 22, fontWeight: 480, margin: 0 }}>{meta.label}</h2>
        <StatusBadge integration={data} />
      </header>
      <p style={{ color: "var(--text-muted)", fontSize: 14, marginBottom: 24 }}>
        {meta.description}
        {meta.docs && <> · <a href={meta.docs} target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent)" }}>Docs</a></>}
      </p>

      {fields.secrets.length > 0 && (
        <section className="settings-section" style={{ marginTop: 0, paddingTop: 0, borderTop: 0 }}>
          <h3 className="settings-section-title">Credenciais</h3>
          {fields.secrets.map((f) => (
            <div key={f.key} className="settings-field">
              <SecretField
                label={f.label}
                hasValue={Boolean(data.config[`has_${f.key}`])}
                last4={data.config[`${f.key}_last4`] as string | undefined}
                value={draft[f.key] || ""}
                onChange={(v) => setDraft((d) => ({ ...d, [f.key]: v }))}
                placeholder={`cole sua ${f.label.toLowerCase()} aqui`}
              />
            </div>
          ))}
        </section>
      )}

      {fields.plain.length > 0 && (
        <section className="settings-section">
          <h3 className="settings-section-title">Configuração</h3>
          {fields.plain.map((f) => (
            <div key={f.key} className="settings-field">
              <label className="settings-field-label">{f.label}</label>
              <input
                className="settings-input"
                type={f.type || "text"}
                value={draft[f.key] || ""}
                onChange={(e) => setDraft((d) => ({ ...d, [f.key]: e.target.value }))}
              />
            </div>
          ))}
        </section>
      )}

      <section className="settings-section">
        <h3 className="settings-section-title">Status</h3>
        {data.last_test_result ? (
          <p style={{ fontSize: 14, margin: 0 }}>
            Última verificação: {new Date(data.last_tested_at!).toLocaleString("pt-BR")} · {data.last_test_result.latency_ms}ms
            <br />
            {data.last_test_result.ok
              ? <span style={{ color: "var(--ok)" }}>✓ OK</span>
              : <span style={{ color: "var(--danger)" }}>✗ {data.last_test_result.error}</span>}
          </p>
        ) : (
          <p style={{ fontSize: 14, color: "var(--text-muted)", margin: 0 }}>Nunca testado.</p>
        )}
      </section>

      <div className="settings-actions" style={{ justifyContent: "space-between" }}>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <button type="submit" className="settings-btn settings-btn-primary" disabled={saving}>
            {saving ? "Salvando…" : "Salvar"}
          </button>
          <TestButton provider={provider} onResult={() => getIntegration(provider).then(setData)} />
          {toast && <span style={{ fontSize: 14, color: "var(--ok)" }}>{toast}</span>}
        </div>
        <button type="button" className="settings-btn settings-btn-danger" onClick={onRemove}>
          Remover
        </button>
      </div>
    </form>
  );
}
```

- [ ] **Step 2: Smoke test ponta-a-ponta**

Backend dev rodando + frontend dev rodando:
1. Abrir `/app/settings/integracoes/resend`, colar API key real, preencher email/nome, Salvar.
2. Refresh — vê badge "termina em xxx7".
3. Click "Testar conexão" — espera badge "✓ OK · NNNms".
4. Lista (`/integracoes`) mostra Resend "Conectado".
5. Click "Substituir" — input vira vazio, digite outra key, salve.
6. Click "Remover" — confirma, volta pra lista, Resend "Desconectado".

- [ ] **Step 3: Build**

Run: `cd frontend && npm run build`
Expected: success.

- [ ] **Step 4: Commit + push + PR**

```bash
git add frontend/src/app/app/settings/integracoes/[provider]/page.tsx
git commit -m "feat(settings): integration detail with secret field, test, remove"
git push -u origin feat/ui-settings-frontend-forms
gh pr create --title "feat(settings): frontend forms — perfil, targeting, integrações" --body "$(cat <<'EOF'
## Summary
- API client tipado em \`api-settings.ts\` (9 funções)
- Componentes: SecretField (replace pattern), ChipsInput, StatusBadge, TestButton
- Página Perfil com 5 campos + persistência
- Página Targeting com chips + numéricos
- Lista de integrações em grid com badges de status
- Detalhe por provider com fields tipados, replace pattern, test inline, remover
- 7 providers cobertos: resend, telegram, apify, llm, hunter, apollo, langsmith

Spec: \`docs/superpowers/specs/2026-04-30-ui-settings-design.md\`

## Smoke checklist
- [x] Perfil: salvar e reload persiste
- [x] Targeting: chips de niches/cities OK, save reflete
- [x] Integração resend: cola key, salva, badge xxx7 aparece
- [x] Substituir chave abre input vazio
- [x] Salvar com input vazio mantém chave atual
- [x] Test button mostra latência ou erro inline
- [x] Remover volta pra lista com badge "Desconectado"
- [x] Mobile <1024px: drill-in funciona
- [x] \`npm run build\` sem erros TypeScript
EOF
)"
```

---

## Self-Review

**1. Spec coverage:**

| Spec section | Plano cobre? |
|---|---|
| Multi-tenant scaffold (workspace_id constante 1) | ✅ Task 1.5/1.6 (DEFAULT 1), 2.2 (tenant resolver) |
| 3 tabelas + indexes | ✅ Task 1.6 |
| Schema config por provider + SECRET_FIELDS | ✅ Task 1.4 |
| Fernet encrypt/decrypt/mask | ✅ Task 1.3 |
| SETTINGS_ENC_KEY obrigatório | ✅ Task 1.2 |
| Resolver DB→env fallback | ✅ Task 2.3 |
| 9 endpoints REST | ✅ Tasks 2.5 + 2.6 |
| PUT semantics (parcial, secret vazio ignorado) | ✅ Task 2.6 testes 3-4 |
| Mascaramento na resposta | ✅ Task 2.6 + teste 2 |
| Test endpoint + last_tested_at gravado | ✅ Task 2.6 + teste 6 |
| 7 testers HTTP | ✅ Task 2.4 |
| Reaproveitar resolver em call sites | ✅ Tasks 3.3-3.5 |
| SettingsLayout + sub-rotas | ✅ Tasks 4.3 |
| Avatar dropdown + sidebar entry | ✅ Task 4.4 |
| API client tipado | ✅ Task 5.2 |
| Replace pattern UI | ✅ Task 5.3 |
| ChipsInput | ✅ Task 5.4 |
| StatusBadge + TestButton | ✅ Task 5.5 |
| Página Perfil | ✅ Task 5.6 |
| Página Targeting | ✅ Task 5.7 |
| Lista integrações | ✅ Task 5.8 |
| Detalhe integração com remove | ✅ Task 5.9 |

Lacunas reconhecidas (mantidas dentro do spec como FORA):
- Página Avançado populada → placeholder "em breve" só
- Rate limit 10 req/min — implementação não incluída (out-of-scope com explicação no spec)
- Audit log de quem testou — `tested_by` não preenchido no v1 (single user)
- Logger formatter mascarando secrets em logs — não implementado, ficaria como hardening separado
- Doc `settings-migration.md` — não criada como tarefa explícita (tarefa de doc opcional pós-merge)

**2. Placeholder scan:** percorrido, sem TBD/TODO. Cada step tem código concreto.

**3. Type consistency:** `IntegrationSummary`, `WorkspaceProfile`, `WorkspaceTargeting`, `ProviderId`, `TestResult` consistentes entre `settings-types.ts`, `api-settings.ts`, componentes e páginas. Pydantic backend `ProfileIn/Out`, `TargetingIn/Out` consistentes com TypeScript.

**4. Ambiguity:** PR 3 tasks 3.3-3.5 dependem de greps locais pra encontrar call sites — riscos de variação. Mitigado por instruções de grep e boundary clara ("trocar `settings.X` por resolver"). Se executor encontrar uso em arquivo não previsto, segue mesmo padrão.
