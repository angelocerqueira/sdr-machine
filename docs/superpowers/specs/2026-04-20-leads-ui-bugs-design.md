# Lead App — Bugs UI (Spec 1 de 3)

**Data:** 2026-04-20
**Escopo:** correções pontuais no `/app/leads`. Não altera arquitetura.
**Specs relacionados:** `2026-04-20-leads-pagination-design.md`, `2026-04-20-leads-marketing-diagnostic-design.md`.

## Contexto

Lead App está em produção com 4 bugs visíveis confirmados pelo usuário (screenshots):

1. **Escape Unicode literais** (`\u2318K`, `\u2026`, `\u00b7`) aparecendo como texto cru em vez de `⌘K`, `…`, `·`
2. **Botões `< / >` da topbar** (`la-topbar.tsx`) são puramente decorativos — não têm `onClick`
3. **Preview da LP** na tab Landing Page renderiza `{"detail":"Nao autenticado"}` porque o iframe aponta pra rota autenticada (`/api/leads/{id}/lp`) e não envia credenciais
4. **Busca** não retorna resultados quando usuário digita nicho/cidade — backend só filtra `nome` e `telefone`; placeholder promete mais

## Objetivo

Corrigir cada bug pontualmente, sem refactor adjacente. Preservar todos os comportamentos existentes (J/K keyboard nav, tabs, etc.).

## Mudanças

### 1. Escape Unicode literais

**Arquivo:** `frontend/src/components/leads/la-master.tsx`
- Linha 51: `placeholder="Buscar por nome, nicho, cidade\u2026"` → `placeholder="Buscar por nome, nicho, cidade…"`
- Linha 55: `<span className="la-master-search-kbd">\u2318K</span>` → `<span className="la-master-search-kbd">⌘K</span>`
- Linha 85: `\u00b7 {g.items.length}` → `· {g.items.length}`
- Linha 99: `{l.niche} \u00b7 {l.city}` → `{l.niche} · {l.city}`

**Arquivo:** `frontend/src/app/app/leads/[id]/page.tsx`
- Linha 71: `" \u00b7 "` em `lp_versions.map` → `" · "`

**Arquivo:** `frontend/src/components/leads/la-tab-landing-page.tsx`
- Linha 107: `"Ativando\u2026"` → `"Ativando…"`

**Por que:** em JSX strings/JS literais, `\u2318` é interpretado como `⌘` normalmente. Esses casos estão com barra dupla escapada no source (`\\u2318` no arquivo renderiza `\u2318` literal). Basta trocar pela glifo real.

### 2. Navegação `< / >` da topbar

**Arquivo:** `frontend/src/components/leads/la-topbar.tsx`
- Adicionar props `onPrev?: () => void` e `onNext?: () => void`
- Wire em cada botão: `onClick={onPrev}` e `onClick={onNext}`
- `disabled={!onPrev}` / `disabled={!onNext}` quando no extremo da lista

**Arquivo:** `frontend/src/app/app/leads/[id]/page.tsx`
- Calcular `prevLead = leads[currentIndex - 1]`, `nextLead = leads[currentIndex + 1]`
- Passar `onPrev={prevLead ? () => router.push(\`/app/leads/${prevLead.id}\`) : undefined}` e análogo pra `onNext` no `<LaTopbar>`

**Não mexer** na lógica de J/K em `use-lead-app.ts` — ambos caminhos convergem no `router.push`.

### 3. Preview da LP autenticado

**Arquivo:** `frontend/src/components/leads/la-tab-landing-page.tsx`
- Linha 30: `const lpUrl = getLeadLpUrl(lead.id);` → `const lpUrl = getLeadLpUrlByPublicId(lead.public_id);`
- Import já existente em `lib/api.ts:151`

**Por que:** `/api/leads/{id}/lp` passa pelo middleware auth. Iframe cross-origin não envia cookie/token. `/api/leads/p/{public_id}/lp` é rota pública (mesma usada por `/lp/[id]/page.tsx`).

### 4. Busca expandida (backend + frontend)

**Arquivo:** `backend/app/routers/leads.py`
- Linha 64 (`lead_counts`): expandir filtro search
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
- Linha 102 (`list_leads`): mesma mudança

**Arquivo:** `frontend/src/components/leads/la-master.tsx`
- Linha 51: placeholder → `"Buscar por nome, nicho, cidade, email…"` (ajuste após fix #1)

**Teste:** backend `tests/test_leads_api.py` deve ganhar um teste que cria 3 leads com valores distintos e verifica busca por nicho/cidade/email.

## Arquivos afetados

| Arquivo | Linhas alteradas |
|---|---|
| `frontend/src/components/leads/la-master.tsx` | 4 strings |
| `frontend/src/components/leads/la-topbar.tsx` | 2 props + 2 onClick |
| `frontend/src/components/leads/la-tab-landing-page.tsx` | 1 string + 1 URL |
| `frontend/src/app/app/leads/[id]/page.tsx` | 2 strings + 2 props |
| `backend/app/routers/leads.py` | 2 filtros expandidos |
| `backend/tests/test_leads_api.py` | +1 teste |

## Critérios de aceite

- ⌘K, …, · renderizam como glifos reais na master list
- Clicar `<` e `>` da topbar navega entre leads da lista filtrada; botão desabilita no extremo
- Iframe da tab Landing Page carrega a LP renderizada (não "Nao autenticado")
- Busca por "salão", "curitiba", "@gmail" retorna leads matching
- `pytest backend/tests/test_leads_api.py` passa
- `npm run lint` passa

## Fora de escopo

- Refactor do `use-lead-app.ts`
- Design system polish (fora bugs listados)
- Paginação (Spec 2)
- Tab nova Estratégia (Spec 3)
