# Enrichment Pipeline -- Documentacao Completa

> Modulo mais complexo do SDR Machine. Responsavel por enriquecer leads com dados
> de website, CNPJ, email, tech stack, Schema.org e Apollo.io, e calcular um
> **opportunity score** (0-100) que indica o potencial comercial de cada lead.

---

## Sumario

1. [Visao Geral](#1-visao-geral)
2. [Arquitetura](#2-arquitetura)
3. [O Orchestrator](#3-o-orchestrator)
4. [Fases de Execucao](#4-fases-de-execucao)
5. [Providers em Detalhe](#5-providers-em-detalhe)
6. [Scoring](#6-scoring)
7. [Precedencia de Dados](#7-precedencia-de-dados)
8. [Override do Usuario](#8-override-do-usuario)
9. [Edge Cases](#9-edge-cases)
10. [Configuracao](#10-configuracao)
11. [Legacy Wrapper](#11-legacy-wrapper)

---

## 1. Visao Geral

O pipeline de enrichment transforma um lead "cru" (apenas nome, telefone e endereco
vindos do Google Maps) em um lead qualificado com:

- Analise tecnica completa do website (SSL, responsividade, CTA, PageSpeed)
- Dados empresariais via CNPJ (razao social, porte, CNAE, socios)
- Emails de contato extraidos do HTML e/ou Hunter.io
- Tech stack detectado (CMS, frameworks, analytics, chatbots)
- Dados estruturados Schema.org (JSON-LD)
- Dados corporativos do Apollo.io (industria, tamanho, LinkedIn)
- **Opportunity score** calculado com base em todas as deficiencias encontradas

O design e **modular**: cada fonte de dados e um `BaseProvider` independente,
coordenado por um `EnrichmentOrchestrator` central.

```
                    +------------------+
                    |      Lead        |
                    | (nome, telefone, |
                    |  website, cnpj)  |
                    +--------+---------+
                             |
                    +--------v---------+
                    |   Orchestrator    |
                    |  plan() + execute |
                    +--------+---------+
                             |
          +------------------+------------------+
          |                  |                  |
   +------v------+   +------v------+   +-------v------+
   |  Discovery  |   |    Crawl    |   |   Contact    |
   |  (CNPJ)     |   | (Crawler + |   |  (Email +    |
   |             |   |  Schema +  |   |   Apollo)    |
   |             |   |  TechStack)|   |              |
   +------+------+   +------+------+   +------+------+
          |                  |                  |
          +------------------+------------------+
                             |
                    +--------v---------+
                    |     Scoring      |
                    | calculate_score()|
                    +--------+---------+
                             |
                    +--------v---------+
                    |   Lead Enriquecido|
                    | (score, reasons,  |
                    |  site_analysis,   |
                    |  tech_stack, ...) |
                    +-------------------+
```

---

## 2. Arquitetura

### 2.1 Estrutura de Arquivos

```
backend/app/pipeline/
  enricher.py                          # Legacy wrapper (ainda funcional)
  enrichment/
    __init__.py                        # Re-exporta tipos publicos
    base_provider.py                   # ABC + EnrichmentContext + ProviderResult
    orchestrator.py                    # EnrichmentOrchestrator + EnrichmentPlan
    scoring.py                         # calculate_score() modular
    providers/
      website_crawler.py               # Crawl HTTP + analise HTML + PageSpeed
      schema_extractor.py              # Parser JSON-LD / Schema.org
      tech_stack.py                    # Deteccao de tecnologias
      tech_stack_patterns.py           # Patterns (HTML, meta generator, headers)
      cnpj_enricher.py                # Consulta BrasilAPI
      email_discoverer.py             # Regex HTML + Hunter.io
      apollo_enricher.py              # Apollo.io Organization Enrichment
```

### 2.2 `EnrichmentContext` -- Estado Compartilhado

O `EnrichmentContext` e um dataclass mutavel que funciona como "memoria" entre
providers durante uma unica execucao. Isso permite que um provider produza dados
que outro consome, sem acoplamento direto.

```python
@dataclass
class EnrichmentContext:
    html_content: str | None = None          # Populado pelo WebsiteCrawler
    response_headers: dict = field(...)      # Populado pelo WebsiteCrawler
    discovered_website: str | None = None    # Populado pelo CnpjProvider
```

**Fluxo tipico:**

```
CnpjProvider  ----> context.discovered_website = "www.empresa.com.br"
                         |
WebsiteCrawler ----> context.html_content = "<html>..."
                     context.response_headers = {"Server": "nginx", ...}
                         |
SchemaOrgProvider ----> le context.html_content
TechStackProvider ----> le context.html_content + context.response_headers
EmailDiscoverer   ----> le context.html_content
```

### 2.3 `ProviderResult` -- Resultado Padronizado

Todo provider retorna um `ProviderResult`:

```python
@dataclass
class ProviderResult:
    success: bool         # O provider em si executou corretamente?
    data: dict            # Campos para merge no Lead
    errors: list[str]     # Erros nao-fatais (nao param outros providers)
    source: str           # Nome do provider (audit trail)
```

**Distincao importante:** `success=True` com `site_analysis.status="ssl_error"`
significa que o provider *executou corretamente* e *descobriu* que o site tem
problema de SSL. O campo `success` indica a saude do provider, nao do site.

### 2.4 `BaseProvider` -- Classe Base Abstrata

```python
class BaseProvider(ABC):
    name: str = ""                  # Identificador unico (ex: "website_crawler")
    display_name: str = ""          # Nome legivel (ex: "Website Crawler")
    required_fields: list[str] = [] # Campos do Lead necessarios
    cost: str = "free"              # "free" | "freemium"

    @abstractmethod
    def can_run(self, lead, context=None) -> bool: ...

    @abstractmethod
    def run(self, lead, context) -> ProviderResult: ...
```

O metodo `can_run()` recebe opcionalmente o `context`, permitindo que providers
da fase Crawl verifiquem se o HTML ja foi obtido antes de rodar.

---

## 3. O Orchestrator

O `EnrichmentOrchestrator` e o cerebro do pipeline. Ele decide **quais** providers
rodar e **em que ordem**, e depois executa o plano mergeando os resultados.

### 3.1 Ordem das Fases (`_PHASE_ORDER`)

```python
_PHASE_ORDER = [
    "cnpj_enricher",       # 1. Discovery
    "website_crawler",     # 2. Crawl
    "schema_extractor",    # 2. Crawl
    "tech_stack",          # 2. Crawl
    "email_discoverer",    # 3. Contact
    "apollo",              # 3. Contact
]
```

A ordem e fixa e deliberada: CNPJ vem primeiro porque pode **descobrir** o website
do lead (via `context.discovered_website`), habilitando toda a cadeia de crawl.

### 3.2 `plan()` -- Planejamento Otimista

O metodo `plan()` constroi um `EnrichmentPlan` (lista ordenada de providers a executar).
O planejamento e **otimista**: se ha chance de um provider rodar, ele e incluido.
A validacao real acontece em `execute()` com o `can_run()` re-check.

**Algoritmo:**

```
plan(lead, skip_providers, force_providers):
  1. skip = set(skip_providers) ou {}
  2. force = set(force_providers) - skip    # skip SEMPRE ganha
  3. has_website = lead.website existe?
  4. might_discover_website = lead.cnpj existe E sem website E cnpj nao skip?
  5. include_crawl_chain = has_website OU might_discover_website

  6. Se include_crawl_chain:
       optimistic_names = {website_crawler, schema_extractor,
                           tech_stack, email_discoverer, apollo}
     Senao:
       optimistic_names = {}

  7. Para cada provider em _PHASE_ORDER:
       - Se name in skip: pula
       - Se name in force: inclui (mesmo sem can_run)
       - Se name in optimistic_names: inclui
       - Senao: chama can_run(lead) como fallback
```

**Exemplo -- lead com CNPJ mas sem website:**

```
Lead: { cnpj: "12.345.678/0001-90", website: None }
skip: [], force: []

  has_website = False
  might_discover_website = True  (tem CNPJ, sem website, CNPJ nao skip)
  include_crawl_chain = True

  Plano otimista: [cnpj_enricher, website_crawler, schema_extractor,
                   tech_stack, email_discoverer, apollo]

  Na execucao, se CnpjProvider nao encontrar website:
    - website_crawler.can_run(context) = False -> skipped
    - schema_extractor.can_run(context) = False -> skipped
    - ...
```

**Exemplo -- lead sem CNPJ e sem website:**

```
Lead: { cnpj: None, website: None }

  has_website = False
  might_discover_website = False
  include_crawl_chain = False
  optimistic_names = {}

  Para cada provider, fallback can_run(lead):
    - cnpj_enricher.can_run() = False (sem cnpj)
    - website_crawler.can_run() = False (sem website)
    - ... todos False

  Plano: [] (vazio)
```

### 3.3 `execute()` -- Execucao com Re-check

O metodo `execute()` percorre o plano sequencialmente, com validacao dupla:

```
execute(lead, plan):
  1. Cria EnrichmentContext() vazio
  2. Inicializa acumuladores (merged_site_analysis, flat, etc.)
  3. Snapshot dos campos protegidos do lead (_PROTECTED_KEYS)

  4. Para cada provider no plano:
     a. Re-check: provider.can_run(lead, context)
        - Se False -> registra "skipped" em enrichment_sources, proximo
     b. result = provider.run(lead, context)
        - Se nao e ProviderResult -> registra "error", proximo
        - Se result.success == False -> registra "skipped", proximo
     c. Merge:
        - site_analysis: dict.update (acumulativo)
        - social_profiles: dict.update (acumulativo)
        - tech_stack: substituicao total (ultimo provider ganha)
        - socios: substituicao total
        - flat fields: first-writer wins, protegidos por _PROTECTED_KEYS

  5. Calcula score com calculate_score()
  6. Retorna dict completo com todos os dados mergeados
```

**Campos protegidos (`_PROTECTED_KEYS`):**

```python
_PROTECTED_KEYS = (
    "email", "cnpj", "razao_social", "porte", "cnae",
    "data_fundacao", "website",
)
```

Esses campos **nunca sobrescrevem** valores ja existentes no lead. Se o lead ja
tem `email`, nenhum provider pode altera-lo.

### 3.4 `run()` -- Conveniencia

```python
def run(self, lead, skip_providers=None, force_providers=None) -> dict:
    plan = self.plan(lead, skip_providers, force_providers)
    return self.execute(lead, plan)
```

Atalho que faz `plan()` + `execute()` em uma chamada.

---

## 4. Fases de Execucao

```
+-----------+     +-----------+     +-----------+     +-----------+
|           |     |           |     |           |     |           |
| Discovery |---->|   Crawl   |---->|  Contact  |---->|  Scoring  |
|           |     |           |     |           |     |           |
+-----------+     +-----------+     +-----------+     +-----------+
     |                  |                 |                 |
 CnpjProvider    WebsiteCrawler    EmailDiscoverer    calculate_score()
                 SchemaOrg         ApolloProvider
                 TechStack
```

### Fase 1: Discovery (CNPJ)

- **Provider:** `CnpjProvider`
- **Objetivo:** Obter dados empresariais e, potencialmente, descobrir o website
- **Saida para context:** `context.discovered_website` (se encontrar)
- **Impacto:** Pode habilitar toda a cadeia de Crawl para leads sem website

### Fase 2: Crawl (Website + Schema + TechStack)

- **Providers:** `WebsiteCrawlerProvider` -> `SchemaOrgProvider` -> `TechStackProvider`
- **Dependencia:** Requer website (do lead ou descoberto pelo CNPJ)
- **Saida para context:** `context.html_content`, `context.response_headers`
- **Encadeamento:** Schema e TechStack consomem o HTML produzido pelo Crawler

### Fase 3: Contact (Email + Apollo)

- **Providers:** `EmailDiscovererProvider`, `ApolloProvider`
- **Dependencia:** Requer HTML (para email) e/ou website/domain (para Apollo)
- **Objetivo:** Encontrar formas de contato alem do telefone

### Fase 4: Scoring

- Nao e um provider -- e chamado pelo Orchestrator apos todos os providers
- Usa `calculate_score()` com os dados acumulados de todas as fases
- Produz `opportunity_score` (0-100) e `opportunity_reasons` (lista de strings)

---

## 5. Providers em Detalhe

### 5.1 WebsiteCrawlerProvider

**Arquivo:** `providers/website_crawler.py`

| Atributo | Valor |
|----------|-------|
| `name` | `website_crawler` |
| `cost` | `free` |
| `required_fields` | `["website"]` |

**O que faz:**

1. Normaliza a URL do lead (adiciona `https://` se necessario)
2. Faz requisicao HTTP GET com timeout de 10s e follow redirects
3. Captura os primeiros **15.000 caracteres** do HTML (`resp.text[:15000]`)
4. Popula `context.html_content` e `context.response_headers`
5. Analisa o HTML com `analyze_html()` do modulo legado
6. Chama Google PageSpeed Insights API (com `time.sleep(1)` para rate limit)
7. Opcionalmente scrapa perfis sociais via Apify (Instagram, LinkedIn)

**Normalizacao de URL:**

```python
def _normalize_url(value: str | None) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    if value.startswith(("http://", "https://")):
        return value
    return f"https://{value}"
```

Exemplos:
- `"empresa.com.br"` -> `"https://empresa.com.br"`
- `"http://empresa.com.br"` -> `"http://empresa.com.br"` (preserva HTTP)
- `""` -> `None`
- `"  "` -> `None`

**`can_run()` com context:**

```python
def can_run(self, lead, context=None) -> bool:
    if _normalize_url(getattr(lead, "website", None)):
        return True
    if context and _normalize_url(context.discovered_website):
        return True
    return False
```

O provider pode rodar mesmo se o lead nao tem `website`, contanto que o
`CnpjProvider` tenha descoberto um via `context.discovered_website`.

**Resolucao de URL (precedencia):**

```python
raw_website = getattr(lead, "website", None) or (
    context.discovered_website if context else None
)
```

`lead.website` tem precedencia sobre `context.discovered_website`.

**Tratamento de erros HTTP:**

| Excecao | `site_analysis.status` |
|---------|----------------------|
| SSL Error | `ssl_error` |
| Connection Error | `connection_error` |
| Timeout | `timeout` |
| Status >= 400 | `http_error` |
| Sucesso (2xx/3xx) | `ok` |

**Cap de HTML em 15KB:**

O HTML e truncado em 15.000 caracteres para evitar consumo excessivo de memoria.
Esse valor e suficiente para capturar head, hero section e elementos de navegacao
da maioria dos sites.

**Saida (`ProviderResult.data`):**

```python
{
    "site_analysis": {
        "status": "ok",
        "has_ssl": True,
        "has_responsive_meta": True,
        "has_whatsapp_link": False,
        "has_analytics": True,
        "has_chatbot": False,
        "has_cta": True,
        "has_social_links": True,
        "title": "Empresa XYZ",
        "description": "Descricao do site...",
        "word_count": 350,
        "image_count": 8,
        "is_template": False,
        "pagespeed": 72,
    },
    "social_profiles": {
        "instagram": { "platform": "instagram", "username": "empresa", ... },
        "facebook": { "platform": "facebook", "url": "..." }
    }
}
```

---

### 5.2 SchemaOrgProvider

**Arquivo:** `providers/schema_extractor.py`

| Atributo | Valor |
|----------|-------|
| `name` | `schema_extractor` |
| `cost` | `free` |
| `required_fields` | `[]` |

**O que faz:**

1. Busca todos os `<script type="application/ld+json">` no HTML
2. Parseia cada bloco JSON-LD
3. Suporta `@graph` (achata a lista de entidades)
4. Seleciona a entidade mais relevante por prioridade de `@type`
5. Extrai nome, telefone, horarios, endereco

**Prioridade de tipos (`_TYPE_PRIORITY`):**

```python
_TYPE_PRIORITY = {
    "LocalBusiness": 100,    # Mais relevante
    "Restaurant": 95,
    "MedicalBusiness": 95,
    "Store": 90,
    "Organization": 80,
    "Corporation": 80,
    "WebSite": 20,
    "WebPage": 10,           # Menos relevante
}
# Tipo desconhecido: 50 (fallback)
```

Tipos como `LocalBusiness` sao priorizados porque contem dados mais ricos
(telefone, endereco, horarios) do que `WebSite` ou `WebPage`.

**Suporte a `@graph`:**

Muitos sites emitem JSON-LD com `@graph`, que e uma lista de entidades em um
unico bloco `<script>`:

```json
{
  "@context": "https://schema.org",
  "@graph": [
    { "@type": "WebSite", "name": "..." },
    { "@type": "LocalBusiness", "name": "...", "telephone": "..." }
  ]
}
```

A funcao `_flatten_candidates()` extrai recursivamente todas as entidades:

```python
def _flatten_candidates(data) -> list[dict]:
    if isinstance(data, list):
        out = []
        for item in data:
            out.extend(_flatten_candidates(item))
        return out
    if isinstance(data, dict):
        if "@graph" in data and isinstance(data["@graph"], list):
            return _flatten_candidates(data["@graph"])
        return [data]
    return []
```

**Saida:**

```python
{
    "site_analysis": {
        "structured_data": {
            "type": "LocalBusiness",
            "name": "Padaria do Joao",
            "telephone": "(11) 99999-9999",
            "opening_hours": "Mo-Sa 07:00-19:00",
            "address": { ... },
            "raw": { ... }      # JSON-LD original completo
        }
    }
}
```

**`can_run()`:** Requer `context.html_content` -- so roda apos o WebsiteCrawler.

---

### 5.3 TechStackProvider

**Arquivo:** `providers/tech_stack.py` + `providers/tech_stack_patterns.py`

| Atributo | Valor |
|----------|-------|
| `name` | `tech_stack` |
| `cost` | `free` |
| `required_fields` | `[]` |

**O que faz:**

Detecta tecnologias usadas pelo site usando tres fontes de patterns:

**1. HTML Patterns** -- regex contra o HTML bruto:

| Pattern | Tecnologia | Categoria |
|---------|-----------|-----------|
| `wp-content/\|wp-includes/` | WordPress | cms |
| `cdn.shopify.com` | Shopify | ecommerce |
| `wix.com\|static.wixstatic.com` | Wix | website_builder |
| `squarespace.com` | Squarespace | website_builder |
| `googletagmanager.com/gtag` | Google Analytics | analytics |
| `googletagmanager.com/gtm` | Google Tag Manager | analytics |
| `connect.facebook.net/.*fbevents.js` | Facebook Pixel | analytics |
| `hotjar.com` | Hotjar | analytics |
| `tidio.co` | Tidio | chat |
| `crisp.chat` | Crisp | chat |
| `intercom.io` | Intercom | chat |
| `tawk.to` | Tawk.to | chat |
| `_next/static\|__NEXT_DATA__` | Next.js | framework |
| `react.production\|react-dom` | React | framework |
| `vue.min.js\|__vue__` | Vue.js | framework |
| `application/x-shockwave-flash` | Adobe Flash | runtime |
| `jquery-1.` | jQuery 1 | js_library |

**2. Meta Generator** -- tag `<meta name="generator">`:

| Pattern | Tecnologia | Categoria |
|---------|-----------|-----------|
| `wix.com` | Wix | website_builder |
| `wordpress` | WordPress | cms |
| `drupal` | Drupal | cms |
| `joomla` | Joomla | cms |
| `shopify` | Shopify | ecommerce |
| `squarespace` | Squarespace | website_builder |

**3. Response Headers:**

| Header | Pattern | Tecnologia | Categoria |
|--------|---------|-----------|-----------|
| `x-powered-by` | `php` | PHP | language |
| `x-powered-by` | `asp.net` | ASP.NET | framework |
| `x-powered-by` | `express` | Express.js | framework |
| `server` | `nginx` | Nginx | web_server |
| `server` | `apache` | Apache | web_server |
| `server` | `cloudflare` | Cloudflare | cdn |

**Deduplicacao:** Usa um `set` (`seen`) para evitar duplicatas (ex: Wix detectado
tanto no HTML quanto no meta generator aparece apenas uma vez).

**Saida:**

```python
{
    "tech_stack": [
        {"name": "WordPress", "category": "cms"},
        {"name": "Google Analytics", "category": "analytics"},
        {"name": "PHP", "category": "language"},
        {"name": "Nginx", "category": "web_server"},
    ]
}
```

**`can_run()`:** Requer `context.html_content`.

---

### 5.4 CnpjProvider

**Arquivo:** `providers/cnpj_enricher.py`

| Atributo | Valor |
|----------|-------|
| `name` | `cnpj_enricher` |
| `cost` | `free` |
| `required_fields` | `["cnpj"]` |

**O que faz:**

1. Limpa o CNPJ removendo caracteres nao-numericos (masking: `12.345.678/0001-90` -> `12345678000190`)
2. Valida que tem exatamente 14 digitos
3. Consulta a BrasilAPI (`brasilapi.com.br/api/cnpj/v1/{cnpj}`)
4. Extrai dados empresariais da resposta
5. Se encontrar `website` na resposta **e** o lead nao tem website, popula `context.discovered_website`

**Limpeza de CNPJ:**

```python
def _clean_cnpj(cnpj: str) -> str:
    return re.sub(r"\D", "", cnpj or "")
```

**Dados extraidos:**

| Campo BrasilAPI | Campo Lead |
|----------------|------------|
| `razao_social` | `razao_social` |
| `porte` | `porte` |
| `cnae_fiscal_descricao` | `cnae` |
| `data_inicio_atividade` | `data_fundacao` (convertido para ISO date) |
| `qsa[].nome_socio` | `socios` (lista de `{"nome": "..."}`) |
| `website` | `website` + `context.discovered_website` |

**Descoberta de website:**

```python
website = body.get("website") or ""
if website and not getattr(lead, "website", None):
    context.discovered_website = website
    data["website"] = website
```

Esse e o ponto-chave: o CNPJ pode fornecer o website que habilita toda a cadeia
de Crawl (WebsiteCrawler, SchemaOrg, TechStack, EmailDiscoverer).

**Rate limits:** A BrasilAPI e gratuita mas tem rate limiting. O timeout da
requisicao e de 15 segundos.

**Saida:**

```python
{
    "razao_social": "EMPRESA LTDA",
    "porte": "ME",
    "cnae": "Restaurantes e similares",
    "data_fundacao": "2018-03-15",
    "socios": [
        {"nome": "JOAO DA SILVA"},
        {"nome": "MARIA DA SILVA"}
    ],
    "website": "www.empresa.com.br"
}
```

---

### 5.5 EmailDiscovererProvider

**Arquivo:** `providers/email_discoverer.py`

| Atributo | Valor |
|----------|-------|
| `name` | `email_discoverer` |
| `cost` | `freemium` |
| `required_fields` | `["website"]` |

**O que faz:**

1. Extrai emails do HTML via regex
2. Filtra falsos positivos
3. Opcionalmente consulta Hunter.io para emails adicionais
4. Seleciona o email preferencial (domain-matching)

**Regex de extracao:**

```python
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
```

**Filtragem de falsos positivos (`_filter_emails()`):**

| Filtro | Exemplo filtrado |
|--------|-----------------|
| Extensoes de imagem | `foto@2x.png`, `icon@1x.jpg` |
| `noreply`/`no-reply` | `noreply@empresa.com` |
| Dominios ignorados | `xxx@sentry.io`, `xxx@wixpress.com`, `xxx@example.com` |
| Pattern `\d+x` (retina) | `2x@` (match `re.fullmatch(r"\d+x", local)`) |
| Duplicatas | Deduplicacao case-insensitive |

**Integracao Hunter.io (opcional):**

Se `HUNTER_API_KEY` esta configurado:

```python
resp = requests.get(
    "https://api.hunter.io/v2/domain-search",
    params={"domain": domain, "api_key": settings.hunter_api_key, "limit": 10},
    timeout=15,
)
```

Emails do Hunter sao **adicionados** aos encontrados no HTML (sem duplicatas).

**Priorizacao de email:**

Quando nao ha email existente no lead, o provider seleciona o mais relevante:

```python
preferred = next(
    (e for e in emails_found if domain and e.endswith(f"@{domain}")),
    emails_found[0],
)
```

**Regra:** Email com dominio igual ao do site e preferido. Se nenhum email
bate com o dominio, o primeiro encontrado e usado.

Exemplo:
- Site: `https://padaria.com.br`
- Emails encontrados: `["contato@gmail.com", "joao@padaria.com.br"]`
- Selecionado: `joao@padaria.com.br` (domain-matching)

**`can_run()`:**

```python
def can_run(self, lead, context=None) -> bool:
    has_html = bool(context and context.html_content)
    has_website = bool(getattr(lead, "website", None) or
                       (context and context.discovered_website))
    return has_html or has_website
```

Pode rodar com HTML (para regex) **ou** apenas com website (para Hunter.io).

**Saida:**

```python
{
    "site_analysis": {
        "emails_found": ["contato@empresa.com.br", "vendas@empresa.com.br"]
    },
    "email": "contato@empresa.com.br"    # Apenas se lead.email era None
}
```

---

### 5.6 ApolloProvider

**Arquivo:** `providers/apollo_enricher.py`

| Atributo | Valor |
|----------|-------|
| `name` | `apollo` |
| `cost` | `freemium` |
| `required_fields` | `["website"]` |

**O que faz:**

1. Extrai o dominio do website do lead
2. Se nao tem website, tenta extrair dominio do email
3. Consulta Apollo.io Organization Enrichment API
4. Retorna dados corporativos (industria, tamanho, LinkedIn, etc.)

**Resolucao de dominio (fallback para email):**

```python
website = getattr(lead, "website", None) or (
    context.discovered_website if context else None
)
domain = _extract_domain(website or "")
if not domain:
    email = getattr(lead, "email", None) or ""
    if "@" in email:
        domain = email.split("@", 1)[1].strip().lower()
```

**`can_run()`:**

```python
def can_run(self, lead, context=None) -> bool:
    if not settings.apollo_api_key:
        return False
    website = getattr(lead, "website", None) or (
        context.discovered_website if context else None
    )
    email = getattr(lead, "email", None)
    return bool(website or email)
```

Requer `APOLLO_API_KEY` configurado. Sem chave, o provider e automaticamente
ignorado.

**Tratamento de rate limit:**

```python
if resp.status_code == 429:
    return ProviderResult(
        success=False, data={}, errors=["http 429 rate limit"], source=self.name
    )
```

Rate limit 429 retorna `success=False` -- o provider registra o erro mas nao
lanca excecao, permitindo que os demais providers continuem.

**Saida:**

```python
{
    "site_analysis": {
        "apollo_data": {
            "name": "Empresa XYZ",
            "description": "Descricao curta...",
            "industry": "Restaurants",
            "estimated_num_employees": 25,
            "linkedin_url": "https://linkedin.com/company/empresa-xyz",
            "founded_year": 2015,
            "logo_url": "https://..."
        }
    }
}
```

---

## 6. Scoring

**Arquivo:** `enrichment/scoring.py`

O score de oportunidade (0-100) e **aditivo**: cada deficiencia encontrada no
site adiciona pontos. Quanto **maior** o score, **pior** o site, **mais
oportunidade** de venda.

### 6.1 Casos Extremos (Early Return)

| Condicao | Score | Reason |
|----------|-------|--------|
| Sem website | 95 | "Sem website -- oportunidade maxima" |
| Site com erro (connection_error, timeout, ssl_error) | 85 | "Site com problemas: {status}" |

### 6.2 Criterios de Site (status == "ok")

| Criterio | Pontos | Reason |
|----------|--------|--------|
| Sem HTTPS/SSL | +15 | "Sem HTTPS/SSL" |
| Sem meta viewport (nao responsivo) | +15 | "Site nao e responsivo (mobile)" |
| Sem link WhatsApp | +10 | "Sem link de WhatsApp" |
| Sem CTA (call-to-action) | +10 | "Sem CTA claro (call-to-action)" |
| PageSpeed < 50 | +10 | "PageSpeed baixo ({score}/100)" |
| Conteudo escasso (< 200 palavras) | +10 | "Conteudo muito escasso" |
| Sem Google Analytics/tracking | +8 | "Sem Google Analytics/tracking" |
| Sem chatbot/atendimento | +8 | "Sem chatbot/atendimento online" |
| Template generico (Wix/WordPress.com) | +5 | "Usa template generico (Wix/WordPress.com)" |
| Quase sem imagens (< 2) | +5 | "Quase sem imagens" |
| Sem links para redes sociais | +5 | "Sem links para redes sociais" |
| Sem dados estruturados (schema.org) | +3 | "Sem dados estruturados (schema.org)" |

**Score maximo possivel de criterios de site: 104** (limitado a 100 pelo cap)

### 6.3 Sinais Adicionais

| Criterio | Pontos | Reason |
|----------|--------|--------|
| Tech stack defasado | +5 | "Tech stack defasado detectado" |
| Email nao profissional | +5 | "Email nao profissional (gmail/hotmail/etc)" |
| Empresa com 5+ anos e score >= 50 | +2 | "Empresa com N anos mas presenca digital fraca" |

**Deteccao de tech defasado:**

```python
_DATED_TECH_NAMES = {"adobe flash", "flash", "silverlight", "jquery 1", "jquery 2"}
```

Qualquer tecnologia no `tech_stack` cujo nome contenha um desses termos (case-insensitive)
e considerada defasada.

**Deteccao de email generico:**

```python
_GENERIC_EMAIL_DOMAINS = {
    "gmail.com", "hotmail.com", "yahoo.com", "outlook.com", "yahoo.com.br",
    "bol.com.br", "uol.com.br", "live.com", "icloud.com",
}
```

### 6.4 Cap

```python
return min(score, 100), reasons
```

O score e sempre limitado a 100, independente de quantos criterios forem atingidos.

### 6.5 Exemplo de Calculo

```
Lead: site sem SSL, sem responsividade, sem WhatsApp, sem CTA,
      PageSpeed 35, usa Wix, email gmail.com

Score: 15 + 15 + 10 + 10 + 10 + 5 + 5 = 70
Reasons: [
    "Sem HTTPS/SSL",
    "Site nao e responsivo (mobile)",
    "Sem link de WhatsApp",
    "Sem CTA claro (call-to-action)",
    "PageSpeed baixo (35/100)",
    "Usa template generico (Wix/WordPress.com)",
    "Email nao profissional (gmail/hotmail/etc)"
]
```

---

## 7. Precedencia de Dados

O sistema de merge no `execute()` segue regras estritas para evitar perda de dados:

### 7.1 Campos Protegidos (Flat Fields)

```
Prioridade: lead existente > primeiro provider > segundo provider > ...
```

Os campos em `_PROTECTED_KEYS` seguem a regra **"dados existentes no lead nunca
sao sobrescritos"** e **"first-writer wins"** entre providers:

```python
for key in _PROTECTED_KEYS:
    if key not in data or not data[key]:   # Provider nao forneceu -> pula
        continue
    if existing_flat.get(key):              # Lead ja tinha -> protegido
        continue
    if flat.get(key):                       # Outro provider ja escreveu -> first-writer wins
        continue
    flat[key] = data[key]
```

**Exemplo:**

```
Lead existente:    { email: "joao@empresa.com", website: None }
CnpjProvider:     { website: "www.empresa.com.br" }
EmailDiscoverer:  { email: "contato@empresa.com.br" }

Resultado flat:
  email   -> "joao@empresa.com"          (protegido, ja existia no lead)
  website -> "www.empresa.com.br"        (first-writer: CnpjProvider)
```

### 7.2 Dados Estruturados

| Tipo | Estrategia de Merge |
|------|---------------------|
| `site_analysis` | `dict.update()` -- acumulativo, chaves posteriores sobrescrevem |
| `social_profiles` | `dict.update()` -- acumulativo |
| `tech_stack` | **Substituicao total** -- ultimo provider ganha |
| `socios` | **Substituicao total** -- ultimo provider ganha |

### 7.3 `enrichment_sources` (Idempotencia)

A lista `enrichment_sources` e **reconstruida do zero** a cada execucao. Nao ha
acumulo com execucoes anteriores. Isso garante idempotencia: re-enriquecer um
lead produz um historico limpo.

```python
enrichment_sources: list = []  # Limpo a cada execute()
```

Cada entrada registra:

```python
{
    "provider": "website_crawler",
    "status": "ok",           # "ok" | "skipped" | "error"
    "timestamp": "2026-04-10T14:30:00+00:00",
    "error": "..."            # Opcional, presente em skipped/error
}
```

---

## 8. Override do Usuario

O orchestrator aceita dois parametros para controle manual:

### 8.1 `skip_providers`

Remove providers do plano **independente** de elegibilidade:

```python
orch.run(lead, skip_providers=["website_crawler", "apollo"])
```

O Crawler e Apollo **nao rodarao**, mesmo que o lead tenha website e API key.

### 8.2 `force_providers`

Adiciona providers ao plano **mesmo que `can_run()` retorne False**:

```python
orch.run(lead, force_providers=["apollo"])
```

Apollo sera incluido no plano mesmo sem API key. Porem, o re-check em `execute()`
ainda ocorre -- se `can_run()` retornar False na execucao, o provider sera
marcado como "skipped".

### 8.3 Regra de Precedencia: Skip > Force

```python
force = set(force_providers or []) - skip  # skip overrides force
```

Se o mesmo provider aparece em ambos, **skip ganha**:

```python
orch.run(lead,
    skip_providers=["apollo"],
    force_providers=["apollo"]  # Ignorado -- skip tem precedencia
)
# Apollo NAO roda
```

### 8.4 Diagrama de Decisao

```
Para cada provider em _PHASE_ORDER:

  name in skip?
    |-- Sim --> PULA
    |-- Nao --> name in force?
                  |-- Sim --> INCLUI (sem checar can_run)
                  |-- Nao --> name in optimistic_names?
                                |-- Sim --> INCLUI
                                |-- Nao --> can_run(lead)?
                                              |-- True  --> INCLUI
                                              |-- False --> PULA
```

---

## 9. Edge Cases

### 9.1 Plano Vazio

Se nenhum provider e elegivel (lead sem CNPJ e sem website), o plano e uma lista
vazia. O `execute()` pula direto para o scoring, que retorna score 95
("Sem website -- oportunidade maxima").

### 9.2 Crash de Provider

Providers que lancam excecoes nao impedem os demais:

```python
except Exception as exc:
    logger.exception("provider %s crashed", provider.name)
    source_entry["status"] = "error"
    source_entry["error"] = str(exc)[:200]
```

O erro e registrado em `enrichment_sources` e a execucao continua com o proximo
provider. Isso e critico para resiliencia -- um timeout no Apollo nao pode
impedir o calculo de score.

### 9.3 Website Vazio (String Vazia)

A funcao `_normalize_url()` trata strings vazias e whitespace-only como `None`:

```python
value = str(value).strip()
if not value:
    return None
```

Portanto, `lead.website = ""` e equivalente a `lead.website = None`.

### 9.4 JSON-LD com `@graph`

O `SchemaOrgProvider` achata `@graph` recursivamente:

```json
{
  "@graph": [
    { "@type": "WebSite", "name": "..." },
    { "@type": "Organization",
      "@graph": [
        { "@type": "LocalBusiness", ... }
      ]
    }
  ]
}
```

Todos os tipos sao extraidos e o de maior prioridade e selecionado.

### 9.5 JSON-LD Malformado

Erros de parse JSON sao capturados individualmente por `<script>`:

```python
except (json.JSONDecodeError, ValueError) as exc:
    errors.append(f"jsonld parse: {str(exc)[:80]}")
    continue  # Proximo <script>, nao aborta
```

Um bloco malformado nao impede o parse dos demais blocos na mesma pagina.

### 9.6 `@type` como Lista

Alguns sites emitem `@type` como lista: `"@type": ["LocalBusiness", "Restaurant"]`.
O scoring de tipo usa apenas o primeiro elemento:

```python
def _score_type(type_value) -> int:
    if isinstance(type_value, list) and type_value:
        type_value = type_value[0]
```

### 9.7 Retorno Invalido de Provider

Se `run()` retorna algo que nao e `ProviderResult`:

```python
if not isinstance(result, ProviderResult):
    source_entry["status"] = "error"
    source_entry["error"] = "invalid result type"
    enrichment_sources.append(source_entry)
    continue
```

O provider e marcado como erro e o proximo e executado.

### 9.8 Email Falso Positivo de Imagem Retina

URLs de imagem retina como `image@2x.png` casam com o regex de email.
O filtro `_filter_emails()` trata isso de duas formas:

```python
if e_lower.endswith(_IMAGE_EXTS):          # Filtro 1: extensao de imagem
    continue
if re.fullmatch(r"\d+x", local):           # Filtro 2: pattern retina (2x, 3x)
    continue
```

---

## 10. Configuracao

### 10.1 Variaveis de Ambiente

| Variavel | Obrigatoria | Usada por | Descricao |
|----------|:-----------:|-----------|-----------|
| `HUNTER_API_KEY` | Nao | `EmailDiscovererProvider` | API key do Hunter.io para busca de emails por dominio |
| `APOLLO_API_KEY` | Nao | `ApolloProvider` | API key do Apollo.io para enrichment corporativo |
| `APIFY_TOKEN` | Nao* | `WebsiteCrawlerProvider` | Token Apify para scraping de perfis sociais (Instagram, LinkedIn) |

*`APIFY_TOKEN` e obrigatorio para o scraper de Google Maps, mas opcional para o enrichment (usado apenas para social scraping).

### 10.2 Comportamento sem API Keys

| Sem chave | Comportamento |
|-----------|--------------|
| Sem `HUNTER_API_KEY` | EmailDiscoverer roda apenas com regex no HTML |
| Sem `APOLLO_API_KEY` | ApolloProvider.can_run() retorna False, provider ignorado automaticamente |
| Sem `APIFY_TOKEN` | WebsiteCrawler pula scraping de perfis sociais |

### 10.3 Flag `skip_social_scraping`

```python
skip_social = getattr(settings, "skip_social_scraping", False)
if getattr(settings, "apify_token", "") and not skip_social:
    # scrape social profiles...
```

Permite desabilitar social scraping mesmo com `APIFY_TOKEN` configurado (util
para testes ou ambientes com rate limit restrito).

---

## 11. Legacy Wrapper

**Arquivo:** `backend/app/pipeline/enricher.py`

O modulo `enricher.py` e o enriquecedor original do projeto. Ele ainda existe
e exporta funcoes usadas pelos novos providers:

### 11.1 Funcoes Reutilizadas

| Funcao | Usada por |
|--------|-----------|
| `analyze_html()` | `WebsiteCrawlerProvider` |
| `check_pagespeed()` | `WebsiteCrawlerProvider` |
| `scrape_social_profiles()` | `WebsiteCrawlerProvider` |

### 11.2 `enrich_lead_via_orchestrator()`

Funcao bridge que conecta o codigo legado ao novo orchestrator:

```python
def enrich_lead_via_orchestrator(
    lead,
    skip_providers: list[str] | None = None,
    force_providers: list[str] | None = None,
) -> dict:
    from app.pipeline.enrichment.orchestrator import EnrichmentOrchestrator
    orch = EnrichmentOrchestrator()
    return orch.run(lead, skip_providers=skip_providers,
                    force_providers=force_providers)
```

**Nota sobre lazy import:** O import do `EnrichmentOrchestrator` e feito dentro
da funcao para evitar dependencia circular:

```
enricher.py -> orchestrator.py -> website_crawler.py -> enricher.py
```

### 11.3 Funcao Legada `enrich_lead_data()`

A funcao original `enrich_lead_data(website, lead_info)` ainda existe e funciona.
Ela executa o pipeline antigo (sem CNPJ, sem tech stack, sem Schema.org, sem
Apollo) mas inclui o diagnostic LangGraph (`run_diagnostic()`).

O novo orchestrator **nao** executa o diagnostic -- essa responsabilidade ficou
no pipeline runner (`_run_enrich` em `routers/pipeline.py`).

---

## Apendice: Fluxo Completo de Dados

```
Lead chega do Scraper
  |
  v
Orchestrator.plan()
  |
  v
[CnpjProvider] -----> BrasilAPI
  |                    |
  |  context.discovered_website = "www.empresa.com.br"
  |  data: { razao_social, porte, cnae, data_fundacao, socios, website }
  |
  v
[WebsiteCrawlerProvider] -----> GET https://www.empresa.com.br
  |                              |
  |  context.html_content = "<html>..."
  |  context.response_headers = { "Server": "nginx", ... }
  |  data: { site_analysis: { status, has_ssl, has_responsive_meta, ... } }
  |
  v
[SchemaOrgProvider] -----> Parse JSON-LD do context.html_content
  |  data: { site_analysis: { structured_data: { type, name, ... } } }
  |
  v
[TechStackProvider] -----> Pattern-match no context.html_content + headers
  |  data: { tech_stack: [ { name, category }, ... ] }
  |
  v
[EmailDiscovererProvider] -----> Regex no HTML + Hunter.io (opcional)
  |  data: { site_analysis: { emails_found: [...] }, email: "..." }
  |
  v
[ApolloProvider] -----> Apollo.io Organization Enrichment API
  |  data: { site_analysis: { apollo_data: { industry, employees, ... } } }
  |
  v
calculate_score() -----> Avalia todos os dados acumulados
  |  score: 70, reasons: ["Sem HTTPS/SSL", "Sem WhatsApp", ...]
  |
  v
Resultado final mesclado:
{
  "opportunity_score": 70,
  "opportunity_reasons": ["Sem HTTPS/SSL", ...],
  "site_analysis": { status, has_ssl, ..., structured_data, apollo_data, ... },
  "social_profiles": { instagram: {...}, ... },
  "tech_stack": [ { name, category }, ... ],
  "socios": [ { nome: "..." }, ... ],
  "enrichment_sources": [ { provider, status, timestamp }, ... ],
  "razao_social": "EMPRESA LTDA",
  "porte": "ME",
  "cnae": "Restaurantes e similares",
  "data_fundacao": "2018-03-15",
  "website": "www.empresa.com.br",
  "email": "contato@empresa.com.br"
}
```
