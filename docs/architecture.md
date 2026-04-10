# Arquitetura do SDR Machine

## 1. Visao Geral

O SDR Machine e uma plataforma de automacao de prospecao comercial (Sales Development) voltada para agencias digitais que atendem negocios locais no Brasil. O sistema executa um pipeline de 4 estagios:

1. **Scraping** de negocios locais no Google Maps
2. **Enriquecimento** com analise tecnica do site, redes sociais, CNPJ e diagnostico de marketing via IA
3. **Geracao** de landing pages personalizadas com IA (2-pass: creative brief + HTML)
4. **Outreach** com mensagens de WhatsApp personalizadas (IA quando disponivel, fallback para templates)

O objetivo e encontrar negocios com presenca digital fraca (opportunity score alto), gerar uma demonstracao gratuita (LP) e iniciar contato via WhatsApp com um link para essa demonstracao.

**Publico-alvo:** agencias digitais, freelancers e estudio de desenvolvimento web que prospectam negocios locais (dentistas, restaurantes, saloes de beleza, clinicas, pet shops, etc.).

---

## 2. Stack Tecnologico

### Backend

| Componente | Tecnologia | Versao |
|---|---|---|
| Framework web | FastAPI | 0.115 |
| ORM | SQLAlchemy | 2.0 |
| Banco de dados | PostgreSQL | 16 |
| Migracoes | Alembic | - |
| Configuracao | pydantic-settings | - |
| SSE | sse-starlette | - |
| Autenticacao | Better Auth (session table) | - |
| HTTP client | requests / httpx | - |
| HTML parsing | BeautifulSoup4 | - |

### Frontend

| Componente | Tecnologia | Versao |
|---|---|---|
| Framework | Next.js (App Router) | 16 |
| UI | React | 19 |
| Linguagem | TypeScript (strict) | 5 |
| CSS | Tailwind CSS (v4, sem config file) | 4 |
| Drag-and-drop | @dnd-kit/core | - |
| Fontes | Outfit, DM Sans, JetBrains Mono | - |

### Deploy

| Servico | Componente | Notas |
|---|---|---|
| Railway | Backend + PostgreSQL | Dockerfile na raiz, auto-migrations |
| Vercel | Frontend | Next.js com App Router |

---

## 3. Diagrama de Arquitetura

```
                         APIs Externas
                    ┌────────────────────────────────┐
                    │  Apify (Google Maps, Instagram, │
                    │         LinkedIn)               │
                    │  LLM API (LP gen, diagnostico,  │
                    │          outreach)               │
                    │  Google PageSpeed Insights       │
                    │  BrasilAPI (CNPJ)                │
                    │  Hunter.io (email discovery)     │
                    │  Apollo.io (email + company)     │
                    └──────────┬─────────────────────┘
                               │
                               │ HTTP
                               │
┌──────────┐   HTTPS    ┌──────┴──────────────┐           ┌──────────────────┐
│          │ ─────────> │                     │           │                  │
│ Browser  │            │  Next.js 16         │  fetch    │  FastAPI         │
│          │ <───────── │  (Vercel)           │ ────────> │  (Railway)       │
│          │   HTML/JS  │                     │           │                  │
│          │            │  - App Router       │ <──────── │  - Routers       │
│          │            │  - Middleware auth   │   JSON    │  - Pipeline BG   │
│          │            │  - Tailwind CSS 4   │           │  - Auth MW       │
└──────────┘            │  - @dnd-kit         │           │  - SSE stream    │
     │                  └─────────────────────┘           └────────┬─────────┘
     │                                                             │
     │                  ┌─────────────────────┐                    │ SQLAlchemy
     │     SSE          │  Better Auth        │                    │
     └─────────────────>│  (session table     │                    │
       GET /api/jobs/   │   em PostgreSQL)    │           ┌────────┴─────────┐
       {id}/stream      └─────────────────────┘           │                  │
                                                          │  PostgreSQL 16   │
                                                          │                  │
                                                          │  - jobs          │
                                                          │  - leads         │
                                                          │  - landing_pages │
                                                          │  - outreach_msgs │
                                                          │  - session (auth)│
                                                          │  - user (auth)   │
                                                          └──────────────────┘
```

### Fluxo de Comunicacao

1. O **browser** carrega a aplicacao Next.js servida pela Vercel.
2. O **middleware do Next.js** verifica o cookie `better-auth.session_token` antes de permitir acesso a rotas protegidas. Rotas publicas: `/login`, `/lp/*`, `/_next`, `/favicon.ico`.
3. O **frontend** faz chamadas `fetch()` para o backend via `fetchAPI()` em `lib/api.ts`, enviando o token no header `Authorization: Bearer <token>`.
4. O **AuthMiddleware** do backend valida o token contra a tabela `session` no PostgreSQL. Paths publicos: `/api/health`, `/api/leads/p/`, `/docs`, `/openapi.json`.
5. Para jobs de longa duracao, o frontend abre uma **conexao SSE** (`GET /api/jobs/{id}/stream`) que recebe eventos de progresso em tempo real.
6. Os **background tasks** do pipeline chamam APIs externas (Apify, LLM, PageSpeed, BrasilAPI, Hunter, Apollo) e persistem resultados no PostgreSQL.

---

## 4. Modelo de Dados

### Diagrama de Relacionamentos

```
┌─────────────┐      1:N (SET NULL)      ┌──────────────┐
│    jobs      │ ──────────────────────── │    leads     │
│             │                          │              │
│  id (PK)    │                          │  id (PK)     │
│  type       │                          │  public_id   │
│  status     │                          │  nome        │
│  params     │                          │  status      │
│  result_sum │                          │  job_id (FK) │
│  error_msg  │                          │  ...         │
│  started_at │                          └──────┬───────┘
│  finished_at│                                 │
│  created_at │                                 │ 1:N (CASCADE)
└─────────────┘                        ┌────────┴────────┐
                                       │                 │
                              ┌────────┴──────┐  ┌───────┴─────────┐
                              │ landing_pages │  │ outreach_msgs   │
                              │               │  │                 │
                              │ id (PK)       │  │ id (PK)         │
                              │ public_id     │  │ lead_id (FK)    │
                              │ lead_id (FK)  │  │ type            │
                              │ html          │  │ message_text    │
                              │ version       │  │ whatsapp_link   │
                              │ is_active     │  │ sent_at         │
                              │ created_at    │  │ response_recv_at│
                              └───────────────┘  │ created_at      │
                                                 └─────────────────┘
```

### Tabela `jobs`

Registra cada execucao de um estagio do pipeline.

| Coluna | Tipo | Descricao |
|---|---|---|
| `id` | `Integer` PK | Auto-increment |
| `type` | `String(50)` | Tipo do job: `scrape`, `enrich`, `generate`, `outreach` |
| `status` | `String(50)` | `pending` → `running` → `done` / `done_with_errors` / `failed` |
| `params` | `JSON` | Parametros enviados na requisicao (nichos, cidades, lead_ids, etc.) |
| `result_summary` | `JSON` | Resumo do resultado: `{created, total, errors}` etc. |
| `error_message` | `Text` | Mensagem de erro (truncada em 500 chars) se o job falhar |
| `started_at` | `DateTime` | Quando o job comecou a rodar |
| `finished_at` | `DateTime` | Quando o job terminou |
| `created_at` | `DateTime` | `func.now()` |

**Relacionamento:** `Job` 1:N `Lead` (via `Lead.job_id`, `ondelete="SET NULL"`)

### Tabela `leads`

Armazena cada negocio prospectado, do scraping ate a entrega final.

| Coluna | Tipo | Descricao |
|---|---|---|
| `id` | `Integer` PK | Auto-increment |
| `public_id` | `String(16)` UNIQUE | Nanoid de 16 chars para URLs publicas |
| `nome` | `String(255)` | Nome do negocio |
| `telefone` | `String(50)` | Telefone |
| `website` | `String(500)` | URL do site |
| `endereco` | `String(500)` | Endereco completo |
| `cidade` | `String(100)` | Cidade alvo |
| `nicho` | `String(100)` | Nicho de mercado |
| `categoria` | `String(100)` | Categoria do Google Maps |
| `rating` | `Numeric(2,1)` | Nota do Google Maps (ex: 4.7) |
| `reviews_count` | `Integer` | Quantidade de avaliacoes |
| `google_maps_url` | `String(500)` | Link do Google Maps |
| `top_reviews` | `JSON` | Ate 3 avaliacoes resumidas (max 200 chars cada) |
| `status` | `String(50)` | Status atual no pipeline (ver fluxo de status abaixo) |
| `opportunity_score` | `Integer` | Score 0-100 (maior = pior site = mais oportunidade) |
| `opportunity_reasons` | `JSON` | Lista de razoes que contribuiram para o score |
| `site_analysis` | `JSON` | Resultado completo da analise tecnica do site |
| `social_profiles` | `JSON` | Dados de redes sociais (Instagram, LinkedIn, etc.) |
| `email` | `String(255)` | Email de contato descoberto |
| `cnpj` | `String(18)` | CNPJ formatado |
| `razao_social` | `String(255)` | Razao social da empresa |
| `porte` | `String(50)` | Porte da empresa (MEI, ME, EPP, etc.) |
| `cnae` | `String(100)` | CNAE principal |
| `data_fundacao` | `Date` | Data de fundacao |
| `socios` | `JSON` | Lista de socios |
| `tech_stack` | `JSON` | Tecnologias detectadas no site |
| `enrichment_sources` | `JSON` | Fontes de dados usadas no enriquecimento |
| `lp_html` | `Text` | HTML da LP ativa (cache rapido, duplicado da `landing_pages`) |
| `job_id` | `Integer` FK | Job que criou este lead |
| `created_at` | `DateTime` | `func.now()` |
| `updated_at` | `DateTime` | Auto-atualizado via trigger PostgreSQL |

**Indexes:**
- `idx_leads_status` (`status`)
- `idx_leads_nicho` (`nicho`)
- `idx_leads_cidade` (`cidade`)
- `idx_leads_score` (`opportunity_score`)
- `idx_leads_email` (`email`)
- `idx_leads_cnpj` (`cnpj`)

**Relacionamentos:**
- `Lead` N:1 `Job` (`SET NULL` on delete)
- `Lead` 1:N `OutreachMessage` (`CASCADE` on delete)
- `Lead` 1:N `LandingPage` (`CASCADE` on delete, ordenado por `version DESC`)

### Tabela `landing_pages`

Armazena versoes de landing pages geradas para cada lead. Suporta versionamento com ativacao/desativacao.

| Coluna | Tipo | Descricao |
|---|---|---|
| `id` | `Integer` PK | Auto-increment |
| `public_id` | `String(16)` UNIQUE | Nanoid para URLs publicas |
| `lead_id` | `Integer` FK | Lead associado (`CASCADE` on delete) |
| `html` | `Text` | HTML completo da landing page |
| `version` | `Integer` | Numero da versao (incremental por lead) |
| `is_active` | `Boolean` | Se esta e a versao ativa |
| `created_at` | `DateTime` | `func.now()` |

**Indexes:**
- `idx_landing_pages_lead_id` (`lead_id`)

**Constraints:**
- `uq_landing_pages_lead_version` UNIQUE (`lead_id`, `version`)

### Tabela `outreach_messages`

Armazena as 3 mensagens de WhatsApp geradas para cada lead.

| Coluna | Tipo | Descricao |
|---|---|---|
| `id` | `Integer` PK | Auto-increment |
| `lead_id` | `Integer` FK | Lead associado (`CASCADE` on delete) |
| `type` | `String(50)` | `initial`, `followup_48h`, `followup_final` |
| `message_text` | `Text` | Texto da mensagem |
| `whatsapp_link` | `Text` | Link `wa.me` pre-preenchido com URL-encoded message |
| `sent_at` | `DateTime` | Quando a mensagem foi enviada (null = nao enviada) |
| `response_received_at` | `DateTime` | Quando o lead respondeu (null = sem resposta) |
| `created_at` | `DateTime` | `func.now()` |

**Indexes:**
- `idx_outreach_messages_lead_id` (`lead_id`)

---

## 5. Fluxo de Dados

### Pipeline de 4 Estagios

```
  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
  │  SCRAPE  │ ──> │  ENRICH  │ ──> │ GENERATE │ ──> │ OUTREACH │
  └──────────┘     └──────────┘     └──────────┘     └──────────┘
   status:          status:          status:           status:
   scraped          enriched         lp_generated      outreach_ready
```

### Transicoes de Status de um Lead

```
scraped ──────────> enriched ────────> lp_generated ───> outreach_ready
   │                    │                    │                 │
   │                    │                    │                 ├──> outreach_sent
   │                    │                    │                 ├──> responded
   ├──> enrich_failed   ├──> generate_failed ├──> outreach_   ├──> in_call
   │                    │                    │    failed       ├──> closed
   │                    ├──> disqualified    │                 └──> delivered
   │                    │                    │
   └────────────────────┴────────────────────┘
```

**Detalhamento dos status:**

| Status | Descricao |
|---|---|
| `scraped` | Lead recem-extraido do Google Maps |
| `enriched` | Analise tecnica e scoring concluidos |
| `disqualified` | Desqualificado pelo diagnostico de IA (nota baixa) |
| `lp_generated` | Landing page gerada com sucesso |
| `outreach_ready` | Mensagens de WhatsApp geradas, prontas para envio |
| `outreach_sent` | Primeira mensagem enviada |
| `responded` | Lead respondeu ao contato |
| `in_call` | Reuniao/chamada agendada |
| `closed` | Negocio fechado |
| `delivered` | Projeto entregue ao cliente |
| `enrich_failed` | Erro durante enriquecimento |
| `generate_failed` | Erro durante geracao de LP |
| `outreach_failed` | Erro durante geracao de mensagens |

### Fluxo Detalhado

1. **Scrape:** O usuario seleciona nichos e cidades. O scraper chama a API Apify `compass/crawler-google-places` para cada combinacao nicho x cidade. Resultados sao deduplicados por telefone ou nome. Leads com rating abaixo de `min_rating` (default: 3.0) sao descartados. Cada lead e criado com `status="scraped"`.

2. **Enrich:** O orchestrator executa providers em fases:
   - **Fase 1 (Discovery):** `CnpjProvider` busca CNPJ na BrasilAPI (pode descobrir website)
   - **Fase 2 (Crawl):** `WebsiteCrawlerProvider` faz fetch do site, `SchemaOrgProvider` extrai dados Schema.org, `TechStackProvider` detecta tecnologias
   - **Fase 3 (Contact):** `EmailDiscovererProvider` (Hunter.io), `ApolloProvider`
   - **Fase 4 (Scoring):** Recalcula `opportunity_score` baseado em todos os dados coletados
   - Opcionalmente, executa diagnostico de marketing via LLM e scraping de redes sociais (Instagram, LinkedIn via Apify)
   - Leads qualificados recebem `status="enriched"`; desqualificados recebem `status="disqualified"`

3. **Generate:** Para cada lead `enriched`, o gerador executa 2 passes de LLM:
   - **Pass 1 (Creative Brief):** Gera um JSON com paleta de cores, tipografia, copy (headlines, CTAs, FAQ), escolha de icones SVG e decisoes de layout
   - **Pass 2 (HTML):** Gera o HTML completo usando o brief como input, com gold standard de referencia
   - Post-processing substitui placeholders `{{icon:nome}}` por SVGs inline reais
   - O HTML e salvo na tabela `landing_pages` (versionado) e cacheado em `lead.lp_html`
   - Status atualizado para `lp_generated`

4. **Outreach:** Para cada lead `lp_generated`, gera 3 mensagens de WhatsApp:
   - `initial` — apresentacao + link da LP de demonstracao
   - `followup_48h` — follow-up leve 48h depois
   - `followup_final` — ultima mensagem, sem pressao
   - Se o lead tem diagnostico de marketing, as mensagens sao geradas por IA. Caso contrario, usa templates fallback (diferenciados para leads com/sem site).
   - Links `wa.me` pre-preenchidos com mensagem URL-encoded
   - Status atualizado para `outreach_ready`

---

## 6. Autenticacao

O SDR Machine usa **Better Auth** como provedor de autenticacao. A autenticacao funciona em duas camadas:

### Camada Frontend (middleware Next.js)

O arquivo `frontend/src/middleware.ts` intercepta todas as requisicoes e verifica a presenca do cookie de sessao Better Auth:

```typescript
// frontend/src/middleware.ts
const sessionCookie = getSessionCookie(request);

if (!sessionCookie) {
  return NextResponse.redirect(new URL("/login", request.url));
}
```

**Rotas publicas** (nao exigem autenticacao):
- `/login`
- `/lp` e `/lp/*` (landing pages publicas)
- `/_next/*` (assets do Next.js)
- `/favicon.ico`

O middleware tambem redireciona usuarios autenticados que tentam acessar `/login` de volta para `/`.

### Camada Backend (AuthMiddleware)

O arquivo `backend/app/middleware/auth.py` implementa um middleware Starlette que valida o token contra a tabela `session` no PostgreSQL:

```python
# backend/app/middleware/auth.py
_VALIDATE_SQL = text('SELECT "expiresAt" FROM "session" WHERE "token" = :token')
```

**Fluxo de validacao:**

1. Extrai token do header `Authorization: Bearer <token>` ou do cookie `better-auth.session_token`
2. O formato do cookie e `token.signature` — extrai apenas a parte `token`
3. Consulta a tabela `session` do Better Auth no PostgreSQL
4. Verifica se o token existe e se `expiresAt` nao expirou
5. Retorna `401 {"detail": "Nao autenticado"}` se qualquer verificacao falhar

**Paths publicos no backend** (configurados em `main.py`):
- `/api/health`
- `/api/leads/p/` (landing pages por public_id)
- `/docs` (Swagger)
- `/openapi.json`

### Fluxo de Sessao Expirada no Frontend

O `fetchAPI()` em `lib/api.ts` trata respostas `401` chamando `forceLogout()`:

```typescript
// frontend/src/lib/api.ts
function forceLogout() {
  if (redirectingToLogin) return;  // Previne redirects paralelos
  redirectingToLogin = true;
  // Limpa cookies Better Auth
  document.cookie.split("; ").forEach((c) => {
    const name = c.split("=")[0];
    if (name.includes("better-auth")) {
      document.cookie = `${name}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
    }
  });
  window.location.replace("/login");
}
```

A flag `redirectingToLogin` (nivel de modulo) garante que chamadas paralelas que retornam 401 simultaneamente nao disparem multiplos redirects.

---

## 7. Deploy

### Backend — Railway

O backend e deployado no Railway usando o `Dockerfile` na raiz do repositorio:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

ENV PYTHONPATH=/app
EXPOSE ${PORT:-8000}

CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

**Pontos importantes:**

- **Migracoes automaticas:** `alembic upgrade head` roda antes do servidor subir, garantindo que o schema do banco esta atualizado
- **Variavel `$PORT`:** O Railway injeta a porta automaticamente; fallback para 8000
- **Base image:** `python:3.12-slim` para manter a imagem leve
- **PostgreSQL:** Provisionado como servico separado no Railway, conectado via `DATABASE_URL`
- **CORS:** Configurado em `main.py` para aceitar `localhost:3000`, `localhost:4000` e o valor de `FRONTEND_URL` (URL da Vercel em producao)

### Frontend — Vercel

O frontend Next.js e deployado na Vercel com configuracao padrao do App Router:

- **Build command:** `npm run build`
- **Variavel de ambiente:** `NEXT_PUBLIC_API_URL` aponta para a URL do backend no Railway
- **Middleware:** Roda no edge runtime da Vercel para verificacao rapida de sessao

### Variaveis de Ambiente

**Backend** (configuradas no Railway):

| Variavel | Obrigatoria | Descricao |
|---|---|---|
| `DATABASE_URL` | Sim | PostgreSQL connection string |
| `APIFY_TOKEN` | Sim | Token da API Apify (scraping) |
| `LLM_API_KEY` / `ANTHROPIC_API_KEY` | Sim | Chave de API do LLM (geracao de LP e diagnostico) |
| `LLM_MODEL` | Nao | Modelo LLM (default: `MiniMax-M2.7`) |
| `LLM_BASE_URL` | Nao | Base URL da API LLM (default: `https://api.minimax.io/v1`) |
| `FRONTEND_URL` | Sim | URL do frontend na Vercel (CORS) |
| `API_URL` | Sim | URL publica do backend (usada em links de LP e outreach) |
| `BUSINESS_NAME` | Nao | Nome da agencia (default: `Studio Digital`) |
| `YOUR_NAME` | Nao | Nome do usuario (usado em mensagens) |
| `YOUR_WHATSAPP` | Nao | WhatsApp para contato |
| `YOUR_EMAIL` | Nao | Email para contato |
| `YOUR_WEBSITE` | Nao | Site da agencia |
| `HUNTER_API_KEY` | Nao | API Hunter.io para descoberta de email |
| `APOLLO_API_KEY` | Nao | API Apollo.io para enriquecimento de contato |
| `LANGSMITH_API_KEY` | Nao | Tracing de LLM via LangSmith |

**Frontend** (configuradas na Vercel):

| Variavel | Obrigatoria | Descricao |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Sim | URL do backend (Railway) |
