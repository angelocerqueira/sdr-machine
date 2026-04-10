# Scraper -- Modulo 1 do Pipeline

**Arquivo:** `backend/app/pipeline/scraper.py`

## O que faz

O modulo de scraping e o primeiro estagio do pipeline do SDR Machine. Ele consulta a API do Google Maps via Apify para buscar negocios locais (leads) em combinacoes de nicho e cidade. Para cada negocio encontrado, extrai dados de contato, avaliacao, categoria e reviews, produzindo uma lista de leads prontos para o proximo estagio (enriquecimento).

---

## API do Apify

O scraper utiliza o actor `compass/crawler-google-places` da Apify, executado de forma sincrona (aguarda o resultado no mesmo request).

### Endpoint

```
POST https://api.apify.com/v2/acts/compass~crawler-google-places/run-sync-get-dataset-items
```

### Payload enviado

```python
payload = {
    "searchStringsArray": [f"{niche} em {city}"],
    "maxCrawledPlacesPerSearch": max_results,
    "language": "pt-BR",
    "includeWebResults": False,
    "maxImages": 0,
    "maxReviews": 3,
    "onlyDataFromSearchPage": False,
}
```

| Campo | Valor | Descricao |
|-------|-------|-----------|
| `searchStringsArray` | `["{nicho} em {cidade}"]` | Query de busca no Google Maps |
| `maxCrawledPlacesPerSearch` | `max_results` (default: 50) | Limite de resultados por busca |
| `language` | `"pt-BR"` | Idioma dos resultados |
| `includeWebResults` | `False` | Nao inclui resultados da web |
| `maxImages` | `0` | Nao baixa imagens |
| `maxReviews` | `3` | Busca ate 3 reviews por negocio |
| `onlyDataFromSearchPage` | `False` | Permite navegar nas paginas de detalhe |

### Query parameters

```python
params = {
    "token": settings.apify_token,
    "timeout": 120,
    "memory": 1024,
}
```

- **timeout:** 120 segundos para o actor finalizar no Apify
- **memory:** 1024 MB de RAM alocada para o actor
- **timeout do requests:** 180 segundos (client-side, via `requests.post(..., timeout=180)`)

---

## Fluxo de Execucao

### `scrape_google_maps(niche, city, max_results)`

Funcao de baixo nivel que executa UMA busca (1 nicho x 1 cidade):

1. Monta o payload com a query `"{niche} em {city}"`
2. Envia `POST` para a API do Apify com autenticacao via token
3. Recebe a lista de resultados JSON
4. Para cada resultado:
   - Filtra por `min_rating` (descarta negocios com nota abaixo do minimo)
   - Extrai todos os campos relevantes
   - Descarta leads sem nome
5. Retorna a lista de leads

### `scrape_all(nichos, cidades, max_results)`

Funcao de alto nivel que orquestra todas as buscas:

```python
def scrape_all(nichos: list[str], cidades: list[str], max_results: int | None = None) -> tuple[list[dict], list[str]]:
```

1. Itera sobre o produto cartesiano `nichos x cidades`
2. Para cada combinacao, chama `scrape_google_maps(niche, city, max_results)`
3. Aplica deduplicacao nos resultados acumulados
4. Captura excecoes por combinacao sem parar o fluxo
5. Retorna uma tupla `(leads, erros)`

Exemplo: se `nichos = ["dentista", "restaurante"]` e `cidades = ["Chapeco SC", "Florianopolis SC"]`, serao feitas 4 chamadas ao Apify.

---

## Deduplicacao

A deduplicacao acontece em `scrape_all()` usando um `set` chamado `seen`:

```python
key = lead["telefone"] or lead["nome"]
if key and key not in seen:
    seen.add(key)
    all_leads.append(lead)
```

A logica de deduplicacao:

1. **Prioridade:** usa o telefone como chave primaria de deduplicacao
2. **Fallback:** se o lead nao tem telefone, usa o nome como chave
3. **Resultado:** o primeiro lead encontrado com aquele telefone/nome e mantido; duplicatas sao descartadas

Isso evita que o mesmo negocio apareca duas vezes quando e encontrado em buscas de nichos diferentes (ex: uma clinica que aparece tanto em "dentista" quanto em "clinica").

---

## Filtragem

A filtragem acontece dentro de `scrape_google_maps()`, apos receber os resultados da API:

```python
rating = item.get("totalScore", 0) or 0
if rating < settings.min_rating:
    continue
```

- **`min_rating`** (default: `3.0`): negocios com nota no Google abaixo desse valor sao descartados
- Negocios sem nota (`totalScore` = `None` ou `0`) tambem sao descartados
- Negocios sem nome sao descartados (verificacao `if lead["nome"]`)

---

## Dados Retornados

Cada lead e um dicionario com os seguintes campos:

| Campo | Origem (Apify) | Tipo | Descricao |
|-------|----------------|------|-----------|
| `nome` | `title` | `str` | Nome do negocio (stripped) |
| `telefone` | `phone` | `str` | Telefone de contato |
| `website` | `website` | `str` | URL do site do negocio |
| `endereco` | `address` | `str` | Endereco completo |
| `cidade` | parametro `city` | `str` | Cidade buscada (nao vem do Apify) |
| `nicho` | parametro `niche` | `str` | Nicho buscado (nao vem do Apify) |
| `rating` | `totalScore` | `float` | Nota no Google Maps (0-5) |
| `reviews_count` | `reviewsCount` | `int` | Quantidade de avaliacoes |
| `google_maps_url` | `url` | `str` | URL do perfil no Google Maps |
| `categoria` | `categoryName` | `str` | Categoria do Google Maps |
| `top_reviews` | `reviews` | `list[str]` | Ate 3 reviews (texto truncado em 200 chars) |

### Processamento dos reviews

Os reviews passam por uma filtragem antes de serem incluidos:

```python
"top_reviews": [
    r.get("text", "")[:200]
    for r in (item.get("reviews", []) or [])[:3]
    if r.get("text")
],
```

- Pega ate 3 reviews
- Filtra reviews sem texto
- Trunca cada review em 200 caracteres

---

## Error Handling

### Em `scrape_google_maps()`

A funcao utiliza `resp.raise_for_status()`, ou seja, erros HTTP (4xx, 5xx) resultam em excecao `requests.HTTPError`. **Nao ha tratamento interno** -- a excecao propaga para o chamador.

### Em `scrape_all()`

Cada combinacao nicho x cidade e executada dentro de um `try/except`:

```python
try:
    leads = scrape_google_maps(niche, city, max_results)
    # ... deduplicacao ...
except Exception as exc:
    errors.append(f"{niche} em {city}: {str(exc)[:300]}")
```

- Excecoes sao capturadas silenciosamente (a mensagem e truncada em 300 chars)
- O erro e adicionado a lista de erros retornada
- O loop continua para as proximas combinacoes
- No final, a funcao retorna tanto os leads encontrados quanto a lista de erros

Isso significa que falhas parciais nao interrompem o scraping -- se 1 de 10 combinacoes falhar, os leads das outras 9 ainda serao retornados.

---

## Configuracao

Variaveis de ambiente relevantes (definidas em `backend/.env`, carregadas via `app/config.py`):

| Variavel | Default | Descricao |
|----------|---------|-----------|
| `APIFY_TOKEN` | `""` (obrigatorio) | Token de autenticacao da API do Apify |
| `TARGET_NICHES` | `["dentista", "restaurante", "salao de beleza", ...]` | Lista de nichos para buscar (10 nichos default) |
| `TARGET_CITIES` | `["Chapeco SC", "Florianopolis SC", ...]` | Lista de cidades para buscar (5 cidades default) |
| `MIN_RATING` | `3.0` | Nota minima no Google Maps para incluir o lead |
| `MAX_RESULTS_PER_SEARCH` | `50` | Maximo de resultados por combinacao nicho x cidade |

### Nichos default

```python
target_niches = [
    "dentista", "restaurante", "salao de beleza", "clinica estetica",
    "pet shop", "academia", "barbearia", "clinica veterinaria",
    "pizzaria", "loja de roupas",
]
```

### Cidades default

```python
target_cities = [
    "Chapeco SC", "Florianopolis SC", "Joinville SC",
    "Curitiba PR", "Cascavel PR",
]
```

Com os defaults, o scraper executa `10 nichos x 5 cidades = 50 chamadas` ao Apify, buscando ate `50 resultados cada = 2.500 leads potenciais` (antes da deduplicacao e filtragem).
