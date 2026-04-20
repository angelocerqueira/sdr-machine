# Lead App — Diagnóstico de Marketing + Tab Estratégia (Spec 3 de 3)

**Data:** 2026-04-20
**Escopo:** restaurar geração do `diagnostico_marketing` no pipeline diagnostic + expor no Lead App via tab nova "Estratégia".
**Specs relacionados:** `2026-04-20-leads-ui-bugs-design.md`, `2026-04-20-leads-pagination-design.md`.

## Contexto

O campo `site_analysis.diagnostico_marketing` foi o output LLM original do enricher (resumo executivo, etapa de funil de marketing, top 3 prioridades, potencial IA/automação, funil detalhado). Spec `2026-04-08-service-level-scoring` substituiu essa estrutura por `site_analysis.service_levels` (4 níveis: lp, automacao_basica, mapa_automacoes, vertical_os).

Situação atual:

- `frontend/src/components/diagnostic-panel.tsx` **existe** e renderiza `diagnostico_marketing` completo — com funil (Descoberta → Apologia), Potencial IA, Top 3, detalhes por etapa. Já usa tokens Instrumento (`bg-surface`, `text-text-muted` etc.)
- `backend/app/pipeline/generator.py:692` e `outreach.py:30` **ainda leem** `diagnostico_marketing` como input primário. Sem ele, caem em fallback de template.
- Pipeline atual (`diagnostic/graph.py`) **não gera mais** esse campo — só `service_levels`.

Resultado: leads novos perdem profundidade em LP e outreach; `DiagnosticPanel` nunca renderiza nada porque o campo sempre vem vazio.

Usuário confirma: sheet/screenshots mostram justamente esse conteúdo, e ele quer "replicar esse enriquecimento no `/app/leads`".

## Objetivo

1. **Restaurar** geração do `diagnostico_marketing` no pipeline diagnostic (novo node paralelo aos 4 analyzers existentes).
2. **Plugar** `DiagnosticPanel` no Lead App via tab nova "Estratégia".
3. Preservar `service_levels` — os dois coexistem em `site_analysis` (não remover, não quebrar backward compat).

## Arquitetura

### Backend: novo node `marketing_diagnostic`

**Decisão:** rodar em paralelo com os 4 analyzers no mesmo `StateGraph`. Depois de rodar, escreve o output em `state.marketing_result`. O `qualify.py` consolida no retorno.

**Arquivos novos:**

- `backend/app/pipeline/diagnostic/prompts/marketing.py` — prompt template single-shot que pede JSON estruturado com os campos:

  ```json
  {
    "resumo_executivo": "...",
    "momento_funil": "descoberta|atracao|consideracao|acao|apologia",
    "potencial_ia_automacao": {
      "score": 0-100,
      "oportunidades": ["..."],
      "justificativa": "..."
    },
    "prioridades_top3": ["...", "...", "..."],
    "funil": {
      "descoberta":   { "diagnostico": "...", "acoes_top2": [{"acao":"...","resultado_esperado":"...","kpi":"..."}] },
      "atracao":      { ... },
      "consideracao": { ... },
      "acao":         { ... },
      "apologia":     { ... }
    }
  }
  ```

- `backend/app/pipeline/diagnostic/nodes/marketing.py` — node `analyze_marketing(state: GraphState) -> dict`. Chama LLM (mesma infra de `analyzers.py`), valida JSON, retorna `{"marketing_result": MarketingDiagnostic(...)}`.

**Arquivos alterados:**

- `backend/app/pipeline/diagnostic/state.py`:
  - Novo Pydantic model `MarketingDiagnostic` com a shape acima
  - `GraphState` ganha `marketing_result: MarketingDiagnostic | None = None`
  - `ServiceLevelAnalysis` ganha `diagnostico_marketing: MarketingDiagnostic | None = None`

- `backend/app/pipeline/diagnostic/graph.py`:
  - `graph.add_node("analyze_marketing", analyze_marketing)`
  - `graph.add_edge(START, "analyze_marketing")`
  - `graph.add_edge("analyze_marketing", "qualify")`

- `backend/app/pipeline/diagnostic/nodes/qualify.py`:
  - Ler `state.marketing_result` e passar pro `ServiceLevelAnalysis(..., diagnostico_marketing=state.marketing_result)`

- `backend/app/pipeline/enricher.py` linha 441-443:
  ```python
  if service_levels:
      site_analysis["service_levels"] = service_levels.model_dump()
      if service_levels.diagnostico_marketing:
          site_analysis["diagnostico_marketing"] = service_levels.diagnostico_marketing.model_dump()
      qualified = service_levels.qualificado
  ```

**Falha isolada:** se `analyze_marketing` falhar (LLM error, JSON inválido), `marketing_result` fica `None` e o resto do diagnóstico ainda funciona. `DiagnosticPanel` já trata `diag == undefined` com `return null`.

**Custo:** +1 chamada LLM por lead enriquecido. Prompt é denso (cobre 5 etapas de funil + Top 3 + IA) → 1 chamada única é melhor que 5 chamadas separadas por etapa.

### Frontend: tab Estratégia

**Componentes:**

- `frontend/src/components/leads/la-tab-strategy.tsx` — novo, thin wrapper:
  ```tsx
  export function LaTabStrategy({ lead }: { lead: LeadAppDetail }) {
    const diag = lead.diagnostico_marketing;
    if (!diag) return <EmptyState cta="Re-enriquecer" />;
    return <DiagnosticPanel siteAnalysis={{ diagnostico_marketing: diag }} compact={false} />;
  }
  ```

- `frontend/src/components/leads/lead-app-types.ts` — adicionar `diagnostico_marketing?: DiagnosticData` no `LeadAppDetail` (tipo copiado de `diagnostic-panel.tsx` ou exportado).

- `frontend/src/app/app/leads/[id]/page.tsx` `mapToDetail()`:
  ```ts
  diagnostico_marketing: (lead.site_analysis as any)?.diagnostico_marketing || undefined,
  ```

- `frontend/src/components/leads/lead-app-mock.ts`:
  - Adicionar tab `{ key: "strategy", label: "Estratégia", count: 0 }` em `buildTabs()`
  - `TAB_ACTIONS.strategy = { label: "Re-enriquecer", action: "enrich" }` (mesma ação de Diagnóstico)

- `frontend/src/app/app/leads/[id]/page.tsx` `tabContent()`:
  ```ts
  case "strategy": return <LaTabStrategy lead={lead} />;
  ```

**Ordem das tabs:** Diagnóstico → **Estratégia** → Landing Page → Mensagens → Informações.

**Empty state da tab Estratégia:**
- "Estratégia não gerada"
- "Este lead ainda não tem diagnóstico de marketing. Execute o enriquecimento pra gerar."
- Botão "Re-enriquecer" chama `runEnrich({ lead_ids: [lead.id] })` (mesma lógica de `LaTabDiag`).

### Integração com generator/outreach

Nada a mudar — `generator.py:692` e `outreach.py:30` já leem `site_analysis.diagnostico_marketing`. Assim que o node novo roda, geração de LP e outreach automaticamente ganham profundidade de volta.

## Modelos Pydantic (state.py)

```python
class FunnelAction(BaseModel):
    acao: str
    resultado_esperado: str
    kpi: str

class FunnelStage(BaseModel):
    diagnostico: str
    acoes_top2: list[FunnelAction] = Field(default_factory=list, max_length=2)

class IAPotencial(BaseModel):
    score: int = Field(ge=0, le=100)
    oportunidades: list[str] = Field(default_factory=list)
    justificativa: str

class MarketingDiagnostic(BaseModel):
    resumo_executivo: str
    momento_funil: Literal["descoberta","atracao","consideracao","acao","apologia"]
    potencial_ia_automacao: IAPotencial
    prioridades_top3: list[str] = Field(default_factory=list, max_length=3)
    funil: dict[str, FunnelStage] = Field(default_factory=dict)
```

## Prompt (resumo)

Input: `lead_info` (nome, nicho, cidade, rating, reviews), `site_data` (has_site, pagespeed, tem_whatsapp, etc.), `html_analysis` (redes sociais, CTAs), `social_profiles`.

Instruções curtas:
- Identifique o momento do funil (Descoberta → Apologia)
- Score 0-100 de potencial IA/automação + justifique
- 3 prioridades de curto prazo, acionáveis
- Para cada uma das 5 etapas do funil: diagnóstico curto + top 2 ações (`acao` + `resultado_esperado` + `kpi`)
- Resumo executivo 2-3 frases
- Retorne JSON estrito, sem prefixo/sufixo

## Testes

**Backend:**
- `tests/test_diagnostic_marketing.py` — testa `analyze_marketing` com LLM mockado retornando JSON válido; testa fallback em JSON inválido
- `tests/test_diagnostic_nodes.py` — adicionar caso onde graph completo retorna `final_result.diagnostico_marketing` populado
- `tests/test_enricher.py` — caso onde `site_analysis["diagnostico_marketing"]` é preenchido após enriquecer

**Frontend:**
- Não há suite automatizada — teste manual: enriquecer lead, abrir tab Estratégia, confirmar render do DiagnosticPanel + empty state quando `diag == null`.

## Migrations

Nenhuma. `site_analysis` é coluna JSON — append-only.

## Arquivos afetados

| Arquivo | Tipo |
|---|---|
| `backend/app/pipeline/diagnostic/prompts/marketing.py` | novo |
| `backend/app/pipeline/diagnostic/nodes/marketing.py` | novo |
| `backend/app/pipeline/diagnostic/state.py` | edit |
| `backend/app/pipeline/diagnostic/graph.py` | edit |
| `backend/app/pipeline/diagnostic/nodes/qualify.py` | edit |
| `backend/app/pipeline/enricher.py` | 3 linhas |
| `backend/tests/test_diagnostic_marketing.py` | novo |
| `backend/tests/test_diagnostic_nodes.py` | +1 caso |
| `backend/tests/test_enricher.py` | +1 caso |
| `frontend/src/components/leads/la-tab-strategy.tsx` | novo |
| `frontend/src/components/leads/lead-app-types.ts` | edit |
| `frontend/src/components/leads/lead-app-mock.ts` | edit (buildTabs + TAB_ACTIONS) |
| `frontend/src/app/app/leads/[id]/page.tsx` | edit (mapToDetail + tabContent) |

## Critérios de aceite

- Após rodar `enrich` num lead, `site_analysis.diagnostico_marketing` existe com shape completa
- Tab "Estratégia" aparece entre Diagnóstico e Landing Page, sempre visível (count dinâmico: 1 se tem diag, 0 se não tem)
- Tab Estratégia renderiza DiagnosticPanel com funil, Potencial IA, Top 3, detalhes por etapa
- Lead sem `diagnostico_marketing` mostra empty state com CTA "Re-enriquecer" que dispara o pipeline
- LP gerada e mensagens de outreach usam o diagnóstico novo (deixam fallback)
- `pytest backend/tests/` passa
- `npm run lint` passa

## Fora de escopo

- Re-skin do DiagnosticPanel com CSS `la-*` (visual já compatível)
- UI de edição manual do diagnóstico
- Histórico/versionamento do diagnóstico (só a última versão fica em `site_analysis`)
- Disparar enrichment automático em leads novos sem `diagnostico_marketing` — continua manual via UI
