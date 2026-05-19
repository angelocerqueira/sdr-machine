# MCP M-5 Prompts + Subscriptions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 4 prompts pre-built (workflow templates) + subscriptions SSE em `conversations://list` e `jobs://{id}` pra notificações em tempo real. Fecha o MVP do MCP.

**Architecture:** Prompts via `@mcp_server.prompt()` decorator do FastMCP — retornam `list[PromptMessage]` que Claude renderiza no chat. Subscriptions usam mecanismo SSE nativo do MCP SDK (`resources/subscribe`); backend dispara `notify_resource_updated()` quando webhook P2 recebe inbound ou quando job emite progress event. Wire em webhook handler + job event store.

**Tech Stack:** Mesmo M-1 até M-4 — FastAPI + SQLAlchemy + `mcp` SDK + pytest

**Spec:** [`docs/superpowers/specs/2026-05-18-mcp-server-m0-architecture.md`](../specs/2026-05-18-mcp-server-m0-architecture.md) §5 (Subscriptions), §6 (Prompts)

**Depende:** M-1 + M-2 + M-3 (server tem todas as tools/resources). M-4 opcional (UI tokens).

---

## Notas de execução

- Branch: `feat/mcp-m5-prompts-subs`. Baseia em main com M-1+M-2+M-3 merged.
- Backend tests cobrem prompts renderização + subscription wire-up (mock)
- Manual smoke pra subscriptions reais (requer Claude Desktop conectado + inbound chegando)
- Commits Conventional Commits

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `backend/app/mcp/prompts.py` | Create | 4 prompts: `triage_hot_leads`, `reply_suggestion`, `lead_meeting_prep`, `weekly_pipeline_review` |
| `backend/app/mcp/notifications.py` | Create | `notify_conversation_inbound(workspace_id)`, `notify_job_progress(job_id)` — chamados via webhook + job runners |
| `backend/app/whatsapp/webhook_handler.py` | Modify | Após inbound persistido com sucesso → `notify_conversation_inbound(workspace_id)` |
| `backend/app/routers/pipeline.py` | Modify | Após `_emit_progress(job_id)` → `notify_job_progress(job_id)` |
| `backend/app/mcp/server.py` | Modify | Registrar prompts |
| `backend/tests/mcp/test_prompts.py` | Create | 4 prompts × 1-2 tests (render shape, args resolution) |
| `backend/tests/mcp/test_notifications.py` | Create | Notify functions callable + payload shape |
| `backend/tests/test_whatsapp_webhook_handler.py` | Modify | Adicionar test que confirma notify chamado pós-inbound |

---

## Task 1: Prompts pre-built

**Files:**
- Create: `backend/app/mcp/prompts.py`
- Create: `backend/tests/mcp/test_prompts.py`

- [ ] **Step 1: Criar branch**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git checkout main && git pull origin main
git checkout -b feat/mcp-m5-prompts-subs
```

- [ ] **Step 2: Test falhando**

Create `backend/tests/mcp/test_prompts.py`:

```python
import pytest

from app.mcp.prompts import (
    triage_hot_leads,
    reply_suggestion,
    lead_meeting_prep,
    weekly_pipeline_review,
)


def test_triage_hot_leads_returns_list_of_messages():
    result = triage_hot_leads(min_score=70, days_silent=5)
    assert isinstance(result, list)
    assert len(result) >= 1
    # Cada item: {role, content} ou objeto similar
    first = result[0]
    if isinstance(first, dict):
        assert "role" in first
        assert "content" in first
    else:
        # PromptMessage object do SDK
        assert hasattr(first, "role")
        assert hasattr(first, "content")


def test_triage_hot_leads_includes_args_in_prompt():
    result = triage_hot_leads(min_score=85, days_silent=10)
    text = _stringify(result)
    assert "85" in text
    assert "10" in text


def test_reply_suggestion_includes_conversation_id():
    result = reply_suggestion(conversation_id=42)
    text = _stringify(result)
    assert "42" in text


def test_lead_meeting_prep_includes_lead_id():
    result = lead_meeting_prep(lead_id=123)
    text = _stringify(result)
    assert "123" in text


def test_weekly_pipeline_review_default_period():
    result = weekly_pipeline_review()
    text = _stringify(result)
    assert "7d" in text or "semana" in text.lower()


def test_weekly_pipeline_review_custom_period():
    result = weekly_pipeline_review(period="30d")
    text = _stringify(result)
    assert "30d" in text


def _stringify(messages):
    """Junta texto de todas as PromptMessages — robusto a múltiplas shapes."""
    out = []
    for m in messages:
        if isinstance(m, dict):
            c = m.get("content")
        else:
            c = getattr(m, "content", None)
        if isinstance(c, str):
            out.append(c)
        elif isinstance(c, dict) and "text" in c:
            out.append(c["text"])
        elif hasattr(c, "text"):
            out.append(c.text)
    return "\n".join(out)
```

- [ ] **Step 3: Rodar — deve falhar**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_prompts.py -v
```

Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 4: Implementar `prompts.py`**

Create `backend/app/mcp/prompts.py`:

```python
"""MCP prompts pre-built — workflow templates que Claude pode invocar.

Cada função retorna `list[PromptMessage]` (ou compatível dict shape).
FastMCP wrappa via `@server.prompt()` decorator no `register_prompts()`.
"""
from __future__ import annotations

from typing import Literal


def triage_hot_leads(min_score: int = 70, days_silent: int = 5) -> list[dict]:
    """Triage leads quentes sem resposta recente, sugerindo prioridade de reabordagem."""
    return [
        {
            "role": "user",
            "content": (
                f"Quero priorizar leads pra reabordar hoje. Faça o seguinte:\n\n"
                f"1. Use a tool `list_leads` com filtro `{{score_min: {min_score}}}` "
                f"e status em ['outreach_sent', 'outreach_ready', 'responded'].\n"
                f"2. Pra cada lead, use `get_conversation` (ou `list_conversations` "
                f"se houver inbox) pra ver se houve atividade nos últimos {days_silent} dias.\n"
                f"3. Filtre quem está silencioso há ≥{days_silent}d.\n"
                f"4. Apresente lista priorizada: top 5 com nome, telefone, score, "
                f"última mensagem (preview), e sugestão de tom de reabordagem.\n\n"
                f"Output em markdown com tabela compacta."
            ),
        },
    ]


def reply_suggestion(conversation_id: int) -> list[dict]:
    """Dada uma conversa específica, gera 2-3 opções de resposta com tons distintos."""
    return [
        {
            "role": "user",
            "content": (
                f"Quero sugerir resposta pra conversa {conversation_id}.\n\n"
                f"Passos:\n"
                f"1. Use `get_conversation` com id={conversation_id} pra ler histórico.\n"
                f"2. Use `get_lead` no lead_id da conversa pra contexto (nicho, score, sinais).\n"
                f"3. Use `workspace_profile` pra contexto do remetente.\n"
                f"4. Gere **3 opções de resposta** com tons distintos:\n"
                f"   - Consultiva (pergunta aberta + valor)\n"
                f"   - Direta (oferece próximo passo concreto)\n"
                f"   - Provocativa (questiona status quo)\n\n"
                f"Cada opção em ~80 palavras. NÃO chame `prepare_send_message` ainda — "
                f"deixe eu escolher qual tom usar primeiro."
            ),
        },
    ]


def lead_meeting_prep(lead_id: int) -> list[dict]:
    """Resumo executivo de 1 lead pra reunião — score, sinais, scripts sugeridos."""
    return [
        {
            "role": "user",
            "content": (
                f"Preciso de um briefing executivo pro lead {lead_id} antes de uma "
                f"reunião. Passos:\n\n"
                f"1. `get_lead({lead_id})` — info base + enrichment\n"
                f"2. `list_landing_pages({lead_id})` — ver se LP foi gerada e ativa\n"
                f"3. Se houver, `get_conversation` no inbox-conv vinculado ao lead — "
                f"resumir últimas trocas\n\n"
                f"Output (markdown):\n"
                f"## Resumo executivo: {{lead.nome}}\n"
                f"**Score:** {{score}}/100 · **Nicho:** {{nicho}} · **Cidade:** {{cidade}}\n\n"
                f"**Sinais relevantes (3-5):**\n- ...\n\n"
                f"**Stack tech detectada:** ...\n\n"
                f"**Histórico de toques:**\n- ...\n\n"
                f"**Scripts sugeridos pra abertura da reunião (2-3 frases iniciais):**"
            ),
        },
    ]


def weekly_pipeline_review(
    period: Literal["7d", "30d", "90d"] = "7d",
) -> list[dict]:
    """KPI report semanal com insights + bottlenecks."""
    return [
        {
            "role": "user",
            "content": (
                f"Faça review do pipeline no período `{period}`. Passos:\n\n"
                f"1. `dashboard_stats()` — números atuais\n"
                f"2. `conversion_funnel(period=\"{period}\")` — taxas por estágio\n"
                f"3. `list_jobs(limit=50)` — pegar jobs do período, identificar "
                f"falhas e durações longas\n\n"
                f"Apresentação (markdown):\n"
                f"## Pipeline {period}\n\n"
                f"**KPIs principais** (tabela compacta: total leads, conversão %, "
                f"reply rate %, avg score)\n\n"
                f"**3 insights destacados** (correlações, surpresas — não factos óbvios)\n\n"
                f"**Bottlenecks identificados** (onde leads ficam estagnados?)\n\n"
                f"**Ações sugeridas pra próxima semana** (3 itens concretos)"
            ),
        },
    ]


def register_prompts(server) -> None:
    """Registra os 4 prompts no FastMCP server via decorator."""
    server.prompt(name="triage_hot_leads")(triage_hot_leads)
    server.prompt(name="reply_suggestion")(reply_suggestion)
    server.prompt(name="lead_meeting_prep")(lead_meeting_prep)
    server.prompt(name="weekly_pipeline_review")(weekly_pipeline_review)
```

- [ ] **Step 5: Rodar tests**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_prompts.py -v
```

Expected: 6 PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/app/mcp/prompts.py backend/tests/mcp/test_prompts.py
git commit -m "feat(mcp): 4 prompts pre-built (triage + reply + meeting + weekly)"
```

---

## Task 2: Notifications module — `notify_*` helpers

**Files:**
- Create: `backend/app/mcp/notifications.py`
- Create: `backend/tests/mcp/test_notifications.py`

FastMCP SDK 1.12+ expõe `server.session_manager` que pode emitir notificações via SSE pros subscribers. API exata varia; vamos abstrair com função que tenta o método disponível e silencia falhas (notification é best-effort).

- [ ] **Step 1: Test falhando**

Create `backend/tests/mcp/test_notifications.py`:

```python
from unittest.mock import Mock, patch

from app.mcp.notifications import (
    notify_conversation_inbound,
    notify_job_progress,
)


def test_notify_conversation_inbound_callable():
    """Helper deve ser callable sem servidor montado (no-op silencioso)."""
    # Não deve raise
    notify_conversation_inbound(workspace_id=1)


def test_notify_job_progress_callable():
    notify_job_progress(job_id=42)


def test_notify_conversation_uses_server_when_available():
    """Quando server está disponível, chama session_manager pra notificar."""
    fake_server = Mock()
    fake_server.session_manager.notify_resource_updated = Mock()

    with patch("app.mcp.notifications._get_server", return_value=fake_server):
        notify_conversation_inbound(workspace_id=1)

    # Não validamos URI exato — varia por SDK version. Só confirmar que foi chamado.
    assert fake_server.session_manager.notify_resource_updated.called


def test_notify_swallows_errors():
    """Falhas de notificação não devem propagar e bloquear o flow."""
    fake_server = Mock()
    fake_server.session_manager.notify_resource_updated.side_effect = RuntimeError("boom")

    with patch("app.mcp.notifications._get_server", return_value=fake_server):
        # Não deve raise
        notify_conversation_inbound(workspace_id=1)
```

- [ ] **Step 2: Rodar — deve falhar**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_notifications.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implementar `notifications.py`**

Create `backend/app/mcp/notifications.py`:

```python
"""Helpers pra disparar SSE notifications pros MCP clients subscritos.

Best-effort: erros são log-only, nunca propagam. Caller (webhook, job runner)
não pode ser bloqueado por falha de notificação MCP.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _get_server() -> Optional[Any]:
    """Retorna o FastMCP server singleton do `app.main`, ou None se não montado.

    Import lazy pra evitar circular imports (notifications é importado
    por handlers que podem ser carregados antes do server build).
    """
    try:
        from app.main import mcp_server  # type: ignore
        return mcp_server
    except ImportError:
        return None
    except AttributeError:
        return None


def _run_async(coro):
    """Executa coroutine em loop existente OR cria novo. Usado pra disparar
    notify de código sync (webhook handler é sync)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(coro)
            return
    except RuntimeError:
        pass
    # Sem loop: cria um
    asyncio.run(coro)


def notify_conversation_inbound(workspace_id: int) -> None:
    """Notifica subscribers da resource `conversations://list` que algo mudou.

    Disparado pelo webhook handler do P2 após inbound persistido.
    """
    server = _get_server()
    if server is None:
        return
    try:
        notifier = getattr(server.session_manager, "notify_resource_updated", None)
        if notifier is None:
            logger.debug("mcp.notify.no_notifier_api")
            return
        # API exata varia entre versões — tentamos shapes comuns:
        coro = notifier(uri="conversations://list")
        if coro is not None and hasattr(coro, "__await__"):
            _run_async(coro)
    except Exception as exc:
        logger.warning("mcp.notify.conversation_failed workspace=%s exc=%s", workspace_id, exc)


def notify_job_progress(job_id: int) -> None:
    """Notifica subscribers da resource `jobs://{id}` que houve progresso."""
    server = _get_server()
    if server is None:
        return
    try:
        notifier = getattr(server.session_manager, "notify_resource_updated", None)
        if notifier is None:
            return
        coro = notifier(uri=f"jobs://{job_id}")
        if coro is not None and hasattr(coro, "__await__"):
            _run_async(coro)
    except Exception as exc:
        logger.warning("mcp.notify.job_failed job=%s exc=%s", job_id, exc)
```

- [ ] **Step 4: Rodar tests**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_notifications.py -v
```

Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/app/mcp/notifications.py backend/tests/mcp/test_notifications.py
git commit -m "feat(mcp): notify_* helpers — SSE best-effort pra subscribers"
```

---

## Task 3: Wire notify em webhook handler (P2) + job runners

**Files:**
- Modify: `backend/app/whatsapp/webhook_handler.py`
- Modify: `backend/app/routers/pipeline.py`
- Modify: `backend/tests/test_whatsapp_webhook_handler.py`

- [ ] **Step 1: Adicionar test ao webhook handler test**

Edit `backend/tests/test_whatsapp_webhook_handler.py`. Adicionar:

```python
def test_webhook_inbound_triggers_mcp_notification(db, seeded):
    """Após inbound persistido com sucesso, notify_conversation_inbound é chamado."""
    from unittest.mock import patch
    raw = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "id": "EVO-NOTIFY-1",
                "remoteJid": "5544999990000@s.whatsapp.net",
                "fromMe": False,
            },
            "message": {"conversation": "oi"},
            "messageTimestamp": 1715000000,
        },
    }

    with patch("app.mcp.notifications.notify_conversation_inbound") as notify:
        handle_webhook(db, workspace_id=1, provider="evolution", raw=raw)
        notify.assert_called_once_with(1)
```

- [ ] **Step 2: Wire em webhook handler**

Edit `backend/app/whatsapp/webhook_handler.py`. Localizar o ponto onde inbound é persistido com sucesso (após `append_message` + `link_outreach_reply`, antes de `summary["inbound_processed"] += 1`).

Adicionar import no topo do arquivo:

```python
from app.mcp.notifications import notify_conversation_inbound
```

E após o `summary["inbound_processed"] += 1`, adicionar:

```python
notify_conversation_inbound(workspace_id=workspace_id)
```

- [ ] **Step 3: Rodar test pra confirmar wiring**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/test_whatsapp_webhook_handler.py::test_webhook_inbound_triggers_mcp_notification -v
```

Expected: PASS.

- [ ] **Step 4: Wire em pipeline job runners**

Edit `backend/app/routers/pipeline.py`. Localizar a função `_emit_progress(job_id, ...)` (ou equivalente que persiste eventos do job).

Adicionar import:

```python
from app.mcp.notifications import notify_job_progress
```

E ao final do `_emit_progress`:

```python
def _emit_progress(job_id: int, ...):  # signature existing
    # ... código existente que append em _job_events ...
    try:
        notify_job_progress(job_id)
    except Exception:
        pass  # best-effort, não bloqueia
```

> Se `_emit_progress` for chamado MUITAS vezes por job (>1/seg), considerar throttle. Mas pra MVP, notify em cada emit é aceitável (clients downstream filtram).

- [ ] **Step 5: Rodar suite completa pra detectar regressões**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest --deselect tests/test_outreach.py 2>&1 | tail -5
```

Expected: ~790 PASS, sem regressões.

- [ ] **Step 6: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/app/whatsapp/webhook_handler.py backend/app/routers/pipeline.py backend/tests/test_whatsapp_webhook_handler.py
git commit -m "feat(mcp): wire notify em webhook handler + job runners"
```

---

## Task 4: Wire prompts em `build_mcp_server`

**Files:**
- Modify: `backend/app/mcp/server.py`
- Modify: `backend/tests/mcp/test_server_build.py`

- [ ] **Step 1: Atualizar `build_mcp_server`**

Edit `backend/app/mcp/server.py`. Adicionar import + registration:

```python
from app.mcp.prompts import register_prompts
```

E dentro de `build_mcp_server()`, depois do registro de tools:

```python
    # M-5 prompts
    register_prompts(server)
```

- [ ] **Step 2: Atualizar test pra verificar prompts**

Edit `backend/tests/mcp/test_server_build.py`. Adicionar test:

```python
def test_server_has_prompts():
    from app.mcp.server import build_mcp_server
    server = build_mcp_server()

    expected_prompts = {
        "triage_hot_leads", "reply_suggestion",
        "lead_meeting_prep", "weekly_pipeline_review",
    }

    registered = set()
    # API exata varia; tentamos múltiplos paths
    if hasattr(server, "_prompts"):
        registered = set(server._prompts.keys())
    elif hasattr(server, "_prompt_manager"):
        registered = set(server._prompt_manager._prompts.keys())

    missing = expected_prompts - registered
    assert not missing, f"Prompts missing: {missing}"
```

> Se o accessor `_prompts` / `_prompt_manager` não existir nessa versão do SDK, adaptar pra `server.list_prompts()` async ou método equivalente.

- [ ] **Step 3: Rodar tests**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest tests/mcp/test_server_build.py -v
```

Expected: TODOS PASS (incluindo novo test_server_has_prompts).

- [ ] **Step 4: Commit**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git add backend/app/mcp/server.py backend/tests/mcp/test_server_build.py
git commit -m "feat(mcp): wire 4 prompts em build_mcp_server"
```

---

## Task 5: Smoke + push + PR

- [ ] **Step 1: Suite full backend**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine/backend && venv/bin/pytest --deselect tests/test_outreach.py 2>&1 | tail -5
```

Expected: ~800 PASS (790 baseline pós-M-4 + ~10 novos M-5).

- [ ] **Step 2: Push**

```bash
cd /Users/angelocerqueira/sollertis/solutions/sdr-machine
git push -u origin feat/mcp-m5-prompts-subs
```

- [ ] **Step 3: Abrir PR**

```bash
gh pr create --base main --title "feat(mcp): M-5 prompts pre-built + SSE subscriptions" --body "$(cat <<'EOF'
## Summary

Fecha o MVP do MCP server.

**Prompts (4 workflow templates):**
- \`triage_hot_leads(min_score=70, days_silent=5)\` — prioriza leads quentes sem resposta recente
- \`reply_suggestion(conversation_id)\` — 3 opções de resposta com tons distintos pra conversa específica
- \`lead_meeting_prep(lead_id)\` — briefing executivo (score, sinais, scripts) pra reunião
- \`weekly_pipeline_review(period="7d")\` — KPI report + insights + bottlenecks + ações

Cada prompt retorna \`list[PromptMessage]\` que Claude renderiza ao user. User invoca via Claude Desktop slash menu (prompts/list).

**Subscriptions (SSE notify):**
- \`conversations://list\` notifica quando inbound chega (wire em webhook handler P2)
- \`jobs://{id}\` notifica em cada \`_emit_progress\` (wire em pipeline.py)

Pattern: \`notify_*\` helpers em \`app/mcp/notifications.py\` são best-effort. Erros em SSE notification são log-only, nunca bloqueiam o flow business (webhook responde 200 mesmo se notify falhar).

## Test Plan

- [x] ~10 testes novos (4 prompts shape + 4 notify callable/error swallow + 2 wiring webhook/job)
- [x] Suite backend full passa (~800 PASS)
- [ ] **Manual:**
  - Claude Desktop conectado, /prompts → 4 prompts disponíveis
  - Invocar \`weekly_pipeline_review\` → Claude faz chains de tool calls + apresenta report
  - Mandar inbound real via WhatsApp, Claude com inbox aberto recebe notification SSE e atualiza lista

## Não coberto

- Audit log materializado de notify (V2)
- Rate limit nas notifications (hoje 1 por inbound, 1 por progress event)
- Subscriptions em outros resources além de conversations + jobs
- Prompts dinâmicos baseados em workspace state (todos hard-coded por enquanto)
EOF
)"
```

---

## Self-Review

**Spec coverage** (vs M-0 §5 + §6):

| Spec item | Task |
|---|---|
| `triage_hot_leads` prompt | Task 1 |
| `reply_suggestion` prompt | Task 1 |
| `lead_meeting_prep` prompt | Task 1 |
| `weekly_pipeline_review` prompt | Task 1 |
| Notify subscribers `conversations://list` quando inbound chega | Tasks 2 + 3 |
| Notify subscribers `jobs://{id}` em progress | Tasks 2 + 3 |
| Notify best-effort (não bloqueia caller em failure) | Task 2 |
| Wire em webhook handler P2 | Task 3 |
| Wire em pipeline job event store | Task 3 |
| Register prompts em build_mcp_server | Task 4 |

**Placeholder scan:** `_emit_progress` signature em Task 3 step 4 é placeholder INTENCIONAL — engineer abre o arquivo e ajusta pra signature real (variável demais pra hard-code). Idem accessor `_prompts` / `_prompt_manager` em Task 4 step 2.

**Type consistency:**
- `notify_conversation_inbound(workspace_id: int) -> None` em notifications.py + chamada em webhook_handler.py ✓
- `notify_job_progress(job_id: int) -> None` em notifications.py + chamada em pipeline.py ✓
- Prompts retornam `list[dict]` (compatível com PromptMessage do SDK) ✓
- `register_prompts(server)` pattern consistente com outros registers ✓

---

## Execution Handoff

Após M-5 merged, **MCP MVP completo** end-to-end. Próximos PRs possíveis:
- **M-B**: SDR consome MCPs externos (direção B do brainstorm)
- **P3 (cadência outreach)**: dispatch_outreach + scheduler bumps
- **Flows Engine M-1**: implementar engine (specs já prontas)

Plan complete and saved to `docs/superpowers/plans/2026-05-18-mcp-m5-prompts-subscriptions.md`.
