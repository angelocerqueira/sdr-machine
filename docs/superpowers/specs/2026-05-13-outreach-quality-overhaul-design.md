# Outreach Quality Overhaul — Spec

**Data:** 2026-05-13
**Escopo:** corrigir bugs visíveis + elevar qualidade do gerador de mensagens em `backend/app/pipeline/outreach.py` (cadência fria B2B 5 toques), com suporte a glossário/compliance por nicho, taxonomia de ângulos/CTAs, observabilidade e A/B feedback loop.
**Trigger:** análise da cadência do lead #639 (Dallagnol Advogados — advocacia, POA) achou 17 problemas P0–P4. Handoff completo no chat do dia 2026-05-13.
**Specs relacionados:** `2026-04-08-service-level-scoring-design.md`, `2026-04-20-leads-marketing-diagnostic-design.md`.

---

## Auditoria — o que já existe vs o que falta

| Item handoff | Estado hoje (`outreach.py`) | Gap |
|---|---|---|
| **P0.1** Placeholders não substituídos (`XXXX`, `[...]`) chegam como pronta | `_FORBIDDEN_PATTERNS` cobre clima/datas/% inventado mas **não** placeholders | regex bloqueante `/X{2,}|\[.*?\]|\{.*?\}|TODO|PLACEHOLDER/i` |
| **P0.2** Capitalização inconsistente no início | sem pós-processamento determinístico | normalizer pós-LLM |
| **P0.3** Pontuação quebrada (`.achei` sem espaço) | sem fix automático | regex `/\.[a-záéíóúâêôãõç]/` → forçar `. A` |
| **P1.4** Hipóteses como fatos | persona pede "use APENAS dados", mas sem lista de templates hipotéticos forçados | injetar templates `parece que / pelo que vi / posso estar enganado` + regra explícita |
| **P1.5** CTA repetitivo ("10 min" em 3/5 toques) | `CADENCE_SPECS.initial` sugere "faz sentido 10 min?"; sem variação entre toques | pool `CTA_BY_TYPE` + tracking `cta_usado` por mensagem |
| **P1.6** Ângulos repetidos entre toques | sem taxonomia, sem tracking | enum `ANGULO` + campo `angulo_usado` passado ao prompt do próximo toque |
| **P1.7** Falta apresentação ("sou X da CerqCompany, ajudamos Y") | persona define remetente mas prompt não obriga bloco de apresentação na initial | regra mínima estrutural da initial |
| **P2.8** Tom "auditor não solicitado" | regras de hook focam em problema-first | estrutura mínima da initial (6 passos: saudação → apresentação → razão → hipótese → CTA leve → saída honrosa) |
| **P2.9** Falta humildade contextual | sem frases obrigatórias por toque | exigir ≥2 marcadores semânticos de humildade na cadência |
| **P2.10** Tech-bro inadequado pro nicho ("ping", "chatbot jurídico") | sem glossário | tabela `glossario_por_nicho` (config JSON) |
| **P2.11** Saudação personalizada (Dr./Dra.) faltando | campo `tratamento_formal` não existe no Lead | nova coluna + injeção no prompt |
| **P3.12** Compliance OAB/CFM ausente | sem camada por nicho | tabela `compliance_por_nicho` (termos bloqueantes/substitutos) |
| **P3.13** Citação literal de review negativa sem salvaguarda | `review_destaque` é passado raw | wrapper de citação com framing protetor |
| **P4.14** Bump d2 vazio de valor | `CADENCE_SPECS.bump_d2` **permite explicitamente** "só dando ping" | redefinir propósito: ≥1 fato/pergunta nova vs initial (conflito com filosofia atual — ver §6) |
| **P4.15** Cara-de-IA não detectado | `_FORBIDDEN_PATTERNS` não cobre clichês SDR-AI | expandir lista (`Achei curioso:`, `Notei que...`, `Vi que vocês...` como abertura) |
| **P4.16** Sem telemetria por mensagem | colunas `sent_at`/`response_received_at` existem; nada de copy/click | colunas `copy_count`, `click_count`, `manual_rating` |
| **P4.17** A/B test loop | função `generate_messages` gera 1 cadência só | endpoint regenera variante alternativa + campo `variant_label` |

### Schema gaps consolidados

**`outreach_messages`:**
- `validation_errors` (JSON, lista de falhas regex que forçaram fallback)
- `angulo_usado` (String(40))
- `cta_usado` (String(40))
- `variant_label` (String(8) — `A`/`B`, null = single)
- `copy_count` (Integer default 0)
- `click_count` (Integer default 0)
- `manual_rating` (SmallInt nullable — `+1`/`-1` flag humano)
- `status` (String(20) — `pronta` / `erro_geracao` / `regenerada`)

**`leads`:**
- `tratamento_formal` (String(10) — `dr`/`dra`/`sr`/`sra`/`primeiro_nome`, nullable)

**Config (JSON estático em `app/config/outreach/`):**
- `glossario_por_nicho.json`
- `compliance_por_nicho.json`
- `ctas.json` (pool por tipo de toque)
- `angulos.json` (taxonomia)

---

## Arquitetura proposta

### 1. Pipeline pós-LLM (novo)

Hoje `_generate_ai_message()` chama LLM e roda `_validate_llm_output()`. Validação é binária (passa/falha → fallback). Proposta: pipeline em 3 estágios.

```
LLM output
  ↓
[Stage 1: hard validators]   ← regex bloqueantes (placeholder, padrões proibidos, comprimento, pontuação)
  ↓ FAIL → log validation_errors, status="erro_geracao", retry (até 2x) ou fallback
  ↓ PASS
[Stage 2: deterministic fixers]   ← capitalização, espaço após ponto, normalização de aspas
  ↓
[Stage 3: soft validators]   ← glossário, compliance, clichês cara-de-IA, humildade
  ↓ FAIL → log warning, regenerar com instruction adicional (até 1x)
  ↓ PASS → grava com status="pronta", angulo_usado, cta_usado
```

**Arquivo novo:** `backend/app/pipeline/outreach/validators.py`
- `validate_hard(text, msg_type) -> ValidationResult` (errors[], passed: bool)
- `validate_soft(text, ctx) -> ValidationResult` (warnings[], passed: bool)
- `fix_capitalization(text) -> str`
- `fix_punctuation_spacing(text) -> str`
- `detect_placeholders(text) -> list[str]` — regex `/X{2,}|\[[^\]]*\]|\{[^}]*\}|TODO|PLACEHOLDER/i`
- `detect_ai_cliches(text) -> list[str]` — lista expandida com "Achei curioso", "Notei que", "Vi que vocês" (abertura), "Faz sentido conversarmos X minutos?", "Espero que esteja tudo bem"
- `check_glossario(text, nicho) -> list[str]` — termos do nicho que devem ser substituídos
- `check_compliance(text, nicho) -> list[str]` — bloqueantes regulatórios

`outreach.py` vira thin orchestrator que chama validators. Refatorar `_validate_llm_output()` → mover regras pra `validators.py`.

### 2. Taxonomia de ângulos e CTAs (novo)

**`app/config/outreach/angulos.json`:**
```json
{
  "seo": "SEO / encontrabilidade",
  "reputacao": "Reputação / reviews",
  "conversao": "Conversão / canais de contato",
  "posicionamento": "Posicionamento / autoridade",
  "experiencia_mobile": "Experiência mobile / técnica",
  "operacao": "Operação / atendimento manual",
  "pipeline": "Pipeline / ferramentas desconectadas"
}
```

**`app/config/outreach/ctas.json`:**
```json
{
  "initial": ["pergunta_aberta_diagnostica", "convite_10min", "diagnostico_link"],
  "bump_d2": ["chegou_a_ver", "pergunta_nova_curta"],
  "insight_d5": ["sem_cta", "valeria_compartilhar"],
  "angle_d9": ["reuniao_curta", "diagnostico_link", "pergunta_pivot"],
  "breakup_d14": ["porta_aberta", "sem_pressao"]
}
```

**Regra:** dentro de uma cadência, CTAs únicos entre toques (validação no `generate_messages`). Se LLM repete CTA já usado, regenerar com instruction `"CTA não pode ser '{cta_anterior}', use outro do pool: {pool}"`.

**Ângulo:** `generate_messages` mantém set `angulos_usados`. Cada chamada `_generate_ai_message` recebe `angulos_disponiveis = todos - usados`. Initial pode escolher livre; demais (sobretudo angle_d9) recebem instruction `"Use um ângulo DIFERENTE de: {angulos_usados}"`.

### 3. Glossário e compliance por nicho (novo)

**`app/config/outreach/glossario_por_nicho.json`:**
```json
{
  "advocacia": {
    "evitar": {
      "captação de clientes": "presença institucional",
      "chatbot": "canal de atendimento automatizado",
      "ping": "retomando o contato",
      "tópico": "assunto",
      "lead": "potencial cliente",
      "conversão": "engajamento"
    }
  },
  "medicina": { ... },
  "contabilidade": { ... }
}
```

**`app/config/outreach/compliance_por_nicho.json`:**
```json
{
  "advocacia": {
    "regulacao": "OAB Provimento 205/2021",
    "bloqueantes": ["captação de clientes", "captar clientes", "trazer mais clientes", "atrair clientes"],
    "preferir": ["visibilidade institucional", "encontrabilidade", "presença digital", "autoridade"]
  },
  "medicina": {
    "regulacao": "CFM Resolução 1.974/2011",
    "bloqueantes": ["garantia de resultado", "antes e depois", "promoção", "oferta", "desconto"]
  }
}
```

**Loader:** `app/config/outreach/__init__.py` carrega JSONs uma vez (módulo-level cache). Funções `glossario(nicho)`, `compliance(nicho)` retornam `{}` se nicho não estiver mapeado (sem bloqueio).

**Aplicação no prompt:** se nicho do lead tem entrada, injetar bloco em `_persona_block()`:
```
# GLOSSÁRIO DO NICHO {nicho}
NUNCA use estes termos:
- "captação de clientes" → use "presença institucional"
- ...
# COMPLIANCE
Regulação: OAB Provimento 205/2021. Bloqueado: captação, captar clientes...
```

**Validação:** `check_glossario` + `check_compliance` rodam em `validate_soft`. Match → regenerar.

### 4. Tratamento formal (novo)

**Inferência:** novo campo `tratamento_formal` no Lead. Default `null` → prompt usa fallback. Classificação:
- Nicho `advocacia`/`medicina`/`odontologia` → `dr`/`dra` (se há nome de pessoa identificável nos sócios; senão fallback)
- Outros nichos → `primeiro_nome` ou `sr`/`sra` se há sócio identificável

**Onde inferir:** novo step em `enrichment/orchestrator.py` (fase Discovery, depois do CnpjProvider preencher `socios`). Provider novo `TratamentoFormalInferrer` (ou inline no CnpjProvider). Backfill via migration script opcional.

**Uso no prompt:** se `tratamento_formal` for `dr` e há nome do sócio mais relevante → injetar "Saudação obrigatória: 'Dr. {primeiro_nome_socio}, ...'".

### 5. Estrutura mínima da initial (novo)

Adicionar bloco em `_persona_block()` quando `msg_type == "initial"`:

```
# ESTRUTURA MÍNIMA DA INITIAL (obrigatória)
1. Saudação cordial com tratamento ({tratamento_formal} {primeiro_nome_socio}) ou "Oi" se não houver.
2. Apresentação em 1 frase: nome + empresa + o que faz. Ex: "Aqui é o Angelo, da CerqCompany — ajudo {nicho} a melhorar presença digital."
3. Razão do contato com humildade (não auditoria).
4. Observação como hipótese (use: "parece que", "pelo que vi do site", "posso estar enganado, mas").
5. Pergunta aberta ou CTA mole (do pool {ctas.initial}).
6. Saída honrosa: "se já estiverem resolvendo, desconsidera" / "espero não estar incomodando".

NUNCA afirme que algo está errado. Sempre apresente como observação/pergunta.
```

E lista explícita de **templates hipotéticos** permitidos (linguagem segura):
- "parece que..."
- "pelo que vi do site..."
- "posso estar enganado, mas..."
- "pode ser proposital, mas notei..."

### 6. Bump d2 — redefinição (decisão pendente)

**Conflito:** `outreach.py:333-338` proíbe explicitamente "introduzir qualquer informação nova" no bump d2; handoff P4#14 diz que isso é vazio e exige ≥1 fato/pergunta nova.

**Recomendação:** seguir handoff. Bumps "ping puro" têm taxa de resposta próxima de zero. Redefinir spec:

```
"bump_d2": {
  "purpose": "top of mind com 1 elemento novo — pergunta ou fato",
  "extra_rules": [
    "Adicione UMA pergunta diferente da initial OU UM fato novo do diagnóstico.",
    "Ainda assim ultra-curto (2-3 linhas).",
    "PROIBIDO repetir ângulo/CTA da initial.",
    "PROIBIDO clima, dia da semana, 'tudo bem'."
  ]
}
```

Validação: comparar overlap textual com initial — se Jaccard > 0.6 nos n-gramas, regenerar.

### 7. Salvaguarda em review negativa (novo)

`_format_ctx_facts()` linha 232 hoje injeta `review_destaque` cru. Risco: LLM cita literal.

**Mudança:**
- Classificar review: se sentimento negativo (heurística: presença de palavras `ruim/péssimo/mal/horrível/decepcionante/grosseiro`), marcar como `review_negativa: true` no contexto.
- Se negativa, **não passar texto literal** — passar resumo: `"existe uma avaliação negativa pontual no Google"`.
- Injetar regra no prompt: "Se mencionar review negativa, enquadrar com cuidado: 'vi que apareceu uma avaliação que pode não refletir o trabalho de vocês' — nunca citar literal."

### 8. Telemetria + A/B (novo)

**Endpoints novos** (`backend/app/routers/outreach.py`, novo router):
- `POST /api/outreach/messages/{id}/copy` — incrementa `copy_count`
- `POST /api/outreach/messages/{id}/click` — incrementa `click_count`
- `POST /api/outreach/messages/{id}/rate` — body `{rating: 1 | -1}` → grava em `manual_rating`
- `POST /api/outreach/messages/{id}/variant` — gera variante alternativa (B), grava com `variant_label="B"`

**Frontend** (`la-tab-mensagens.tsx`):
- Botão "Copiar" → também dispara `POST /copy`
- Link WA → também dispara `POST /click`
- Botões 👍/👎 sutis no rodapé da mensagem
- Botão "Gerar variação" → chama `/variant` e renderiza A/B lado-a-lado com toggle

**Feedback loop:** análise futura (não MVP) — endpoint `GET /api/outreach/stats?nicho=X` retorna agregados (taxa cópia/clique/rating médio por nicho/ângulo/CTA) pra prompt-tuning manual.

---

## Mudanças por arquivo

### Backend

**Novo:**
- `backend/app/pipeline/outreach/__init__.py` (mover `outreach.py` pra pacote)
- `backend/app/pipeline/outreach/generator.py` (orchestrator, era o `outreach.py` antigo)
- `backend/app/pipeline/outreach/validators.py` (validators hard + soft + fixers)
- `backend/app/pipeline/outreach/cadence_specs.py` (CADENCE_SPECS + revisões P4#14)
- `backend/app/pipeline/outreach/prompts.py` (persona, hook, estrutura initial, glossário injection)
- `backend/app/config/outreach/glossario_por_nicho.json`
- `backend/app/config/outreach/compliance_por_nicho.json`
- `backend/app/config/outreach/ctas.json`
- `backend/app/config/outreach/angulos.json`
- `backend/app/config/outreach/__init__.py` (loaders)
- `backend/app/routers/outreach.py` (telemetria + A/B)
- `backend/alembic/versions/o08_outreach_quality_fields.py` (migration)
- `backend/tests/test_outreach_validators.py`
- `backend/tests/test_outreach_glossario.py`
- `backend/tests/test_outreach_compliance.py`

**Alterado:**
- `backend/app/models.py` — `OutreachMessage` ganha 8 colunas (ver §schema gaps); `Lead` ganha `tratamento_formal`.
- `backend/app/schemas.py` — `OutreachMessageOut` expõe `validation_errors`, `angulo_usado`, `cta_usado`, `variant_label`, `copy_count`, `click_count`, `manual_rating`, `status`.
- `backend/app/routers/pipeline.py:294-360` (`_run_outreach`) — passa `angulos_usados` set entre toques; grava novos campos.
- `backend/app/main.py` — registra `routers/outreach.py`.
- `backend/app/pipeline/enrichment/providers/cnpj.py` — preencher `tratamento_formal` baseado em nicho + sócios.

**Deletado:** nada. `outreach.py` vira `outreach/generator.py` (re-export pra manter import path estável).

### Frontend

**Alterado:**
- `frontend/src/components/leads/la-tab-mensagens.tsx` — botões rate +/-, telemetria de copy/click, render de A/B side-by-side, badge de `status` (erro_geracao em vermelho).
- `frontend/src/components/leads/lead-app-types.ts` — `LeadAppMessage` ganha campos novos.
- `frontend/src/lib/api.ts` — `copyMessage`, `trackClick`, `rateMessage`, `generateVariant`.
- `frontend/src/components/leads/lead-app.css` — estilos do toggle A/B + rate buttons.

---

## Migration

```python
# o08_outreach_quality_fields.py
def upgrade():
    op.add_column("leads", sa.Column("tratamento_formal", sa.String(10), nullable=True))
    op.create_index("idx_leads_tratamento_formal", "leads", ["tratamento_formal"])

    op.add_column("outreach_messages", sa.Column("validation_errors", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("outreach_messages", sa.Column("angulo_usado", sa.String(40), nullable=True))
    op.add_column("outreach_messages", sa.Column("cta_usado", sa.String(40), nullable=True))
    op.add_column("outreach_messages", sa.Column("variant_label", sa.String(8), nullable=True))
    op.add_column("outreach_messages", sa.Column("copy_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("outreach_messages", sa.Column("click_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("outreach_messages", sa.Column("manual_rating", sa.SmallInteger(), nullable=True))
    op.add_column("outreach_messages", sa.Column("status", sa.String(20), nullable=False, server_default="pronta"))
```

Reversível (drop colunas/index). Sem `data migration` — campos opcionais ou com default.

---

## Ordem de implementação (5 PRs)

| PR | Escopo | Fase handoff | Risco |
|----|--------|-------------|-------|
| **PR1** | `validators.py` (hard validators + fixers P0.1-3) + migration colunas mínimas (`status`, `validation_errors`) + testes | P0 | baixo, isolado |
| **PR2** | Taxonomia `ctas.json`/`angulos.json` + tracking `cta_usado`/`angulo_usado` + apresentação obrigatória initial + templates hipotéticos + bump d2 redefinido | P1 | médio (toca prompt) |
| **PR3** | Estrutura mínima initial + humildade + `tratamento_formal` (Lead + inferer no CnpjProvider) + clichês cara-de-IA expandidos | P2 | médio |
| **PR4** | Glossário + compliance por nicho (advocacia + medicina + contabilidade no MVP) + salvaguarda review negativa | P3 | médio (novos JSONs) |
| **PR5** | Telemetria (`copy_count`/`click_count`/`manual_rating`) + endpoint A/B + UI A/B side-by-side | P4 | baixo (additive) |

Cada PR independente — pode mergear em ordem ou pular (ex: PR5 pode vir antes de PR4 se quiser dado de baseline primeiro). Recomendação: ordem natural P0→P4.

---

## Testes mínimos por PR

- **PR1:** unit tests `validators.py` (cobertura: placeholder, capitalização, pontuação, comprimento, padrões proibidos). Snapshot test do fluxo `generate_messages` com fallback acionado.
- **PR2:** test que valida que 5 toques têm CTAs únicos. Test que `angulo_usado` é diferente entre initial e angle_d9.
- **PR3:** test do bloco de estrutura mínima injetado no prompt. Test do `tratamento_formal` inferido.
- **PR4:** test que termo bloqueante do glossário força regeneração. Test de compliance OAB no nicho advocacia.
- **PR5:** test do endpoint copy/click/rate. Test de geração de variante B.

---

## Decisões (open questions resolvidas — 2026-05-13)

1. **Retry policy:** ~~sem retry~~. Acertar de primeira. Pipeline: LLM → hard validators → fixers → soft validators. Qualquer fail → fallback determinístico direto (sem regenerar). Mais previsível, menos custo de token.
2. **Bump d2:** redefinir conforme handoff P4#14. ≥1 fato/pergunta nova vs initial. Sem alternativa conservadora.
3. **Tratamento formal — múltiplos sócios:** pular pra "Oi" sem nome. Não tentar adivinhar sócio principal.
4. **Compliance scope:** expandir MVP. PR4 cobre **advocacia, medicina, odontologia, contabilidade, arquitetura, engenharia** — todos com regulação profissional. Demais nichos sem compliance específico (passthrough).
5. **A/B loop automático:** backlog futuro confirmado.
6. **Cadência:** manter piso 5 toques. Sem `social_proof_d7`.
7. **Quantificação de dor:** liberar **com salvaguardas**. Templates permitidos só sobre dados reais já no contexto:
   - "vi {reviews_count} avaliações no Google" — OK
   - "rating {rating}★" — OK
   - Cálculos hipotéticos ("se X% fechassem") **proibidos** — nova regex em `_FORBIDDEN_PATTERNS`: `\bse\s+\d+\s*%`.
   - Sem inventar volume de leads/clientes/receita.
8. **Lifecycle status:** **PR6 separado** (não bloqueia PR3). Motivo: migration + lógica de detecção de resposta (parser de mensagem inbound) é escopo distinto. Mantém PR3 focado em tom/estrutura.
9. **Checklist humano** — explicação abaixo:

### Sobre #9 — Checklist humano primeiros leads por nicho

Cenário: PR4 introduz glossário + compliance pra advocacia. Primeira vez que esse glossário roda, **não temos certeza** que cobre tudo (termos OAB sutis podem escapar). Risco: mandar mensagem que viola OAB pra advogado real → queima lead e expõe Sollertis.

Mitigação proposta: primeiros **10 leads** de um nicho que estreia compliance não vão direto pra `outreach_ready`. Vão pra **status intermediário** onde humano (você) revisa as 5 mensagens no Lead App e clica "Aprovar" ou "Regenerar". Depois dos 10 aprovados, nicho destrava e segue automático.

**Duas variantes:**
- **(a) Bloqueante** — status `outreach_pending_review`. Lead trava até aprovação. Mais seguro, mais fricção.
- **(b) Notificação** — gera normal, marca flag `needs_review: true`, badge no Lead App. Não trava envio. Você revisa quando quiser. Mais ágil, risco maior.

**Decisão: (b) notificação.** Implementação:
- Coluna `needs_review: bool` em `outreach_messages` (default `false`).
- Setada `true` quando lead pertence a nicho com glossário/compliance estreando (controlado por contador: primeiros 10 leads por `nicho` que ativaram compliance flag).
- Frontend `la-tab-mensagens.tsx`: badge "🔍 revisar" no header da mensagem quando `needs_review === true`.
- Sem bloqueio de pipeline. Lead segue `outreach_ready` normalmente.
- Endpoint `POST /api/outreach/messages/{id}/mark-reviewed` zera flag e incrementa contador do nicho.

Entra em **PR4** junto com glossário/compliance.

---

## Anexo A — Validação @comercial / Commercial Squad

> Cross-check do spec com `comercial/commercial-squad/voice/voz-smb.md` e `tasks/pipeline/design-multi-touch-cadence.md`. ICP do SDR Machine = SMB tier 3 local (advocacia, médicos, contabilidade — donos/sócios, 10-30 pessoas), canal WhatsApp. Squad foca no que move resposta nesse perfil.

### A.1 Onde o spec acerta vs squad

| Decisão do spec | Validação squad |
|---|---|
| Estrutura mínima da initial com saudação cordial + apresentação 1 frase + saída honrosa | ✅ Match com voz SMB: "Sou da Sollertis, a gente ajuda…" + "Se não for o momento, tranquilo". |
| Pool de CTAs variados, sem repetir "10 min" | ✅ Match. Voz SMB prefere "Faz sentido pra vocês ou não é o caso?" sobre "agendar reunião". |
| Tratamento formal (Dr./Dra.) injetado | ✅ Match. Voz SMB: "SMB quer relação, não transação". Trato cordial é diferencial. |
| Glossário/compliance por nicho (OAB/CFM) | ✅ Match. Voz SMB: "Evitar jargão" — extensão natural pra termos regulados. |
| Bump d2 com fato/pergunta novos (P4#14) | ✅ Match com squad: "Cada toque aborda ângulo diferente — não repetir mesma mensagem". |
| Cadência 5 toques em 14 dias | ✅ Bate com squad Tier 3 SMB: "5-7 toques em 14 dias". No piso, mas válido. |
| Humildade explícita ("posso estar enganado") | ✅ Match: voz SMB exige "Dá saída honrosa", "Não força". |
| Salvaguarda em review negativa | ✅ Reduz risco de queimar relação — voz SMB: "SMB lembra de quem ajudou". |

### A.2 Gaps que o spec não cobre (vindos do squad)

**Gap 1 — Falta princípio de "quantificar dor".**
Voz SMB: *"200 leads parados = R$40k de oportunidade"* é mais persuasivo que vaga "tem espaço pra melhorar". Spec atual permite hipóteses sóbrias, mas não força quantificação quando há dado.
→ **Sugestão:** novo template de hook permitido na initial: "se 10% dos seus leads do Google fechassem, seria X clientes". Validar regex que não gere número inventado — só usar `reviews_count` e proxies reais. Adicionar à lista de FONTES DE HOOK em `_hook_calibration_block`.

**Gap 2 — Falta case similar / "empresa do seu tamanho".**
Voz SMB: *"Empresa X (mesmo tamanho, mesmo segmento) fez e deu certo"* — frame canônico. Spec não tem campo `case_referencia` por nicho.
→ **Sugestão:** novo JSON `cases_por_nicho.json` com 1-2 cases por nicho (anônimos se necessário). Injetar em angle_d9 ou insight_d5 como prova social leve. Cuidado anti-hallucination: forbidden pattern já bloqueia "concorrentes seus já fazem X" sem dado — então só usar case se realmente houver registro.

**Gap 3 — Falta risk reversal / piloto.**
Voz SMB: *"Risco é meu, não seu. Se não funcionar, você não paga a segunda parcela"*. Spec não tem nada de oferta no outreach. Pode não caber na initial (cold), mas no angle_d9 / breakup_d14 cabe um CTA de baixo atrito.
→ **Sugestão:** adicionar ao pool `ctas.json`:
- `angle_d9`: `"piloto_curto"` → "topa testar com 1 lead/cliente em 2 semanas, sem custo?"
- `breakup_d14`: `"diagnostico_gratuito"` → "se quiser, mando um diagnóstico curto sem custo — só responder 'sim'."

**Gap 4 — Cadência 5 toques no piso do squad.**
Squad recomenda 5-7 toques pra Tier 3 SMB. SDR Machine está em 5. Maximizar resposta sugere expandir.
→ **Open question (novo, #6 do spec):** vale subir pra 6 toques? Sugestão: insert D+7 entre insight_d5 e angle_d9 com tipo `social_proof_d7` (case similar). Decidir em PR2/PR3.

**Gap 5 — Canal único (WhatsApp).**
Squad pra SMB recomenda mix: email + LinkedIn + WhatsApp. SDR Machine só gera WhatsApp link. Limitação conhecida — vale documentar.
→ **Sugestão (backlog):** PR futuro `outreach-multichannel` — gerar variante email + variante LinkedIn DM da mesma cadência. Não bloqueia esse spec, mas registrar.

**Gap 6 — Falta "regras de parada" / status pós-cadência.**
Squad task define explicitamente:
- resposta positiva → qualificação
- "não agora" → nurture 60-90d
- opt-out explícito → remove
- sem resposta após N toques → tentar daqui 6 meses
SDR Machine `Lead.status` vai até `closed`/`delivered` mas não tem `nurture_60d` nem `opt_out`. Cadência D+14 termina e lead fica em limbo.
→ **Sugestão:** novos status no Lead:
- `nurture_60d` (auto-set quando lead responde "não agora" — detectar no futuro via integração de resposta)
- `opt_out` (manual ou detectado por padrão "não quero mais", "para de mandar")
- `cold_revisit` (auto-set 14 dias após breakup_d14 se nenhuma resposta — fila pra retry em 6 meses)
Não bloqueia esse spec — vira PR follow-up "outreach-lifecycle".

**Gap 7 — Telemetria sem KPIs de conversão.**
Spec prevê copy/click/rating — bom. Squad task pede também: **taxa de resposta por toque** e **toque com maior conversão**. Sem isso, não dá pra iterar prompt.
→ **Sugestão:** estender PR5. Adicionar coluna `response_at` (já existe `response_received_at`, ok) e endpoint `GET /api/outreach/stats?nicho=X&period=Y` com agregados:
```
{
  "por_toque": {"initial": {"sent": 100, "responded": 12, "qualified": 3}, ...},
  "por_angulo": {"seo": {"resposta_pct": 0.18}, ...},
  "por_cta": {"convite_10min": {"resposta_pct": 0.08, "diagnostico_link": {...}}, ...}
}
```

**Gap 8 — Falta regra de "você" vs "vocês".**
Voz SMB: usa "você" quando há dono identificado (relação pessoal); "vocês" quando há time. Spec não distingue.
→ **Sugestão:** quando `tratamento_formal != null` E há sócio identificado, prompt usa "você"; senão usa "vocês". Regra mínima no `_persona_block()`.

**Gap 9 — Checklist humano opcional pra primeira semana de cada nicho.**
Squad task tem 9-itens checklist de validação. SDR Machine valida tudo automático.
→ **Sugestão:** quando glossário/compliance pra um nicho é introduzido, primeiros 10 leads do nicho ficam em `status="outreach_pending_review"` (humano valida no Lead App antes de marcar `outreach_ready`). Aprovação manual destrava — ou auto-aprova após N dias sem revisão. Adicionar coluna `pending_review_reason` na `outreach_messages`. Decisão go/no-go: PR4 ou PR5.

**Gap 10 — Falta "Problema-Solução-Prova-Preço" como frame para angle_d9.**
Voz SMB: o frame canônico que converte SMB é PSPP. Initial é frio demais pra usar — mas angle_d9 já tem aquecimento e cabe um esqueleto:
- Problema: 1 dor concreta do diagnóstico
- Solução: 1 entrega curta (não pitch)
- Prova: case similar ou métrica real
- Próximo passo: pequeno (não preço aqui, mas diagnóstico ou piloto)
→ **Sugestão:** adicionar `CADENCE_SPECS.angle_d9.extra_rules` template estrutural opcional. Não forçar — se LLM achar que pivot pra outro ângulo funciona, livre.

### A.3 Não-mudanças (squad pediria, mas não cabe no SDR Machine)

- **Mix multichannel (email + LinkedIn + phone):** SDR Machine é WhatsApp-only by design. Não cabe.
- **Pesquisa profunda 15-20 min/lead:** SDR Machine é automatizado tier 3. Pesquisa = enrichment automático. Match.
- **Voicemail / cold call:** fora de escopo.
- **Pricing claro na cadência fria:** voz SMB pede preço claro em proposta, não em outreach frio. Cadência atual está certa em não citar preço.

### A.4 Ordem de implementação revisada (com gaps do squad incorporados)

| PR | Escopo original | + ajuste squad |
|----|----|----|
| **PR1** | Validators hard (P0) | — |
| **PR2** | Taxonomia CTA/ângulo + apresentação + bump d2 redefinido | + adicionar CTAs squad: `validacao_aberta`, `piloto_curto`, `diagnostico_gratuito`. + regra "você"/"vocês" (Gap 8) |
| **PR3** | Estrutura mínima + humildade + tratamento formal | + frame PSPP opcional em angle_d9 (Gap 10) |
| **PR4** | Glossário + compliance + review negativa | + `cases_por_nicho.json` com 1 case por nicho (Gap 2) + checklist humano opcional primeiros 10 leads (Gap 9) |
| **PR5** | Telemetria + A/B | + endpoint `/api/outreach/stats` agregados (Gap 7) |
| **PR6 (novo)** | Outreach lifecycle | Status `nurture_60d`/`opt_out`/`cold_revisit` (Gap 6) |
| **PR7 (backlog)** | Multichannel | Variantes email + LinkedIn da mesma cadência (Gap 5) |

### A.5 Decisões adicionais

6. ~~Subir pra 6 toques~~ — **manter piso 5**. Sem `social_proof_d7`.
7. **Quantificação:** liberar só com dados reais (`reviews_count`, `rating`). Bloquear cálculos hipotéticos com regex `\bse\s+\d+\s*%`.
8. **Lifecycle (PR6)** — separado do PR3. Não bloqueia.
9. **Notificação não-bloqueante.** Coluna `needs_review` + badge no Lead App + endpoint `mark-reviewed`. Entra no PR4.

