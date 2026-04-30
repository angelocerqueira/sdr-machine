# UI Settings — Configuração de Integrações & Workspace

**Data:** 2026-04-30
**Status:** Spec aprovado, aguardando plano de implementação
**Autor:** Angelo + Claude

---

## Resumo

Construir superfície de configuração no frontend (`/app/settings/*`) para que o usuário gerencie credenciais de integrações, perfil de remetente e preferências de targeting via UI — substituindo gradualmente o uso direto de variáveis de ambiente no `app/config.py`. Schema multi-tenant-ready (queries já filtram por `workspace_id`, single-workspace hoje, sem dor de migração depois).

## Motivação

- Hoje todas credenciais (Apify, LLM, Hunter, Apollo, Langsmith) e perfil do remetente vivem em `.env`. Mudar = redeploy.
- Cadência multicanal exige novas integrações (Resend, Telegram). Adicionar como env vars perpetua o problema.
- Visão de produto é multi-tenant (cliente B2B traz BYOK pra Apify/LLM/etc) — modelo precisa nascer compatível.
- Auditoria mostrou 7 integrações + perfil + targeting elegíveis pra UI; 6 tunables avançados ficam pra v2; 3 vars de infra (database/api/frontend URLs) ficam em env permanentemente.

## Decisões

| # | Pergunta | Decisão |
|---|---|---|
| 1 | Schema | Extensível tipado: discriminator `provider` + `config jsonb`, validado por Pydantic schemas registry |
| 2 | Storage de secret | Fernet (AES-128 + HMAC) com master key em env `SETTINGS_ENC_KEY` |
| 3 | Shape da UI | Sub-rotas por categoria; sidebar interna desktop, drill-in mobile |
| 4 | Test de credencial | Botão "Testar" explícito por provider, com nudge (badges ⚠ não testado / ✓ ok / ✗ falha) |
| 5 | Acesso | Avatar dropdown + atalho na sidebar (descoberta + acesso de 1 clique) |
| 6 | Edição de credencial | Replace pattern: badge "configurada • xxx7" + botão "Substituir chave" |

---

## Arquitetura

### Multi-tenant scaffold (single-tenant disfarçado)

Tabelas novas nascem com `workspace_id INT NOT NULL DEFAULT 1`. Hoje sempre `1`. Tabela `workspaces` **não é criada nesta fase** — vem com migração multi-tenant separada que adiciona membership e middleware. Resolver de tenant hoje retorna constante `DEFAULT_WORKSPACE_ID = 1`.

Migração futura (fora do escopo):
1. `CREATE TABLE workspaces (id, slug, name, created_at)`
2. `CREATE TABLE workspace_users (workspace_id, user_id, role)`
3. Middleware extrai `workspace_id` do session do Better Auth
4. `INSERT INTO workspaces VALUES (1, 'default', 'Default')` + FKs

### 3 tabelas novas

```sql
-- Credenciais de integração (1 linha por workspace × provider)
CREATE TABLE integration_settings (
  id            SERIAL PRIMARY KEY,
  workspace_id  INT NOT NULL DEFAULT 1,
  provider      VARCHAR(32) NOT NULL,
  config        JSONB NOT NULL DEFAULT '{}'::jsonb,
  enabled       BOOLEAN NOT NULL DEFAULT TRUE,
  last_tested_at TIMESTAMPTZ,
  last_test_result JSONB,
  created_at    TIMESTAMPTZ DEFAULT now(),
  updated_at    TIMESTAMPTZ DEFAULT now(),
  UNIQUE(workspace_id, provider)
);
CREATE INDEX idx_integration_settings_workspace ON integration_settings(workspace_id);

-- Perfil de remetente (1 linha por workspace)
CREATE TABLE workspace_profile (
  workspace_id   INT PRIMARY KEY DEFAULT 1,
  business_name  VARCHAR(255),
  your_name      VARCHAR(255),
  your_email     VARCHAR(255),
  your_whatsapp  VARCHAR(50),
  your_website   VARCHAR(500),
  legal_basis    VARCHAR(64) DEFAULT 'legitimo_interesse_b2b',
  updated_at     TIMESTAMPTZ DEFAULT now()
);

-- Preferências de scraping (1 linha por workspace)
CREATE TABLE workspace_targeting (
  workspace_id            INT PRIMARY KEY DEFAULT 1,
  target_niches           JSONB DEFAULT '[]'::jsonb,
  target_cities           JSONB DEFAULT '[]'::jsonb,
  min_rating              FLOAT DEFAULT 3.0,
  max_results_per_search  INT   DEFAULT 50,
  opportunity_score_threshold INT DEFAULT 40,
  -- v2 advanced (nullable, fallback pro env):
  diagnostic_model        VARCHAR(64),
  skip_ai_diagnostic      BOOLEAN,
  skip_social_scraping    BOOLEAN,
  ai_potential_threshold  INT,
  disqualify_threshold    INT,
  skip_service_level_analysis BOOLEAN,
  updated_at              TIMESTAMPTZ DEFAULT now()
);
```

### Schema do `config` por provider

Validado por Pydantic. `SecretStr` marca campos cifrados.

```python
# app/integrations/schemas.py
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
```

### Crypto helper

```python
# app/integrations/crypto.py
from cryptography.fernet import Fernet
from app.config import settings

_fernet = Fernet(settings.settings_enc_key.encode())

def encrypt(plain: str) -> str:
    return _fernet.encrypt(plain.encode()).decode()

def decrypt(cipher: str) -> str:
    return _fernet.decrypt(cipher.encode()).decode()

def mask(plain: str, keep: int = 4) -> str:
    return "•" * 8 + plain[-keep:] if plain and len(plain) > keep else "•" * 8
```

Master key obrigatória — `app/config.py` ganha:

```python
settings_enc_key: str = Field(..., env="SETTINGS_ENC_KEY")
```

App falha no startup se ausente. `.env.example` ganha instrução de geração:
```
# Gere com: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
SETTINGS_ENC_KEY=
```

Rotação anual recomendada — script utilitário não incluído no v1 (ver Escopo — FORA).

### Resolver DB → env fallback

```python
# app/integrations/resolver.py
def get_provider_config(workspace_id: int, provider: str) -> dict | None:
    row = db.query(IntegrationSettings).filter_by(
        workspace_id=workspace_id, provider=provider, enabled=True,
    ).first()
    if row:
        return _decrypt_secrets(provider, row.config)
    return _env_fallback(provider)

def _env_fallback(provider: str) -> dict | None:
    if provider == "apify":
        return {"token": settings.apify_token} if settings.apify_token else None
    if provider == "llm":
        return {
            "api_key": settings.llm_api_key,
            "model": settings.llm_model,
            "base_url": settings.llm_base_url,
        } if settings.llm_api_key else None
    if provider == "hunter":
        return {"api_key": settings.hunter_api_key} if settings.hunter_api_key else None
    if provider == "apollo":
        return {"api_key": settings.apollo_api_key} if settings.apollo_api_key else None
    if provider == "langsmith":
        return {
            "api_key": settings.langsmith_api_key,
            "project": settings.langsmith_project,
            "tracing": settings.langsmith_tracing,
        } if settings.langsmith_api_key else None
    return None  # resend, telegram nunca tiveram env, retornam None
```

Permite migração progressiva — zero breakage; UI sobrescreve quando setado.

---

## Backend — Endpoints

Router novo: `app/routers/workspace_settings.py`, prefixo `/api/workspace`.

```
GET    /api/workspace/profile                       → perfil atual
PUT    /api/workspace/profile                       → upsert perfil

GET    /api/workspace/targeting                     → targeting + advanced
PUT    /api/workspace/targeting                     → upsert targeting

GET    /api/workspace/integrations                  → lista todos providers
GET    /api/workspace/integrations/{provider}       → detalhe (config mascarado)
PUT    /api/workspace/integrations/{provider}       → upsert config
DELETE /api/workspace/integrations/{provider}       → disconnect (apaga linha)
POST   /api/workspace/integrations/{provider}/test  → roda ping, grava resultado
```

### Auth & tenant

Middleware existente (`middleware/auth.py`) extrai `user_id`. Adicionar resolver `get_current_workspace_id(request) -> int` que retorna `DEFAULT_WORKSPACE_ID = 1` hoje. Migração multi-tenant troca implementação sem mudar call sites.

### PUT semantics (importante)

- Body parcial = OK (PATCH-like, mas usamos PUT por simplicidade REST).
- Campos secretos (`SecretStr`) ausentes no body = mantém valor atual.
- Campos secretos presentes mas string vazia (`""`) = ignorados (não apaga). Pra apagar tudo da integração = `DELETE`.
- Campos não-secretos seguem semântica normal de upsert.

### Mascaramento na resposta

`config` retornado nunca expõe secret em texto. Helper `mask_config(provider, raw_config)` aplica:
- Cada `SecretStr` vira `null` no body, com flags adicionais `has_<field>: true` e `<field>_last4: "xxx7"`.

Exemplo response `GET /integrations/resend`:
```json
{
  "provider": "resend",
  "enabled": true,
  "last_tested_at": "2026-04-30T13:45:12Z",
  "last_test_result": {"ok": true, "latency_ms": 234, "tested_by": "user_123"},
  "config": {
    "from_email": "get@suaempresa.com",
    "from_name": "SDR Machine",
    "reply_to": "vendas@suaempresa.com",
    "has_api_key": true,
    "api_key_last4": "xxx7",
    "has_webhook_secret": false
  }
}
```

### Test endpoint

Cada provider tem implementação em `app/integrations/testers.py`:

```python
TESTERS = {
    "resend":    test_resend,    # GET /domains
    "telegram":  test_telegram,  # POST /bot{token}/getMe
    "apify":     test_apify,     # GET /v2/users/me
    "llm":       test_llm,       # 5-token completion
    "hunter":    test_hunter,    # GET /v2/account
    "apollo":    test_apollo,    # GET /v1/auth/health
    "langsmith": test_langsmith, # GET /info
}

@dataclass
class TestResult:
    ok: bool
    latency_ms: int
    error: str | None = None

def test_resend(cfg: dict) -> TestResult:
    t0 = time.monotonic()
    try:
        r = httpx.get(
            "https://api.resend.com/domains",
            headers={"Authorization": f"Bearer {cfg['api_key']}"},
            timeout=10,
        )
        return TestResult(
            ok=r.status_code == 200,
            latency_ms=int((time.monotonic() - t0) * 1000),
            error=r.text[:200] if r.status_code != 200 else None,
        )
    except Exception as e:
        return TestResult(ok=False, latency_ms=int((time.monotonic() - t0) * 1000), error=str(e)[:200])
```

POST endpoint chama tester apropriado, grava `last_test_result` e `last_tested_at`, retorna resultado síncrono.

### Rate limit

POST test: 10 req/min por user. Helper simples in-memory dict (single-instance suficiente hoje).

---

## Frontend — Rotas e UI

### Estrutura

```
src/app/app/settings/
├── layout.tsx                       # SettingsLayout: sidebar interna desktop, lista mobile
├── page.tsx                         # redireciona pra /settings/perfil
├── perfil/page.tsx                  # form perfil (5 campos)
├── targeting/page.tsx               # form targeting (5 campos + chips)
├── integracoes/
│   ├── page.tsx                     # lista cards (7 providers)
│   └── [provider]/page.tsx          # detalhe/edição
└── avancado/page.tsx                # placeholder "em breve" (v2)
```

### SettingsLayout

**Desktop (≥1024px):** sidebar interna 200px à esquerda lista categorias, conteúdo à direita. Active state via `bg-accent-soft`.

```
┌──────────────┬────────────────────────────────┐
│ Configurações│                                │
│              │   <conteúdo da sub-rota>       │
│ Perfil       │                                │
│ Integrações  │                                │
│ Targeting    │                                │
│ Avançado     │                                │
└──────────────┴────────────────────────────────┘
   200px           resto
```

**Mobile (<1024px):** `/settings` mostra lista vertical de tiles com chevron à direita. Clique entra na sub-rota; sub-rota tem `← Voltar` no topbar (padrão LaTopbar).

### `/settings/integracoes` — grid de cards

1 col mobile, 2 cols desktop. Cada card:

```
┌─────────────────────────────────┐
│ Resend              ✓ Conectado │
│ Email outreach                  │
│ ✓ testado 12min atrás           │
│ from: get@suaempresa.com        │
│                  [Configurar →] │
└─────────────────────────────────┘
```

Estados de badge:
- `✓ Conectado` (verde) — último test OK
- `✗ Falha` (vermelho) — último test fail
- `⚠ Não testado` (mostarda) — config presente, nunca testou
- `Desconectado` (cinza) — sem config

### `/settings/integracoes/[provider]` — detalhe

Mock da página Resend:

```
← Voltar pra integrações

Resend                                [Conectado ✓]
Email transacional pra cadência de outreach.
Docs: resend.com/docs

────────── Credencial ──────────
✓ Chave configurada • termina em xxx7         [Substituir chave]

────────── Configuração ──────────
From email      [get@suaempresa.com______________]
From name       [SDR Machine____________________]
Reply-to        [vendas@suaempresa.com__________]   (opcional)
Webhook secret  ✓ configurado                     [Substituir]

────────── Status ──────────
Última verificação: 12min atrás · 234ms
✓ OK

  [Salvar]  [Testar conexão]                     [Remover integração]
```

**Replace pattern (Q6)**: ao clicar "Substituir chave", badge some, input vazio aparece. Salvar com input preenchido = troca; com input vazio = mantém atual + toast "campo vazio, chave atual mantida".

**Remover integração**: modal de confirmação: *"Isso desabilita Resend. Cadências em andamento podem falhar. Confirmar?"*

### `/settings/perfil` — form

5 campos texto: business_name, your_name, your_email, your_whatsapp, your_website. Save único, retorna toast "Perfil atualizado".

### `/settings/targeting` — form

- Niches: input com chips removíveis + botão add. Mobile-first.
- Cities: idem.
- min_rating, max_results_per_search, opportunity_score_threshold: inputs numéricos com validation client-side.

### `/settings/avancado` — placeholder

Página vazia com texto "Em breve — tunables avançados de pipeline serão configuráveis aqui."

### Acesso

- **Avatar dropdown** (em `app-sidebar.tsx`): novo item "Configurações" entre "Tema" e "Sair", com ícone `<Icon name="settings" />`.
- **Sidebar** (em `app-sidebar.tsx`): novo botão `<Icon name="settings" />` embaixo, separado dos 4 principais (Dashboard/Pipeline/Leads/Jobs) por margin-top maior. Em mobile (drawer 240px) aparece como linha "Configurações" no fim da lista.

### API client (`src/lib/api.ts`)

Novos endpoints tipados:

```ts
getWorkspaceProfile(): Promise<WorkspaceProfile>
updateWorkspaceProfile(data: WorkspaceProfileInput): Promise<WorkspaceProfile>

getWorkspaceTargeting(): Promise<WorkspaceTargeting>
updateWorkspaceTargeting(data: WorkspaceTargetingInput): Promise<WorkspaceTargeting>

listIntegrations(): Promise<IntegrationSummary[]>
getIntegration(provider: ProviderId): Promise<IntegrationDetail>
updateIntegration(provider: ProviderId, data: IntegrationConfigInput): Promise<IntegrationDetail>
deleteIntegration(provider: ProviderId): Promise<void>
testIntegration(provider: ProviderId): Promise<TestResultResponse>
```

Tipos discriminados em `src/lib/types.ts`:

```ts
type ProviderId = 'resend' | 'telegram' | 'apify' | 'llm' | 'hunter' | 'apollo' | 'langsmith';

type IntegrationDetail =
  | { provider: 'resend';   from_email: string; from_name: string; reply_to?: string;
                            has_api_key: boolean; api_key_last4?: string;
                            has_webhook_secret: boolean; webhook_secret_last4?: string;
                            enabled: boolean; last_tested_at?: string; last_test_result?: TestResult; }
  | { provider: 'telegram'; chat_id: string; has_bot_token: boolean; bot_token_last4?: string;
                            enabled: boolean; ... }
  // ... e os demais
```

---

## Migração de envvars existentes

**Não migra automaticamente.** Quando user salva uma integração na UI pela primeira vez, ela sobrescreve env via resolver. Enquanto não salvar, fallback continua lendo `.env`. Migração explícita evita dupla-fonte ambígua.

Doc nova `docs/settings-migration.md` orienta o user em como migrar (passos: gerar `SETTINGS_ENC_KEY`, abrir cada integração na UI, colar value do `.env`, testar, deletar do `.env`).

---

## Reaproveitamento em call sites existentes

Substituir leitura direta de `settings.x` por `get_provider_config(ws_id, "<provider>")` nos seguintes arquivos (descobertos via `grep`):

- `app/pipeline/scraper.py` — `settings.apify_token` → `apify` config
- `app/pipeline/generator.py` — `settings.llm_api_key`, `llm_model`, `llm_base_url` → `llm` config
- `app/pipeline/enrichment/providers/email_discoverer.py` — `settings.hunter_api_key` → `hunter`
- `app/pipeline/enrichment/providers/apollo.py` — `settings.apollo_api_key` → `apollo`
- Pontos de tracing Langsmith (auditar)

Cada call site adapta gracefully: se resolver retorna `None` (integração desabilitada e sem env fallback), código pula a stage com warning (comportamento atual já tolera Hunter/Apollo ausentes).

---

## Testing

### Backend

`tests/test_settings_crypto.py`:
- encrypt → decrypt roundtrip
- mask preserva últimos 4 chars
- tampering Fernet token = `InvalidToken` raised

`tests/test_settings_schemas.py`:
- Pydantic schemas validam shape (api_key obrigatório em Resend, chat_id em Telegram, etc.)
- SecretStr roundtrip com encrypt/decrypt

`tests/test_settings_router.py`:
- GET retorna config mascarado (nunca secret em texto)
- PUT cria + criptografa secret
- PUT parcial sem secret = mantém secret atual
- PUT secret vazio (`""`) = ignorado
- DELETE remove linha
- GET inexistente retorna 200 com shape uniforme (`enabled: false`, `config: {}`, `last_tested_at: null`); UI infere "desconectado" quando todas flags `has_*` são `false`
- Auth: 401 sem session

`tests/test_settings_testers.py`:
- Cada tester com `httpx_mock` — mockar resposta 200 + 401 + timeout, assertar `last_test_result`

`tests/test_settings_resolver.py`:
- DB hit retorna DB
- Sem DB retorna env fallback
- Integração desabilitada (`enabled=false`) → fallback (não retorna config inválido)

Reaproveita `conftest.py` (SQLite in-memory). Adicionar fixture `enc_key` que gera Fernet key fresca por test.

### Frontend (smoke checklist no PR)

- Cada sub-rota carrega
- Salvar perfil reflete em outra tela após reload
- Substituir chave → input aparece → salvar com vazio mantém + toast aviso
- Test button mostra latência ou erro inline
- Mobile: drill-in funciona, voltar volta, drawer não overlapa
- Avatar dropdown e sidebar abrem `/settings`

Sem testes E2E (Playwright) nessa fase — projeto não tem hoje.

---

## Segurança

| Risco | Mitigação |
|---|---|
| Master key vaza | Fernet key em env, separada de DB. Vazamento de DB sozinho = dump cifrado inútil. |
| Replay de PUT com payload antigo | Better Auth session valida cada call; cookies SameSite=Lax + Bearer = sem CSRF token extra. |
| User vê secret de outro tenant | Hoje N/A (single workspace). Schema multi-tenant ready: query SEMPRE filtra `workspace_id` derivado do session. |
| Test endpoint usado pra exfiltrar key | Rate limit 10 req/min por user; log `last_test_result.tested_by`. |
| Logs vazam secret | Logger formatter custom em `integrations/*` filtra strings que match `re_*`, `sk_*`, JWT, Fernet token. |
| Hard-coded keys em commits | `.env.example` ganha `SETTINGS_ENC_KEY` placeholder com instrução de geração. |

---

## Marcos de implementação (5 PRs)

PRs pequenos, rebasáveis, mergeáveis sequencial:

1. **Migration + crypto + schemas** — tabelas, Fernet helper, Pydantic schemas, tests do crypto + schemas
2. **Backend router + testers + resolver** — endpoints + testers dos 7 providers + DB→env fallback + tests do router
3. **Reaproveitar resolver em call sites existentes** — Apify/LLM/Hunter/Apollo/Langsmith param de ler `settings.x` direto
4. **Frontend layout + rotas + avatar/sidebar** — SettingsLayout, sub-rotas vazias, navegação, smoke
5. **Frontend forms + integração com API** — perfil, targeting, lista integrações, detalhe `[provider]`, replace pattern, test button, masks

Estimativa total: ~3-4 dias dev.

---

## Escopo — DENTRO

- 3 tabelas + migration + indexes
- Fernet helper + master key obrigatória em config
- Pydantic schemas dos 7 providers + registry
- Router `/api/workspace/{profile,targeting,integrations}`
- Testers dos 7 providers (Resend, Telegram, Apify, LLM, Hunter, Apollo, Langsmith)
- Resolver DB → env fallback
- Frontend: 5 rotas + SettingsLayout + replace pattern + test button + masks
- Avatar dropdown entry + sidebar entry
- Reaproveitar resolver em call sites existentes
- Tests backend (unit + router)
- Doc `docs/settings-migration.md`

## Escopo — FORA

- Tabela `workspaces` real + middleware de tenant + filtros em queries de Lead/Job (migração multi-tenant separada)
- Página `/settings/avancado` populada (placeholder hoje)
- Webhook handlers Resend/Telegram (cadência inteira é spec separado)
- Cron de re-test automático + alerta Telegram quando provider cai
- Script utilitário de rotação da Fernet key
- Logs de auditoria de mudanças em config
- E2E Playwright
- Migration UI ("importar valores do .env atual com 1 clique")
- I18n — pt-BR fixo (convenção do projeto)

---

## Referências

- Audit do `app/config.py`: 7 vars credenciais + 5 perfil + 5 targeting + 6 advanced + 3 infra
- Patterns de B2B SaaS analisados: Stripe (test webhook), Resend (verify), Twilio (test SMS), Cloudflare (verify token), Auth0 (try connection), Supabase (mixed: SMTP test + OAuth save-only), Linear/GitHub (save-only), Zapier/Make/n8n (test on save bloqueante)
- Memória do projeto: mobile-first DS Instrumento, sempre PR (nunca push direto main)
- Modelo atual: `backend/app/models.py` — sem multi-tenancy hoje, vai ganhar `workspace_id` em fase futura
