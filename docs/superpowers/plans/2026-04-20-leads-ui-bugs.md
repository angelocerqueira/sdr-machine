# Lead App UI Bugs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corrigir 4 bugs visíveis no `/app/leads` (escape Unicode literal, navegação `< >` inerte, preview LP autenticado, busca limitada).

**Architecture:** Fixes pontuais sem refactor. Apenas as linhas citadas na spec — cada fix é independente e testável isolado. Spec: `docs/superpowers/specs/2026-04-20-leads-ui-bugs-design.md`.

**Tech Stack:** Next.js 16 / React 19 / TypeScript (frontend), FastAPI / SQLAlchemy (backend), pytest.

---

## File Structure

- `frontend/src/components/leads/la-master.tsx` — trocar escapes literais + placeholder
- `frontend/src/components/leads/la-topbar.tsx` — wire onClicks em < >
- `frontend/src/components/leads/la-tab-landing-page.tsx` — trocar URL iframe + 1 escape
- `frontend/src/app/app/leads/[id]/page.tsx` — trocar 2 escapes + passar props nav
- `backend/app/routers/leads.py` — expandir filtro search em 2 endpoints
- `backend/tests/test_leads_api.py` — adicionar teste busca expandida

---

## Task 1: Backend — expandir busca pra nicho/cidade/email/razao_social

**Files:**
- Modify: `backend/app/routers/leads.py:63-64` (lead_counts)
- Modify: `backend/app/routers/leads.py:101-102` (list_leads)
- Test: `backend/tests/test_leads_api.py`

- [ ] **Step 1: Write failing test pra busca por nicho**

Adicionar ao final de `backend/tests/test_leads_api.py`:

```python
def test_search_by_nicho(client):
    # Cria 3 leads com nichos diferentes
    from app.models import Lead
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        db.add_all([
            Lead(nome="Boiger Beauty", nicho="salão de beleza", cidade="Curitiba", telefone="1"),
            Lead(nome="Clinica XYZ", nicho="clínica estética", cidade="Curitiba", telefone="2"),
            Lead(nome="Bar do Zé", nicho="bar", cidade="Porto Alegre", telefone="3"),
        ])
        db.commit()
    finally:
        db.close()

    resp = client.get("/api/leads?search=salão")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["nome"] == "Boiger Beauty"


def test_search_by_cidade(client):
    from app.models import Lead
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        db.add_all([
            Lead(nome="A", nicho="x", cidade="Porto Alegre", telefone="1"),
            Lead(nome="B", nicho="y", cidade="Curitiba", telefone="2"),
        ])
        db.commit()
    finally:
        db.close()

    resp = client.get("/api/leads?search=porto")
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["cidade"] == "Porto Alegre"


def test_search_by_email(client):
    from app.models import Lead
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        db.add_all([
            Lead(nome="X", telefone="1", email="contato@loja.com"),
            Lead(nome="Y", telefone="2", email="outro@empresa.com"),
        ])
        db.commit()
    finally:
        db.close()

    resp = client.get("/api/leads?search=loja.com")
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["email"] == "contato@loja.com"
```

- [ ] **Step 2: Run test — deve falhar (busca só em nome+telefone)**

```bash
cd backend && pytest tests/test_leads_api.py::test_search_by_nicho -v
```

Expected: FAIL — retorna 0 leads (busca atual só em nome/telefone).

- [ ] **Step 3: Implementar — expandir `or_` em list_leads**

Em `backend/app/routers/leads.py`, linhas 101-102, substituir:

```python
    if search:
        query = query.filter(or_(Lead.nome.ilike(f"%{search}%"), Lead.telefone.ilike(f"%{search}%")))
```

por:

```python
    if search:
        term = f"%{search}%"
        query = query.filter(or_(
            Lead.nome.ilike(term),
            Lead.telefone.ilike(term),
            Lead.nicho.ilike(term),
            Lead.cidade.ilike(term),
            Lead.email.ilike(term),
            Lead.razao_social.ilike(term),
        ))
```

- [ ] **Step 4: Implementar — mesma mudança em lead_counts**

Em `backend/app/routers/leads.py`, linhas 63-64, substituir:

```python
    if search:
        query = query.filter(or_(Lead.nome.ilike(f"%{search}%"), Lead.telefone.ilike(f"%{search}%")))
```

por:

```python
    if search:
        term = f"%{search}%"
        query = query.filter(or_(
            Lead.nome.ilike(term),
            Lead.telefone.ilike(term),
            Lead.nicho.ilike(term),
            Lead.cidade.ilike(term),
            Lead.email.ilike(term),
            Lead.razao_social.ilike(term),
        ))
```

- [ ] **Step 5: Run tests — devem passar**

```bash
cd backend && pytest tests/test_leads_api.py -v
```

Expected: PASS (todos os 3 novos + existentes).

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/leads.py backend/tests/test_leads_api.py
git commit -m "feat(api): expand lead search to nicho/cidade/email/razao_social

Match placeholder promise in frontend. Search filter now matches
nome, telefone, nicho, cidade, email, razao_social via ilike OR.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Frontend — trocar escapes Unicode literais

**Files:**
- Modify: `frontend/src/components/leads/la-master.tsx:51,55,85,99`
- Modify: `frontend/src/app/app/leads/[id]/page.tsx:71`
- Modify: `frontend/src/components/leads/la-tab-landing-page.tsx:107`

- [ ] **Step 1: Fix `la-master.tsx` linha 51 — placeholder**

Substituir:

```tsx
            placeholder="Buscar por nome, nicho, cidade\u2026"
```

por:

```tsx
            placeholder="Buscar por nome, nicho, cidade, email…"
```

- [ ] **Step 2: Fix `la-master.tsx` linha 55 — kbd**

Substituir:

```tsx
          <span className="la-master-search-kbd">\u2318K</span>
```

por:

```tsx
          <span className="la-master-search-kbd">⌘K</span>
```

- [ ] **Step 3: Fix `la-master.tsx` linha 85 — separador count**

Substituir:

```tsx
                <span className="count">\u00b7 {g.items.length}</span>
```

por:

```tsx
                <span className="count">· {g.items.length}</span>
```

- [ ] **Step 4: Fix `la-master.tsx` linha 99 — separador meta**

Substituir:

```tsx
                    <div className="la-master-meta">
                      {l.niche} \u00b7 {l.city}
                    </div>
```

por:

```tsx
                    <div className="la-master-meta">
                      {l.niche} · {l.city}
                    </div>
```

- [ ] **Step 5: Fix `page.tsx` linha 71 — lp_versions date separator**

Em `frontend/src/app/app/leads/[id]/page.tsx` linha 71, substituir:

```ts
      created: new Date(lp.created_at).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }) +
        " \u00b7 " +
        new Date(lp.created_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }),
```

por:

```ts
      created: new Date(lp.created_at).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }) +
        " · " +
        new Date(lp.created_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }),
```

- [ ] **Step 6: Fix `la-tab-landing-page.tsx` linha 107 — ellipsis**

Substituir:

```tsx
                    {activating === v.id ? "Ativando\u2026" : "Ativar"}
```

por:

```tsx
                    {activating === v.id ? "Ativando…" : "Ativar"}
```

- [ ] **Step 7: Verify visualmente — rodar dev**

```bash
cd frontend && npm run dev
```

Abrir `http://localhost:3000/app/leads/<algum-id>` e verificar:
- Placeholder do search renderiza "Buscar por nome, nicho, cidade, email…" (sem `\u`)
- Badge `⌘K` renderiza o símbolo Command
- Grupos da master list mostram `· N` (separador e contagem)
- Metadata de lead mostra `{nicho} · {cidade}`
- Data de versão LP mostra `DD/MM · HH:MM`
- Botão ativar LP em progresso mostra "Ativando…"

- [ ] **Step 8: Lint**

```bash
cd frontend && npm run lint
```

Expected: no warnings/errors nos arquivos tocados.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/leads/la-master.tsx frontend/src/components/leads/la-tab-landing-page.tsx frontend/src/app/app/leads/[id]/page.tsx
git commit -m "fix(leads): render Unicode glyphs instead of literal escapes

JSX string literals like 'cidade\u2026' were being rendered as text.
Replace with actual glyphs (⌘K, ·, …) so UI shows the intended chars.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Frontend — wire botões `< >` na topbar

**Files:**
- Modify: `frontend/src/components/leads/la-topbar.tsx` (interface + onClick)
- Modify: `frontend/src/app/app/leads/[id]/page.tsx` (passar callbacks)

- [ ] **Step 1: Atualizar interface LaTopbarProps**

Em `frontend/src/components/leads/la-topbar.tsx`, substituir o bloco:

```ts
interface LaTopbarProps {
  lead: LeadAppDetail;
  railOpen: boolean;
  setRailOpen: (open: boolean) => void;
  position?: number;
  total?: number;
}
```

por:

```ts
interface LaTopbarProps {
  lead: LeadAppDetail;
  railOpen: boolean;
  setRailOpen: (open: boolean) => void;
  position?: number;
  total?: number;
  onPrev?: () => void;
  onNext?: () => void;
}
```

- [ ] **Step 2: Receber props nova assinatura**

Substituir:

```ts
export function LaTopbar({
  lead,
  railOpen,
  setRailOpen,
  position = 1,
  total = 1,
}: LaTopbarProps) {
```

por:

```ts
export function LaTopbar({
  lead,
  railOpen,
  setRailOpen,
  position = 1,
  total = 1,
  onPrev,
  onNext,
}: LaTopbarProps) {
```

- [ ] **Step 3: Wire o botão "Anterior"**

Substituir:

```tsx
        <button className="la-topbar-nav-btn" aria-label="Anterior">
          <Icon
            name="chevron-r"
            size={16}
            style={{ transform: "rotate(180deg)" }}
          />
        </button>
```

por:

```tsx
        <button
          className="la-topbar-nav-btn"
          aria-label="Anterior"
          onClick={onPrev}
          disabled={!onPrev}
        >
          <Icon
            name="chevron-r"
            size={16}
            style={{ transform: "rotate(180deg)" }}
          />
        </button>
```

- [ ] **Step 4: Wire o botão "Próximo"**

Substituir:

```tsx
        <button className="la-topbar-nav-btn" aria-label="Próximo">
          <Icon name="chevron-r" size={16} />
        </button>
```

por:

```tsx
        <button
          className="la-topbar-nav-btn"
          aria-label="Próximo"
          onClick={onNext}
          disabled={!onNext}
        >
          <Icon name="chevron-r" size={16} />
        </button>
```

- [ ] **Step 5: Passar callbacks em `page.tsx`**

Em `frontend/src/app/app/leads/[id]/page.tsx`, no `<LaTopbar>` (linhas 218-224), substituir:

```tsx
            <LaTopbar
              lead={lead}
              railOpen={railOpen}
              setRailOpen={setRailOpen}
              position={currentIndex + 1}
              total={total}
            />
```

por:

```tsx
            <LaTopbar
              lead={lead}
              railOpen={railOpen}
              setRailOpen={setRailOpen}
              position={currentIndex + 1}
              total={total}
              onPrev={
                currentIndex > 0
                  ? () => router.push(`/app/leads/${leads[currentIndex - 1].id}`)
                  : undefined
              }
              onNext={
                currentIndex < leads.length - 1 && currentIndex >= 0
                  ? () => router.push(`/app/leads/${leads[currentIndex + 1].id}`)
                  : undefined
              }
            />
```

- [ ] **Step 6: Verify manualmente**

Em dev:
- Abrir lead no meio da lista — `<` e `>` funcionam
- Abrir primeiro lead — `<` fica disabled, `>` funciona
- Abrir último lead — `>` fica disabled, `<` funciona
- J/K ainda funciona (não regrediu)

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/leads/la-topbar.tsx frontend/src/app/app/leads/[id]/page.tsx
git commit -m "fix(leads): wire topbar prev/next buttons to router navigation

Buttons were decorative — now dispatch router.push to neighbor lead.
Disabled at list extremes. J/K keyboard nav unchanged.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Frontend — iframe LP preview sem auth

**Files:**
- Modify: `frontend/src/components/leads/la-tab-landing-page.tsx:30`

- [ ] **Step 1: Trocar URL autenticada pela pública**

Em `frontend/src/components/leads/la-tab-landing-page.tsx`, no topo do arquivo adicionar ao import de `@/lib/api`:

```ts
import { getLeadLpUrlByPublicId, activateLandingPage } from "@/lib/api";
```

(remover `getLeadLpUrl` se não for mais usado).

Linha 30, substituir:

```ts
  const lpUrl = getLeadLpUrl(lead.id);
```

por:

```ts
  const lpUrl = getLeadLpUrlByPublicId(lead.public_id);
```

- [ ] **Step 2: Verify manualmente**

Em dev, abrir lead com LP gerada, ir na tab Landing Page — iframe renderiza a LP (não `{"detail":"Nao autenticado"}`).

- [ ] **Step 3: Lint**

```bash
cd frontend && npm run lint
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/leads/la-tab-landing-page.tsx
git commit -m "fix(leads): use public LP URL in iframe preview

Iframe couldn't send Bearer token → /api/leads/{id}/lp returned
'Nao autenticado'. Switch to /api/leads/p/{public_id}/lp which is
public (same endpoint used by /lp/[id] preview page).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Final verification

- [ ] **Step 1: Backend tests pass**

```bash
cd backend && pytest
```

- [ ] **Step 2: Frontend builds**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Manual smoke test**

- Abrir `/app/leads/<id>`
- Verificar: placeholder, `⌘K`, `·`, `…` renderizam corretos
- Clicar `<` e `>` da topbar — navega
- Tab Landing Page — iframe mostra LP
- Digitar "salão" ou "curitiba" no search — retorna resultados
