# Outreach -- Modulo 4 do Pipeline

**Arquivo:** `backend/app/pipeline/outreach.py`

## O que faz

O modulo de outreach e o quarto e ultimo estagio do pipeline do SDR Machine. Ele gera 3 mensagens de WhatsApp personalizadas para cada lead (initial, followup_48h, followup_final), com links pre-preenchidos wa.me prontos para envio com um clique.

O modulo opera com duas estrategias:

1. **IA (prioritaria):** se o lead tem diagnostico de marketing (`site_analysis.diagnostico_marketing`), gera mensagens via Claude API com personalizacao profunda baseada nos dados do diagnostico
2. **Templates fallback:** se nao ha diagnostico ou a API falha, usa templates estaticos com variaveis de personalizacao basicas

---

## Fluxo de Execucao

### `generate_messages(lead_id, lead_data)`

Funcao principal que produz as 3 mensagens:

```python
def generate_messages(lead_id: int | str, lead_data: dict) -> list[dict]:
```

1. Constroi a URL da landing page: `{API_URL}/api/leads/{lead_id}/lp`
2. Limpa e normaliza o telefone (adiciona prefixo `55`)
3. Verifica se o lead tem site funcional (`website` + `site_analysis.status == "ok"`)
4. Verifica se ha diagnostico de marketing disponivel
5. Se ha diagnostico: tenta gerar as 3 mensagens via IA (com `time.sleep(1)` entre chamadas para rate limiting)
6. Se a IA falhar ou nao houver diagnostico: usa templates fallback
7. Gera links wa.me pre-preenchidos para cada mensagem
8. Retorna lista de 3 dicionarios

### Retorno

```python
[
    {
        "type": "initial",
        "message_text": "texto da mensagem...",
        "whatsapp_link": "https://wa.me/5549999999999?text=texto%20encodado",
    },
    {
        "type": "followup_48h",
        "message_text": "...",
        "whatsapp_link": "...",
    },
    {
        "type": "followup_final",
        "message_text": "...",
        "whatsapp_link": "...",
    },
]
```

---

## Mensagens Geradas por IA

Quando ha diagnostico de marketing disponivel, o modulo chama a Claude API para gerar cada mensagem individualmente, usando dados reais do diagnostico do negocio.

### Dados do diagnostico usados

```python
diag = lead_data.get("site_analysis", {}).get("diagnostico_marketing")
momento = diag.get("momento_funil", "")
resumo = diag.get("resumo_executivo", "")
prioridades = diag.get("prioridades_top3", [])
ia_opps = diag.get("potencial_ia_automacao", {}).get("oportunidades", [])
```

### API Call

```python
resp = requests.post(
    f"{settings.llm_base_url}/chat/completions",
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.llm_api_key}",
    },
    json={
        "model": model,  # settings.diagnostic_model ou settings.llm_model
        "messages": [{"role": "user", "content": prompt}],
    },
    timeout=30,
)
```

O modelo usado e `settings.diagnostic_model` (se definido), senao `settings.llm_model`.

### Post-processing da resposta IA

```python
# Strip thinking blocks
text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
# Remove aspas envolventes
if text.startswith('"') and text.endswith('"'):
    text = text[1:-1]
```

---

## Message Types

### 1. `initial` -- Mensagem Inicial

**Proposito:** primeiro contato, apresentacao + demonstracao da LP.

**Prompt IA -- Regras:**
1. Tom casual e amigavel, como WhatsApp normal
2. Maximo 6-8 linhas
3. Menciona algo ESPECIFICO do diagnostico
4. Se ha oportunidade de IA/automacao, menciona naturalmente
5. Inclui link da LP como demonstracao gratuita
6. Fecha com algo leve, sem pressao
7. Maximo 2 emojis
8. Sem linguagem corporativa ("venho por meio desta", "prezado")
9. Assina com nome e empresa

**Dados injetados no prompt:**
- Nome, nicho, nota Google, reviews, website atual
- Resumo do diagnostico, momento de funil, top 3 prioridades, oportunidades de IA
- Link da LP de demonstracao

### 2. `followup_48h` -- Follow-up 48h

**Proposito:** reengajar apos 48h sem resposta, gerar interesse.

**Prompt IA -- Regras:**
1. Maximo 4-5 linhas
2. Casual e leve, sem pressao
3. Menciona UMA coisa especifica que poderia melhorar rapidamente
4. Inclui o link de novo
5. Sem emojis excessivos
6. Assina com nome

**Dados injetados:** top 3 prioridades, oportunidade de IA mais relevante, link da LP.

### 3. `followup_final` -- Follow-up Final

**Proposito:** ultima mensagem, deixar porta aberta sem pressao.

**Prompt IA -- Regras:**
1. Maximo 3-4 linhas
2. Respeitoso, sem pressao
3. Deixa claro que e a ultima mensagem
4. Deixa porta aberta pro futuro
5. Assina com nome e site

**Dados injetados:** apenas nome do negocio, nome e site do vendedor.

---

## Templates Fallback

Os templates sao usados quando nao ha diagnostico de marketing ou quando a API falha. Ha dois templates de mensagem inicial (com site vs sem site) e templates unicos para os follow-ups.

### `_fallback_initial_com_site` -- Lead com site ruim

Para leads que TEM site mas foi avaliado como ruim pelo enricher:

```
Oi! Tudo bem?

Me chamo {YOUR_NAME}, trabalho com criacao de sites e automacoes pra negocios locais.

Encontrei a {nome} no Google Maps e curti demais a avaliacao de voces ({rating} estrelas). Vi que o site atual tem algumas oportunidades de melhoria ({gaps}).

Fiz uma versao moderna do site de voces como demonstracao -- totalmente gratuita, sem compromisso:

{lp_url}

Se curtir, a gente conversa sobre implementar. Se nao curtir, ta tudo certo tambem!

Abraco!
{YOUR_NAME}
{BUSINESS_NAME}
```

O campo `gaps` usa `lead_data["opportunity_reasons"][:2]` -- as 2 primeiras razoes do opportunity score (ex: "sem SSL", "nao responsivo").

### `_fallback_initial_sem_site` -- Lead sem site

Para leads que NAO possuem site:

```
Oi! Tudo bem?

Me chamo {YOUR_NAME}, trabalho com criacao de sites pra negocios locais.

Encontrei a {nome} no Google Maps -- nota {rating} estrelas com {reviews_count} avaliacoes, voces mandam muito bem!

Notei que voces ainda nao tem um site. Criei uma versao profissional como demonstracao gratuita:

{lp_url}

Ficou com a cara de voces! Se quiser implementar, me avisa. Sem compromisso nenhum.

Abraco!
{YOUR_NAME}
{BUSINESS_NAME}
```

### `_fallback_followup_48h`

```
Oi! So passando pra saber se conseguiu ver a previa que fiz pra {nome}?

{lp_url}

Caso tenha interesse, essa semana ainda consigo implementar com condicao especial. Me avisa!

{YOUR_NAME}
```

### `_fallback_followup_final`

```
Oi! Ultima mensagem sobre aquela previa do site da {nome}.

Se nao for o momento, sem problemas! Mas se quiser conversar sobre presenca digital no futuro, e so me chamar.

Bom trabalho pra voces!
{YOUR_NAME} | {YOUR_WEBSITE}
```

---

## Diferenciacao: Bad Site vs No Site

A logica de diferenciacao acontece em `generate_messages()`:

```python
has_site = lead_data.get("website") and lead_data.get("site_analysis", {}).get("status") == "ok"
```

Um lead e considerado "com site" quando:
1. Tem um valor no campo `website` E
2. O `site_analysis.status` e `"ok"` (o site foi acessado com sucesso pelo enricher)

| Cenario | Mensagem IA | Template Fallback |
|---------|-------------|-------------------|
| Tem site ruim | Prompt inclui website + diagnostico completo | `_fallback_initial_com_site` (menciona gaps) |
| Nao tem site | Prompt mostra website como "NAO TEM" | `_fallback_initial_sem_site` (foca na oportunidade) |
| Tem diagnostico | Usa `_generate_ai_message()` | N/A |
| Sem diagnostico | N/A | Usa templates fallback |
| API falha | Fallback para templates | N/A |

A estrategia de fallback e por mensagem individual:

```python
if not initial_text:
    initial_text = _fallback_initial_com_site(lead_data, lp) if has_site else _fallback_initial_sem_site(lead_data, lp)
if not followup_48h_text:
    followup_48h_text = _fallback_followup_48h(lead_data, lp)
if not followup_final_text:
    followup_final_text = _fallback_followup_final(lead_data)
```

Isso significa que e possivel ter a mensagem initial gerada por IA e os follow-ups por template (se a API falhar nas chamadas subsequentes).

---

## wa.me Links

Os links pre-preenchidos de WhatsApp sao gerados pela funcao interna `_whatsapp_link`:

```python
def _whatsapp_link(text: str) -> str:
    if not phone:
        return ""
    return f"https://wa.me/{phone}?text={urllib.parse.quote(text)}"
```

### Limpeza do telefone

A funcao `_clean_phone` normaliza o numero:

```python
def _clean_phone(phone: str) -> str:
    cleaned = (phone or "").replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
    if cleaned and not cleaned.startswith("55"):
        cleaned = "55" + cleaned
    return cleaned
```

1. Remove caracteres especiais: `+`, `-`, espacos, parenteses
2. Adiciona prefixo `55` (codigo do Brasil) se nao estiver presente
3. Resultado: numero puro (ex: `5549999999999`)

### Formato final do link

```
https://wa.me/5549999999999?text=Oi%21%20Tudo%20bem%3F%0A%0AMe%20chamo%20...
```

O texto da mensagem e URL-encoded via `urllib.parse.quote()`, permitindo que o WhatsApp pre-preencha o campo de mensagem quando o link for aberto.

Se o lead nao tem telefone, o `whatsapp_link` retorna string vazia.

---

## URL da Landing Page

A URL e construida pela funcao `_lp_url`:

```python
def _lp_url(lead_id: int | str) -> str:
    return f"{settings.api_url}/api/leads/{lead_id}/lp"
```

Formato: `http://localhost:8000/api/leads/42/lp` (ou o dominio de producao configurado em `API_URL`).

---

## Configuracao

Variaveis de ambiente relevantes:

| Variavel | Default | Onde e usada |
|----------|---------|-------------|
| `YOUR_NAME` | `Seu Nome` | Assinatura de todas as mensagens |
| `YOUR_WHATSAPP` | `5549999999999` | Nao usado diretamente no outreach (e o WhatsApp do vendedor, nao do lead) |
| `YOUR_EMAIL` | `seu@email.com` | Nao usado nos templates atuais |
| `YOUR_WEBSITE` | `https://seuportfolio.com` | Assinatura do follow-up final |
| `BUSINESS_NAME` | `Studio Digital` | Assinatura da mensagem initial |
| `API_URL` | `http://localhost:8000` | Base URL para construir link da LP |
| `LLM_API_KEY` / `ANTHROPIC_API_KEY` | `""` | Chave da API para geracao IA |
| `LLM_MODEL` | `MiniMax-M2.7` | Modelo LLM (fallback se `DIAGNOSTIC_MODEL` nao definido) |
| `DIAGNOSTIC_MODEL` | `""` | Modelo preferencial para outreach IA |
| `LLM_BASE_URL` | `https://api.minimax.io/v1` | Base URL do provider LLM |

### Dependencia de outros modulos

O outreach depende dos resultados dos modulos anteriores:

- **Scraper:** fornece `nome`, `telefone`, `rating`, `reviews_count`, `nicho`, `categoria`
- **Enricher:** fornece `website`, `opportunity_reasons`, `site_analysis` (incluindo `diagnostico_marketing`)
- **Generator:** a LP deve estar gerada para que o link `lp_url` funcione
