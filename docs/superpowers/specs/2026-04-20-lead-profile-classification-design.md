# Lead Profile Classification — Design

**Data:** 2026-04-20
**Status:** Draft (aguardando aprovação do usuário)
**Spec:** 1 de 3 do ciclo "Growth Loops" (spec 2: LP Conversion Tracking; spec 3: LP Public Reach/SEO)
**Referências:**
- `operacao-20k-plano-completo.md` — matriz original de 7 perfis de lead (consolidada aqui para 5)
- `CLAUDE.md` — arquitetura do orchestrator de enriquecimento e padrão de jobs/SSE
- `docs/superpowers/specs/2026-04-10-smart-enrichment-pipeline-design.md` — padrão de providers

---

## 1. Visão geral

**Objetivo:** classificar cada lead do SDR Machine em um **perfil** (5 buckets) e um **nicho canônico** (15 buckets), para que outreach, priorização no kanban e benchmark futuro operem em cima de taxonomia consistente.

**Por que agora:** 100+ leads na fila de enriquecimento + listas de CRMs externos estão prontos para entrar no funil, mas sem perfil/nicho padronizados, não dá para priorizar, escolher template de mensagem, nem medir resposta por segmento. Também é pré-requisito das specs 2 (conversion tracking) e 3 (SEO/branding da LP).

**Onde encaixa no código:**
- Novo módulo puro `backend/app/pipeline/enrichment/classifier.py` (lógica independente, testável isolada)
- Novo provider `ClassificationProvider` em `backend/app/pipeline/enrichment/providers/classification.py` (integra no orchestrator, roda pós-scoring)
- Novo endpoint `POST /api/pipeline/classify` (background job para batch) e `POST /api/leads/{id}/reclassify` (manual síncrono)
- Novos campos no model `Lead` (migration Alembic, tudo nullable)
- Mudanças no frontend: kanban, lead app, dashboard e nova rota de revisão de nichos

**Fora do escopo:**
- Tracking de conversão na LP (spec 2)
- SEO/branding/URL amigável da LP (spec 3)
- Benchmark dashboard por nicho × cidade (depende de spec 2 gerar dado de resposta primeiro)
- Dogfooding da própria SDR Machine em estética/advocacia/indústria (operação, não feature)
- Sistema de toast notifications global (escopo separado; essa spec usa padrões inline existentes)
- Observabilidade estruturada (metrics/traces) — fica em spec própria

**Dependências externas:**
- LLM API (mesmo `settings.llm_model` já configurado; Haiku preferível por custo)
- Biblioteca `tenacity` para retries (adicionar ao `requirements.txt`)
- Nenhuma dependência de serviço novo

**Princípio de design dominante:** o pipeline não pode travar por bug previsível. Cada etapa tem fallback; cada lead é isolado; batch tem circuit breaker. Resiliência é critério de aceitação, não afterthought.

---

## 2. Modelo de dados

### 2.1 Enums

Arquivo sugerido: `backend/app/models/enums.py` (criar ou estender).

```python
class LeadProfile(str, Enum):
    HOT_NO_SITE = "hot_no_site"
    HOT_BAD_SITE = "hot_bad_site"
    WARM = "warm"
    COLD = "cold"
    DISQUALIFIED = "disqualified"

class NichoCanonico(str, Enum):
    DENTISTA = "dentista"
    ESTETICA = "estetica"
    SALAO_BARBEARIA = "salao_barbearia"
    RESTAURANTE = "restaurante"
    PETSHOP_VET = "petshop_vet"
    ACADEMIA = "academia"
    CONTABILIDADE = "contabilidade"
    IMOBILIARIA = "imobiliaria"
    LOJA_ROUPAS = "loja_roupas"
    AUTO_ESCOLA = "auto_escola"
    ADVOCACIA = "advocacia"
    INDUSTRIA = "industria"
    CLINICA_MEDICA = "clinica_medica"
    ESCOLA_CURSO = "escola_curso"
    OUTROS = "outros"

class NichoSource(str, Enum):
    APIFY_CATEGORY = "apify_category"     # direto do scrape
    FUZZY_MATCH = "fuzzy_match"           # keyword/difflib bateu
    LLM_INFERRED = "llm_inferred"         # classificador LLM
    MANUAL = "manual"                     # editado pelo usuário
    FAILED = "failed"                     # fallback quando tudo falhou

class PacoteSugerido(str, Enum):
    ESSENCIAL = "essencial"
    PROFISSIONAL = "profissional"
    PREMIUM = "premium"
    SKIP = "skip"

class Prioridade(str, Enum):
    MAXIMA = "maxima"
    ALTA = "alta"
    MEDIA = "media"
    BAIXA = "baixa"
    PULAR = "pular"
```

### 2.2 Novos campos em `Lead`

Todos nullable + default NULL para migration segura.

| Campo | Tipo | Index | Default | Observação |
|---|---|---|---|---|
| `perfil_lead` | `Enum(LeadProfile)` | ✅ | NULL | Armazenado para filtro SQL |
| `nicho_canonico` | `Enum(NichoCanonico)` | ✅ | NULL | Armazenado para filtro SQL |
| `nicho_source` | `Enum(NichoSource)` | — | NULL | Auditoria |
| `nicho_confidence` | `Float` | — | NULL | 0-1 |
| `pacote_sugerido` | `Enum(PacoteSugerido)` | ✅ | NULL | Derivado do perfil |
| `prioridade` | `Enum(Prioridade)` | ✅ | NULL | Derivado do perfil |
| `classification_hash` | `String(32)` | — | NULL | MD5 dos inputs usados — idempotência |
| `classified_at` | `DateTime` | — | NULL | Timestamp da última classificação |
| `has_instagram` | `Boolean` | — | NULL | `True` se scrape retornou link de Instagram no Google Maps. Extração **nova** no `scraper.py` (hoje esse dado está no payload mas não populado em coluna dedicada). Leads antigos ficam NULL até re-scrape — fallback seguro pela Seção 3.3 trata `None` como `False` |

### 2.3 Migration

Alembic autogen + ajuste manual para garantir:
- Nenhum `NOT NULL` nem default não-NULL (executa em milissegundos mesmo com milhões de leads)
- Zero backfill na migration — backfill vive no batch job (que tem circuit breaker)
- Rollback seguro: `downgrade()` faz apenas `DROP COLUMN`, não perde dados pré-existentes

### 2.4 Idempotência

```python
classification_hash = md5(
    f"{has_website}|{score}|{rating}|{review_count}|"
    f"{has_ssl}|{has_analytics}|{has_chatbot}|{has_instagram}|"
    f"{nicho_raw}|{nome}"
)
```

Antes de re-classificar, compara hash armazenado com o atual:
- **Igual** → skip (retorna `skipped` no ProviderResult)
- **Diferente** → re-roda perfil (barato). Nicho só se `nicho_source == "failed"` OU `(nicho_source == "llm_inferred" AND nicho_confidence < 0.5)` OU `force=True`

### 2.5 Por que armazenar `pacote_sugerido` e `prioridade`?

Ambos são 100% derivados de `perfil_lead` (mapeamento 1:1 fixo). Calculáveis on-the-fly. Armazenados porque:
- Queries como "todos HOT em São Paulo ainda sem outreach" viram `WHERE prioridade IN ('maxima','alta') AND cidade='SP' AND status='enriched'` — SQL direto, index-friendly
- Frontend não precisa resolver mapeamento a cada render
- Custo: 2 colunas extras, atualizadas em transação junto com `perfil_lead`

---

## 3. Módulo classificador (lógica pura)

### 3.1 Localização e princípios

Arquivo principal: `backend/app/pipeline/enrichment/classifier.py`

Arquivos de suporte:
- `classifier_rules.py` — thresholds e dicionário de aliases de nicho (externalizados para tuning sem tocar lógica)
- `classifier_prompts.py` — prompt do LLM e exemplos few-shot

Princípios:
- **Sem dependência de DB ou sessão** — recebe dict, devolve dataclass. Testável isolado
- **Nunca levanta exceção** — qualquer falha vira fallback interno (`DISQUALIFIED`/`OUTROS` com `source=failed`)
- Mesmo módulo usado pelo provider (fluxo normal) e pelo batch job (backlog)

### 3.2 Interface principal

```python
@dataclass
class ClassificationResult:
    perfil_lead: LeadProfile
    nicho_canonico: NichoCanonico
    nicho_source: NichoSource
    nicho_confidence: float
    pacote_sugerido: PacoteSugerido
    prioridade: Prioridade
    classification_hash: str
    error_reason: Optional[str] = None  # preenchido quando source=failed

def classify(lead_data: dict, *, llm_client=None) -> ClassificationResult:
    """
    Input:  dados consolidados do lead (scrape + enrichment)
    Output: perfil + nicho + derivados + source + confidence

    Nunca levanta exceção — falhas viram fallback (outros/failed).
    """
```

`llm_client` é injetável (permite mock em testes e cliente real em produção).

**`lead_data` dict consolidado — origem de cada campo:**

| Campo no `lead_data` | Origem |
|---|---|
| `has_website` | Derivado de `lead.website` (bool(website)) |
| `score` | `lead.opportunity_score` |
| `rating`, `review_count` | Campos diretos do Lead (scrape) |
| `has_ssl`, `has_analytics`, `has_chatbot`, `has_whatsapp_cta` | Extraídos de `lead.site_analysis` (JSON gerado pelo `WebsiteCrawlerProvider`) |
| `has_instagram` | Novo campo na Lead (ver 2.2) |
| `nicho_raw` | `lead.nicho` (texto livre como veio) |
| `nome`, `descricao` | Campos diretos do Lead |
| `reviews` | Sample de até 3 reviews para contexto do LLM |

Se algum desses campos estiver ausente, fallbacks da Seção 3.3 cobrem.

### 3.3 Regras de perfil — cascata determinística

Ordem importa (primeiro match vence):

```
1. DISQUALIFIED se:
   - rating < 3.0, OU
   - (review_count < 3 AND sem telefone), OU
   - dados críticos completamente ausentes (sem nome E sem telefone E sem endereço)

2. HOT_NO_SITE se:
   - has_website == False AND
   - rating >= 4.0 AND
   - review_count >= 30

3. HOT_BAD_SITE se:
   - has_website == True AND
   - score >= 60 AND
   - (has_instagram == True OR review_count >= 30)

4. COLD se:
   - has_website == True AND
   - score < 20 AND
   - has_ssl AND
   - has_analytics AND
   - (has_chatbot OR has_whatsapp_cta)

5. WARM — catch-all dos casos que não caíram acima
```

**Defaults seguros para dados faltando:**
- `has_website is None` → trata como `False`
- `score is None` → trata como `50` (neutro; não vira HOT_BAD_SITE nem COLD)
- `rating is None` → trata como `0`, só desqualifica se `review_count` também ausente
- `review_count is None` → trata como `0`
- `has_instagram is None` → trata como `False`
- Demais flags booleanas `None` → tratar como `False`

### 3.4 Inferência de nicho — 3 camadas

```
Camada 1 — Direct match
  Se nicho_raw (do scrape/CRM) ∈ aliases curados → match direto.
  Exemplos: "Dentist" → dentista; "Pizzaria" → restaurante.
  source: APIFY_CATEGORY | confidence: 1.0

Camada 2 — Fuzzy match (keyword + difflib.get_close_matches)
  Keywords curadas por bucket. Ex "dentista" casa com:
    ["odonto", "clinica odontologica", "sorriso", "ortodontia", "implante dentario", ...]
  Match se ratio >= 0.75 em algum alias.
  source: FUZZY_MATCH | confidence: ratio do difflib

Camada 3 — LLM fallback (só se 1 e 2 falharem)
  Modelo: settings.llm_model (preferencialmente Haiku)
  Input: nome + nicho_raw + descrição + 1 review (200-300 tokens de contexto)
  Output: bucket + confidence via tool-use com enum fechado
  source: LLM_INFERRED | confidence: valor retornado

Se LLM falha/timeout/JSON inválido/valor fora do enum:
  → NichoCanonico.OUTROS | source: FAILED | confidence: 0
```

O prompt do LLM usa tool-use com JSON schema forçando enum válido. Mesmo assim, validação defensiva pós-resposta: se valor não bater, cai em fallback.

### 3.5 Mapeamento perfil → derivados (tabela fixa)

| Perfil | Pacote sugerido | Prioridade |
|---|---|---|
| HOT_NO_SITE | `essencial` (ou `profissional`) | `maxima` |
| HOT_BAD_SITE | `profissional` (ou `premium`) | `alta` |
| WARM | `essencial` | `media` |
| COLD | `skip` (ou micro-oferta `premium`) | `baixa` |
| DISQUALIFIED | `skip` | `pular` |

Implementado como dicionário constante no módulo. Mudança de regra de negócio acontece em um único lugar.

---

## 4. Integração com orchestrator

### 4.1 Novo provider

Arquivo: `backend/app/pipeline/enrichment/providers/classification.py`

Segue o padrão dos 6 providers existentes (`CnpjProvider`, `WebsiteCrawlerProvider`, etc). Implementa a interface `BaseProvider`:

```python
class ClassificationProvider(BaseProvider):
    name = "classification"
    phase = Phase.CLASSIFICATION
    requires = []                                          # roda com dados parciais
    optional = ["website_crawler", "schema_org",
                "tech_stack", "cnpj"]                      # consome se disponíveis
```

### 4.2 Nova fase no orchestrator

Orchestrator hoje tem 4 fases (Discovery → Crawl → Contact → Scoring). Adicionar **Phase.CLASSIFICATION** após Scoring:

```
Discovery (CNPJ)
  → Crawl (website, schema.org, tech stack)
  → Contact (email, Apollo)
  → Scoring
  → Classification  ← nova fase, sempre última
```

Razão: classificador consome `score` (de Scoring) + flags de tech/crawl (de Crawl) + dados do scrape (disponíveis desde o início). Precisa de tudo rodado antes.

### 4.3 Comportamento do provider

```python
def run(self, context: EnrichmentContext) -> ProviderResult:
    lead_data = self._consolidate(context)

    # Idempotência
    new_hash = compute_classification_hash(lead_data)
    if (context.lead.classification_hash == new_hash
            and not context.force_classification):
        return ProviderResult(skipped=True, reason="hash_unchanged")

    # Classificação (nunca levanta exceção)
    result = classify(lead_data, llm_client=self.llm_client)

    # Preservação de nicho manual/LLM anterior
    if (context.lead.nicho_canonico
            and context.lead.nicho_source in ("manual", "llm_inferred")
            and not context.force_classification):
        result.nicho_canonico = context.lead.nicho_canonico
        result.nicho_source = context.lead.nicho_source
        result.nicho_confidence = context.lead.nicho_confidence

    # Provider escreve no context; orchestrator persiste no DB em transação única
    context.classification = result
    return ProviderResult(success=True, data=result.to_dict())
```

Coerente com padrão existente:
- Provider **nunca escreve no DB diretamente** — orchestrator consolida
- Provider **nunca levanta exceção** — top-level try/except retorna `ProviderResult(success=False, error=...)` em caso de bug imprevisto
- Respeita `skip_providers` e `force_providers` já existentes no orchestrator

### 4.4 Trigger automático de re-classificação do perfil

Implementado no orchestrator (não via trigger PostgreSQL):

- Sempre que orchestrator termina qualquer run de enrichment, chama `ClassificationProvider`
- Provider compara hash. Se mudou → re-classifica perfil (regra de negócio barata). Se não mudou → skip
- **Nicho não é re-rodado automaticamente** (regra: nicho só muda via `force_classification=True` ou `nicho_source == "failed"`)

Vantagens vs trigger de DB:
- Lógica em Python — testável, debugável, explícita
- Zero mágica escondida em stored procedure
- Custo de chamar sempre: ~1ms (só hash + comparação quando não muda)

### 4.5 `EnrichmentContext`

Adicionar campo `classification: Optional[ClassificationResult]` ao dataclass existente. Orchestrator persiste todos os 9 campos novos do Lead junto com os campos que os outros providers já gravam (uma só transação, padrão atual preservado).

---

## 5. Endpoints & background job

### 5.1 Endpoint: batch classification

`POST /api/pipeline/classify`

Request body:

```json
{
  "scope": "unclassified" | "all" | "by_job" | "by_status",
  "scope_filter": { "job_id": 123, "status": "enriched" },
  "force": false
}
```

Comportamento:
- Cria registro `Job` tipo `classification` (segue padrão dos outros jobs)
- Dispara background task via FastAPI `BackgroundTasks`
- Retorna `{ "job_id": 456 }` imediatamente (201 Created)
- Progresso via SSE em `GET /api/jobs/{id}/stream` (rota já existe)

Scopes:
- `unclassified` (default) — `WHERE perfil_lead IS NULL`
- `all` — todos os leads (usado após mudar regras/taxonomia)
- `by_job` — `WHERE job_id = X` (classifica leads de um import/scrape específico)
- `by_status` — `WHERE status = X`

### 5.2 Endpoint: reclassify individual

`POST /api/leads/{id}/reclassify`

Request body: `{ "force": true }` (opcional, default `true`)

Comportamento:
- Síncrono (não cria Job — é um lead só)
- Chama `classify()` diretamente
- Persiste + retorna lead atualizado
- Usado pelo botão "Re-classificar" no lead detail e pela tabela de revisão

Concorrência: usa `SELECT FOR UPDATE` no lead com timeout de 5s. Se não pega lock → 409 Conflict com mensagem clara.

### 5.3 Background task — lógica do batch

```python
async def run_classification_job(job_id, scope, scope_filter, force):
    leads = query_leads(scope, scope_filter)
    total = len(leads)
    emit_sse(job_id, {"status": "running", "total": total})

    results = {"ok": 0, "failed": 0, "skipped": 0, "errors": {}}
    consecutive_failures = 0

    for idx, lead in enumerate(leads):
        try:
            lead_data = consolidate_lead_data(lead)
            result = classify(lead_data, llm_client=llm_client)
            persist_classification(lead, result)

            if result.nicho_source == "failed":
                results["failed"] += 1
                consecutive_failures += 1
            else:
                results["ok"] += 1
                consecutive_failures = 0
        except Exception as e:
            # Rede de segurança — classify() já não raises, mas persist pode
            results["failed"] += 1
            results["errors"][lead.id] = str(e)
            consecutive_failures += 1
            # NÃO RE-RAISE — isolamento por lead

        # Circuit breaker: 50% após 20 leads processados
        if idx + 1 >= 20:
            failure_rate = results["failed"] / (idx + 1)
            if failure_rate > 0.5:
                emit_sse(job_id, {"status": "stalled", "reason": "too_many_failures"})
                mark_job_stalled(job_id)
                return

        if idx % 5 == 0:
            emit_sse(job_id, {
                "status": "running",
                "progress": idx + 1,
                "total": total,
                "results": results,
            })

    emit_sse(job_id, {"status": "done", "results": results})
```

### 5.4 Integração com CSV import existente

`POST /api/pipeline/csv-import` já cria leads com dados parciais. Mudança mínima:

- Após import bem-sucedido (Job tipo `csv_import` marcado como done), dispara automaticamente job encadeado tipo `classification` com `scope="by_job"` e `scope_filter={"job_id": <csv_import_id>}`
- Isso classifica os leads recém-importados sem ação manual

Se o job encadeado falhar, **o job de import permanece bem-sucedido** — usuário pode re-disparar classification manualmente pela UI.

### 5.5 Concorrência e rate limit do LLM

- Dentro de um batch: leads processados sequencialmente (sem paralelismo)
- Razão: gargalo é o LLM de nicho; paralelizar dispara rate limit sem ganho real
- Tempo estimado: ~2-3s por lead quando nicho cai em camada 3 (LLM). 100 leads ≈ 3-5 min
- Futuro (>1000 leads): adicionar semáforo de ~5 concurrent. Fora do escopo agora

### 5.6 Reuso de infra

- Model `Job` e rotas `/api/jobs/*` — zero mudança
- SSE stream `/api/jobs/{id}/stream` — zero mudança
- Padrão `job.result_summary["errors"]` — zero mudança
- `BackgroundTasks` do FastAPI — zero mudança

---

## 6. Frontend

Consistente com design system "Instrumento" existente. Zero dependência externa nova — apenas primitivos em `components/ui/`.

### 6.1 Componente novo: `ProfileBadge`

`frontend/src/components/ui/profile-badge.tsx`

```tsx
<ProfileBadge profile="hot_no_site" />
```

Mapa de cor (paleta de score existente):

| Perfil | Cor | Ícone | Texto |
|---|---|---|---|
| `hot_no_site` | `--score-hot` (terracotta) | 🔥 | "Sem site validado" |
| `hot_bad_site` | `--score-hot` (terracotta) | 🔥 | "Site ruim" |
| `warm` | `--score-warm` (mostarda) | — | "Oportunidade média" |
| `cold` | `--score-cool` (salvia) | — | "Site ok" |
| `disqualified` | `--text-muted` | — | "Desqualificado" |

Emoji sutil, opt-out via prop `showEmoji`. Texto em pt-BR.

### 6.2 Kanban — badge e filtro

- Card do lead em `components/kanban-board.tsx`: `<ProfileBadge>` ao lado do score existente
- Header do kanban (`kanban-filters.tsx`): novos dropdowns "Perfil" (multi-select, 5 opções) e "Nicho" (multi-select, 15 opções)
- Ordenação: novo valor `order_by=prioridade` em `lib/api.ts`. Quando selecionado, ordena por `prioridade` (máxima → pular) como chave primária e `score` como desempate

### 6.3 Lead App — exibição e edição

**`la-header.tsx`:** badge de perfil ao lado do status pill.

**`la-rail.tsx`:** nova seção "Classificação" com:
- Perfil (badge grande + descrição)
- Nicho canônico (pill)
- Fonte do nicho (`apify_category` | `fuzzy_match` | `llm_inferred` | `manual` | `failed`) — ícone pequeno + tooltip
- Confiança (barra 0-100%)
- Pacote sugerido (badge)
- Prioridade (badge)

**Edição manual de nicho:** clicar no pill abre popover com select dos 15 buckets. Ao salvar: `PATCH /api/leads/{id}` com `{nicho_canonico: X, nicho_source: "manual", nicho_confidence: 1.0}`.

**Botão "Re-classificar":** topo do rail. Chama `POST /api/leads/{id}/reclassify` com `force: true`. Spinner inline; feedback inline ao concluir (sem toast global nesta spec).

### 6.4 Lead List (master) — filtros

`components/leads/la-master.tsx` ganha os mesmos dropdowns de perfil e nicho. Persistência em localStorage coerente com filtros atuais.

### 6.5 Pipeline page — botão "Classificar backlog"

`components/pipeline-controls.tsx` adiciona 5º botão:

```
[Scrape] [Enrich] [Generate] [Outreach] [Classificar]
```

Modal ao clicar:
- Scope (dropdown): "Apenas não classificados" (default), "Todos os leads", "Leads deste job" (dropdown com jobs recentes)
- Checkbox: "Forçar re-classificação de nicho" (default off)
- Botão "Iniciar" → `POST /api/pipeline/classify`

Progresso via SSE pelo componente `JobProgress` existente (zero mudança lá). Exibe `ok / failed / skipped / errors` em tempo real.

### 6.6 Dashboard — widgets novos

Em `components/dashboard/`:
- **Card "Distribuição por perfil":** 5 barras horizontais com contagem + %. Cada barra clicável → navega para `/app/kanban?perfil=X`
- **Card "Distribuição por nicho":** top 10 buckets + "outros" expansível. Clicável → filtra leads por nicho

Posição: no grid existente, abaixo de "Leads por status".

### 6.7 Tabela de revisão — rota nova

`/app/leads/review`

Mostra leads com `nicho_canonico = outros` OR `nicho_source = failed` OR `nicho_confidence < 0.5`.

Tabela:
- Colunas: nome, `nicho_raw` (texto original do scrape/CRM), sugestão atual, confidence, ações
- Ação primária: dropdown inline para escolher bucket correto → marca `nicho_source = manual`
- Ação secundária: "Re-classificar" (roda LLM de novo)
- Link no sidebar (`app-sidebar.tsx`): "Revisão de nichos" com badge de contagem pendente

### 6.8 API client

`lib/api.ts` ganha:
- `classifyLeads(scope, scope_filter, force) → { job_id }`
- `reclassifyLead(id, force) → Lead`
- `getLeadsForReview(filters) → { leads, total }`

Reusa o wrapper `fetchAPI` existente. Tipos atualizados em `lib/types.ts` — campos novos adicionados ao type `Lead`.

### 6.9 Notificações — intencionalmente fora do escopo

A auditoria do frontend apontou ausência de toast system. Esta spec **não introduz** um — usa padrões existentes (loading state em botões, mensagens inline, erros via `console.error` e `catch` local). Toast system é escopo próprio; introduzir aqui mistura responsabilidades.

---

## 7. Error handling & resiliência

Pilar explícito da spec. Degradação graciosa em cada camada. Lead nunca é perdido; batch nunca trava.

### 7.1 Camada — função `classify()`

| Cenário | Comportamento |
|---|---|
| Dados mínimos faltando (rating, review_count, has_website todos NULL) | Retorna `DISQUALIFIED` + `OUTROS/failed`. Não raise |
| Campos parciais | Defaults seguros da Seção 3.3 aplicam. Lead cai em `WARM` no pior caso |
| Bug interno (exceção inesperada em regra) | Top-level try/except: retorna `ClassificationResult` com `DISQUALIFIED/OUTROS/failed` e `error_reason` preenchido |

Garantia: **`classify()` nunca levanta exceção**. Testada com property-based testing (Hypothesis) gerando dicts aleatórios.

### 7.2 Camada — inferência de nicho via LLM

| Cenário | Comportamento |
|---|---|
| Timeout (>15s) | Retry 3× com backoff exponencial (1s, 2s, 4s + jitter) via `tenacity` |
| HTTP 429 | Retry respeitando header `Retry-After` |
| HTTP 500/503 | Retry 3× exponencial |
| HTTP 401/403 (auth) | **Não retry.** `OUTROS/failed`, log crítico, job result ganha flag de alerta |
| JSON inválido no response | Try/except no parse. Fallback `OUTROS/failed` |
| Valor fora do enum | Validação pós-resposta. Inválido → `OUTROS/failed` |
| Confidence retornado baixo (< 0.5) | Mantém `source=llm_inferred` e confidence real. Entra automaticamente na tabela `/app/leads/review` para revisão manual (threshold alinhado com 6.7) |

Tempo máximo total de retry: 30s. Depois → fallback sem matar o lead.

### 7.3 Camada — provider no orchestrator

| Cenário | Comportamento |
|---|---|
| `classify()` crasheia inesperadamente (bug) | Provider captura, retorna `ProviderResult(success=False, error=...)`. Orchestrator continua |
| Consolidação de dados falha (KeyError etc) | Mesmo fallback acima |
| Hash corrompido no DB (length != 32 ou não-hex) | Ignora e re-classifica |

### 7.4 Camada — batch job

| Cenário | Comportamento |
|---|---|
| Lead individual falha no loop | Try/except por lead, erro para `job.result_summary["errors"][lead_id]`, continua |
| Circuit breaker: >50% falhas após 20 processados | Job pausa status `stalled`, SSE avisa frontend, para de escrever |
| DB connection loss durante batch | Libera sessão, reconecta, continua do próximo lead não processado (filtro `perfil_lead IS NULL` é naturalmente reentrante) |
| Background task crasheia | Timeout hard de 30 min no job → status vira `timeout` automaticamente. Frontend oferece "retry" |
| SSE falha | Job continua no backend. Frontend reconecta; se perder estado, consulta `GET /api/jobs/{id}` |

Threshold de circuit breaker: **50% após 20 leads**. Mais permissivo que o draft original (10%) para não disparar falso positivo em realidades ruidosas.

### 7.5 Camada — migration

- Todos os campos novos: `nullable + default NULL`. Migration em ms mesmo com milhões de leads
- Zero backfill na migration. Backfill fica no batch job (que tem fallbacks e circuit breaker)
- Rollback seguro: downgrade só `DROP COLUMN`

### 7.6 Camada — CSV import

| Cenário | Comportamento |
|---|---|
| Colunas obrigatórias ausentes | 422 upfront com lista clara. Nada é criado |
| Linha com encoding inválido | Skip + reporta em `job.result_summary["errors"]`. Import continua |
| Duplicatas (mesmo telefone/email) | Comportamento existente do CSV import, mantido |
| Auto-dispatch de classification falha após import | Import permanece sucesso. Classification job falha separadamente; user re-dispara |

### 7.7 Camada — concorrência

| Cenário | Comportamento |
|---|---|
| User clica "Re-classificar" 2× rápido | Botão desabilita até resposta. Backend: idempotência por hash evita trabalho duplicado |
| Dois batch jobs concorrentes | Cada job filtra `perfil_lead IS NULL`; o segundo vê menos leads e skipa os já classificados. Race aceitável (resultado é idempotente) |
| Lead sendo enriquecido + user pede reclassify | `SELECT FOR UPDATE` com timeout de 5s. Sem lock → 409 Conflict |

### 7.8 Observabilidade

Cada falha produz log estruturado JSON no stdout:

```json
{
  "event": "classification.failed",
  "lead_id": 1234,
  "phase": "nicho_inference",
  "reason": "llm_timeout",
  "retries": 3,
  "duration_ms": 31520,
  "job_id": 567
}
```

Reusa logger existente. Stdout → Railway captura. Infraestrutura de métricas/traces fica para spec própria.

---

## 8. Testing strategy & critério de sucesso

### 8.1 Camadas de teste

**Unit — `backend/tests/test_classifier.py`**
- Tabela de casos para cada regra de perfil (um por perfil + edge cases com dados faltando)
- Fuzzy match: entradas variadas ("clinica odontologica", "Dr. Silva Odonto", "Ortodontia Sorriso") → `dentista`
- Mock LLM via `llm_client` injetado: retorna JSON válido / inválido / fora do enum / timeout simulado
- Hash de idempotência: mesmos inputs → mesmo hash; mudança em campo-chave → hash diferente
- Property-based (Hypothesis): `classify()` nunca raise para dicts aleatórios com qualquer combinação de campos

**Integration — `backend/tests/test_classification_provider.py`**
- Provider roda no orchestrator após scoring; resultado escrito em `context.classification`
- `skip_providers=["classification"]` respeitado
- `force_providers=["classification"]` força re-classificação mesmo com hash igual
- Orchestrator persiste os 9 campos em transação única
- Leads com `nicho_source="manual"` não têm nicho sobrescrito em re-classificação automática

**Integration — `backend/tests/test_classify_job.py`**
- Batch de 50 leads sintéticos: todos classificados, sem erro
- Batch com 25 válidos + 25 malformados: 25 ok, 25 `failed`, zero crash
- Circuit breaker: injetar `classify()` falhando em 60% → job termina `stalled` após 20 leads
- Idempotência: rodar 2× sobre mesmo scope → segunda rodada processa 0
- Scope `by_job` filtra corretamente
- Auto-dispatch após CSV import: job encadeado cria e processa

**E2E resilience — `backend/tests/test_classification_resilience.py`**
- LLM JSON inválido → fallback `OUTROS/failed`
- LLM timeout 3× → fallback, lead persistido
- DB connection loss no meio do batch (fixture) → retoma
- Dois jobs concorrentes → sem double-write corrompido

**Frontend — Playwright ou checklist manual documentado**
- Kanban filtra por perfil e nicho
- Badge de perfil renderiza com cor correta
- Botão "Re-classificar" no lead detail chama API e atualiza UI
- Modal "Classificar backlog" inicia job, SSE mostra progresso, finaliza com results
- Tabela `/app/leads/review` exibe apenas leads com `outros/failed/confidence<0.5`
- Edição manual de nicho marca `source=manual` e persiste

### 8.2 QA manual — amostra real

Revisar **20 leads** classificados da base real:
- Quantos perfis "parecem certos" para quem conhece o negócio? (meta: ≥90%, ou seja ≥18/20)
- Quantos nichos caíram em `outros`? (meta: ≤20%, ou seja ≤4/20)
- Dos `outros`, quantos poderiam ter entrado num bucket conhecido? (se >50%, taxonomia precisa ajuste antes de declarar pronto)

### 8.3 Critério de sucesso

A spec está **pronta** quando **todos** os três blocos abaixo forem verdadeiros:

**Bloco funcional**
- 100% dos leads no DB têm `perfil_lead` e `nicho_canonico` não-nulos após batch completo
- Amostra manual de 20 leads: ≥18 perfis corretos (90%)
- Distribuição no DB: ≤20% em `outros`

**Bloco operacional**
- Batch de 100+ leads roda sem travar
- Todos os testes de resiliência (Seção 7) passam verdes
- Re-classificação idempotente verificada (2× = mesmo resultado quando dados não mudam)
- Circuit breaker dispara em teste forçado

**Bloco usável**
- Kanban filtrável por perfil + nicho
- Lead App exibe badge + permite edição manual + botão re-classify funcional
- Dashboard mostra widget de distribuição (2 gráficos)
- `/app/leads/review` lista e permite ação inline
- Pipeline page tem botão "Classificar backlog" funcional

### 8.4 Fora do escopo de testes

- Teste de carga (1000+ leads simultâneos) — bottleneck real só aparece com volume; revisitar quando chegar
- Teste de custo LLM real — monitorado em produção via dashboard Anthropic, não CI
- Teste cross-browser no frontend — segue padrão existente

---

## Próximos passos

1. Aprovação desta spec pelo usuário
2. Criação do plano de implementação via skill `writing-plans` (quebrar em etapas sequenciais e paralelizáveis)
3. Dispatch do plano para agentes (worktrees separados para backend e frontend)
4. Execução com review por checkpoints
5. QA manual em amostra real + ativação do batch job sobre o backlog existente
6. Transição para **spec 2 — LP Conversion Tracking**
