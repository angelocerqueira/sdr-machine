# Service Level Scoring — Design Spec

**Data:** 2026-04-08
**Status:** Aprovado
**Escopo:** Backend (LangGraph) + Frontend (tabs no lead sheet)

## Contexto

O SDR Machine hoje avalia leads com um score único de oportunidade (técnico) e um diagnóstico de marketing via LLM (potencial IA/automação). O processo não diferencia o **nível de serviço** que faz sentido oferecer a cada lead.

## Objetivo

Adicionar uma **escada de valor com 4 níveis** ao processo de enriquecimento, onde cada lead recebe um score independente por nível de serviço. O vendedor vê tabs no lead sheet com scores e justificativas, e o sistema recomenda por qual nível começar.

## Escada de Valor — 4 Níveis

### Nível 1 — LP (Landing Page)

**Avalia:** qualidade do site atual (ou ausência), presença digital básica, facilidade de fechar a venda de LP, competitividade do nicho na cidade.

- **Score alto:** sem site ou site muito ruim, concorrentes com presença melhor, reviews boas mas site não reflete qualidade, operação que depende de presença online
- **Score baixo:** já tem site decente, nicho que não depende de site

### Nível 2 — Automação Básica

**Avalia:** canais de atendimento manuais, volume de interações repetitivas, ausência de ferramentas básicas. Qualquer automação que não exige integração complexa entre sistemas.

- **Score alto:** atendimento 100% manual com volume, canais desconectados, processos repetitivos visíveis
- **Score baixo:** já usa chatbot/CRM, negócio de baixo volume, operação simples

### Nível 3 — Mapa + Automações Completas

**Avalia:** presença no Google Meu Negócio, necessidade de fluxos integrados multi-canal, potencial pra agents que executam tarefas, maturidade digital. Envolve agents.

- **Score alto:** múltiplos pontos de contato, fluxo de venda com 3+ etapas manuais, GMB desotimizado, base digital existente mas fluxos desconectados
- **Score baixo:** negócio simples demais, sem maturidade digital, pouca recorrência

### Nível 4 — Vertical OS

**Avalia:** complexidade operacional (agendamento + estoque + financeiro + equipe + clientes), escala do negócio, nicho com processos fragmentados, demanda recorrente, existência de vertical OS no mercado. Sistema completo que substitui todas as ferramentas e centraliza a operação core do nicho.

- **Score alto:** operação complexa com múltiplas áreas, equipe de 5+ pessoas, nicho com fragmentação de ferramentas, reviews/site indicam operação sofisticada
- **Score baixo:** negócio de 1-2 pessoas, operação simples, nicho já dominado por OS existente que o lead usa

## Qualificação

- Cada nível tem score independente (0-100)
- O sistema recomenda o **nível de entrada** (maior score viável na escada)
- Lead é **desqualificado** se TODOS os 4 scores ficam abaixo do `DISQUALIFY_THRESHOLD` (default: 25)
- **Lógica do nível recomendado:** percorre os níveis de cima pra baixo (OS → Mapa → Automação → LP). O nível recomendado é o mais alto cujo score ≥ 40 (threshold de viabilidade). Se nenhum atinge 40, recomenda o de maior score absoluto (desde que não desqualificado).

## Arquitetura — LangGraph no Backend

### Grafo `lead_diagnostic`

```
START
  │
  ▼
[collect_context]          ← Python puro, sem LLM
  │                          Monta payload com site_data, html_analysis,
  │                          pagespeed, social_profiles, lead_info
  ▼
[fan_out]                  ← LangGraph parallel branching
  │
  ├→ [analyze_lp]          ← LLM (MiniMax M2.7) + structured output
  ├→ [analyze_automation]   ← LLM (MiniMax M2.7) + structured output
  ├→ [analyze_advanced]     ← LLM (MiniMax M2.7) + structured output
  ├→ [analyze_os]           ← LLM (MiniMax M2.7) + structured output
  │
  ▼
[fan_in / qualify]         ← Python puro, sem LLM
  │                          Consolida 4 scores
  │                          Determina nível recomendado
  │                          Desqualifica se todos < threshold
  ▼
END → ServiceLevelAnalysis
```

### LLM: MiniMax M2.7

- Provider: `https://api.minimax.io/v1` (OpenAI-compatible)
- Suporta function calling (97% compliance rate em benchmarks)
- Integração via `langchain-openai` (`ChatOpenAI` + `with_structured_output`)
- Retorna `<think>` tags que o LangChain trata automaticamente com structured output

### Pydantic Schemas

```python
class NivelScore(BaseModel):
    score: int            # 0-100
    sinais: list[str]     # evidências encontradas
    oportunidades: list[str]  # o que pode ser oferecido
    justificativa: str    # por que esse score

class ServiceLevelAnalysis(BaseModel):
    lp: NivelScore
    automacao_basica: NivelScore
    mapa_automacoes: NivelScore
    vertical_os: NivelScore
    nivel_recomendado: str  # "lp" | "automacao_basica" | "mapa_automacoes" | "vertical_os"
    qualificado: bool
    motivo_desqualificacao: str | None
    resumo_executivo: str   # 2-3 frases consolidando tudo
```

### Estrutura de arquivos

```
backend/app/pipeline/
  enricher.py              ← mantém scraping/análise técnica, substitui generate_diagnostic()
  diagnostic/              ← NOVO
    __init__.py
    graph.py               ← definição do grafo LangGraph
    state.py               ← Pydantic models (State, NivelScore, ServiceLevelAnalysis)
    nodes/
      collect.py           ← nó collect_context
      analyze_lp.py        ← nó analyze_lp
      analyze_automation.py
      analyze_advanced.py
      analyze_os.py
      qualify.py           ← nó qualify (consolida + recomenda + desqualifica)
    prompts/
      lp.py                ← prompt template do nível LP
      automation.py
      advanced.py
      os.py
```

## Integração com Pipeline Existente

### Mudança no enricher.py

```python
# Antes:
diagnostic = generate_diagnostic(lead_info, site_data, html_analysis, pagespeed, html)
site_analysis["diagnostico_marketing"] = diagnostic

# Depois:
from app.pipeline.diagnostic import run_diagnostic

service_levels = run_diagnostic(lead_info, site_data, html_analysis, pagespeed, html, social_profiles)
site_analysis["service_levels"] = service_levels.model_dump()
```

### Dados salvos em `site_analysis`

```json
{
  "status": "ok",
  "has_ssl": true,
  "pagespeed": 45,
  "...campos técnicos existentes...",

  "service_levels": {
    "lp": {
      "score": 82,
      "sinais": ["Site inexistente", "Concorrentes com presença forte"],
      "oportunidades": ["LP responsiva com CTA WhatsApp", "SEO local básico"],
      "justificativa": "Negócio com 4.5 no Google mas sem site..."
    },
    "automacao_basica": {
      "score": 65,
      "sinais": ["Atendimento manual via WhatsApp", "Sem auto-resposta"],
      "oportunidades": ["Chatbot para agendamento", "Auto-resposta fora do horário"],
      "justificativa": "Volume de interações sugere..."
    },
    "mapa_automacoes": {
      "score": 40,
      "sinais": ["Google Meu Negócio desatualizado"],
      "oportunidades": ["Otimização GMB", "Fluxo agendamento→confirmação"],
      "justificativa": "Operação ainda simples demais para..."
    },
    "vertical_os": {
      "score": 15,
      "sinais": ["Negócio pequeno, 2 funcionários"],
      "oportunidades": [],
      "justificativa": "Escala insuficiente para justificar..."
    },
    "nivel_recomendado": "lp",
    "qualificado": true,
    "motivo_desqualificacao": null,
    "resumo_executivo": "Clínica com boa reputação mas zero presença digital. Começar por LP + automação de agendamento."
  }
}
```

### Config novas (`app/config.py`)

```python
disqualify_threshold: int = 25       # abaixo em TODOS os 4 = desqualificado
skip_service_level_analysis: bool = False  # feature flag
```

Settings existentes reutilizadas: `llm_api_key`, `llm_base_url`, `llm_model`, `diagnostic_model`.

### Compatibilidade

- `opportunity_score` e `opportunity_reasons` continuam existindo (score técnico do site)
- `diagnostico_marketing` (campo antigo) não é mais gerado, mas leads antigos que já têm continuam funcionando
- Sem database migration — tudo em JSON dentro de `site_analysis`
- Endpoints da API não mudam

## Frontend — Tabs no Lead Sheet

### Componentes

```
frontend/src/components/
  service-level-tabs.tsx    ← NOVO: tabs com 4 níveis
  service-level-card.tsx    ← NOVO: conteúdo de cada tab
  diagnostic-panel.tsx      ← MANTÉM: fallback pra leads antigos
  lead-sheet.tsx            ← EDITA: renderiza ServiceLevelTabs ou DiagnosticPanel
  lead-detail.tsx           ← EDITA: mesmo tratamento
```

### Tipos TypeScript

```typescript
interface NivelScore {
  score: number
  sinais: string[]
  oportunidades: string[]
  justificativa: string
}

interface ServiceLevels {
  lp: NivelScore
  automacao_basica: NivelScore
  mapa_automacoes: NivelScore
  vertical_os: NivelScore
  nivel_recomendado: "lp" | "automacao_basica" | "mapa_automacoes" | "vertical_os"
  qualificado: boolean
  motivo_desqualificacao: string | null
  resumo_executivo: string
}
```

### Layout das tabs

- Header de cada tab: nome do nível + score numérico com cor (verde ≥60, amarelo 40-59, cinza <40)
- Tab do nível recomendado vem pré-selecionada com indicador visual (borda emerald)
- Tab ativa expande: barra de progresso do score, sinais detectados, oportunidades, justificativa
- Lead desqualificado: banner vermelho no topo com motivo
- Sem `service_levels` (leads antigos): fallback pro DiagnosticPanel atual ou mensagem "Enriqueça novamente"

### Na lista/kanban

Sem mudança — continua mostrando `opportunity_score`. Detalhes por nível só no lead sheet/detail.

## Edge Cases

| Caso | Tratamento |
|------|------------|
| 1 dos 4 analistas falha (timeout, JSON inválido) | Score daquele nível = 0, sinais = ["Análise indisponível"]. Os outros 3 continuam normais. |
| Todos os 4 falham | `qualified = True` (não desqualifica por erro), `service_levels` não é salvo |
| Lead sem website | Contexto vai pros 4 analistas com `status: "no_website"`. LP tende alto, OS tende baixo. |
| `skip_service_level_analysis = True` | Pula o grafo inteiro, sem `service_levels` |
| Lead com `diagnostico_marketing` antigo | Frontend: se `service_levels` existe → tabs. Se não → DiagnosticPanel. |
| Re-enriquecer lead | Sobrescreve `service_levels` |

## Custos

| Métrica | Atual | Novo |
|---------|-------|------|
| Chamadas LLM por lead | 1 | 4 (em paralelo) |
| Tokens input (estimado) | ~2k | ~4k total (~1k por analista) |
| Tokens output (estimado) | ~1.5k | ~2k total (~500 por analista) |
| Latência | ~8-10s | ~8-10s (paralelo) |
| Custo por lead (MiniMax M2.7) | ~$0.002 | ~$0.005 |

## Dependências Novas

```
# backend/requirements.txt
langgraph>=0.4
langchain-openai>=0.3
langchain-core>=0.3
```

## O que NÃO muda

- `opportunity_score` e `opportunity_reasons` (score técnico)
- Pipeline stages (scrape → enrich → generate → outreach)
- SSE streaming de progresso
- Modelos de banco de dados (sem migration)
- Endpoints da API
- Outreach messages
- Lead status flow
