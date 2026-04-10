# Pipeline — Visao Geral Tecnica

## 1. Como o Pipeline Funciona

O pipeline do SDR Machine e composto por 4 estagios independentes, cada um executado como um **background task** do FastAPI. Quando o usuario dispara um estagio (ex: `POST /api/pipeline/scrape`), o sistema:

1. Verifica se ja existe um job do mesmo tipo em execucao (retorna `409 Conflict` se sim)
2. Cria um registro `Job` no banco com `status="pending"`
3. Registra o background task via `BackgroundTasks.add_task()`
4. Retorna o `Job` imediatamente (o endpoint nao bloqueia)
5. O background task roda em thread separada, atualizando o banco e emitindo eventos SSE

O codigo de dispatch fica em `backend/app/routers/pipeline.py`:

```python
def _start_job(job_type: str, params: dict, bg: BackgroundTasks, db: Session) -> Job:
    existing = db.query(Job).filter(Job.type == job_type, Job.status == "running").first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Ja existe um job '{job_type}' em execucao (#{existing.id})"
        )
    job = Job(type=job_type, params=params)
    db.add(job)
    db.commit()
    db.refresh(job)
    bg.add_task(_RUNNERS[job_type], job.id, params)
    return job
```

Os 4 runners sao registrados em um dicionario:

```python
_RUNNERS = {
    "scrape": _run_scrape,
    "enrich": _run_enrich,
    "generate": _run_generate,
    "outreach": _run_outreach,
}
```

---

## 2. Ciclo de Vida de um Job

### Status do Job

```
pending ──> running ──┬──> done
                      ├──> done_with_errors
                      └──> failed
```

| Status | Descricao |
|---|---|
| `pending` | Job criado, aguardando inicio do background task |
| `running` | Background task em execucao, processando leads |
| `done` | Todos os leads processados com sucesso |
| `done_with_errors` | Concluido, mas alguns leads falharam (erros em `result_summary.errors`) |
| `failed` | Excecao fatal — o job inteiro falhou |

### Timeline de Eventos SSE

```
1. Job criado (status=pending)
   │
   ▼
2. Background task inicia
   ├── job.status = "running"
   ├── job.started_at = now()
   └── Emite: {"type": "started", "job_id": 123}
   │
   ▼
3. Loop por cada lead/item
   ├── Processa lead
   ├── Emite: {"type": "progress", "current": 1, "total": 50}
   ├── Processa proximo lead...
   ├── Emite: {"type": "progress", "current": 2, "total": 50}
   └── (repete ate o fim)
   │
   ▼
4a. Sucesso (com ou sem erros por lead)
    ├── job.status = "done" ou "done_with_errors"
    ├── job.result_summary = {success_count, total, errors: [...]}
    ├── job.finished_at = now()
    └── Emite: {"type": "done", "summary": {...}}

4b. Falha fatal (excecao nao capturada)
    ├── db.rollback()
    ├── job.status = "failed"
    ├── job.error_message = str(exc)[:500]
    ├── job.finished_at = now()
    └── Emite: {"type": "error", "message": "..."}
```

---

## 3. Pattern de Background Task

Todos os 4 runners seguem exatamente o mesmo pattern. Abaixo esta a estrutura completa, usando `_run_enrich` como exemplo:

```python
def _run_enrich(job_id: int, params: dict):
    from app.pipeline.enricher import enrich_lead_via_orchestrator

    db = SessionLocal()                        # 1. Sessao propria (nao usa get_db)
    try:
        job = db.get(Job, job_id)
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()
        _emit(job_id, {"type": "started", "job_id": job_id})

        # ... busca leads ...

        enriched = 0
        errors: list[str] = []
        for idx, lead in enumerate(leads):
            try:                               # 2. Try/except POR LEAD
                result = enrich_lead_via_orchestrator(lead, ...)
                lead.opportunity_score = result.get("opportunity_score")
                # ... aplica demais campos ...
                lead.status = "enriched"
                enriched += 1
                db.commit()
                _emit(job_id, {"type": "progress", "current": idx + 1, "total": len(leads)})
            except Exception as exc:
                db.rollback()                  # 3. Rollback por lead
                lead.status = "enrich_failed"  # 4. Status de falha individual
                db.commit()
                errors.append(f"Lead {lead.id} ({lead.nome}): {str(exc)[:120]}")

        job.status = "done_with_errors" if errors else "done"
        job.result_summary = {"enriched": enriched, "total": len(leads), "errors": errors}
        job.finished_at = datetime.utcnow()
        db.commit()
        _emit(job_id, {"type": "done", "summary": job.result_summary})

    except Exception as exc:                   # 5. Catch global (falha fatal)
        db.rollback()
        job = db.get(Job, job_id)
        if job:
            job.status = "failed"
            job.error_message = str(exc)[:500]
            job.finished_at = datetime.utcnow()
            db.commit()
        _emit(job_id, {"type": "error", "message": str(exc)[:500]})
    finally:
        db.close()                             # 6. Sempre fecha sessao
```

### Pontos-chave do Pattern

1. **Sessao propria via `SessionLocal()`:** O background task roda em thread separada do request. Usar `get_db()` (que e request-scoped) causaria compartilhamento de sessao entre threads. Por isso, cada runner cria sua propria sessao e fecha no `finally`.

2. **Try/except por lead:** Erros em leads individuais nao interrompem o processamento dos demais. O lead que falhou recebe um status de falha (`enrich_failed`, `generate_failed`, etc.), e o erro e registrado na lista `errors`.

3. **Rollback por lead:** Quando um lead falha, apenas a transacao pendente daquele lead e revertida (`db.rollback()`). O lead recebe o status de falha em um novo commit limpo.

4. **Catch global:** Se algo falhar fora do loop de leads (ex: erro ao consultar o banco), o job inteiro recebe `status="failed"` com a mensagem de erro truncada em 500 caracteres.

5. **Lazy imports:** Os modulos do pipeline sao importados dentro da funcao (nao no topo do arquivo) para evitar dependencias circulares e reduzir tempo de startup.

---

## 4. Resumo dos 4 Estagios

### Estagio 1: Scrape (`backend/app/pipeline/scraper.py`)

Busca negocios locais no Google Maps via API Apify (`compass/crawler-google-places`). Recebe listas de nichos e cidades, itera todas as combinacoes `nicho x cidade`, e chama a API com timeout de 120s e 1024MB de memoria. Os resultados sao filtrados por `min_rating` (default 3.0) e deduplicados por telefone ou nome do negocio. Cada lead e extraido com nome, telefone, website, endereco, rating, reviews (top 3, max 200 chars cada) e URL do Google Maps. Erros de HTTP por combinacao sao silenciados (lista vazia retornada). **Input:** nichos, cidades, max_results. **Output:** leads com `status="scraped"`, `result_summary.created` e `result_summary.total_scraped`.

### Estagio 2: Enrich (`backend/app/pipeline/enricher.py`)

Analisa e enriquece cada lead `scraped` usando um pipeline de providers orquestrado pelo `EnrichmentOrchestrator`. Os providers executam em fases ordenadas: (1) CNPJ via BrasilAPI — pode descobrir website, razao social, socios; (2) crawl do site — fetch HTML, analise BeautifulSoup, deteccao Schema.org e tech stack; (3) descoberta de contato via Hunter.io e Apollo; (4) recalculo do opportunity score (0-100, aditivo: sem SSL +15, nao responsivo +15, sem WhatsApp +10, sem CTA +10, sem analytics +8, sem chatbot +8, PageSpeed <50 +10, conteudo escasso +10, template generico +5, poucas imagens +5; sem website = 95; site fora do ar = 85). Opcionalmente executa diagnostico de marketing via LLM e scraping de redes sociais (Instagram e LinkedIn via Apify). **Input:** lead_ids ou todos os leads `scraped`. **Output:** leads com `status="enriched"` ou `"disqualified"`, com `opportunity_score`, `opportunity_reasons`, `site_analysis`, `social_profiles`, `tech_stack`, `email`, `cnpj`, etc.

### Estagio 3: Generate (`backend/app/pipeline/generator.py`)

Gera landing pages HTML personalizadas para cada lead `enriched` usando uma arquitetura de 2 passes de LLM. **Pass 1 (Creative Brief):** gera um JSON estruturado com paleta de cores (escolhida pelo modelo, nao hardcoded), tipografia (Google Fonts), copy completo (headlines, CTAs, FAQ, servicos), escolha de icones SVG e decisoes de layout — tudo guiado por um `NICHE_GUIDE` com mood, direcao de cor/tipografia e framework de copy (PAS, AIDA ou BAB). **Pass 2 (HTML):** gera o HTML completo a partir do brief, com gold standard de referencia visual, biblioteca de icones SVG inline, e requisitos detalhados de responsividade e animacao (GSAP + ScrollTrigger). Post-processing substitui placeholders `{{icon:nome}}` por SVGs reais. O HTML e salvo na tabela `landing_pages` (com versionamento — LPs anteriores sao desativadas) e cacheado em `lead.lp_html`. **Input:** lead_ids ou todos os leads `enriched`, max_count. **Output:** leads com `status="lp_generated"`, HTML na `landing_pages`.

### Estagio 4: Outreach (`backend/app/pipeline/outreach.py`)

Gera 3 mensagens de WhatsApp para cada lead `lp_generated`: `initial` (apresentacao + link da LP), `followup_48h` (follow-up leve) e `followup_final` (ultima mensagem). Se o lead possui diagnostico de marketing no `site_analysis`, as mensagens sao geradas via LLM com contexto do diagnostico (resumo executivo, momento no funil, prioridades, oportunidades de IA). Caso contrario, usa templates fallback diferenciados para leads com site ruim vs sem site. O telefone e normalizado com prefixo `55` (Brasil). Cada mensagem inclui um link `wa.me` pre-preenchido com o texto URL-encoded. **Input:** lead_ids ou todos os leads `lp_generated`. **Output:** 3 `OutreachMessage` por lead, status atualizado para `outreach_ready`.

---

## 5. SSE Event Format

### Infraestrutura de Eventos

Os eventos sao armazenados em um dicionario in-memory no processo do servidor:

```python
_job_events: dict[int, list[dict]] = {}
```

A funcao `_emit()` adiciona eventos a lista do job. Quando o evento e `done` ou `error`, um `threading.Timer` agenda a limpeza automatica dos eventos apos 60 segundos:

```python
def _emit(job_id: int, event: dict):
    if job_id not in _job_events:
        _job_events[job_id] = []
    _job_events[job_id].append(event)
    if event.get("type") in ("done", "error"):
        threading.Timer(60, lambda: _job_events.pop(job_id, None)).start()
```

### Endpoint SSE

`GET /api/jobs/{job_id}/stream` retorna um `EventSourceResponse` que faz polling da lista de eventos a cada 0.5 segundos:

```python
@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        sent = 0
        while True:
            events = _job_events.get(job_id, [])
            while sent < len(events):
                yield {"data": json.dumps(events[sent])}
                if events[sent].get("type") in ("done", "error"):
                    return
                sent += 1
            await asyncio.sleep(0.5)

    return EventSourceResponse(event_generator())
```

### Tipos de Evento

#### `started`

Emitido quando o background task inicia a execucao.

```json
{
  "type": "started",
  "job_id": 42
}
```

#### `progress`

Emitido apos cada lead ser processado (com sucesso ou falha individual).

```json
{
  "type": "progress",
  "current": 7,
  "total": 50
}
```

#### `done`

Emitido quando o job termina (status `done` ou `done_with_errors`).

```json
{
  "type": "done",
  "summary": {
    "created": 45,
    "total_scraped": 50,
    "errors": [
      "dentista em Chapeco SC: HTTP 429 Too Many Requests"
    ]
  }
}
```

O conteudo de `summary` varia por tipo de job:

| Tipo | Campos do `summary` |
|---|---|
| `scrape` | `created`, `total_scraped`, `errors` |
| `enrich` | `enriched`, `total`, `errors` |
| `generate` | `generated`, `total`, `errors` |
| `outreach` | `messaged`, `total`, `errors` |

#### `error`

Emitido quando o job falha fatalmente (excecao nao capturada no nivel do job).

```json
{
  "type": "error",
  "message": "sqlalchemy.exc.OperationalError: connection to server lost"
}
```

A mensagem e truncada em 500 caracteres.

### Consumo no Frontend

O frontend consome o SSE via `fetch()` com `ReadableStream` (nao usa `EventSource` nativo):

```typescript
// frontend/src/lib/api.ts
export const streamJob = (id: number, onEvent: (event: { type: string; message: string }) => void) => {
  const controller = new AbortController();

  (async () => {
    const token = getSessionToken();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(`${API}/api/jobs/${id}/stream`, {
      headers,
      signal: controller.signal,
    });
    if (res.status === 401) { forceLogout(); return; }
    if (!res.ok || !res.body) return;

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const data = JSON.parse(line.slice(6));
        onEvent(data);
        if (data.type === "done" || data.type === "error") {
          controller.abort();
          return;
        }
      }
    }
  })();

  return () => controller.abort();  // Funcao de cleanup
};
```

Essa abordagem e usada em vez de `EventSource` nativo porque permite enviar headers customizados (como `Authorization`), que o `EventSource` padrao nao suporta.

---

## 6. Error Handling

### Erros por Lead (nao fatais)

Quando o processamento de um lead individual falha, o pattern e:

1. **Rollback** da transacao pendente
2. **Marca o lead** com status de falha especifico: `enrich_failed`, `generate_failed`, `outreach_failed`
3. **Commit** do status de falha
4. **Registra o erro** na lista `errors` com formato padronizado
5. **Continua** processando os proximos leads

```python
except Exception as exc:
    db.rollback()
    lead.status = "enrich_failed"
    db.commit()
    errors.append(f"Lead {lead.id} ({lead.nome}): {str(exc)[:120]}")
```

Os erros por lead sao truncados em **120 caracteres** na mensagem.

### Erros de Job (fatais)

Quando uma excecao nao capturada escapa do loop de leads:

1. **Rollback** de qualquer transacao pendente
2. **Marca o job** com `status="failed"`
3. **Salva** a mensagem de erro truncada em **500 caracteres** no campo `error_message`
4. **Emite** evento SSE `error`
5. **Fecha** a sessao no `finally`

```python
except Exception as exc:
    db.rollback()
    job = db.get(Job, job_id)
    if job:
        job.status = "failed"
        job.error_message = str(exc)[:500]
        job.finished_at = datetime.utcnow()
        db.commit()
    _emit(job_id, {"type": "error", "message": str(exc)[:500]})
finally:
    db.close()
```

### Formato de `result_summary`

O campo `result_summary` do `Job` sempre contem:

```json
{
  "<success_metric>": 45,
  "total": 50,
  "errors": [
    "Lead 123 (Clinica Sorriso): Connection timeout after 10s",
    "Lead 456 (Pet Shop Rex): CNPJ invalido: 12.345.678/0001-99",
    "dentista em Florianopolis SC: HTTP 429 Too Many Requests"
  ]
}
```

A chave de sucesso varia: `created` (scrape), `enriched` (enrich), `generated` (generate), `messaged` (outreach).

Se `errors` e uma lista nao-vazia, o job recebe `status="done_with_errors"` em vez de `"done"`. Isso permite ao frontend mostrar um indicador amarelo (parcial) em vez de verde (completo) na interface de jobs.

### Prevencao de Jobs Concorrentes

Cada tipo de job so pode ter uma instancia `running` por vez. A funcao `_start_job` verifica isso antes de criar o job:

```python
existing = db.query(Job).filter(Job.type == job_type, Job.status == "running").first()
if existing:
    raise HTTPException(
        status_code=409,
        detail=f"Ja existe um job '{job_type}' em execucao (#{existing.id})"
    )
```

Isso previne, por exemplo, dois jobs de `scrape` rodando em paralelo e criando leads duplicados.

### Limpeza de Eventos SSE

Os eventos in-memory sao limpos automaticamente 60 segundos apos o job terminar, via `threading.Timer`. Isso garante que clientes que conectam ao stream apos o termino ainda recebem os eventos finais (por ate 1 minuto), sem acumular memoria indefinidamente.
