# Flows Engine — F-1 Schema + Engine Backend Spec

> **Foundation:** [F-0 Architecture](2026-05-17-flows-engine-f0-architecture.md)
> **Status:** ready to plan
> **Depende:** F-0 aprovada
> **Bloqueia:** F-3 (precisa engine pra triggerar), F-4 (precisa schema pra editar), F-5 (precisa runs pra mostrar)

## 1. Objetivo

Implementar **schema relacional** + **engine executor** + **6 node types MVP** definidos em F-0 §3 + §5.

Output: API Python (`app.flows`) consumível por F-3 (API HTTP), F-4 (editor), F-5 (runtime UI). Sem rota HTTP neste sub-projeto — só camada de domínio + worker.

## 2. Arquitetura interna

```
backend/app/flows/
├── __init__.py
├── models.py             # SQLAlchemy: Flow, FlowRun, FlowRunStep
├── schemas.py            # Pydantic: FlowSpec, NodeSpec, EdgeSpec, FlowConfig
├── validation.py         # validate_flow() — checks de §6 do F-0
├── engine/
│   ├── __init__.py
│   ├── executor.py       # tick loop principal
│   ├── worker.py         # thread daemon + lifecycle
│   ├── context.py        # ExecutionContext (run, db, services injetados)
│   ├── nodes/
│   │   ├── base.py       # NodeHandler ABC
│   │   ├── send_whatsapp.py
│   │   ├── send_email.py
│   │   ├── wait.py
│   │   ├── branch_on_reply.py
│   │   ├── set_status.py
│   │   ├── start.py
│   │   └── end.py
│   └── advance.py        # advance(run, outcome) — traça próxima edge
├── services.py           # CRUD: create_flow, start_run, cancel_run, list_runs
├── templating.py         # render_template(body, lead, workspace) — Jinja2 sandbox
└── exceptions.py         # RetryableError, FatalError, ValidationError
```

## 3. Schema migration

Criar migration `alembic revision -m "flows engine schema"`:

```python
# revision r14
op.create_table(
    "flows",
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("workspace_id", sa.Integer, nullable=False, server_default="1"),
    sa.Column("name", sa.String(120), nullable=False),
    sa.Column("description", sa.Text),
    sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("false")),
    sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    sa.Column("triggers", sa.JSON, nullable=False, server_default=sa.text("'[]'::json")),
    sa.Column("nodes", sa.JSON, nullable=False, server_default=sa.text("'[]'::json")),
    sa.Column("edges", sa.JSON, nullable=False, server_default=sa.text("'[]'::json")),
    sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    sa.UniqueConstraint("workspace_id", "name", name="uq_flows_workspace_name"),
)
op.create_index("ix_flows_workspace_enabled", "flows", ["workspace_id", "enabled"])

op.create_table(
    "flow_runs",
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("flow_id", sa.Integer, sa.ForeignKey("flows.id", ondelete="CASCADE"), nullable=False),
    sa.Column("flow_version", sa.Integer, nullable=False),
    sa.Column("flow_snapshot", sa.JSON, nullable=False),  # snapshot {nodes, edges} pra evitar mid-run drift
    sa.Column("lead_id", sa.Integer, sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
    sa.Column("workspace_id", sa.Integer, nullable=False, server_default="1"),
    sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
    sa.Column("current_node_id", sa.String(40)),
    sa.Column("next_run_at", sa.DateTime),
    sa.Column("started_at", sa.DateTime),
    sa.Column("finished_at", sa.DateTime),
    sa.Column("cancel_reason", sa.Text),
    sa.Column("state", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")),
    sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
)
op.create_index("ix_flow_runs_status_next_run", "flow_runs", ["status", "next_run_at"])
op.create_index("ix_flow_runs_lead", "flow_runs", ["lead_id"])
# Partial unique: 1 run ativa por (flow, lead) — Postgres-only
op.execute("""
    CREATE UNIQUE INDEX uq_flow_runs_active_per_pair
    ON flow_runs (flow_id, lead_id)
    WHERE status IN ('pending', 'running', 'waiting');
""")

op.create_table(
    "flow_run_steps",
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("run_id", sa.Integer, sa.ForeignKey("flow_runs.id", ondelete="CASCADE"), nullable=False),
    sa.Column("node_id", sa.String(40), nullable=False),
    sa.Column("node_type", sa.String(40), nullable=False),
    sa.Column("status", sa.String(20), nullable=False),
    sa.Column("payload", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")),
    sa.Column("error", sa.Text),
    sa.Column("started_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    sa.Column("finished_at", sa.DateTime),
)
op.create_index("ix_flow_run_steps_run_started", "flow_run_steps", ["run_id", "started_at"])
```

> **Decisão schema:** JSON columns pra nodes/edges (em vez de tabela separada). Justificativa: engine sempre carrega flow inteiro, queries não filtram por node, JSON serializa direto pro editor frontend (F-4). Tabela separada teria custo de join sem benefício.

> **Decisão snapshot:** `flow_runs.flow_snapshot` JSON dump de `{nodes, edges}` no momento de criação. Engine usa snapshot, não a versão atual. Garante consistência mid-run. Tradeoff: storage extra ~5KB/run aceitável.

## 4. Pydantic schemas

```python
# schemas.py
class TriggerManual(BaseModel):
    type: Literal["manual"]

class TriggerLeadStatus(BaseModel):
    type: Literal["lead_status"]
    from_: list[str] | None = Field(None, alias="from")
    to: list[str]

class TriggerExternalWebhook(BaseModel):
    type: Literal["external_webhook"]
    secret_field: str = "webhook_secret"

Trigger = Union[TriggerManual, TriggerLeadStatus, TriggerExternalWebhook]


class NodeBase(BaseModel):
    id: str  # único dentro do flow (gerado pelo editor)
    type: str
    position: dict  # {x, y} pro editor — engine ignora
    params: dict


# Params específicos por tipo (validados em validation.py):

class SendWhatsappParams(BaseModel):
    body: str  # template Jinja-like
    media_url: str | None = None

class SendEmailParams(BaseModel):
    subject: str
    body: str  # template

class WaitParams(BaseModel):
    delay_seconds: int | None = None
    until_event: Literal["lead_reply"] | None = None
    timeout_seconds: int | None = None
    cancel_on_reply: bool = False

class BranchOnReplyParams(BaseModel):
    window_seconds: int = 86400
    match: Literal["any", "keyword"] = "any"
    pattern: str | None = None

class SetStatusParams(BaseModel):
    new_status: str

# start, end: sem params

class Edge(BaseModel):
    id: str
    source: str  # node id
    target: str  # node id
    label: Literal["out", "out_yes", "out_no"] = "out"


class FlowConfig(BaseModel):
    name: str
    description: str | None = None
    triggers: list[Trigger]
    nodes: list[NodeBase]
    edges: list[Edge]
    enabled: bool = False
```

## 5. Engine executor

```python
# engine/executor.py
class Executor:
    """Loop principal. Roda em thread dedicada (worker.py)."""

    TICK_INTERVAL_SECONDS = 2
    BATCH_SIZE = 50
    NODE_TIMEOUT_SECONDS = 30

    def __init__(self, sessionmaker, channel_registry):
        self.SessionLocal = sessionmaker
        self.channels = channel_registry  # WA + email adapters
        self.handlers = self._build_handlers()
        self._stop = threading.Event()

    def _build_handlers(self) -> dict[str, NodeHandler]:
        return {
            "start": StartHandler(),
            "send_whatsapp": SendWhatsappHandler(self.channels),
            "send_email": SendEmailHandler(self.channels),
            "wait": WaitHandler(),
            "branch_on_reply": BranchOnReplyHandler(),
            "set_status": SetStatusHandler(),
            "end": EndHandler(),
        }

    def run_forever(self):
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:
                logger.exception("flows.executor.tick_failed")
            self._stop.wait(self.TICK_INTERVAL_SECONDS)

    def tick(self):
        db = self.SessionLocal()
        try:
            runs = self._claim_runs(db, limit=self.BATCH_SIZE)
            for run in runs:
                self._execute_one(db, run)
        finally:
            db.close()

    def _claim_runs(self, db, limit: int) -> list[FlowRun]:
        # FOR UPDATE SKIP LOCKED — exclusão mútua entre workers
        return (
            db.query(FlowRun)
            .filter(FlowRun.status.in_(["pending", "waiting"]))
            .filter(
                or_(FlowRun.next_run_at.is_(None),
                    FlowRun.next_run_at <= datetime.utcnow())
            )
            .order_by(FlowRun.next_run_at.asc().nullsfirst())
            .limit(limit)
            .with_for_update(skip_locked=True)
            .all()
        )

    def _execute_one(self, db, run: FlowRun):
        snapshot = run.flow_snapshot  # {nodes, edges}
        node_id = run.current_node_id or self._find_start(snapshot)
        node = self._find_node(snapshot, node_id)
        if node is None:
            return self._fail(db, run, f"Node not found: {node_id}")

        handler = self.handlers.get(node["type"])
        if handler is None:
            return self._fail(db, run, f"No handler for type: {node['type']}")

        step = self._begin_step(db, run, node)
        run.status = "running"
        run.started_at = run.started_at or datetime.utcnow()
        db.commit()

        try:
            ctx = ExecutionContext(db=db, run=run, node=node, channels=self.channels)
            outcome = handler.execute(ctx)
            self._finish_step(db, step, "success", outcome.payload)
            advance(db, run, snapshot, outcome)
        except RetryableError as e:
            self._finish_step(db, step, "failed", {}, error=str(e))
            self._schedule_retry(db, run, e)
        except FatalError as e:
            self._finish_step(db, step, "failed", {}, error=str(e))
            self._fail(db, run, str(e))
        db.commit()

    def _schedule_retry(self, db, run, e: RetryableError):
        """Backoff exponencial 2^n minutos, max 3 retries."""
        run.state["retries"] = (run.state.get("retries", 0)) + 1
        if run.state["retries"] > 3:
            self._fail(db, run, f"Max retries exceeded: {e}")
        else:
            delay = 60 * (2 ** run.state["retries"])
            run.next_run_at = datetime.utcnow() + timedelta(seconds=delay)
            run.status = "waiting"
```

### NodeHandler ABC

```python
# engine/nodes/base.py
class NodeOutcome(TypedDict, total=False):
    next_edge_label: str          # "out" | "out_yes" | "out_no"
    next_run_at: datetime         # se waiting
    new_status: str               # se mudou run status (waiting/completed/etc)
    payload: dict                 # gravado em FlowRunStep.payload

class NodeHandler(ABC):
    @abstractmethod
    def execute(self, ctx: ExecutionContext) -> NodeOutcome: ...
```

## 6. Implementação por node

### `start`
No-op. Imediatamente avança via edge `out`.

### `send_whatsapp`
1. Render template via `templating.render_template(body, ctx.lead, ctx.workspace)`
2. Resolve provider via `whatsapp.registry.get_provider(db, workspace_id)`
3. Chama `provider.send_text(to_phone=ctx.lead.telefone, body=rendered, idempotency_key=f"flow_run_{run.id}_node_{node.id}")`
4. Salva `payload = {body, provider_message_id, sent_at}`
5. Avança via `out`
6. Erro 5xx/timeout → `RetryableError`. Erro 4xx → `FatalError`.

### `send_email`
1. Análogo a WA mas via F-2 `EmailProvider` (Resend adapter)
2. Idempotency key igual: `flow_run_{id}_node_{id}`
3. Persiste em tabela `email_messages` (criada em F-2)

### `wait`
Duas modalidades:

- **Delay fixo** (`params.delay_seconds`):
  ```python
  outcome = {
      "new_status": "waiting",
      "next_run_at": now + timedelta(seconds=params.delay_seconds),
      "payload": {"waiting_until": next_run_at.isoformat()}
  }
  ```

- **Até evento** (`params.until_event="lead_reply"` + `timeout_seconds`):
  ```python
  outcome = {
      "new_status": "waiting",
      "next_run_at": now + timedelta(seconds=params.timeout_seconds),
      "payload": {"waiting_for": "lead_reply", "until": next_run_at.isoformat()}
  }
  ```
  P2 webhook chama `flows.services.notify_lead_reply(lead_id)` que faz `UPDATE flow_runs SET next_run_at = now() WHERE lead_id = ? AND status = 'waiting'`. Tick imediato pega.

Quando wake-up acontece:
- `cancel_on_reply=true` + lead realmente respondeu → run → `cancelled`
- Senão → segue edge `out` normal

### `branch_on_reply`
Modela como `wait` + decisão na wake-up:
- Primeira visita: agenda wake-up em `now + window_seconds`, status=`waiting`
- Wake-up: verifica se lead respondeu dentro da janela (consulta `conversation_messages` por `lead_id, direction='in', created_at > started_at`)
- Match (`any` ou keyword via `params.pattern`):
  - Hit → `out_yes`
  - Miss → `out_no`

### `set_status`
1. `UPDATE leads SET status = params.new_status WHERE id = ctx.lead.id`
2. Comita
3. Avança `out`

### `end`
Marca `run.status = "completed"`, `finished_at = now`. Sem edge.

## 7. Templating

Jinja2 sandboxed environment:

```python
from jinja2.sandbox import SandboxedEnvironment

_env = SandboxedEnvironment(
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)

def render_template(body: str, lead: Lead, workspace: WorkspaceProfile) -> str:
    return _env.from_string(body).render(
        lead={
            "nome": lead.nome,
            "nicho": lead.nicho,
            "cidade": lead.cidade,
            "email": lead.email or "",
            "lp_url": _lp_url_for(lead),
        },
        workspace={
            "business_name": workspace.business_name or "",
            "your_name": workspace.your_name or "",
        }
    )
```

Erros de render → `FatalError` (template mal escrito é problema do user, não retry).

## 8. Worker lifecycle

```python
# engine/worker.py
_executor: Executor | None = None
_thread: threading.Thread | None = None

def start_worker(sessionmaker, channels):
    global _executor, _thread
    _executor = Executor(sessionmaker, channels)
    _thread = threading.Thread(target=_executor.run_forever, daemon=True, name="flows-executor")
    _thread.start()
    logger.info("flows.worker.started")

def stop_worker():
    if _executor:
        _executor._stop.set()
    if _thread:
        _thread.join(timeout=10)
    logger.info("flows.worker.stopped")
```

Wire em `app/main.py`:
```python
@app.on_event("startup")
def _start_flows_worker():
    from app.flows.engine.worker import start_worker
    from app.database import SessionLocal
    from app.flows.channels import build_registry
    start_worker(SessionLocal, build_registry())

@app.on_event("shutdown")
def _stop_flows_worker():
    from app.flows.engine.worker import stop_worker
    stop_worker()
```

### Reaper de runs órfãs no startup
Reaproveita padrão de `_reap_orphaned_jobs`:
```python
def _reap_running_runs(db):
    """Runs em status=running quando o worker morre — re-enfileira como pending."""
    stuck = db.query(FlowRun).filter_by(status="running").all()
    for run in stuck:
        run.status = "pending"
        run.next_run_at = datetime.utcnow()  # imediato
    if stuck:
        db.commit()
```

## 9. Services (camada pública pro F-3 chamar)

```python
# services.py
def create_flow(db, *, workspace_id: int, config: FlowConfig) -> Flow: ...
def update_flow(db, *, flow_id: int, config: FlowConfig) -> Flow: ...
def delete_flow(db, *, flow_id: int) -> None: ...
def get_flow(db, *, flow_id: int) -> Flow | None: ...
def list_flows(db, *, workspace_id: int) -> list[Flow]: ...

def start_run(db, *, flow_id: int, lead_id: int) -> FlowRun:
    """Cria FlowRun pending. Falha se já há run ativo pra mesmo (flow,lead)
    (constraint partial unique). Snapshot do flow é capturado."""

def cancel_run(db, *, run_id: int, reason: str) -> FlowRun: ...
def list_runs(db, *, flow_id: int | None = None, lead_id: int | None = None,
              status: str | None = None) -> list[FlowRun]: ...
def get_run_steps(db, *, run_id: int) -> list[FlowRunStep]: ...

def notify_lead_reply(db, *, lead_id: int) -> None:
    """Chamado por webhook P2 quando inbound chega. Acorda runs waiting deste lead."""
```

## 10. Channel registry

```python
# channels.py
class ChannelRegistry:
    def __init__(self, wa_resolver, email_resolver):
        self.wa = wa_resolver  # callable(db, workspace_id) -> WhatsAppProvider
        self.email = email_resolver  # F-2 — callable(db, workspace_id) -> EmailProvider

def build_registry() -> ChannelRegistry:
    from app.whatsapp.registry import get_provider as get_wa_provider
    from app.email.registry import get_provider as get_email_provider  # F-2
    return ChannelRegistry(wa_resolver=get_wa_provider, email_resolver=get_email_provider)
```

## 11. Validação

```python
# validation.py
class FlowValidationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))

def validate_flow(config: FlowConfig) -> None:
    errors = []
    node_ids = {n.id for n in config.nodes}

    # 1. Exatamente 1 start
    starts = [n for n in config.nodes if n.type == "start"]
    if len(starts) != 1:
        errors.append(f"Expected 1 start node, got {len(starts)}")

    # 2. Edge references válidas
    for e in config.edges:
        if e.source not in node_ids:
            errors.append(f"Edge {e.id}: source {e.source} not in nodes")
        if e.target not in node_ids:
            errors.append(f"Edge {e.id}: target {e.target} not in nodes")

    # 3. Acíclico (DFS)
    if _has_cycle(config):
        errors.append("Flow has cycles (must be DAG)")

    # 4. Todo path do start chega em end
    if not _all_paths_reach_end(config):
        errors.append("Some paths don't end in 'end' node")

    # 5. branch_on_reply tem 2 edges
    for n in config.nodes:
        if n.type == "branch_on_reply":
            outs = [e for e in config.edges if e.source == n.id]
            labels = {e.label for e in outs}
            if labels != {"out_yes", "out_no"}:
                errors.append(f"Node {n.id} (branch_on_reply): need exactly 'out_yes' + 'out_no'")

    # 6. Params específicos válidos
    for n in config.nodes:
        validator = _PARAM_VALIDATORS.get(n.type)
        if validator:
            try:
                validator(**n.params)
            except ValidationError as e:
                errors.append(f"Node {n.id} params invalid: {e}")

    if errors:
        raise FlowValidationError(errors)
```

## 12. Testing

Estrutura tests:
```
tests/flows/
├── test_flow_models.py            # schema + constraints
├── test_flow_validation.py        # DAG, cycles, missing end, etc
├── test_engine_executor.py        # tick loop, claim, retry, backoff
├── test_engine_nodes_send_wa.py   # mock provider, template render, idempotency
├── test_engine_nodes_send_email.py
├── test_engine_nodes_wait.py       # delay + until_event semantics
├── test_engine_nodes_branch.py     # any vs keyword
├── test_engine_nodes_set_status.py
├── test_engine_resume.py           # webhook notify_lead_reply wake-up
├── test_engine_reaper.py           # startup recovery
└── test_flow_services.py           # CRUD + start_run + cancel
```

Mocks: `httpx_mock` pra adapters externos. SQLite via conftest pra DB.

## 13. Métricas / observabilidade

Logs estruturados (sem libraries novas):
- `flows.tick.processed count=N`
- `flows.run.started run_id=X flow_id=Y lead_id=Z`
- `flows.node.executed node_type=T duration_ms=D run_id=X`
- `flows.node.failed node_type=T error=E run_id=X`
- `flows.run.completed run_id=X duration_seconds=S`
- `flows.run.cancelled run_id=X reason=R`

Não criar tabela de métricas neste sub-projeto. F-5 agrega via query ad-hoc; tabela materializada vem depois se precisar.

## 14. Não coberto

- Triggers automáticos por status / webhook (F-3)
- API HTTP (F-3)
- Frontend editor (F-4)
- Métricas dashboard (F-5)
- Email channel adapter — só interface consumida (F-2)
- Tagging, schedule trigger, sub-flows, A/B — explícitos no F-0 §11

## 15. Critérios de aceite

- [ ] Migration r14 aplica + reverte sem erro
- [ ] `Executor.tick` processa run pending → completed sem intervenção externa (test com flow de 3 nodes lineares)
- [ ] `wait` com `until_event` acorda quando `notify_lead_reply` é chamado
- [ ] `branch_on_reply` toma `out_yes` se há inbound dentro da janela, `out_no` senão
- [ ] Idempotency: re-executar mesmo node 2x não duplica `provider_message_id` (engine deve detectar e ir direto pra próxima edge)
- [ ] Reaper marca runs `running` → `pending` no startup
- [ ] 30+ testes passando, sem regressão nos 684 existentes
