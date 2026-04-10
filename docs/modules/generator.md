# Generator -- Modulo 3 do Pipeline

**Arquivo:** `backend/app/pipeline/generator.py`

## O que faz

O modulo de geracao e o terceiro estagio do pipeline do SDR Machine. Ele cria landing pages HTML completas e personalizadas para cada lead, usando a Claude API (ou outro LLM compativel com OpenAI API). A geracao segue uma arquitetura de 2 passes: primeiro cria um creative brief (copy, paleta, layout), depois gera o HTML completo a partir desse brief.

As landing pages sao standalone (sem dependencias externas alem de Google Fonts e GSAP via CDN), responsivas (mobile-first), com cores dinamicas escolhidas pela IA por negocio, icones SVG inline e animacoes CSS/GSAP.

---

## Arquitetura 2-Pass

### Pass 1 -- Creative Brief

A IA atua como "diretor criativo" e produz um JSON estruturado com todas as decisoes criativas:

- **Paleta de cores:** `bg`, `bg_deep`, `bg_soft`, `surface`, `accent`, `accent_rgb`
- **Tipografia:** heading font + body font (Google Fonts)
- **Hero:** headline, subheadline, CTA text, micro copy
- **Secoes:** problems (4 cards), solution, services (5, com 1 featured), steps (3), FAQ (5), CTA final
- **Design decisions:** hero variant, grid break, accent usage

### Pass 2 -- HTML Generation

A IA atua como "design engineer" e gera o HTML completo usando o brief do Pass 1 como fundacao, junto com um gold standard snippet como referencia de qualidade visual.

### Orquestracao

A funcao principal `generate_landing_page(lead_data)` coordena os 2 passes:

```python
def generate_landing_page(lead_data: dict) -> str:
    # 1. Prepara dados (reviews, gaps, diagnostico, niche guide)
    # 2. Pass 1: Creative Brief (JSON)
    brief = _generate_creative_brief(...)
    # 3. Pass 2: HTML completo
    html = _generate_html(..., brief=brief, ...)
    # 4. Post-processing: substitui {{icon:nome}} por SVG real
    html = re.sub(r'\{\{icon:([^}]+)\}\}', _replace_icon, html)
    return html
```

Se o Pass 1 falhar, a geracao e abortada e retorna string vazia.

---

## API Call

O modulo faz chamadas HTTP diretas via `requests` (nao usa o SDK da Anthropic/OpenAI). Isso permite compatibilidade com qualquer provider que siga o formato OpenAI (`/chat/completions`).

### Pass 1 (Creative Brief)

```python
resp = requests.post(
    f"{settings.llm_base_url}/chat/completions",
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.llm_api_key}",
    },
    json={
        "model": settings.llm_model,
        "temperature": 0.85,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    },
    timeout=60,
)
```

| Parametro | Valor |
|-----------|-------|
| Modelo | `settings.llm_model` (default: `MiniMax-M2.7`) |
| Temperature | `0.85` (alta, para criatividade) |
| Timeout | 60s |

### Pass 2 (HTML)

```python
resp = requests.post(
    f"{settings.llm_base_url}/chat/completions",
    headers={...},
    json={
        "model": settings.llm_model,
        "temperature": 0.7,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    },
    timeout=240,
)
```

| Parametro | Valor |
|-----------|-------|
| Modelo | `settings.llm_model` |
| Temperature | `0.7` (menor que Pass 1, para HTML mais consistente) |
| Timeout | 240s (4 minutos, pois HTML e longo) |

### Compatibilidade de formatos

A extracao da resposta suporta tanto formato OpenAI quanto Anthropic:

```python
choices = data.get("choices") or []
content = data.get("content") or []
if choices:
    raw = choices[0].get("message", {}).get("content", "")
elif content:
    raw = content[0].get("text", "")
```

---

## Prompt Engineering

### Pass 1 -- System Prompt (Creative Brief)

O system prompt do Pass 1 define a persona como "diretor criativo de agencia digital brasileira com 15 anos de experiencia" e especifica a estrutura JSON esperada:

```json
{
  "palette": { "bg": "#hex", "bg_deep": "#hex", "bg_soft": "#hex", "surface": "#hex", "accent": "#hex", "accent_rgb": "r,g,b" },
  "typography": { "heading": "Google Font", "body": "Google Font" },
  "hero": { "headline": "...", "subheadline": "...", "cta_text": "...", "micro_copy": "...", "cta_secondary": "..." },
  "sections": {
    "problems": [4 cards com title, description, icon],
    "solution_headline": "...",
    "solution_bullets": [3 bullets],
    "services": [5 servicos, 1 featured],
    "steps": [3 passos],
    "faq": [5 perguntas],
    "cta_final_headline": "..."
  },
  "design_decisions": { "hero_variant": "split|centered|gradient", "grid_break": "...", "accent_usage": "..." }
}
```

### Pass 1 -- User Prompt

O user prompt inclui:

- **Dados do negocio:** nome, categoria, cidade, nota Google, website, reviews reais
- **Problemas do site atual:** lista de `opportunity_reasons` do enricher
- **Diagnostico de marketing:** resumo executivo, momento de funil, prioridades, potencial de IA
- **Direcao do nicho:** mood, cores, tipografia, metaforas visuais, framework de copy (vem do `NICHE_GUIDES`)
- **Icones disponiveis:** lista completa de nomes SVG

Regras criticas do brief:
1. Headlines sao BENEFICIO/TRANSFORMACAO, nunca descritivas
2. CTAs em 1a pessoa ("Agendar MINHA consulta")
3. Cores com PERSONALIDADE (nunca verde-menta generico)
4. Pelo menos 4 tons de escuro para profundidade
5. Fontes especificas para o negocio

### Pass 2 -- System Prompt (HTML)

A persona do Pass 2 e "VITOR -- design engineer de elite, 12 anos criando LPs premium". O system prompt inclui:

1. **18 regras tecnicas** cobrindo: DOCTYPE, SVG icons, animacoes, GSAP, mobile-first, responsividade, cards com borda gradient, grid assimetrico, etc.
2. **Biblioteca de icones SVG** completa (todos os SVGs inline disponiveis)
3. **Gold Standard** -- snippet HTML de referencia que demonstra o nivel de qualidade visual esperado (hero com gradient mesh, text reveal, orb flutuante, cards com borda gradient via mask-composite)

### Pass 2 -- User Prompt

O user prompt do Pass 2 inclui:

- **Dados do negocio:** nome, categoria, endereco, telefone, WhatsApp link, nota
- **Creative Brief:** JSON completo do Pass 1
- **Avaliacoes reais** (ou instrucao para nao inventar)
- **Banner de credito:** texto e estilo para o banner do topo
- **Footer de credito**
- **Estrutura obrigatoria** -- 14 secoes definidas:

```
1.  BANNER TOPO (preview da agencia)
2.  NAVBAR (sticky, blur, links ancora)
3.  HERO (100svh, gradient mesh, text reveal, CTA shimmer, orb)
4.  BARRA DE CONFIANCA (stats com counter GSAP)
5.  PROBLEMA (dores do cliente, cards com icones SVG)
6.  SOLUCAO (negocio como resposta)
7.  SERVICOS (grid irregular: 1 featured + menores)
8.  COMO FUNCIONA (3 steps timeline)
9.  CTA MID-PAGE (WhatsApp + micro-copy)
10. DEPOIMENTOS (reviews reais OU nota + estrelas)
11. FAQ (details/summary, 5 perguntas)
12. CTA FINAL (background accent, botao grande)
13. FOOTER (endereco, telefone, copyright)
14. CTA FLUTUANTE MOBILE (fixed bottom, so mobile)
```

- **Requisitos tecnicos:** DOCTYPE, lang="pt-BR", meta viewport, Google Fonts, CSS Variables, GSAP 3.12 + ScrollTrigger, section reveals, parallax, counter animado, navbar scroll shadow, prefers-reduced-motion

---

## Niche Guides (NICHE_GUIDES)

O modulo contem guias de personalidade para 14 nichos, cada um definindo:

| Campo | Descricao |
|-------|-----------|
| `mood` | Tom emocional da LP |
| `color_direction` | Direcao de cores (nao paleta fixa -- a IA decide) |
| `typography_direction` | Sugestoes de fontes heading/body |
| `visual_metaphors` | Metaforas visuais do nicho |
| `copy_framework` | Framework de copywriting: `PAS`, `AIDA`, ou `BAB` |
| `icon_suggestions` | Lista de icones SVG sugeridos |

### Nichos suportados

| Nicho | Framework | Mood |
|-------|-----------|------|
| `advocacia` | PAS | autoridade, confianca institucional |
| `dentista` | PAS | confianca clinica, modernidade |
| `clinica` | PAS | autoridade medica, acolhimento |
| `estetica` | AIDA | luxo acessivel, transformacao |
| `restaurante` | BAB | experiencia sensorial, calor humano |
| `pizzaria` | BAB | artesanal, tradicao com energia |
| `salao` | AIDA | glamour, autocuidado |
| `barbearia` | BAB | masculino premium, craft |
| `pet` | PAS | carinhoso, confiavel |
| `academia` | BAB | energia, resultado, disciplina |
| `veterinaria` | PAS | cuidado profissional, empatia |
| `loja` | AIDA | curadoria, descoberta |
| `imobiliaria` | AIDA | aspiracional, patrimonio |
| `construcao` | BAB | solidez, competencia |

Se o nicho do lead nao casar com nenhum dos 14, um fallback generico e usado com mood "profissional, confiavel, moderno" e framework PAS.

O matching e feito por substring case-insensitive:

```python
niche_lower = (niche or "").lower()
for key, guide in NICHE_GUIDES.items():
    if key in niche_lower:
        return guide
```

### Copy Frameworks

```python
_COPY_FRAMEWORKS = {
    "PAS": "PAS (Problema->Agitacao->Solucao): H1 descreve o PROBLEMA, sub agita a consequencia, CTA apresenta a solucao.",
    "AIDA": "AIDA (Atencao->Interesse->Desejo->Acao): H1 bold captura atencao, sub desperta curiosidade, secoes constroem desejo, CTA e acao clara.",
    "BAB": "BAB (Antes->Depois->Ponte): H1 descreve o estado antes, sub pinta o depois, negocio e a ponte.",
}
```

---

## Biblioteca de Icones SVG (SVG_ICONS)

O modulo inclui uma biblioteca de ~35 icones SVG inline (stroke-based, viewBox 0 0 24 24). Categorias:

- **Geral:** shield, shield-check, scale, gavel, file-text, file-search, alert-triangle, check-circle, clock, map-pin, phone, star, star-outline, users, trending-up, zap, target, award, eye, lock, refresh-cw, message-circle, calendar, arrow-right, chevron-down, quote
- **Saude/Dental:** tooth, heart-pulse, stethoscope
- **Food:** utensils, flame
- **Beauty:** scissors, sparkles
- **Pet/Vet:** paw
- **Fitness:** dumbbell
- **Imoveis/Construcao:** building, hard-hat
- **Misc:** dollar-sign, handshake, leaf, wrench

No Pass 1, a IA escolhe icones pelo nome. No Pass 2, ela usa placeholders `{{icon:nome}}` que sao substituidos pelo SVG real no post-processing:

```python
def _replace_icon(match):
    name = match.group(1).strip()
    return SVG_ICONS.get(name, f'<!-- icon "{name}" not found -->')

html = re.sub(r'\{\{icon:([^}]+)\}\}', _replace_icon, html)
```

---

## Gold Standard

O modulo inclui um snippet HTML chamado `GOLD_STANDARD` que serve como referencia de qualidade visual. **Nao e um template** -- a IA usa como ancora de craft. O snippet demonstra:

- **Hero** com gradient mesh (3 radial-gradients sobrepostos, animados), text reveal via clip-path com stagger, orb flutuante com border-radius morphing + blur
- **CTA** com shimmer sweep + glow pulsante, icone WhatsApp SVG inline
- **Card** com borda gradient via mask-composite + inner spotlight hover, container de icone estilizado

---

## Post-processing

Apos receber o HTML da IA, o modulo aplica os seguintes processamentos:

### 1. Strip de thinking blocks

```python
html = re.sub(r"<think>.*?</think>", "", html, flags=re.DOTALL).strip()
```

Remove blocos `<think>` gerados por modelos que usam chain-of-thought visivel (MiniMax, DeepSeek, etc.).

### 2. Strip de code fences

```python
if html.startswith("```"):
    html = re.sub(r"^```\w*\n?", "", html)
    html = re.sub(r"\n?```$", "", html)
```

Remove markdown code fences caso a IA envolva o HTML em ````html ... ````.

### 3. Garantia de DOCTYPE

```python
if not html.lstrip().lower().startswith("<!doctype"):
    html = "<!DOCTYPE html>\n" + html
```

### 4. Substituicao de icones

Troca `{{icon:nome}}` pelo SVG real da biblioteca.

---

## Landing Page Versioning

O sistema suporta multiplas versoes de landing page por lead, implementado no model `LandingPage` e no pipeline runner `_run_generate`.

### Model `LandingPage`

```python
class LandingPage(Base):
    __tablename__ = "landing_pages"

    id = Column(Integer, primary_key=True)
    public_id = Column(String(16), unique=True, nullable=False, default=generate_nanoid)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    html = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=func.now())
```

- Cada LP tem um `public_id` unico (nanoid de 16 chars) para URLs publicas
- `version` e sequencial por lead (1, 2, 3...)
- `is_active` indica qual versao esta ativa (apenas uma por vez)
- Constraint unica em `(lead_id, version)` garante que nao existem versoes duplicadas

### Fluxo de criacao (em `_run_generate`)

Quando uma nova LP e gerada para um lead:

```python
# 1. Desativa LPs anteriores
db.query(LandingPage).filter(
    LandingPage.lead_id == lead.id,
    LandingPage.is_active.is_(True)
).update({"is_active": False})

# 2. Calcula proxima versao
max_version = db.query(func.max(LandingPage.version)).filter(
    LandingPage.lead_id == lead.id
).scalar() or 0

# 3. Cria novo registro
lp = LandingPage(
    lead_id=lead.id,
    html=html,
    version=max_version + 1,
    is_active=True,
)
db.add(lp)

# 4. Atualiza campo legado no lead
lead.lp_html = html
lead.status = "lp_generated"
```

Isso significa que:
- Versoes anteriores sao preservadas (nao deletadas), apenas desativadas
- O campo `lead.lp_html` e mantido por compatibilidade, sempre com o HTML da versao mais recente
- O status do lead e atualizado para `lp_generated`
- Se a geracao falhar, o status vai para `generate_failed`

---

## Error Handling

### Pass 1 (Creative Brief)

- **Resposta vazia:** loga erro detalhado (finish_reason, output_sensitive_type, base_resp) e retorna `None`
- **JSON invalido:** loga os primeiros 500 chars do raw e retorna `None`
- **Excecao generica:** loga com traceback e retorna `None`

Se Pass 1 retorna `None`, a geracao e **abortada** -- nao tenta gerar HTML sem brief.

### Pass 2 (HTML)

- **Resposta vazia:** loga erro detalhado e retorna `""`
- **Excecao generica:** loga com traceback e retorna `""`

### No pipeline runner

- Se `generate_landing_page()` retorna string vazia, o lead recebe status `generate_failed`
- Excecoes por lead sao capturadas: `db.rollback()`, status `generate_failed`, erro adicionado a lista
- O job continua processando os demais leads

---

## Configuracao

Variaveis de ambiente relevantes:

| Variavel | Default | Descricao |
|----------|---------|-----------|
| `LLM_API_KEY` / `ANTHROPIC_API_KEY` | `""` (obrigatorio) | Chave de API do LLM |
| `LLM_MODEL` | `MiniMax-M2.7` | Modelo a ser usado na geracao |
| `LLM_BASE_URL` | `https://api.minimax.io/v1` | Base URL do provider LLM (formato OpenAI) |
| `BUSINESS_NAME` | `Studio Digital` | Nome da agencia (aparece no banner e footer) |
| `YOUR_NAME` | `Seu Nome` | Nome do vendedor |
| `YOUR_WEBSITE` | `https://seuportfolio.com` | Site da agencia (aparece no banner) |

A compatibilidade com formato OpenAI API (`/chat/completions`) permite usar qualquer provider: Anthropic (via proxy), OpenAI, MiniMax, DeepSeek, etc.
