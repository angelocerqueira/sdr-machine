# Diagnostic -- Sistema de Diagnostico com IA via LangGraph

## 1. Visao Geral

O modulo **diagnostic** e o cerebro analitico do pipeline de enriquecimento do SDR Machine. Ele utiliza um grafo LangGraph para executar **4 analises de LLM em paralelo**, cada uma avaliando o potencial de venda de um nivel de servico diferente para o lead.

O objetivo e responder: **"Qual servico devo oferecer para este lead e quanto potencial ele tem?"**

Cada lead recebe scores independentes (0-100) para quatro niveis de servico, e o sistema consolida tudo em uma recomendacao final com qualificacao automatica.

**Localicacao no codigo:** `backend/app/pipeline/diagnostic/`

```
backend/app/pipeline/diagnostic/
  __init__.py              # Exporta run_diagnostic()
  graph.py                 # Grafo LangGraph, funcao principal run_diagnostic()
  state.py                 # Modelos Pydantic: GraphState, NivelScore, ServiceLevelAnalysis
  nodes/
    __init__.py
    collect.py             # Node de coleta de contexto
    analyzers.py           # 4 nodes de analise (LLM calls)
    qualify.py             # Node de qualificacao e consolidacao
  prompts/
    __init__.py
    shared.py              # Formatacao de contexto compartilhada
    lp.py                  # Prompt para Landing Page
    automation.py          # Prompt para Automacao Basica
    advanced.py            # Prompt para Mapa + Automacoes
    os.py                  # Prompt para Vertical OS
```

---

## 2. Arquitetura

### Estrutura do Grafo LangGraph

O diagnostico usa um `StateGraph` do LangGraph com topologia **fan-out / fan-in**:

```
                        +----------------+
                        |     START      |
                        +-------+--------+
                                |
              +---------+-------+-------+---------+
              |         |               |         |
              v         v               v         v
        +-----------+ +-----------+ +-----------+ +-----------+
        | analyze   | | analyze   | | analyze   | | analyze   |
        |   _lp     | | _automa-  | | _advanced | |   _os     |
        |           | |  tion     | |           | |           |
        +-----------+ +-----------+ +-----------+ +-----------+
              |         |               |         |
              +---------+-------+-------+---------+
                                |
                        +-------v--------+
                        |    qualify     |
                        +-------+--------+
                                |
                        +-------v--------+
                        |      END       |
                        +----------------+
```

**Caracteristicas:**

- Os 4 analyzers rodam **em paralelo** (fan-out a partir de `START`).
- Todos convergem para o node `qualify` (fan-in).
- O grafo e compilado uma unica vez e cacheado em `_compiled_graph` (singleton).
- Tracing via LangSmith e configurado no nivel do modulo se as variaveis estiverem presentes.

### Fluxo de Execucao

1. `run_diagnostic()` e chamado pelo `enricher.py` durante o enriquecimento.
2. `collect_context()` monta o `GraphState` inicial a partir dos dados brutos.
3. O grafo compilado e invocado com `graph.invoke(initial_state.model_dump())`.
4. Os 4 analyzers executam em paralelo, cada um fazendo uma chamada LLM.
5. O node `qualify` consolida os 4 resultados em um `ServiceLevelAnalysis`.
6. O resultado final e retornado ou `None` em caso de erro/desabilitacao.

### Compilacao e Cache do Grafo

```python
_compiled_graph = None

def _get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = _build_graph()
    return _compiled_graph
```

O grafo e compilado na primeira invocacao e reutilizado para todas as chamadas subsequentes.

---

## 3. State

O estado do grafo e definido em `state.py` usando modelos Pydantic.

### `GraphState`

O estado principal que flui por todos os nodes do grafo:

```python
class GraphState(BaseModel):
    # Input context (set by collect node)
    lead_info: dict          # Dados do lead (nome, nicho, cidade, rating, reviews)
    site_data: dict          # Resultado do fetch do site (status, html, has_ssl)
    html_analysis: dict      # Analise BeautifulSoup (responsivo, CTA, analytics, etc.)
    pagespeed: dict          # Resultado PageSpeed Insights (performance_score)
    html: str                # HTML bruto do site
    social_profiles: dict    # Perfis de redes sociais coletados

    # Intermediate results (set by analyzer nodes)
    lp_result: NivelScore | None = None
    automacao_result: NivelScore | None = None
    advanced_result: NivelScore | None = None
    os_result: NivelScore | None = None

    # Final result (set by qualify node)
    final_result: ServiceLevelAnalysis | None = None
```

### `NivelScore`

Score e analise para um unico nivel de servico:

```python
class NivelScore(BaseModel):
    score: int          # 0 a 100, clamped via field_validator
    sinais: list[str]   # Evidencias encontradas nos dados
    oportunidades: list[str]  # O que pode ser oferecido
    justificativa: str  # Por que esse score, em 2-3 frases
```

O campo `score` possui um validator que garante que o valor esteja sempre entre 0 e 100:

```python
@field_validator("score")
@classmethod
def clamp_score(cls, v: int) -> int:
    return max(0, min(100, v))
```

### `ServiceLevelAnalysis`

Resultado consolidado final:

```python
class ServiceLevelAnalysis(BaseModel):
    lp: NivelScore
    automacao_basica: NivelScore
    mapa_automacoes: NivelScore
    vertical_os: NivelScore
    nivel_recomendado: NivelKey   # "lp" | "automacao_basica" | "mapa_automacoes" | "vertical_os"
    qualificado: bool
    motivo_desqualificacao: str | None = None
    resumo_executivo: str
```

### `FALLBACK_NIVEL`

Quando um analyzer falha (excecao), ele retorna um fallback com score 0:

```python
FALLBACK_NIVEL = NivelScore(
    score=0,
    sinais=["Analise indisponivel"],
    oportunidades=[],
    justificativa="Falha na analise -- resultado indisponivel.",
)
```

---

## 4. Nodes em Detalhe

### 4.1 `collect` -- Coleta de Contexto

**Arquivo:** `nodes/collect.py`

O node `collect_context` nao e um node do grafo propriamente -- ele e chamado **antes** da invocacao do grafo para montar o `GraphState` inicial.

```python
def collect_context(lead_info, site_data, html_analysis, pagespeed, html, social_profiles) -> GraphState:
    return GraphState(
        lead_info=lead_info,
        site_data=site_data,
        html_analysis=html_analysis,
        pagespeed=pagespeed,
        html=html,
        social_profiles=social_profiles,
    )
```

**Dados de entrada tipicos:**

| Campo | Origem | Exemplo |
|-------|--------|---------|
| `lead_info` | Dados do scraper + DB | `{"nome": "Clinica Vida", "nicho": "dentista", "cidade": "Chapeco SC", "rating": 4.5, "reviews_count": 120, "top_reviews": [...]}` |
| `site_data` | `fetch_website()` | `{"status": "ok", "html": "<html>...", "has_ssl": True}` |
| `html_analysis` | `analyze_html()` | `{"has_responsive_meta": True, "has_cta": False, "word_count": 350, ...}` |
| `pagespeed` | PageSpeed API | `{"performance_score": 45}` |
| `html` | HTML bruto | `"<html><head>..."` |
| `social_profiles` | `scrape_social_profiles()` | `{"instagram": {"username": "clinicavida", "followers": 2500, ...}}` |

### 4.2 `analyzers` -- Nodes de Analise LLM

**Arquivo:** `nodes/analyzers.py`

Existem 4 nodes de analise, todos usando o mesmo pattern via `_run_analyzer()`:

| Node | Result Key | System Prompt | Build Prompt |
|------|-----------|---------------|-------------|
| `analyze_lp` | `lp_result` | `LP_SYSTEM_PROMPT` | `build_lp_prompt` |
| `analyze_automation` | `automacao_result` | `AUTOMATION_SYSTEM_PROMPT` | `build_automation_prompt` |
| `analyze_advanced` | `advanced_result` | `ADVANCED_SYSTEM_PROMPT` | `build_advanced_prompt` |
| `analyze_os` | `os_result` | `OS_SYSTEM_PROMPT` | `build_os_prompt` |

#### Fluxo de cada analyzer:

1. **Cria LLM** via `_get_llm()` -- instancia `ChatOpenAI` apontando para o provider configurado.
2. **Monta contexto** via `_build_context()`:
   - Extrai texto visivel do HTML via `_extract_visible_text()` (limite 2000 chars).
   - Formata com `format_lead_context()` (prompt compartilhado).
3. **Constroi prompt** via `build_*_prompt(context)` + appenda `JSON_INSTRUCTION`.
4. **Chama LLM** com `[system_prompt, user_prompt]`.
5. **Faz parse da resposta** via `_parse_response()`:
   - Remove blocos `<think>` (modelos de raciocinio como DeepSeek).
   - Extrai JSON de fences markdown (````json ... ```).
   - Parseia em `NivelScore`.
6. **Retorna** `{result_key: NivelScore}` ou `{result_key: FALLBACK_NIVEL}` em caso de erro.

#### Configuracao do LLM

```python
def _get_llm() -> ChatOpenAI:
    model = settings.diagnostic_model or settings.llm_model
    return ChatOpenAI(
        model=model,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        max_tokens=4096,
        timeout=60,
    )
```

O modelo e configuravel via `DIAGNOSTIC_MODEL`. Se nao definido, usa o `LLM_MODEL` padrao. O provider usa a interface compativel com OpenAI (`ChatOpenAI`) apontando para qualquer `LLM_BASE_URL`.

#### Instrucao JSON

Todos os prompts recebem ao final esta instrucao:

```
IMPORTANTE: Responda APENAS com JSON valido neste formato exato, sem texto adicional:
{"score": <int>, "sinais": [<strings>], "oportunidades": [<strings>], "justificativa": "<string>"}
```

#### Parse de Resposta

```python
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)

def _parse_response(text: str) -> NivelScore:
    cleaned = _THINK_RE.sub("", text).strip()  # Remove <think> blocks
    match = _JSON_BLOCK_RE.search(cleaned)      # Extrai de fences markdown
    if match:
        cleaned = match.group(1).strip()
    return NivelScore(**json.loads(cleaned))
```

Esse parse lida com dois cenarios comuns de LLMs:
- **Modelos de raciocinio** (ex: DeepSeek R1) que envolvem respostas em `<think>...</think>`.
- **Modelos que formatam JSON em code fences** (ex: ````json { ... } ```).

### 4.3 `qualify` -- Qualificacao e Consolidacao

**Arquivo:** `nodes/qualify.py`

O node `qualify` recebe o estado com os 4 resultados dos analyzers e produz o `ServiceLevelAnalysis` final.

#### Mapeamento de resultados

```python
_RESULT_MAP = [
    ("lp_result",        "lp"),
    ("automacao_result", "automacao_basica"),
    ("advanced_result",  "mapa_automacoes"),
    ("os_result",        "vertical_os"),
]
```

#### Logica de qualificacao

```python
VIABLE_THRESHOLD = 40  # Threshold para um nivel ser "viavel"
```

1. Coleta os scores dos 4 niveis.
2. **Desqualificacao:** Se **todos** os scores estiverem abaixo de `disqualify_threshold` (padrao: 25), o lead e desqualificado. O motivo inclui todos os scores.
3. **Qualificado:** Se pelo menos um score >= `disqualify_threshold`:
   - Percorre os niveis **de tras pra frente** (`vertical_os` -> `mapa_automacoes` -> `automacao_basica` -> `lp`).
   - Recomenda o **nivel mais alto** que tenha score >= `VIABLE_THRESHOLD` (40).
   - Se nenhum atingir 40, recomenda o de maior score absoluto.

A ordem reversa garante que o sistema sempre tenta **vender o servico de maior valor** (upsell).

#### Resumo Executivo

O `resumo_executivo` e montado automaticamente:

```
"Clinica Vida: nivel recomendado e Automacao Basica (score 78/100).
 Oportunidades: chatbot WhatsApp, auto-resposta, agendamento online."
```

Inclui ate 3 oportunidades do nivel recomendado.

---

## 5. Prompts

### 5.1 `shared.py` -- Contexto Compartilhado

A funcao `format_lead_context()` monta um bloco de texto estruturado que todos os 4 analyzers recebem. Inclui:

**Secao DADOS DO NEGOCIO:**
- Nome, nicho/categoria, cidade.
- Nota Google e quantidade de avaliacoes.
- Ate 3 avaliacoes destaque (top_reviews).

**Secao ANALISE TECNICA DO SITE:**
- Status do site (funcional ou problemas).
- SSL/HTTPS, responsividade, WhatsApp, Google Analytics, chatbot, CTA.
- Links de redes sociais, quantidade de palavras e imagens.
- Deteccao de template generico.
- Score PageSpeed mobile.
- Titulo da pagina.

**Secao CONTEUDO VISIVEL:**
- Texto visivel extraido do HTML (ate 2000 caracteres), ou "SEM WEBSITE." se nao houver.

**Secao REDES SOCIAIS:**
- Instagram: username, seguidores, posts, tipo de conta (comercial/pessoal).
- LinkedIn: nome, seguidores, faixa de funcionarios.
- Facebook, TikTok, YouTube: URL do perfil se encontrado.

**Exemplo de contexto formatado:**

```
DADOS DO NEGOCIO:
- Nome: Clinica Vida
- Nicho/Categoria: dentista / Dentist
- Cidade: Chapeco SC
- Nota Google: 4.5 (120 avaliacoes)
- Avaliacoes destaque:
- "Excelente atendimento, mas dificil agendar pelo telefone"
- "Otima clinica, site desatualizado"
- "Demorou pra responder no WhatsApp"

ANALISE TECNICA DO SITE:
- Status: Site funcional
- SSL/HTTPS: Sim
- Responsivo (mobile): Nao
- Link WhatsApp: Nao
- Google Analytics: Nao
- Chatbot: Nao
- CTA: Nao
- Redes sociais no site: Sim
- Conteudo: 180 palavras, 3 imagens
- Template generico: Sim
- PageSpeed mobile: 35/100
- Titulo: Clinica Vida - Dentista

CONTEUDO VISIVEL (trecho):
Clinica Vida Odontologia Bem-vindo a Clinica Vida...

REDES SOCIAIS:
- Instagram: @clinicavida | 2500 seguidores | 85 posts | Comercial
```

### 5.2 `lp.py` -- Landing Page

**System prompt:** Analista de presenca digital de negocios locais. Avalia necessidade de Landing Page e facilidade de venda.

**Criterios para score alto (70-100):**
- Sem site ou site muito ruim (quebrado, lento, nao responsivo).
- Concorrentes com presenca digital melhor.
- Reviews boas mas site nao reflete a qualidade do servico.
- Nicho dependente de presenca online (restaurante, clinica, salao).
- Reviews mencionam dificuldade de encontrar informacao.

**Criterios para score baixo (0-30):**
- Site decente e funcional.
- Nicho que nao depende de site (distribuidora B2B).
- Site recente e bem feito.

### 5.3 `automation.py` -- Automacao Basica

**System prompt:** Analista de automacao comercial. Avalia necessidade de automacoes basicas que nao exigem integracoes complexas.

**Escopo do servico:** Chatbot WhatsApp, auto-resposta, CRM simples, email marketing basico, agendamento online, formularios inteligentes.

**Criterios para score alto (70-100):**
- Atendimento 100% manual com volume significativo.
- Canais desconectados (Instagram DM + WhatsApp + telefone).
- Reviews mencionam "demora pra responder", "nao consegui agendar".
- Nicho com alto volume de interacoes repetitivas.
- Sem chatbot, sem auto-resposta, sem CRM.

**Criterios para score baixo (0-30):**
- Ja usa chatbot ou CRM funcional.
- Baixo volume de interacao com clientes.
- Operacao simples sem processos repetitivos.

### 5.4 `advanced.py` -- Mapa + Automacoes Completas

**System prompt:** Analista de automacao avancada e presenca digital completa. Avalia necessidade de automacoes multi-canal com agents de IA.

**Escopo do servico:** Otimizacao de Google Meu Negocio, fluxos integrados multi-canal (agendamento -> confirmacao -> follow-up -> remarketing), agents de IA que executam tarefas, integracoes CRM + WhatsApp + email + redes sociais.

**Criterios para score alto (70-100):**
- Multiplos pontos de contato com cliente.
- Fluxo de venda/atendimento com 3+ etapas manuais.
- Google Meu Negocio desotimizado com potencial.
- Base digital existente mas fluxos desconectados.
- Nicho com jornada complexa (clinica, imobiliaria, escola).

**Criterios para score baixo (0-30):**
- Negocio simples demais para automacoes complexas.
- Sem maturidade digital (nem WhatsApp Business usa).
- Pouca recorrencia de clientes.
- Jornada de compra muito simples (compra unica).

### 5.5 `os.py` -- Vertical OS

**System prompt:** Analista de plataformas verticais. Avalia potencial para adocao de sistema operacional vertical -- plataforma unica que substitui todas as ferramentas do nicho.

**Escopo do servico:** Sistema completo que substitui ERP + CRM + agendamento + financeiro + marketing + gestao de equipe. Exemplos de mercado: Toast (restaurantes), ServiceTitan (servicos de campo), Mindbody (wellness).

**Criterios para score alto (70-100):**
- Operacao complexa com multiplas areas.
- Equipe de 5+ pessoas com necessidade de coordenacao.
- Nicho com processos fragmentados (5+ ferramentas desconectadas).
- Demanda recorrente de clientes (assinatura, manutencao).
- Reviews/site indicam operacao sofisticada.
- Nicho onde existem vertical OS no mercado.

**Criterios para score baixo (0-30):**
- Negocio de 1-2 pessoas sem equipe.
- Operacao simples sem necessidade de sistema integrado.
- Nicho ja dominado por OS vertical existente que o lead provavelmente ja usa.
- Sem escala para justificar investimento.

---

## 6. Service Levels

Os 4 niveis de servico representam ofertas comerciais de valor crescente:

| Nivel Key | Label | Descricao | Ticket Estimado |
|-----------|-------|-----------|-----------------|
| `lp` | Landing Page | Site/landing page profissional | Baixo |
| `automacao_basica` | Automacao Basica | Chatbot, auto-resposta, CRM simples, agendamento | Medio |
| `mapa_automacoes` | Mapa + Automacoes | Fluxos multi-canal, agents IA, Google Meu Negocio | Alto |
| `vertical_os` | Vertical OS | Plataforma completa customizada para o nicho | Muito alto |

### Logica de Recomendacao

A recomendacao segue a estrategia de **upsell**: o sistema prioriza o nivel mais alto viavel.

```
Para cada nivel, de vertical_os ate lp (ordem reversa):
    Se score >= VIABLE_THRESHOLD (40):
        Recomenda este nivel.
        Para.

Se nenhum atingir 40:
    Recomenda o de maior score absoluto.
```

Isso significa que se `automacao_basica` tem score 75 e `mapa_automacoes` tem score 50, o sistema recomenda `mapa_automacoes` porque e o nivel mais alto acima de 40.

### Scores e Interpretacao

| Faixa | Significado |
|-------|-------------|
| 0-30 | Baixo potencial. Lead provavelmente nao precisa deste servico. |
| 31-39 | Potencial marginal. Possivel, mas nao e o foco. |
| 40-69 | Potencial viavel (`VIABLE_THRESHOLD`). Pode ser oferecido. |
| 70-100 | Alto potencial. Forte indicacao de necessidade. |

---

## 7. Logica de Qualificacao

### Qualificado vs Desqualificado

Um lead e **desqualificado** quando **todos** os 4 scores estao abaixo de `disqualify_threshold` (configuravel, padrao: 25).

```python
all_below = all(s < threshold for s in scores.values())
if all_below:
    qualificado = False
    motivo = f"Todos os scores abaixo de {threshold}: lp=12, automacao_basica=8, ..."
```

Isso filtra leads que nao tem potencial para **nenhum** dos servicos oferecidos.

### Thresholds

| Setting | Padrao | Funcao |
|---------|--------|--------|
| `DISQUALIFY_THRESHOLD` | 25 | Se **todos** os scores < este valor, lead e desqualificado |
| `VIABLE_THRESHOLD` | 40 | Score minimo para um nivel ser considerado viavel para recomendacao |
| `AI_POTENTIAL_THRESHOLD` | 25 | Usado em outros contextos do pipeline (nao no diagnostic) |

### Exemplo de Qualificacao

**Lead qualificado:**
```json
{
  "lp": {"score": 85},
  "automacao_basica": {"score": 65},
  "mapa_automacoes": {"score": 40},
  "vertical_os": {"score": 15},
  "nivel_recomendado": "mapa_automacoes",
  "qualificado": true,
  "motivo_desqualificacao": null,
  "resumo_executivo": "Clinica Vida: nivel recomendado e Mapa + Automacoes (score 40/100). Oportunidades: fluxo agendamento->confirmacao->lembrete, integracao WhatsApp+CRM."
}
```

**Lead desqualificado:**
```json
{
  "lp": {"score": 10},
  "automacao_basica": {"score": 20},
  "mapa_automacoes": {"score": 5},
  "vertical_os": {"score": 8},
  "nivel_recomendado": "automacao_basica",
  "qualificado": false,
  "motivo_desqualificacao": "Todos os scores abaixo de 25: lp=10, automacao_basica=20, mapa_automacoes=5, vertical_os=8",
  "resumo_executivo": "Distribuidora ABC: nivel recomendado e Automacao Basica (score 20/100)."
}
```

---

## 8. Integracao com Enricher

O diagnostic e chamado como **etapa 6** do pipeline de enriquecimento, dentro de `enrich_lead_data()` em `backend/app/pipeline/enricher.py`.

### Fluxo de chamada

```python
# enricher.py (simplificado)

from app.pipeline.diagnostic import run_diagnostic

def enrich_lead_data(website, lead_info=None, skip_pagespeed=False):
    # 1. Fetch site
    site_data = fetch_website(website)
    # 2. Analise HTML
    html_analysis = analyze_html(site_data)
    # 3. Score de oportunidade
    score, reasons = calculate_score(site_data, html_analysis)
    # 4. PageSpeed
    pagespeed = get_pagespeed(website)
    # 5. Redes sociais
    social_profiles = scrape_social_profiles(lead_info, social_urls)

    # 6. Service Level Analysis via LangGraph
    qualified = True
    if lead_info:
        service_levels = run_diagnostic(
            lead_info=lead_info,
            site_data=site_data,
            html_analysis=html_analysis,
            pagespeed=pagespeed,
            html=site_data.get("html", ""),
            social_profiles=social_profiles,
        )
        if service_levels:
            site_analysis["service_levels"] = service_levels.model_dump()
            qualified = service_levels.qualificado

    return {
        "opportunity_score": score,
        "opportunity_reasons": reasons,
        "site_analysis": site_analysis,
        "social_profiles": social_profiles,
        "qualified": qualified,
    }
```

### O que acontece com o resultado

1. O `ServiceLevelAnalysis` e serializado via `.model_dump()` e armazenado dentro de `site_analysis["service_levels"]` no lead.
2. O campo `qualified` determina se o lead segue no pipeline ou e filtrado.
3. Se `run_diagnostic()` retornar `None` (desabilitado ou sem API key), `qualified` permanece `True` -- o lead nao e filtrado.

### Condicoes de bypass

`run_diagnostic()` retorna `None` sem executar o grafo quando:
- `settings.skip_service_level_analysis` e `True`.
- `settings.llm_api_key` nao esta configurada.

---

## 9. Configuracao

Todas as configuracoes estao em `backend/app/config.py` via Pydantic Settings (carregadas do `.env`):

### Variaveis do Diagnostic

| Variavel | Padrao | Descricao |
|----------|--------|-----------|
| `DIAGNOSTIC_MODEL` | `""` (vazio) | Modelo especifico para diagnostic. Se vazio, usa `LLM_MODEL`. |
| `LLM_MODEL` | `"MiniMax-M2.7"` | Modelo padrao para todas as chamadas LLM. |
| `LLM_BASE_URL` | `"https://api.minimax.io/v1"` | URL base do provider (compativel com API OpenAI). |
| `LLM_API_KEY` | `""` | API key do provider LLM (alias: `ANTHROPIC_API_KEY`). |
| `SKIP_SERVICE_LEVEL_ANALYSIS` | `false` | Desabilita completamente o diagnostic. |
| `SKIP_AI_DIAGNOSTIC` | `false` | Flag adicional para pular diagnostico IA. |
| `AI_POTENTIAL_THRESHOLD` | `25` | Threshold de potencial IA (usado em outros contextos). |
| `DISQUALIFY_THRESHOLD` | `25` | Score minimo -- se todos os niveis ficarem abaixo, lead e desqualificado. |

### Variaveis do LangSmith (Tracing)

| Variavel | Padrao | Descricao |
|----------|--------|-----------|
| `LANGSMITH_API_KEY` | `""` | API key do LangSmith para tracing. |
| `LANGSMITH_PROJECT` | `"sdr-machine"` | Nome do projeto no LangSmith. |
| `LANGSMITH_TRACING` | `false` | Habilita/desabilita tracing. |

Quando `LANGSMITH_TRACING=true` e `LANGSMITH_API_KEY` esta definida, o modulo configura as variaveis de ambiente do LangChain automaticamente:

```python
if settings.langsmith_tracing and settings.langsmith_api_key:
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
```

### Exemplo de `.env`

```env
LLM_API_KEY=sk-...
LLM_MODEL=MiniMax-M2.7
LLM_BASE_URL=https://api.minimax.io/v1
DIAGNOSTIC_MODEL=
SKIP_SERVICE_LEVEL_ANALYSIS=false
DISQUALIFY_THRESHOLD=25
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=sdr-machine
```

---

## 10. `html_utils.py` -- Extracao de Texto Visivel

**Arquivo:** `backend/app/pipeline/html_utils.py`

Utilitario compartilhado que extrai texto visivel de HTML para enviar como contexto ao LLM.

```python
def _extract_visible_text(html: str) -> str:
    """Extrai texto visivel do HTML, limitado a 2000 chars pra economizar tokens."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return text[:2000]
```

### Funcionamento

1. Recebe o HTML bruto do site do lead.
2. Faz parse com BeautifulSoup.
3. Remove tags `<script>`, `<style>` e `<noscript>` (conteudo nao visivel).
4. Extrai todo o texto visivel concatenado com espacos.
5. Trunca em **2000 caracteres** para economizar tokens da LLM.

### Papel no Diagnostic

O texto extraido e incluido na secao "CONTEUDO VISIVEL (trecho)" do contexto compartilhado que todos os 4 analyzers recebem. Isso permite que a LLM analise o conteudo real do site sem precisar processar HTML bruto.

Se o lead nao tem site (`html` vazio), a secao mostra "SEM WEBSITE." e o analyzer pode dar scores altos para servicos como Landing Page.

---

## Apendice: Exemplo Completo de Output

Para uma clinica odontologica ficticia, o diagnostic poderia retornar:

```json
{
  "lp": {
    "score": 82,
    "sinais": [
      "Site nao responsivo (sem meta viewport)",
      "PageSpeed mobile 35/100",
      "Apenas 180 palavras de conteudo",
      "Template generico detectado",
      "Sem CTA claro"
    ],
    "oportunidades": [
      "Landing page profissional com agendamento integrado",
      "SEO local otimizado para dentista em Chapeco",
      "Galeria de antes/depois dos tratamentos"
    ],
    "justificativa": "Site atual e um template generico com performance ruim e sem conversao. Uma LP profissional teria alto impacto na captacao de pacientes."
  },
  "automacao_basica": {
    "score": 78,
    "sinais": [
      "Sem chatbot ou auto-resposta",
      "Reviews mencionam demora no atendimento",
      "Sem agendamento online",
      "Instagram comercial ativo mas sem integracao"
    ],
    "oportunidades": [
      "Chatbot WhatsApp para triagem e agendamento",
      "Auto-resposta para perguntas frequentes",
      "Formulario de agendamento online"
    ],
    "justificativa": "Clinica com alto volume de interacoes manuais e reviews indicando demora. Automacao basica resolveria gargalos imediatos de atendimento."
  },
  "mapa_automacoes": {
    "score": 55,
    "sinais": [
      "Multiplos canais ativos mas desconectados",
      "Google Meu Negocio com fotos desatualizadas",
      "Jornada do paciente com 4+ etapas manuais"
    ],
    "oportunidades": [
      "Fluxo agendamento -> confirmacao -> lembrete -> follow-up",
      "Integracao WhatsApp + agenda + CRM",
      "Otimizacao completa do Google Meu Negocio"
    ],
    "justificativa": "Potencial moderado. A clinica se beneficiaria de automacoes integradas, mas precisa primeiro da base (LP + automacao basica)."
  },
  "vertical_os": {
    "score": 30,
    "sinais": [
      "Operacao aparenta ter equipe pequena",
      "Nicho com vertical OS existentes (Dentrix, etc.)"
    ],
    "oportunidades": [
      "Sistema integrado de gestao de clinica"
    ],
    "justificativa": "Nicho valido para vertical OS, mas a escala do negocio parece pequena para justificar uma plataforma completa. Provavel que ja use algum sistema odontologico."
  },
  "nivel_recomendado": "mapa_automacoes",
  "qualificado": true,
  "motivo_desqualificacao": null,
  "resumo_executivo": "Clinica Vida: nivel recomendado e Mapa + Automacoes (score 55/100). Oportunidades: fluxo agendamento -> confirmacao -> lembrete -> follow-up, integracao WhatsApp + agenda + CRM, otimizacao completa do Google Meu Negocio."
}
```

Neste exemplo, apesar de `lp` ter o score mais alto (82), o `nivel_recomendado` e `mapa_automacoes` (score 55). Isso acontece porque o algoritmo percorre os niveis de tras pra frente (`vertical_os` -> `mapa_automacoes` -> `automacao_basica` -> `lp`) e para no primeiro com score >= `VIABLE_THRESHOLD` (40). Como `vertical_os` (30) esta abaixo de 40 mas `mapa_automacoes` (55) esta acima, ele e selecionado -- priorizando sempre o servico de maior valor que seja viavel.
