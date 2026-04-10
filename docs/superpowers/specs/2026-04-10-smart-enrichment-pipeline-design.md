# Smart Enrichment Pipeline — Design Spec

**Data:** 2026-04-10
**Status:** Aprovado
**Escopo:** Reescrever o enricher como pipeline modular com orquestração inteligente, adicionar novos providers (CNPJ, tech stack, schema.org, email, Apollo), campo email no Lead, e score de oportunidade revisado.

---

## 1. Visão Geral

O enricher atual (`enricher.py`) faz uma coisa: crawl do website + análise de qualidade. Isso limita o enriquecimento a leads que já têm website preenchido.

O novo sistema transforma o enricher em um **orquestrador inteligente** que:
- Avalia o que o lead já tem (quais campos estão preenchidos)
- Decide quais **providers** rodar baseado nos dados disponíveis
- Executa os providers em ordem otimizada (reusando dados entre eles)
- Permite override do usuário (forçar ou pular providers)
- Recalcula o score de oportunidade com base em todos os dados coletados

---

## 2. Providers

Cada provider é um módulo independente com responsabilidade única. Todos implementam a mesma interface base.

### 2.1 Interface Base

```python
class BaseProvider:
    name: str                    # identificador único (ex: "website_crawler")
    display_name: str            # nome pro frontend (ex: "Website Crawler")
    required_fields: list[str]   # campos do lead necessários pra rodar
    cost: str                    # "free" | "freemium"

    async def can_run(self, lead: Lead) -> bool:
        """Retorna True se o lead tem os dados mínimos pra esse provider."""

    async def run(self, lead: Lead, context: EnrichmentContext) -> ProviderResult:
        """Executa o enriquecimento. Retorna dados encontrados."""
```

`EnrichmentContext` é um objeto compartilhado entre providers. Permite que um provider reuse dados de outro (ex: Schema.org reusa o HTML já baixado pelo Crawler).

```python
@dataclass
class EnrichmentContext:
    html_content: str | None = None       # HTML do site, preenchido pelo crawler
    response_headers: dict = field(default_factory=dict)
    discovered_website: str | None = None  # website descoberto por outro provider (ex: CNPJ)

@dataclass
class ProviderResult:
    success: bool
    data: dict           # campos a atualizar no lead
    errors: list[str]    # erros não-fatais
    source: str          # nome do provider
```

### 2.2 Provider: Website Crawler

**Input mínimo:** `website`
**Custo:** Free
**O que faz:** Extraído do `enricher.py` atual. Crawl do site, análise de SSL, responsividade, CTA, PageSpeed, extração de social links.
**Output:** `site_analysis`, `social_profiles` (parcial), HTML no context.
**Notas:** Popula `context.html_content` pra providers subsequentes reusarem.

### 2.3 Provider: Schema.org Extractor

**Input mínimo:** `context.html_content` (depende do Crawler ter rodado)
**Custo:** Free
**O que faz:** Parseia tags `<script type="application/ld+json">` e microdata do HTML. Extrai tipo de negócio, serviços oferecidos, horário de funcionamento, endereço estruturado.
**Output:** Campos em `site_analysis.structured_data`.

### 2.4 Provider: Tech Stack Detector

**Input mínimo:** `context.html_content` + `context.response_headers`
**Custo:** Free
**O que faz:** Detecta tecnologias do site analisando:
- Scripts e links no HTML (ex: `wp-content/` → WordPress)
- Meta tags e generators
- Response headers (ex: `X-Powered-By`)
- Patterns conhecidos (baseado no dataset Wappalyzer open-source)
**Output:** `tech_stack` (lista de objetos `{name, category, version?}`).
**Implementação:** Usar a base de detecção do Wappalyzer (MIT license) — arquivo JSON de patterns que mapeiam regex → tecnologia.

### 2.5 Provider: CNPJ Enricher

**Input mínimo:** `cnpj` (direto) OU `nome` + `cidade` (busca)
**Custo:** Free
**O que faz:**
- Se tem CNPJ: consulta direto na BrasilAPI (`brasilapi.com.br/api/cnpj/v1/{cnpj}`)
- Se tem nome + cidade: tenta buscar via ReceitaWS ou BrasilAPI (busca por nome)
- Extrai: razão social, nome fantasia, CNAE, porte, data de fundação, sócios, endereço completo
- Se descobrir website no cadastro e o lead não tinha: popula `context.discovered_website`
**Output:** `razao_social`, `cnpj`, `porte`, `cnae`, `data_fundacao`, `socios`, potencialmente `website` e `endereco`.
**Rate limit:** ReceitaWS tem 3 req/min. Implementar throttle.

### 2.6 Provider: Email Discoverer

**Input mínimo:** `website`
**Custo:** Freemium (Hunter.io — 25 buscas/mês grátis)
**O que faz:**
1. Extrai emails do HTML crawleado (regex + parsing de mailto: links)
2. Tenta padrões comuns: `contato@`, `info@`, `comercial@`, `atendimento@`
3. Se configurado, usa Hunter.io Domain Search pra encontrar emails associados ao domínio
4. Valida formato dos emails encontrados
**Output:** `email` (melhor email encontrado), lista completa em `site_analysis.emails_found`.
**Notas:** Hunter.io é opcional. Se a API key não estiver configurada, roda só com extração do HTML + padrões.

### 2.7 Provider: Apollo Enricher

**Input mínimo:** `website` OU `email`
**Custo:** Freemium (Apollo — 10k credits/mês grátis)
**O que faz:**
- Organization enrichment via domain
- Retorna: descrição da empresa, número de funcionários, indústria, LinkedIn da empresa, receita estimada
**Output:** Dados em `site_analysis.apollo_data`.
**Notas:** Apollo é opcional. Se a API key não estiver configurada, provider é pulado. Free tier é generoso pra volume de PME.

---

## 3. Orquestração Inteligente

### 3.1 Lógica de Decisão

O orquestrador avalia os campos preenchidos do lead e monta um plano de execução:

```
FASE 1 — Descoberta (tentar conseguir website se não tem):
  se NÃO tem website:
    se tem cnpj → CNPJ Enricher (pode descobrir website)
    se tem nome + cidade → CNPJ Enricher (busca por nome)
    se tem email → extrair domínio como website candidato
    se descobriu website → continua pra Fase 2

FASE 2 — Crawl (precisa de website):
  se tem website:
    → Website Crawler (popula context.html_content)
    → Schema.org Extractor (usa HTML do crawler)
    → Tech Stack Detector (usa HTML do crawler)

FASE 3 — Contato (enriquecimento de dados de contato):
  se tem website:
    → Email Discoverer
  se tem website OU email:
    → Apollo Enricher

FASE 4 — Scoring:
  → Recalcular opportunity_score com todos os dados
  → Registrar quais providers rodaram em enrichment_sources
```

### 3.2 Override do Usuário

O endpoint de enrich aceita parâmetros opcionais:

```python
class EnrichRequest(BaseModel):
    lead_ids: list[int] | None = None
    nicho: str | None = None
    cidade: str | None = None
    skip_providers: list[str] = []      # providers pra pular
    force_providers: list[str] = []     # providers pra forçar mesmo sem input mínimo
```

- `skip_providers: ["apollo", "hunter"]` → não roda esses providers
- `force_providers: ["cnpj"]` → roda CNPJ mesmo que a orquestração pularia

### 3.3 Resiliência

- Cada provider roda em try/except individual. Falha de um não bloqueia os outros.
- Timeout por provider: 30s default (configurável).
- Providers freemium (Hunter, Apollo) checam rate limit antes de rodar. Se estourou, pulam silenciosamente e logam aviso.
- Resultados parciais são salvos — se o crawler rodou mas o Apollo falhou, os dados do crawler são mantidos.

---

## 4. Mudanças no Modelo Lead

### 4.1 Novos Campos

```python
# Contato
email = Column(String(255), nullable=True)

# Dados empresariais (CNPJ)
cnpj = Column(String(18), nullable=True)          # formato: XX.XXX.XXX/XXXX-XX
razao_social = Column(String(255), nullable=True)
porte = Column(String(50), nullable=True)          # MEI, ME, EPP, DEMAIS
cnae = Column(String(100), nullable=True)          # atividade principal
data_fundacao = Column(Date, nullable=True)
socios = Column(JSON, default=[])

# Tech
tech_stack = Column(JSON, default=[])              # [{name, category, version?}]

# Meta
enrichment_sources = Column(JSON, default=[])      # [{provider, status, timestamp, error?}]
```

### 4.2 Novo Index

- Index em `email` (buscas por email)
- Index em `cnpj` (dedup por CNPJ)

### 4.3 Migration

Uma migration Alembic adicionando todos os campos novos. Todos nullable, sem impacto em leads existentes.

---

## 5. Score de Oportunidade Revisado

O score continua aditivo (0-100, maior = mais oportunidade), mas agora incorpora mais sinais:

| Critério | Pontos | Fonte |
|----------|--------|-------|
| Sem website | +40 | Orquestrador |
| SSL ausente | +15 | Website Crawler |
| Site não responsivo | +15 | Website Crawler |
| Sem CTA (botão/link de ação) | +10 | Website Crawler |
| PageSpeed < 50 | +10 | Website Crawler |
| Tech stack defasado (Flash, tabelas, frameworks pré-2015) | +5 | Tech Stack Detector |
| Sem redes sociais no site | +5 | Website Crawler |
| Email não profissional (gmail/hotmail/yahoo no domínio) | +5 | Email Discoverer |
| Sem dados estruturados (schema.org) | +3 | Schema.org Extractor |
| Empresa com >5 anos e site com score alto | +2 | CNPJ Enricher + Score |

**Score máximo teórico:** 110 (capped em 100).

**Nota:** Lead sem website que antes recebia 95 fixo, agora recebe 40 base + outros critérios que puderem ser avaliados (ex: email não profissional = +5).

---

## 6. Estrutura de Arquivos

```
backend/app/pipeline/
  enrichment/
    __init__.py              # exports
    orchestrator.py          # EnrichmentOrchestrator — lógica de decisão + execução
    base_provider.py         # BaseProvider ABC + EnrichmentContext + ProviderResult
    scoring.py               # cálculo do score revisado
    providers/
      __init__.py
      website_crawler.py     # extraído do enricher.py atual
      schema_extractor.py    # parser de JSON-LD e microdata
      tech_stack.py          # detecção via patterns Wappalyzer
      cnpj_enricher.py       # BrasilAPI + ReceitaWS
      email_discoverer.py    # extração + padrões + Hunter.io
      apollo_enricher.py     # Apollo.io API
```

O `enricher.py` atual é mantido temporariamente como wrapper que chama o orquestrador, pra não quebrar o pipeline existente. Depois de validado, pode ser removido.

---

## 7. Variáveis de Ambiente Novas

```env
# Opcional — se não configurado, provider é pulado
HUNTER_API_KEY=          # Hunter.io API key
APOLLO_API_KEY=          # Apollo.io API key
```

---

## 8. Frontend — Painel de Enrich

O componente de trigger do enrich (em `PipelineControls` ou `LeadSheet`) ganha uma seção expansível "Fontes de Enriquecimento":

- Toggle por provider (default: todos ligados)
- Providers sem API key configurada aparecem desabilitados com tooltip "API key não configurada"
- Após enrich, lead detail mostra badges de quais fontes contribuíram (campo `enrichment_sources`)

---

## 9. Fora de Escopo

- Importação de leads (CSV/paste) — será spec separado
- UI de configuração de API keys (configurar via .env)
- Dashboard de uso de créditos (Hunter/Apollo)
- Enriquecimento automático (sem trigger manual)
