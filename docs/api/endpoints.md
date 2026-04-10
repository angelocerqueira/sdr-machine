# Referencia da API

Base URL: `http://localhost:8000` (desenvolvimento) ou o valor de `API_URL` em producao.

Todas as rotas (exceto as [publicas](#rotas-publicas)) requerem autenticacao via cookie `better-auth.session_token` ou header `Authorization: Bearer <token>`.

---

## Leads

### GET /api/leads

Lista leads com filtros, paginacao e ordenacao.

**Query Parameters:**

| Parametro | Tipo | Padrao | Descricao |
|-----------|------|--------|-----------|
| `status` | `string` | -- | Filtra por status. Use `"failed"` para agrupar todos os `*_failed`. |
| `nicho` | `string` | -- | Filtra por nicho exato. |
| `cidade` | `string` | -- | Filtra por cidade exata. |
| `score_min` | `int` | -- | Filtra leads com `opportunity_score >= score_min`. |
| `search` | `string` | -- | Busca por nome ou telefone (case-insensitive, parcial). |
| `order_by` | `string` | `"score_desc"` | Ordenacao. Valores: `score_desc`, `score_asc`, `name_asc`, `created_desc`, `updated_desc`. |
| `page` | `int` | `1` | Pagina (minimo 1). |
| `per_page` | `int` | `20` | Itens por pagina (1-100). |

**Response `200 OK`:**

```json
{
  "items": [
    {
      "id": 42,
      "public_id": "aBcDeFgHiJkLmNoP",
      "nome": "Clinica Sorriso",
      "telefone": "49999881234",
      "email": "contato@clinicasorriso.com.br",
      "website": "https://clinicasorriso.com.br",
      "endereco": "Rua das Flores, 123",
      "cidade": "Chapeco SC",
      "nicho": "dentista",
      "categoria": "Dentista",
      "rating": 4.5,
      "reviews_count": 87,
      "google_maps_url": "https://maps.google.com/?cid=...",
      "top_reviews": ["Otimo atendimento", "Recomendo"],
      "cnpj": "12.345.678/0001-90",
      "razao_social": "Clinica Sorriso Ltda",
      "porte": "ME",
      "cnae": "8630-5/04",
      "data_fundacao": "2018-03-15",
      "socios": ["Dr. Joao Silva"],
      "status": "enriched",
      "opportunity_score": 72,
      "opportunity_reasons": ["Sem SSL", "Site nao responsivo"],
      "tech_stack": ["WordPress", "PHP"],
      "enrichment_sources": ["website", "pagespeed", "cnpj_ws"],
      "job_id": 5,
      "created_at": "2026-04-10T14:30:00",
      "updated_at": "2026-04-10T15:45:00"
    }
  ],
  "total": 156,
  "page": 1,
  "per_page": 20
}
```

> **Nota:** A listagem usa `LeadSummaryOut`, que exclui os campos `lp_html`, `site_analysis` e `social_profiles` para manter payloads pequenos.

---

### GET /api/leads/{lead_id}

Retorna um lead completo com todos os campos, incluindo `lp_html`, `site_analysis` e `social_profiles`.

**Path Parameters:**

| Parametro | Tipo | Descricao |
|-----------|------|-----------|
| `lead_id` | `int` | ID do lead. |

**Response `200 OK`:**

```json
{
  "id": 42,
  "public_id": "aBcDeFgHiJkLmNoP",
  "nome": "Clinica Sorriso",
  "telefone": "49999881234",
  "email": "contato@clinicasorriso.com.br",
  "website": "https://clinicasorriso.com.br",
  "endereco": "Rua das Flores, 123",
  "cidade": "Chapeco SC",
  "nicho": "dentista",
  "categoria": "Dentista",
  "rating": 4.5,
  "reviews_count": 87,
  "google_maps_url": "https://maps.google.com/?cid=...",
  "top_reviews": ["Otimo atendimento", "Recomendo"],
  "cnpj": "12.345.678/0001-90",
  "razao_social": "Clinica Sorriso Ltda",
  "porte": "ME",
  "cnae": "8630-5/04",
  "data_fundacao": "2018-03-15",
  "socios": ["Dr. Joao Silva"],
  "status": "enriched",
  "opportunity_score": 72,
  "opportunity_reasons": ["Sem SSL", "Site nao responsivo"],
  "site_analysis": {
    "has_ssl": false,
    "is_responsive": false,
    "has_cta": true,
    "pagespeed_score": 38,
    "word_count": 450
  },
  "social_profiles": {
    "instagram": "https://instagram.com/clinicasorriso",
    "facebook": "https://facebook.com/clinicasorriso"
  },
  "tech_stack": ["WordPress", "PHP"],
  "enrichment_sources": ["website", "pagespeed", "cnpj_ws"],
  "lp_html": "<!DOCTYPE html><html>...</html>",
  "job_id": 5,
  "created_at": "2026-04-10T14:30:00",
  "updated_at": "2026-04-10T15:45:00"
}
```

**Response `404 Not Found`:**

```json
{ "detail": "Lead not found" }
```

---

### GET /api/leads/{lead_id}/lp

Retorna o HTML da landing page ativa do lead como `text/html`. Util para renderizar em iframes.

**Path Parameters:**

| Parametro | Tipo | Descricao |
|-----------|------|-----------|
| `lead_id` | `int` | ID do lead. |

**Response `200 OK`:**

Content-Type: `text/html`

Corpo: HTML completo da landing page.

**Response `404 Not Found`:**

```json
{ "detail": "Landing page not generated yet" }
```

---

### GET /api/leads/p/{public_id}

Retorna um lead pelo `public_id` (nanoid de 16 caracteres). **Rota publica** -- nao requer autenticacao.

**Path Parameters:**

| Parametro | Tipo | Descricao |
|-----------|------|-----------|
| `public_id` | `string` | ID publico do lead (nanoid). |

**Response:** Mesmo formato de `GET /api/leads/{lead_id}`.

---

### GET /api/leads/p/{public_id}/lp

Retorna o HTML da landing page pelo `public_id`. **Rota publica** -- nao requer autenticacao. Usado nos links de outreach enviados via WhatsApp.

**Response:** Mesmo formato de `GET /api/leads/{lead_id}/lp`.

---

### PATCH /api/leads/{lead_id}

Atualiza campos do lead. Atualmente suporta apenas atualizacao de `status`.

**Path Parameters:**

| Parametro | Tipo | Descricao |
|-----------|------|-----------|
| `lead_id` | `int` | ID do lead. |

**Request Body:**

```json
{
  "status": "outreach_sent"
}
```

**Status validos:** `scraped`, `enriched`, `disqualified`, `lp_generated`, `outreach_ready`, `outreach_sent`, `responded`, `in_call`, `closed`, `delivered`, `scrape_failed`, `enrich_failed`, `generate_failed`, `outreach_failed`

**Response `200 OK`:** Lead completo atualizado (formato `LeadOut`).

**Response `404 Not Found`:**

```json
{ "detail": "Lead not found" }
```

**Response `422 Unprocessable Entity`:**

```json
{
  "detail": "Invalid status 'invalido'. Must be one of: ['closed', 'delivered', ...]"
}
```

---

### DELETE /api/leads/{lead_id}

Exclui um lead e todos os seus registros associados (outreach messages e landing pages via CASCADE).

**Path Parameters:**

| Parametro | Tipo | Descricao |
|-----------|------|-----------|
| `lead_id` | `int` | ID do lead. |

**Response `204 No Content`:** Sem corpo.

**Response `404 Not Found`:**

```json
{ "detail": "Lead not found" }
```

---

### GET /api/leads/filters

Retorna valores distintos de `nicho` e `cidade` existentes no banco. Usado para popular dropdowns de filtro no frontend.

**Response `200 OK`:**

```json
{
  "nichos": ["academia", "barbearia", "dentista", "restaurante"],
  "cidades": ["Chapeco SC", "Curitiba PR", "Florianopolis SC"]
}
```

---

### GET /api/leads/counts

Retorna contagem de leads por status. Usado nos headers das colunas do Kanban.

**Query Parameters:**

| Parametro | Tipo | Descricao |
|-----------|------|-----------|
| `nicho` | `string` | Filtro opcional por nicho. |
| `cidade` | `string` | Filtro opcional por cidade. |
| `score_min` | `int` | Filtro opcional por score minimo. |
| `search` | `string` | Busca opcional por nome ou telefone. |

**Response `200 OK`:**

```json
{
  "scraped": 45,
  "enriched": 32,
  "lp_generated": 18,
  "outreach_ready": 12,
  "outreach_sent": 8,
  "responded": 3,
  "closed": 1,
  "failed": 5
}
```

> **Nota:** Todos os status `*_failed` sao agrupados sob a chave `"failed"`.

---

### GET /api/leads/{lead_id}/messages

Retorna as mensagens de outreach (WhatsApp) associadas ao lead.

**Path Parameters:**

| Parametro | Tipo | Descricao |
|-----------|------|-----------|
| `lead_id` | `int` | ID do lead. |

**Response `200 OK`:**

```json
[
  {
    "id": 1,
    "lead_id": 42,
    "type": "initial",
    "message_text": "Ola! Vi que a Clinica Sorriso...",
    "whatsapp_link": "https://wa.me/5549999881234?text=Ola%21%20Vi%20que...",
    "sent_at": null,
    "response_received_at": null,
    "created_at": "2026-04-10T16:00:00"
  },
  {
    "id": 2,
    "lead_id": 42,
    "type": "followup_48h",
    "message_text": "Oi! Mandei uma mensagem...",
    "whatsapp_link": "https://wa.me/5549999881234?text=Oi%21...",
    "sent_at": null,
    "response_received_at": null,
    "created_at": "2026-04-10T16:00:00"
  },
  {
    "id": 3,
    "lead_id": 42,
    "type": "followup_final",
    "message_text": "Ultima tentativa...",
    "whatsapp_link": "https://wa.me/5549999881234?text=Ultima...",
    "sent_at": null,
    "response_received_at": null,
    "created_at": "2026-04-10T16:00:00"
  }
]
```

**Response `404 Not Found`:**

```json
{ "detail": "Lead not found" }
```

---

### GET /api/leads/{lead_id}/landing-pages

Retorna todas as versoes de landing pages do lead, ordenadas por versao decrescente (mais recente primeiro).

**Path Parameters:**

| Parametro | Tipo | Descricao |
|-----------|------|-----------|
| `lead_id` | `int` | ID do lead. |

**Response `200 OK`:**

```json
[
  {
    "id": 15,
    "public_id": "xYzAbCdEfGhIjKlM",
    "lead_id": 42,
    "version": 3,
    "is_active": true,
    "created_at": "2026-04-10T18:00:00"
  },
  {
    "id": 10,
    "public_id": "nOpQrStUvWxYzAbC",
    "lead_id": 42,
    "version": 2,
    "is_active": false,
    "created_at": "2026-04-09T14:30:00"
  },
  {
    "id": 5,
    "public_id": "dEfGhIjKlMnOpQrS",
    "lead_id": 42,
    "version": 1,
    "is_active": false,
    "created_at": "2026-04-08T10:15:00"
  }
]
```

**Response `404 Not Found`:**

```json
{ "detail": "Lead not found" }
```

---

### POST /api/leads/{lead_id}/landing-pages/{lp_id}/activate

Ativa uma landing page especifica e desativa todas as outras do mesmo lead. Tambem sincroniza o campo `lp_html` do lead com o HTML da LP ativada (compatibilidade retroativa).

**Path Parameters:**

| Parametro | Tipo | Descricao |
|-----------|------|-----------|
| `lead_id` | `int` | ID do lead. |
| `lp_id` | `int` | ID da landing page. |

**Response `200 OK`:**

```json
{
  "id": 10,
  "public_id": "nOpQrStUvWxYzAbC",
  "lead_id": 42,
  "version": 2,
  "is_active": true,
  "created_at": "2026-04-09T14:30:00"
}
```

**Response `404 Not Found`:**

```json
{ "detail": "Landing page not found" }
```

---

## Pipeline

### POST /api/pipeline/scrape

Inicia um job de scraping do Google Maps via Apify.

**Request Body:**

```json
{
  "nichos": ["dentista", "restaurante"],
  "cidades": ["Chapeco SC", "Curitiba PR"],
  "max_results": 50
}
```

| Campo | Tipo | Padrao | Descricao |
|-------|------|--------|-----------|
| `nichos` | `string[]` | `[]` (usa `TARGET_NICHES` do config) | Nichos para buscar. |
| `cidades` | `string[]` | `[]` (usa `TARGET_CITIES` do config) | Cidades para buscar. |
| `max_results` | `int` | `50` | Maximo de resultados por combinacao nicho+cidade. |

**Response `200 OK`:**

```json
{
  "id": 12,
  "type": "scrape",
  "status": "pending",
  "params": {
    "nichos": ["dentista"],
    "cidades": ["Chapeco SC"],
    "max_results": 50
  },
  "result_summary": {},
  "error_message": null,
  "started_at": null,
  "finished_at": null,
  "created_at": "2026-04-10T14:30:00"
}
```

**Response `409 Conflict`:**

```json
{ "detail": "Ja existe um job 'scrape' em execucao (#11)" }
```

---

### POST /api/pipeline/enrich

Inicia um job de enriquecimento de leads. Analisa websites, PageSpeed, CNPJ, etc.

**Request Body:**

```json
{
  "lead_ids": [],
  "skip_providers": ["apollo"],
  "force_providers": ["cnpj_ws"]
}
```

| Campo | Tipo | Padrao | Descricao |
|-------|------|--------|-----------|
| `lead_ids` | `int[]` | `[]` (todos com status `scraped`) | IDs especificos para enriquecer. |
| `skip_providers` | `string[]` | `[]` | Providers de enriquecimento para pular. |
| `force_providers` | `string[]` | `[]` | Providers para forcar execucao mesmo se ja executados. |

**Response `200 OK`:** Formato `JobOut` (mesmo do scrape).

**Response `409 Conflict`:** Se ja existe um job `enrich` rodando.

---

### POST /api/pipeline/generate

Inicia um job de geracao de landing pages via Claude API.

**Request Body:**

```json
{
  "lead_ids": [],
  "max_count": 50
}
```

| Campo | Tipo | Padrao | Descricao |
|-------|------|--------|-----------|
| `lead_ids` | `int[]` | `[]` (todos com status `enriched`) | IDs especificos. Leads com status `disqualified` sao ignorados. |
| `max_count` | `int` | `50` | Limite de leads a processar (quando `lead_ids` vazio). |

**Response `200 OK`:** Formato `JobOut`.

**Response `409 Conflict`:** Se ja existe um job `generate` rodando.

---

### POST /api/pipeline/outreach

Inicia um job de geracao de mensagens de outreach (WhatsApp).

**Request Body:**

```json
{
  "lead_ids": []
}
```

| Campo | Tipo | Padrao | Descricao |
|-------|------|--------|-----------|
| `lead_ids` | `int[]` | `[]` (todos com status `lp_generated`) | IDs especificos. Leads com status `disqualified` sao ignorados. |

**Response `200 OK`:** Formato `JobOut`.

**Response `409 Conflict`:** Se ja existe um job `outreach` rodando.

---

### GET /api/pipeline/status

Retorna o estado atual do pipeline: quantos leads estao elegiveis para cada etapa e quais jobs estao rodando.

**Response `200 OK`:**

```json
{
  "eligible_counts": {
    "scrape": 0,
    "enrich": 45,
    "generate": 32,
    "outreach": 18,
    "disqualified": 7
  },
  "running_jobs": ["enrich"]
}
```

| Campo | Descricao |
|-------|-----------|
| `eligible_counts.scrape` | Sempre `0` (scrape nao depende de leads existentes). |
| `eligible_counts.enrich` | Leads com status `scraped`. |
| `eligible_counts.generate` | Leads com status `enriched`. |
| `eligible_counts.outreach` | Leads com status `lp_generated`. |
| `eligible_counts.disqualified` | Leads com status `disqualified`. |
| `running_jobs` | Tipos de jobs atualmente em execucao (`scrape`, `enrich`, `generate`, `outreach`). |

---

## Jobs

### GET /api/jobs

Lista jobs com paginacao, ordenados por data de criacao (mais recente primeiro).

**Query Parameters:**

| Parametro | Tipo | Padrao | Descricao |
|-----------|------|--------|-----------|
| `page` | `int` | `1` | Pagina. |
| `per_page` | `int` | `20` | Itens por pagina (1-100). |

**Response `200 OK`:**

```json
{
  "items": [
    {
      "id": 12,
      "type": "scrape",
      "status": "done",
      "params": {
        "nichos": ["dentista"],
        "cidades": ["Chapeco SC"],
        "max_results": 50
      },
      "result_summary": {
        "created": 23,
        "total_scraped": 25,
        "errors": ["Lead Joao da Silva: duplicate phone"]
      },
      "error_message": null,
      "started_at": "2026-04-10T14:30:05",
      "finished_at": "2026-04-10T14:32:45",
      "created_at": "2026-04-10T14:30:00"
    }
  ],
  "total": 45,
  "page": 1,
  "per_page": 20
}
```

**Status possiveis do job:** `pending`, `running`, `done`, `done_with_errors`, `failed`.

**Campos do `result_summary` por tipo de job:**

| Tipo | Campos |
|------|--------|
| `scrape` | `created`, `total_scraped`, `errors` |
| `enrich` | `enriched`, `total`, `errors` |
| `generate` | `generated`, `total`, `errors` |
| `outreach` | `messaged`, `total`, `errors` |

---

### GET /api/jobs/{job_id}

Retorna detalhes de um job especifico.

**Path Parameters:**

| Parametro | Tipo | Descricao |
|-----------|------|-----------|
| `job_id` | `int` | ID do job. |

**Response `200 OK`:** Formato `JobOut`.

**Response `404 Not Found`:**

```json
{ "detail": "Job not found" }
```

---

### GET /api/jobs/{job_id}/stream

Conecta a um stream SSE (Server-Sent Events) para acompanhar o progresso de um job em tempo real. Veja a documentacao completa em [SSE Events](./sse-events.md).

**Path Parameters:**

| Parametro | Tipo | Descricao |
|-----------|------|-----------|
| `job_id` | `int` | ID do job. |

**Response `200 OK`:**

Content-Type: `text/event-stream`

Eventos enviados no formato SSE:

```
data: {"type": "started", "job_id": 12}

data: {"type": "progress", "current": 5, "total": 25}

data: {"type": "done", "summary": {"created": 23, "total_scraped": 25, "errors": []}}
```

**Response `404 Not Found`:**

```json
{ "detail": "Job not found" }
```

---

## Dashboard

### GET /api/dashboard/stats

Retorna estatisticas agregadas para o dashboard.

**Response `200 OK`:**

```json
{
  "total_leads": 156,
  "leads_by_status": {
    "scraped": 45,
    "enriched": 32,
    "lp_generated": 18,
    "outreach_ready": 12,
    "outreach_sent": 8,
    "responded": 3,
    "in_call": 2,
    "closed": 1,
    "delivered": 1,
    "failed": 5
  },
  "avg_score": 58.74,
  "total_jobs": 45,
  "conversion_rate": 1.28
}
```

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `total_leads` | `int` | Total de leads no banco. |
| `leads_by_status` | `dict[str, int]` | Contagem por status. Status `*_failed` sao agrupados em `"failed"`. |
| `avg_score` | `float \| null` | Media do `opportunity_score`. `null` se nenhum lead tem score. |
| `total_jobs` | `int` | Total de jobs (todos os tipos e status). |
| `conversion_rate` | `float \| null` | Percentual de leads em `closed` + `delivered` sobre o total. `null` se nao ha leads. |

---

## Settings

### GET /api/settings

Retorna configuracoes da aplicacao relevantes para o frontend. Somente leitura.

**Response `200 OK`:**

```json
{
  "target_niches": [
    "dentista", "restaurante", "salao de beleza", "clinica estetica",
    "pet shop", "academia", "barbearia", "clinica veterinaria",
    "pizzaria", "loja de roupas"
  ],
  "target_cities": [
    "Chapeco SC", "Florianopolis SC", "Joinville SC",
    "Curitiba PR", "Cascavel PR"
  ],
  "min_rating": 3.0,
  "max_results_per_search": 50,
  "opportunity_score_threshold": 40,
  "business_name": "Studio Digital",
  "your_name": "Seu Nome"
}
```

---

## Health

### GET /api/health

Health check. **Rota publica** -- nao requer autenticacao.

**Response `200 OK`:**

```json
{ "status": "ok" }
```

---

## Rotas Publicas

As seguintes rotas nao requerem autenticacao no backend:

| Rota | Descricao |
|------|-----------|
| `GET /api/health` | Health check |
| `GET /api/leads/p/{public_id}` | Lead por ID publico |
| `GET /api/leads/p/{public_id}/lp` | Landing page por ID publico |
| `GET /docs` | Swagger UI |
| `GET /openapi.json` | Schema OpenAPI |

---

## Codigos de Status HTTP

| Codigo | Significado |
|--------|-------------|
| `200` | Sucesso. |
| `204` | Sucesso sem corpo (usado em DELETE). |
| `401` | Nao autenticado -- sessao ausente, invalida ou expirada. |
| `404` | Recurso nao encontrado. |
| `409` | Conflito -- ja existe um job do mesmo tipo rodando. |
| `422` | Erro de validacao (status invalido, parametros invalidos). |

---

## Paginacao

Endpoints paginados (`GET /api/leads`, `GET /api/jobs`) seguem o padrao:

**Request:** `?page=2&per_page=20`

**Response:**

```json
{
  "items": [...],
  "total": 156,
  "page": 2,
  "per_page": 20
}
```

O offset e calculado como `(page - 1) * per_page`.

---

## Schemas

### LeadSummaryOut

Usado em listagens. Exclui `lp_html`, `site_analysis` e `social_profiles`.

```
id: int
public_id: string
nome: string
telefone: string | null
email: string | null
website: string | null
endereco: string | null
cidade: string | null
nicho: string | null
categoria: string | null
rating: float | null
reviews_count: int
google_maps_url: string | null
top_reviews: string[]
cnpj: string | null
razao_social: string | null
porte: string | null
cnae: string | null
data_fundacao: date | null
socios: any[]
status: string
opportunity_score: int | null
opportunity_reasons: string[]
tech_stack: any[]
enrichment_sources: any[]
job_id: int | null
created_at: datetime
updated_at: datetime
```

### LeadOut

Usado em detalhes. Inclui todos os campos de `LeadSummaryOut` mais:

```
site_analysis: dict
social_profiles: dict
lp_html: string | null
```

### JobOut

```
id: int
type: string           // "scrape" | "enrich" | "generate" | "outreach"
status: string         // "pending" | "running" | "done" | "done_with_errors" | "failed"
params: dict
result_summary: dict
error_message: string | null
started_at: datetime | null
finished_at: datetime | null
created_at: datetime
```

### LandingPageOut

```
id: int
public_id: string
lead_id: int
version: int
is_active: bool
created_at: datetime
```

### OutreachMessageOut

```
id: int
lead_id: int
type: string              // "initial" | "followup_48h" | "followup_final"
message_text: string
whatsapp_link: string | null
sent_at: datetime | null
response_received_at: datetime | null
created_at: datetime
```

### DashboardStats

```
total_leads: int
leads_by_status: dict[str, int]
avg_score: float | null
total_jobs: int
conversion_rate: float | null
```

### PipelineStatusOut

```
eligible_counts: dict[str, int]
running_jobs: string[]
```
