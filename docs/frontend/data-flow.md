# Fluxo de Dados do Frontend

Documentação técnica do API client, tipos, funções de API, autenticação e tratamento de erros.

---

## 1. API Client

O módulo `frontend/src/lib/api.ts` centraliza toda comunicação com o backend. A base URL é definida pela variável de ambiente `NEXT_PUBLIC_API_URL` (default: `http://localhost:8000`).

### `fetchAPI<T>(path, options?)`

Função genérica que encapsula `fetch` com:

1. **Headers automáticos:** adiciona `Content-Type: application/json` e, se disponível, `Authorization: Bearer {token}`.
2. **Token de sessão:** extraído do cookie `better-auth.session_data` (base64-encoded JSON) ou fallback para `better-auth.session_token`. A função `getSessionToken()` tenta ambos os formatos.
3. **Redirect em 401:** qualquer resposta `401 Unauthorized` aciona `forceLogout()`, que limpa cookies de sessão e redireciona para `/login` via `window.location.replace()`.
4. **Guard contra redirects paralelos:** a variável `redirectingToLogin` (módulo-level) garante que múltiplos fetches falhando com 401 simultaneamente gerem apenas um redirect.
5. **Parsing de erro:** respostas não-ok (exceto 401) lançam `Error` com o texto do body.

```ts
async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getSessionToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...options?.headers as Record<string, string>,
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${API}${path}`, { ...options, headers });
  if (res.status === 401) {
    forceLogout();
    throw new Error("Sessão expirada");
  }
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API error ${res.status}: ${error}`);
  }
  return res.json();
}
```

### `streamJob(id, onEvent)`

Caso especial que **não usa `fetchAPI`**. Implementa SSE manualmente via `fetch` + `ReadableStream`:

1. Faz `fetch` para `GET /api/jobs/{id}/stream` com header `Authorization`.
2. Lê o body como stream, parseia linhas `data: {...}` do SSE.
3. Chama `onEvent({ type, message })` para cada evento.
4. Fecha automaticamente quando recebe `type: "done"` ou `type: "error"`.
5. Retorna uma função de cleanup que aborta a conexão.
6. Trata 401 chamando `forceLogout()`.

---

## 2. Type Definitions

Todas as interfaces ficam em `frontend/src/lib/types.ts`.

### Lead

```ts
interface Lead {
  id: number;
  public_id: string;           // UUID público para URLs de LP
  nome: string;
  telefone: string | null;
  website: string | null;
  endereco: string | null;
  cidade: string | null;
  nicho: string | null;
  categoria: string | null;
  rating: number | null;       // Nota do Google Maps (1-5)
  reviews_count: number;
  google_maps_url: string | null;
  top_reviews: string[];
  status: string;              // scraped, enriched, lp_generated, etc.
  opportunity_score: number | null;  // 0-100 (maior = pior site = mais oportunidade)
  opportunity_reasons: string[];     // Lista de gaps detectados
  site_analysis: Record<string, unknown>;  // Dados brutos do diagnóstico
  social_profiles: Record<string, unknown>;
  lp_html: string | null;     // Indica se LP foi gerada (conteúdo servido via endpoint)
  email: string | null;
  cnpj: string | null;
  razao_social: string | null;
  porte: string | null;
  cnae: string | null;
  data_fundacao: string | null;
  socios: Array<{ nome: string }>;
  tech_stack: Array<{ name: string; category: string }>;
  enrichment_sources: Array<{
    provider: string;          // Nome do provider (ex: "website_crawler")
    status: string;            // "ok", "skipped", "error"
    timestamp: string;
    error?: string;
  }>;
  job_id: number | null;
  created_at: string;          // ISO 8601
  updated_at: string;
}
```

### LeadListResponse

```ts
interface LeadListResponse {
  items: Lead[];
  total: number;
  page: number;
  per_page: number;
}
```

### Job

```ts
interface Job {
  id: number;
  type: string;                // "scrape", "enrich", "generate", "outreach"
  status: string;              // "pending", "running", "done", "done_with_errors", "failed"
  params: Record<string, unknown>;
  result_summary: Record<string, unknown>;  // { total, created/enriched/generated/messaged, errors[] }
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}
```

### JobListResponse

```ts
interface JobListResponse {
  items: Job[];
  total: number;
  page: number;
  per_page: number;
}
```

### DashboardStats

```ts
interface DashboardStats {
  total_leads: number;
  leads_by_status: Record<string, number>;  // ex: { scraped: 10, enriched: 5 }
  avg_score: number | null;
  total_jobs: number;
  conversion_rate: number | null;           // Percentual de leads que chegaram a "closed"
}
```

### Settings

```ts
interface Settings {
  target_niches: string[];     // Nichos sugeridos no ScrapeModal
  target_cities: string[];     // Cidades sugeridas no ScrapeModal
  min_rating: number;
  max_results_per_search: number;
  opportunity_score_threshold: number;
  business_name: string;
  your_name: string;
}
```

### OutreachMessage

```ts
interface OutreachMessage {
  id: number;
  lead_id: number;
  type: string;                // "initial", "followup_48h", "final"
  message_text: string;
  whatsapp_link: string | null;  // URL wa.me com mensagem pre-filled
  sent_at: string | null;
  response_received_at: string | null;
  created_at: string;
}
```

### LandingPage

```ts
interface LandingPage {
  id: number;
  public_id: string;
  lead_id: number;
  version: number;             // Incrementa a cada regeneração
  is_active: boolean;          // Apenas uma LP é ativa por lead
  created_at: string;
}
```

### NivelScore / NivelKey / ServiceLevels

```ts
interface NivelScore {
  score: number;               // 0-100
  sinais: string[];            // Sinais detectados no site
  oportunidades: string[];     // Oportunidades para este nível de serviço
  justificativa: string;       // Justificativa da IA
}

type NivelKey = "lp" | "automacao_basica" | "mapa_automacoes" | "vertical_os";

interface ServiceLevels {
  lp: NivelScore;
  automacao_basica: NivelScore;
  mapa_automacoes: NivelScore;
  vertical_os: NivelScore;
  nivel_recomendado: NivelKey;
  qualificado: boolean;
  motivo_desqualificacao: string | null;
  resumo_executivo: string;
}
```

### EnrichRequest

```ts
interface EnrichRequest {
  lead_ids?: number[];         // Se fornecido, enriquece leads específicos
  skip_providers?: string[];   // Providers a pular (ex: ["apollo", "email_discoverer"])
  force_providers?: string[];  // Providers a forçar mesmo se já rodaram
}
```

---

## 3. API Functions

Todas exportadas de `api.ts`. Cada função retorna uma Promise tipada.

### Leads

| Função | Método | Endpoint | Retorno | Descrição |
|--------|--------|----------|---------|-----------|
| `getLeads(params?)` | GET | `/api/leads?{qs}` | `LeadListResponse` | Lista paginada de leads. Aceita `status`, `nicho`, `cidade`, `score_min`, `search`, `order_by`, `page`, `per_page`. |
| `getLeadFilters()` | GET | `/api/leads/filters` | `{ nichos: string[]; cidades: string[] }` | Valores únicos de nicho e cidade para os filtros do Kanban. |
| `getLeadCounts(params?)` | GET | `/api/leads/counts?{qs}` | `Record<string, number>` | Contagem de leads agrupada por status, respeitando filtros. |
| `getLead(id)` | GET | `/api/leads/{id}` | `Lead` | Busca um lead por ID. |
| `updateLead(id, data)` | PATCH | `/api/leads/{id}` | `Lead` | Atualiza campos do lead (ex: `{ status: "outreach_sent" }`). |
| `deleteLead(id)` | DELETE | `/api/leads/{id}` | `Response` | Remove um lead. Implementação manual (não usa `fetchAPI`). |
| `getLeadLpUrl(id)` | -- | -- | `string` | Gera URL direta para o HTML da LP: `{API}/api/leads/{id}/lp`. Não faz fetch. |
| `getLeadByPublicId(publicId)` | GET | `/api/leads/p/{publicId}` | `Lead` | Busca lead pelo ID público (usado na page de LP pública). |
| `getLeadLpUrlByPublicId(publicId)` | -- | -- | `string` | Gera URL: `{API}/api/leads/p/{publicId}/lp`. Não faz fetch. |
| `getLeadMessages(leadId)` | GET | `/api/leads/{leadId}/messages` | `OutreachMessage[]` | Lista mensagens de outreach do lead. |

### Landing Pages

| Função | Método | Endpoint | Retorno | Descrição |
|--------|--------|----------|---------|-----------|
| `getLeadLandingPages(leadId)` | GET | `/api/leads/{leadId}/landing-pages` | `LandingPage[]` | Lista todas as versões de LP de um lead. |
| `activateLandingPage(leadId, lpId)` | POST | `/api/leads/{leadId}/landing-pages/{lpId}/activate` | `LandingPage` | Define uma versão específica como ativa. |

### Dashboard

| Função | Método | Endpoint | Retorno | Descrição |
|--------|--------|----------|---------|-----------|
| `getDashboardStats()` | GET | `/api/dashboard/stats` | `DashboardStats` | Estatísticas gerais: total de leads, score médio, total de jobs, taxa de conversão, leads por status. |

### Jobs

| Função | Método | Endpoint | Retorno | Descrição |
|--------|--------|----------|---------|-----------|
| `getJobs(params?)` | GET | `/api/jobs?{qs}` | `JobListResponse` | Lista paginada de jobs. |
| `getJob(id)` | GET | `/api/jobs/{id}` | `Job` | Busca um job por ID. |
| `streamJob(id, onEvent)` | GET (SSE) | `/api/jobs/{id}/stream` | cleanup function | Stream de progresso em tempo real. Retorna função para abortar. |

### Pipeline

| Função | Método | Endpoint | Retorno | Descrição |
|--------|--------|----------|---------|-----------|
| `runScrape(params)` | POST | `/api/pipeline/scrape` | `Job` | Inicia scraping. Params: `{ nichos, cidades, max_results }`. |
| `runEnrich(params)` | POST | `/api/pipeline/enrich` | `Job` | Inicia enriquecimento. Params: `EnrichRequest`. |
| `runGenerate(params)` | POST | `/api/pipeline/generate` | `Job` | Inicia geração de LPs. Params: `{ lead_ids?, max_count? }`. |
| `runOutreach(params)` | POST | `/api/pipeline/outreach` | `Job` | Inicia geração de outreach. Params: `{ lead_ids? }`. |
| `getPipelineStatus()` | GET | `/api/pipeline/status` | `{ eligible_counts, running_jobs }` | Retorna contagem de leads elegíveis por fase e lista de fases com jobs em execução. |

### Settings

| Função | Método | Endpoint | Retorno | Descrição |
|--------|--------|----------|---------|-----------|
| `getSettings()` | GET | `/api/settings` | `Settings` | Configurações do sistema (nichos/cidades alvo, thresholds, dados do usuário). |

---

## 4. Auth Client

Definido em `frontend/src/lib/auth-client.ts`:

```ts
import { createAuthClient } from "better-auth/react";
export const authClient = createAuthClient();
```

O [Better Auth](https://www.better-auth.com/) client é criado com configuração default, o que significa:

- **Base URL:** aponta para o próprio frontend (Next.js) em `/api/auth/*` (proxy para o backend ou handler direto).
- **Sessão:** gerenciada via cookies (`better-auth.session_token` e `better-auth.session_data`).
- **Cookie cache:** o cookie `session_data` (não-HttpOnly) contém a sessão serializada em base64, permitindo que o `getSessionToken()` em `api.ts` extraia o token sem fazer uma request adicional.

### Fluxo de autenticação

1. **Login:** `LoginPage` chama `authClient.signIn.email({ email, password })`. Em caso de sucesso, redireciona para `/`.
2. **Sessão para API:** `fetchAPI` chama `getSessionToken()` a cada request, extrai o token do cookie, e envia como `Authorization: Bearer {token}`.
3. **Logout:** `SignOutButton` chama `authClient.signOut()`, redireciona para `/login`, e faz `router.refresh()`.
4. **Sessão expirada:** se qualquer API retornar 401, `forceLogout()` limpa cookies `better-auth` e redireciona para `/login`.

---

## 5. Error Handling

### Propagação de erros

O fluxo de erro segue este caminho:

```
Backend (HTTP status code)
  -> fetchAPI (throw Error)
    -> Componente (try/catch)
      -> Estado local (error state ou console.error)
```

**Padrões observados nos componentes:**

1. **PipelineControls:** captura o erro e exibe em `error` state com UI de alerta inline.
2. **KanbanBoard / KanbanColumn:** erros em `getLeads`, `getLeadCounts` são logados via `console.error`. A UI mostra "Nenhum lead" ou continua com dados parciais.
3. **LeadSheet:** ações (enrich, generate, outreach) capturam erros silenciosamente (`catch {}`) -- o job pode estar processando em background.
4. **Dashboard / Jobs:** erros não são tratados explicitamente -- um fetch falhando deixa o state null, exibindo loading infinito.

### Resiliência

- `getLeadFilters()`, `getLeadMessages()`, `getLeadLandingPages()` frequentemente usam `.catch(() => fallback)` para não bloquear o carregamento principal em caso de falha.
- `Promise.all` com `catch` individual: o `LeadSheet` faz `Promise.all([getLeadMessages(...).catch(...), getLeadLandingPages(...).catch(...)])` para carregar dados secundários sem bloquear.

### Rollback otimista

No `KanbanBoard`, o drag-and-drop faz update otimista de contagens. Se `updateLead()` falhar:

```ts
// Rollback counts
setCounts((prev) => ({
  ...prev,
  [sourceStatus]: (prev[sourceStatus] || 0) + 1,
  [newStatus]: Math.max(0, (prev[newStatus] || 0) - 1),
}));
```

---

## 6. ENRICH_PROVIDERS

Registry estático definido em `types.ts`, usado pelo `PipelineControls` para renderizar checkboxes de providers de enriquecimento:

```ts
export const ENRICH_PROVIDERS: EnrichProvider[] = [
  { name: "website_crawler",   display_name: "Website Crawler",       cost: "free" },
  { name: "schema_extractor",  display_name: "Schema.org Extractor",  cost: "free" },
  { name: "tech_stack",        display_name: "Tech Stack Detector",   cost: "free" },
  { name: "cnpj_enricher",     display_name: "CNPJ (BrasilAPI)",      cost: "free" },
  { name: "email_discoverer",  display_name: "Email Discoverer",      cost: "freemium" },
  { name: "apollo",            display_name: "Apollo.io",             cost: "freemium" },
];
```

### Uso no PipelineControls

1. Todos os providers iniciam habilitados: `new Set(ENRICH_PROVIDERS.map(p => p.name))`.
2. O usuário pode desabilitar providers individuais via checkboxes no `ConfirmModal` da fase "enrich".
3. Providers com `cost: "freemium"` exibem badge visual amarelo.
4. Ao confirmar, providers desabilitados são enviados como `skip_providers` no body do POST:

```ts
const skip = ENRICH_PROVIDERS
  .filter((p) => !enabledProviders.has(p.name))
  .map((p) => p.name);
handleRun(pendingPhase, skip.length > 0 ? { skip_providers: skip } : {});
```
