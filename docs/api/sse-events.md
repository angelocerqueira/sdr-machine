# Server-Sent Events (SSE)

## Como Funciona

O SDR Machine usa Server-Sent Events para transmitir o progresso dos jobs de pipeline em tempo real. A implementacao esta em `backend/app/routers/pipeline.py` e utiliza a biblioteca `sse-starlette`.

### Arquitetura

```
[Background Task]  ──emit()──>  [_job_events dict]  ──poll 0.5s──>  [EventSourceResponse]  ──SSE──>  [Frontend]
```

1. **Event store em memoria**: um dicionario global `_job_events: dict[int, list[dict]]` armazena os eventos de cada job, indexados por `job_id`.
2. **Emissao**: a funcao `_emit(job_id, event)` adiciona eventos ao store. E chamada pelas background tasks (`_run_scrape`, `_run_enrich`, etc.) a cada etapa do processamento.
3. **Streaming**: o endpoint `GET /api/jobs/{job_id}/stream` retorna um `EventSourceResponse` que faz polling do store a cada 0.5 segundos e envia eventos novos ao cliente.

### Endpoint

```
GET /api/jobs/{job_id}/stream
```

- **Content-Type:** `text/event-stream`
- **Autenticacao:** requer sessao valida (cookie ou Bearer token)
- **Formato:** cada evento e uma linha `data: {JSON}\n\n` seguindo o protocolo SSE

---

## Lifecycle

O ciclo de vida de eventos SSE acompanha o ciclo de vida do job:

```
1. POST /api/pipeline/scrape (ou enrich/generate/outreach)
   │
   ├── Job criado no banco com status "pending"
   ├── BackgroundTask agendada
   │
2. Background task inicia
   │
   ├── Job.status → "running"
   ├── _emit(job_id, {"type": "started", "job_id": 12})
   │
3. Processamento iterativo
   │
   ├── Para cada item processado:
   │   └── _emit(job_id, {"type": "progress", "current": N, "total": M})
   │
4a. Sucesso
   │
   ├── Job.status → "done" ou "done_with_errors"
   ├── _emit(job_id, {"type": "done", "summary": {...}})
   ├── Timer de 60s inicia para limpeza
   │
4b. Falha catastrofica
   │
   ├── Job.status → "failed"
   ├── _emit(job_id, {"type": "error", "message": "..."})
   ├── Timer de 60s inicia para limpeza
   │
5. Apos 60 segundos
   │
   └── _job_events[job_id] removido do dicionario
```

---

## Event Types

### `started`

Emitido quando a background task comeca a executar.

```json
{
  "type": "started",
  "job_id": 12
}
```

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `type` | `string` | Sempre `"started"`. |
| `job_id` | `int` | ID do job. |

---

### `progress`

Emitido apos cada item processado (cada lead scrapeado, enriquecido, etc.).

```json
{
  "type": "progress",
  "current": 15,
  "total": 50
}
```

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `type` | `string` | Sempre `"progress"`. |
| `current` | `int` | Numero do item atual (1-indexed). |
| `total` | `int` | Total de itens a processar. |

A porcentagem de progresso pode ser calculada como `(current / total) * 100`.

---

### `done`

Emitido quando o job termina (com ou sem erros por lead).

```json
{
  "type": "done",
  "summary": {
    "created": 23,
    "total_scraped": 25,
    "errors": [
      "Lead Clinica XYZ: duplicate phone"
    ]
  }
}
```

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `type` | `string` | Sempre `"done"`. |
| `summary` | `object` | Resumo do resultado. Campos variam por tipo de job. |

**Campos do `summary` por tipo de job:**

| Tipo de Job | Campos do Summary |
|-------------|-------------------|
| `scrape` | `created: int`, `total_scraped: int`, `errors: string[]` |
| `enrich` | `enriched: int`, `total: int`, `errors: string[]` |
| `generate` | `generated: int`, `total: int`, `errors: string[]` |
| `outreach` | `messaged: int`, `total: int`, `errors: string[]` |

> **Nota:** O job pode terminar com status `"done_with_errors"` no banco, mas o evento SSE sempre sera `"done"` -- o array `errors` no summary indica quais leads falharam individualmente.

---

### `error`

Emitido quando o job falha de forma catastrofica (excecao nao tratada no nivel do job, nao de um lead individual).

```json
{
  "type": "error",
  "message": "Connection refused: could not connect to Apify API"
}
```

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `type` | `string` | Sempre `"error"`. |
| `message` | `string` | Mensagem de erro (truncada em 500 caracteres). |

---

## Integracao Frontend

### Conectando via `streamJob()`

O frontend conecta ao SSE atraves da funcao `streamJob()` em `lib/api.ts`. Ela usa `fetch()` com leitura de stream (nao `EventSource` nativo) para poder incluir o header `Authorization`:

```typescript
import { streamJob } from "@/lib/api";

// Inicia o streaming
const abort = streamJob(jobId, (event) => {
  switch (event.type) {
    case "started":
      console.log("Job iniciado");
      break;
    case "progress":
      console.log(`Progresso: ${event.current}/${event.total}`);
      break;
    case "done":
      console.log("Job concluido", event.summary);
      break;
    case "error":
      console.error("Job falhou", event.message);
      break;
  }
});

// Para cancelar o streaming manualmente:
abort();
```

### Como funciona internamente

A funcao `streamJob()`:

1. Extrai o token de sessao do cookie `session_data`.
2. Faz `fetch()` para `GET /api/jobs/{id}/stream` com header `Authorization: Bearer <token>`.
3. Le o `ReadableStream` do response body com um `TextDecoder`.
4. Faz parse das linhas SSE: identifica linhas que comecam com `data: ` e faz `JSON.parse()` do conteudo.
5. Chama o callback `onEvent` para cada evento.
6. Quando recebe um evento `done` ou `error`, aborta a conexao via `AbortController`.
7. Retorna uma funcao `abort()` para cancelamento externo.

### Tratamento de 401

Se o endpoint SSE retornar `401`, a funcao chama `forceLogout()` que limpa os cookies de sessao e redireciona para `/login`.

### Exemplo de uso no componente `job-progress.tsx`

No frontend, o componente `job-progress.tsx` consome o stream e exibe uma barra de progresso com log de mensagens:

```typescript
useEffect(() => {
  if (!jobId) return;

  const abort = streamJob(jobId, (event) => {
    if (event.type === "progress") {
      setProgress({ current: event.current, total: event.total });
      addLog(`Processando ${event.current}/${event.total}...`);
    } else if (event.type === "done") {
      setStatus("done");
      onJobDone?.(); // Dispara reload da pagina
    } else if (event.type === "error") {
      setStatus("error");
      addLog(`Erro: ${event.message}`);
    }
  });

  return () => abort(); // Cleanup ao desmontar
}, [jobId]);
```

---

## Cleanup

### Limpeza automatica

Quando um evento `done` ou `error` e emitido, a funcao `_emit()` agenda um `threading.Timer` de **60 segundos** para remover os eventos do dicionario:

```python
def _emit(job_id: int, event: dict):
    if job_id not in _job_events:
        _job_events[job_id] = []
    _job_events[job_id].append(event)
    if event.get("type") in ("done", "error"):
        threading.Timer(60, lambda: _job_events.pop(job_id, None)).start()
```

Os 60 segundos de delay permitem que clientes que se conectaram tarde (ou reconectaram) ainda recebam o evento final antes da limpeza.

### Reconexao tardia

Se um cliente conectar ao stream apos o job ter terminado mas antes da limpeza (dentro dos 60s):

1. O endpoint encontra todos os eventos no `_job_events[job_id]`.
2. Envia todos de uma vez (started, progress, progress, ..., done).
3. Fecha a conexao ao encontrar o evento terminal.

Se conectar apos a limpeza (depois dos 60s):

1. `_job_events.get(job_id, [])` retorna lista vazia.
2. O stream fica em loop infinito de polling sem nunca receber eventos.
3. O cliente deve implementar um timeout e consultar `GET /api/jobs/{job_id}` para verificar o status final.

---

## Limitacoes

### Armazenamento em memoria

Os eventos SSE sao armazenados em um dicionario Python em memoria (`_job_events`). Isso significa:

- **Perda em restart**: se o servidor reiniciar durante um job, todos os eventos sao perdidos. O job ficara com status `running` no banco mas sem stream ativo. O frontend deve tratar isso consultando `GET /api/jobs/{job_id}` como fallback.
- **Uso de memoria**: em cenarios com muitos jobs simultaneos e muitos leads, o dicionario pode crescer. Na pratica, a limpeza automatica de 60s mitiga isso.

### Single-instance only

O event store e local ao processo Python. Em um deploy com **multiplas instancias** (ex.: 2+ replicas no Railway):

- O stream SSE so funciona se o cliente conectar na mesma instancia que esta executando o job.
- Nao ha sincronizacao entre instancias.
- Para escalar, seria necessario migrar o event store para Redis Pub/Sub ou similar.

### Sem persistencia de eventos

Os eventos nao sao salvos no banco de dados. Para historico de jobs, use `GET /api/jobs/{job_id}` que retorna `result_summary` e `error_message` persistidos no PostgreSQL.

### Sem reconnect automatico

A implementacao atual no frontend nao usa `EventSource` nativo (que tem reconnect automatico) porque precisa enviar o header `Authorization`. Em vez disso, usa `fetch()` com `ReadableStream`. Se a conexao cair, o stream nao reconecta automaticamente -- o componente precisa ser remontado.

### Polling interval fixo

O servidor faz polling do event store a cada **0.5 segundos**. Isso significa que pode haver ate 500ms de latencia entre a emissao de um evento e sua entrega ao cliente. Para a maioria dos casos de uso (scraping que leva minutos), isso e imperceptivel.
