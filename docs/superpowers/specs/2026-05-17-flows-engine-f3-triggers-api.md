# Flows Engine — F-3 Triggers + API Spec

> **Foundation:** [F-0](2026-05-17-flows-engine-f0-architecture.md) · [F-1](2026-05-17-flows-engine-f1-engine-backend.md)
> **Status:** ready to plan
> **Depende:** F-1 (services + engine prontos)
> **Bloqueia:** F-4 (editor consome API), F-5 (runtime UI consome API)

## 1. Objetivo

Expor a engine F-1 via **API HTTP** + ativar os **3 tipos de trigger** definidos em F-0 §4:
1. **Manual** — `POST /api/flows/{id}/runs` com `lead_ids`
2. **Auto por status do lead** — listener em `app.flows.triggers.lead_status` reage a updates de `Lead.status`
3. **Webhook externo** — `POST /api/flows/{id}/trigger` HMAC-validated com payload livre

## 2. Estrutura

```
backend/app/routers/
└── flows.py              # POST/GET/PUT/DELETE /api/flows + /runs + /trigger

backend/app/flows/triggers/
├── __init__.py
├── manual.py             # função start_runs(flow_id, lead_ids)
├── lead_status.py        # listener: subscribe_to_status_change(callback)
├── external_webhook.py   # função handle_external_trigger(flow_id, raw, signature)
└── registry.py           # ativa todos no startup

backend/tests/test_flows_*.py
```

## 3. Endpoints

### CRUD Flows

```
GET    /api/flows                       → list_flows(workspace)
POST   /api/flows                       → create_flow + validate
GET    /api/flows/{id}                  → get_flow
PUT    /api/flows/{id}                  → update_flow + validate + bump version
DELETE /api/flows/{id}                  → delete_flow (CASCADE em runs)
POST   /api/flows/{id}/validate         → dry-run validate (sem salvar)
PUT    /api/flows/{id}/enable           → enabled=true após validate
PUT    /api/flows/{id}/disable          → enabled=false (não cancela runs ativos)
```

### Runs

```
GET    /api/flows/{id}/runs?status=&lead_id=&limit=&offset=
GET    /api/flows/runs/{run_id}
GET    /api/flows/runs/{run_id}/steps
POST   /api/flows/{id}/runs             → start manual: {lead_ids: [...]}
DELETE /api/flows/runs/{run_id}         → cancel
```

### Trigger externo (público, HMAC)

```
POST /api/flows-trigger/{id}            → handle_external_trigger
   Headers: X-Sdr-Signature: sha256=...
   Body: { "lead_id": 123 } | { "lead_email": "a@b.com" }
```

> **Path separado** (`/api/flows-trigger` em vez de `/api/flows/{id}/trigger`) pra que `public_paths` no AuthMiddleware faça prefix match sem deixar todo `/api/flows/*` público.

Lookup do lead:
- `lead_id` → direto
- `lead_email` → `WHERE email = ... LIMIT 1`
- Outras chaves possíveis (v2): `lead_telefone`, `external_id`

Retorna `201 { "ok": true, "run_id": N }` se criado, `409 { "ok": false, "reason": "already_running" }` se constraint partial bate (run ativo já existe pra esse flow+lead).

## 4. Pydantic schemas (input)

```python
# routers/flows.py
from app.flows.schemas import FlowConfig  # F-1

class CreateFlowIn(FlowConfig): pass

class UpdateFlowIn(BaseModel):
    name: str | None = None
    description: str | None = None
    triggers: list[Trigger] | None = None
    nodes: list[NodeBase] | None = None
    edges: list[Edge] | None = None

class StartRunsIn(BaseModel):
    lead_ids: list[int] = Field(min_length=1, max_length=5000)

class ExternalTriggerIn(BaseModel):
    lead_id: int | None = None
    lead_email: EmailStr | None = None
    state: dict | None = None  # contexto inicial pro run.state
```

## 5. Implementação `start_runs` (manual + multi-lead)

```python
# triggers/manual.py
def start_runs(db: Session, *, flow_id: int, lead_ids: list[int]) -> dict:
    """Cria FlowRun pra cada lead. Skipa leads que já têm run ativa.

    Returns: {created: [run_ids], skipped: [{lead_id, reason}]}
    """
    flow = db.get(Flow, flow_id)
    if not flow or not flow.enabled:
        raise ValueError(f"Flow {flow_id} not enabled")

    snapshot = {"nodes": flow.nodes, "edges": flow.edges}
    created = []
    skipped = []

    for lead_id in lead_ids:
        # Constraint partial unique pega race; tentamos optimistic
        try:
            run = FlowRun(
                flow_id=flow.id, flow_version=flow.version,
                flow_snapshot=snapshot, lead_id=lead_id,
                workspace_id=flow.workspace_id, status="pending",
                next_run_at=datetime.utcnow(),  # imediato
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            created.append(run.id)
        except IntegrityError:
            db.rollback()
            skipped.append({"lead_id": lead_id, "reason": "already_running"})

    return {"created": created, "skipped": skipped}
```

## 6. Trigger `lead_status` (auto)

**Não usar SQLAlchemy events** — frágil em re-conexões e cross-process. Usar **invocação explícita** em todos os call sites onde `Lead.status` muda:

```python
# triggers/lead_status.py
def notify_status_change(db: Session, *,
    lead: Lead, old_status: str, new_status: str,
) -> list[int]:
    """Procura Flows com trigger lead_status que matcham essa transição.
    Cria runs pros leads matched. Retorna lista de run_ids criados.
    """
    matching_flows = (
        db.query(Flow)
        .filter_by(workspace_id=lead.workspace_id if hasattr(lead, 'workspace_id') else 1)
        .filter(Flow.enabled == True)
        .all()
    )
    run_ids = []
    for flow in matching_flows:
        for trigger in flow.triggers:
            if trigger.get("type") != "lead_status":
                continue
            from_list = trigger.get("from")
            to_list = trigger.get("to", [])
            if from_list and old_status not in from_list:
                continue
            if new_status not in to_list:
                continue
            result = start_runs(db, flow_id=flow.id, lead_ids=[lead.id])
            run_ids.extend(result["created"])
            break  # 1 run por flow por evento

    return run_ids
```

### Wire em call sites

Locais identificados que mudam `Lead.status`:
- `routers/leads.py` (PATCH lead, bulk PATCH, /messages, /lp)
- `routers/pipeline.py` (background tasks ao final de cada stage)
- `whatsapp/services.py:link_outreach_reply` (já existe — atualizar)

Cada call site faz:
```python
old_status = lead.status
lead.status = new_status
db.commit()
notify_status_change(db, lead=lead, old_status=old_status, new_status=new_status)
```

**Refactor cuidadoso:** centralizar via helper `set_lead_status(db, lead, new_status)` em `app/leads/services.py` (novo módulo). Substituir mutações diretas.

## 7. Trigger external_webhook

```python
# triggers/external_webhook.py
def handle_external_trigger(
    db: Session, *, flow_id: int, raw_body: bytes, signature: str | None,
    payload: dict,
) -> dict:
    flow = db.get(Flow, flow_id)
    if not flow or not flow.enabled:
        raise HTTPException(404, "flow not found or disabled")

    # 1. Localizar trigger external_webhook na config
    ext_trigger = next(
        (t for t in flow.triggers if t.get("type") == "external_webhook"),
        None,
    )
    if not ext_trigger:
        raise HTTPException(401, "invalid signature")  # don't leak

    # 2. Resolver secret via IntegrationSettings (provider="flows")
    cfg = get_provider_config(db, workspace_id=flow.workspace_id, provider="flows")
    if not cfg or not cfg.get(ext_trigger["secret_field"]):
        raise HTTPException(401, "invalid signature")
    secret = cfg[ext_trigger["secret_field"]]

    # 3. HMAC verify (reusa app.whatsapp.hmac do P2)
    if not verify_signature(secret, raw_body, signature):
        raise HTTPException(401, "invalid signature")

    # 4. Resolver lead
    lead = None
    if payload.get("lead_id"):
        lead = db.get(Lead, payload["lead_id"])
    elif payload.get("lead_email"):
        lead = db.query(Lead).filter_by(email=payload["lead_email"]).first()
    if not lead:
        raise HTTPException(404, "lead not found")

    # 5. Iniciar run
    result = start_runs(db, flow_id=flow.id, lead_ids=[lead.id])
    if not result["created"]:
        return {"ok": False, "reason": result["skipped"][0]["reason"]}
    return {"ok": True, "run_id": result["created"][0]}
```

### Integration settings `flows` provider

Pequena extensão no schema P0 `app/integrations/schemas.py`:
```python
class FlowsConfig(BaseModel):
    webhook_secret: SecretStr  # único campo; suporta multiple secrets se F-3 escalar

PROVIDER_SCHEMAS["flows"] = FlowsConfig
SECRET_FIELDS["flows"] = {"webhook_secret"}
```

Configurável via Settings UI mesmo flow do P5 (provider="flows" aparece na lista).

## 8. Wire em `main.py`

```python
# main.py linha 13: import
from app.routers import dashboard, flows, leads, pipeline, settings, webhooks, workspace_settings

# linha 81 (public_paths): add prefix /api/flows-trigger ao público
public_paths=["/api/health", "/api/leads/p/", "/api/webhooks", "/api/flows-trigger",
              "/docs", "/openapi.json"],
```

Router define endpoint público em `APIRouter(prefix="/api/flows-trigger")` (separado do `/api/flows` autenticado).

```python
app.include_router(flows.router)
```

## 9. Acessar engine sem rota

Engine F-1 expõe service `start_runs`. Triggers (manual/lead_status/external) chamam esse service direto. API é wrapper HTTP. Não duplicar lógica.

## 10. Erros

| Cenário | HTTP | Body |
|---|---|---|
| Flow não existe | 404 | `{"detail": "flow not found"}` |
| Flow disabled | 409 | `{"detail": "flow disabled"}` |
| Validação falhou (PUT/POST) | 422 | `{"detail": "validation_failed", "errors": [...]}` |
| Run não existe | 404 | |
| HMAC inválido | 401 | `{"detail": "invalid signature"}` |
| Lead não encontrado em trigger | 404 | |
| Run já ativo pro lead | 409 | `{"ok": false, "reason": "already_running"}` |

## 11. Tests

```
tests/test_flows_router_crud.py        # 10: create/get/update/delete/validate/enable
tests/test_flows_router_runs.py        # 8: start manual, list runs, get steps, cancel
tests/test_flows_router_trigger.py     # 7: HMAC valid/invalid, lead_id lookup, email, race
tests/test_flows_trigger_lead_status.py # 6: from/to match, no match, disabled flow ignored
tests/test_lead_status_helper.py       # 4: set_lead_status helper consistente
```

## 12. Migration helper `set_lead_status`

Novo arquivo `app/leads/services.py`:

```python
def set_lead_status(db: Session, lead: Lead, new_status: str,
                    *, commit: bool = True) -> None:
    """Centraliza mudanças de Lead.status. Dispara triggers lead_status."""
    if lead.status == new_status:
        return
    old_status = lead.status
    lead.status = new_status
    if commit:
        db.commit()
    from app.flows.triggers.lead_status import notify_status_change
    notify_status_change(db, lead=lead, old_status=old_status, new_status=new_status)
```

Refactor PR separado (ou no início deste F-3): substituir `lead.status = X; db.commit()` por `set_lead_status(db, lead, X)` nos call sites.

## 13. Backward compat

- Cadência atual (`outreach/generator.py`) **não chama** `set_lead_status` pros 5 toques fixos. Sem triggers ativos hoje, não muda comportamento.
- Quando user habilita primeiro flow, mudanças de status passam a disparar runs. Behavior new feature; sem regressão.

## 14. Critérios de aceite

- [ ] Endpoint CRUD `/api/flows` funciona end-to-end (create → enable → list → delete)
- [ ] `POST /api/flows/{id}/runs` com 5 lead_ids cria 5 runs (ou skipa duplicados)
- [ ] `POST /api/flows/{id}/trigger` com HMAC válido cria run; sem HMAC → 401
- [ ] `notify_status_change` é chamado em todos os call sites de mudança de status (grep audit no PR)
- [ ] Trigger `lead_status` cria run quando lead muda pra status configurado
- [ ] Run criado entra na queue do engine e progride
- [ ] 30+ testes novos sem regressão

## 15. Não coberto

- Editor visual (F-4)
- Runtime UI (F-5)
- Schedule trigger (cron)
- Pausar/retomar flow disable
- Retry policy customizada por node (usa default do engine)
- Cancellation cascade em todos os runs de um flow quando desabilita (deixa runs ativos rodarem)
