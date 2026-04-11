# LP Preview Intelligence — Design Spec

**Data:** 2026-04-11
**Status:** Aprovado
**Tipo:** Enriquecimento da pagina publica /lp/[id] com dados reais do lead

---

## Objetivo

Transformar a pagina publica `/lp/[id]` (que hoje mostra apenas o HTML gerado) numa experiencia de venda completa. O lead que recebe a LP passa a ver: um chat flutuante simulando atendimento IA no negocio dele, um blueprint dos gaps digitais identificados, e um mission control mostrando como o OS operaria na empresa dele. Todos alimentados por dados reais do enrichment.

## Premissa

A LP so e gerada apos o enrichment (stage 3 do pipeline). Todo lead em `/lp/[id]` ja tem dados completos: opportunity_score, opportunity_reasons, site_analysis, tech_stack, nicho, etc.

## Arquitetura

### Componentes reutilizados

Os componentes `shared/` criados no PR #39 sao reutilizados aqui com dados reais:
- `components/shared/agent-chat.tsx` — aceita `AgentChatData`
- `components/shared/digital-blueprint.tsx` — aceita `BlueprintData`
- `components/shared/mission-control.tsx` — aceita `MissionControlData`

### Novos arquivos

```
frontend/src/
  lib/
    lead-to-practice.ts       <- Funcoes que convertem Lead -> AgentChatData / BlueprintData / MissionControlData
    chat-templates.ts         <- Templates de chat por nicho (top 6) + fallback generico
  components/
    shared/
      chat-widget.tsx         <- Widget flutuante (bolha + painel expansivel) wrapping AgentChat
```

### Pagina modificada

```
frontend/src/app/lp/[id]/page.tsx  <- Busca lead completo, renderiza LP + widget + secoes
```

## Layout da Pagina

```
+--------------------------------------------------+
|  [Header: voltar | nome lead | desktop/mobile]   |
+--------------------------------------------------+
|                                                  |
|            iframe da LP gerada                   |
|                                                  |
+--------------------------------------------------+
|                                                  |
|     Secao: Blueprint Digital (dados reais)       |
|     [Radar Chart]  [Gap Map com gaps do lead]    |
|                                                  |
+--------------------------------------------------+
|                                                  |
|     Secao: Mission Control (dados reais)         |
|     [KPIs simulados baseados no enrichment]      |
|                                                  |
+--------------------------------------------------+

                              +------------------+
                              | Chat Widget      |
                              | (flutuante,      |
                              |  canto inf dir)  |
                              +------------------+
```

## Chat Widget Flutuante

### Aparencia

- Bolha circular no canto inferior direito (position fixed, z-index alto)
- Avatar com gradient animado + pulse ring (mesmo visual do chat na LP marketing)
- Badge "1" simulando notificacao
- Ao clicar: expande para painel 380px wide x 500px tall com o AgentChat dentro
- Botao X pra fechar (volta pra bolha)

### Entrada

- Delay de 4 segundos apos page load
- Slide-up animation (translateY 100% -> 0) com Framer Motion
- Apos abrir, primeiro ciclo de typewriter comeca automaticamente

### Dados

O chat usa templates contextuais por nicho do lead.

## Chat Templates

### Estrutura

```typescript
interface NicheTemplate {
  niche: string;           // match contra lead.nicho (case-insensitive, includes)
  messages: ChatMessage[];
  quickActions: string[];
  responses: Record<string, ChatMessage[]>;
}
```

### Templates por nicho (top 6)

1. **Advocacia** — cliente perguntando sobre processo, agendamento, documentos
2. **Odontologia** — paciente perguntando sobre tratamento, valores, horarios
3. **Restaurante** — cliente perguntando sobre cardapio, reserva, delivery
4. **Academia** — interessado perguntando sobre planos, horarios, avaliacao
5. **Clinica medica** — paciente perguntando sobre consulta, exames, convenios
6. **Contabilidade** — empresario perguntando sobre abertura de empresa, impostos

### Fallback generico

Para nichos nao mapeados, template generico que interpola dados do lead:
- `{businessName}` -> lead.nome
- `{niche}` -> lead.nicho
- Mensagens focam em atendimento, agendamento, servicos — universais

### Selecao de template

```typescript
function selectChatTemplate(lead: Lead): AgentChatData {
  // 1. Tentar match por nicho (case-insensitive includes)
  const template = NICHE_TEMPLATES.find(t =>
    lead.nicho?.toLowerCase().includes(t.niche.toLowerCase())
  );
  // 2. Fallback generico com interpolacao
  // 3. Substituir {businessName} por lead.nome em todas as mensagens
  return buildChatData(template || GENERIC_TEMPLATE, lead);
}
```

## Lead -> BlueprintData

Converter dados reais do enrichment em scores do radar e gaps.

### Radar Scores (0-100)

| Eixo | Fonte no Lead | Calculo |
|------|---------------|---------|
| SEO | site_analysis.has_meta_description, site_analysis.has_structured_data | true=70, false=20 |
| Performance | site_analysis.pagespeed_score | direto (0-100) ou 30 se ausente |
| Mobile | site_analysis.is_responsive | true=80, false=15 |
| Conteudo | site_analysis.has_structured_data, lead.top_reviews.length | structured=+40, reviews>3=+30 |
| Seguranca | site_analysis.has_ssl | true=80, false=10 |
| Presenca | lead.website, lead.social_profiles | website=+40, socials>0=+30 |

### Maturity Score

`100 - opportunity_score` (opportunity_score alto = site ruim = maturidade baixa). Simples e consistente com o scoring existente.

### Gaps

Derivar de `opportunity_reasons` (array de strings). Cada reason vira um `GapBlock`:
- Mapear reasons conhecidas pra severity + solution
- Ex: "Sem certificado SSL" -> severity: "critico", solution: "LP profissional com SSL"
- Ex: "Site nao responsivo" -> severity: "fraco", solution: "LP otimizada mobile-first"

## Lead -> MissionControlData

Dados simulados mas contextualizados pro lead.

### Pipeline KPIs

Numeros aspiracionais mas proporcionais ao contexto:
- Leads captados: baseado no nicho (ex: "247 negocios de {nicho} na regiao")
- Outreach: ~30% dos captados
- Respostas: ~20% do outreach
- Reunioes: ~30% das respostas

### AI Metrics

Hardcoded aspiracional (mesmos valores da LP marketing — R$0.42/lead, 47x ROI, etc.)

### Agent Performance

Hardcoded (mesmos valores da LP marketing).

### Feed

Contextualizado com nome do lead:
- "Lead qualificado — {lead.nome} — Score: {lead.opportunity_score}"
- "LP gerada — {lead.nome}"
- "Outreach enviado — {lead.nome}"

### Integracoes

Hardcoded (WhatsApp, Analytics, Claude IA conectados, CRM pendente).

## Modificacao da Pagina /lp/[id]

### Estado atual

```
page.tsx -> busca lead via getLeadByPublicId -> passa nome pro LpPreview
LpPreview -> header + iframe
```

### Estado novo

```
page.tsx -> busca lead COMPLETO via getLeadByPublicId -> passa lead inteiro
  -> LpPreview (header + iframe) -- mantido
  -> Secao Blueprint (dados reais do lead)
  -> Secao Mission Control (dados contextualizados)
  -> ChatWidget flutuante (template por nicho)
```

A pagina deixa de ser apenas um wrapper de iframe e vira uma experiencia de venda. O header e toggle desktop/mobile continuam.

### Layout responsivo

- Desktop: iframe full-width, secoes abaixo, widget no canto
- Mobile: iframe adaptado, secoes empilhadas, widget menor (320px wide)

## Diretrizes Visuais

- Mesmas do bloco "Veja na Pratica" da LP marketing (dark theme, accent emerald, sem emojis)
- Secoes Blueprint e Mission Control: com headers proprios ("Diagnostico Digital", "Mission Control")
- Widget: glassmorphism, accent border, pulse animation na bolha
- Secoes usam max-w-5xl (nao 60% — aqui e pagina inteira, nao bloco centralizado)

## Dependencias

Nenhuma nova. Reutiliza Framer Motion e componentes shared existentes.

## Fora de Escopo

- Chat com IA real (tudo mockado/pre-programado)
- Dados reais de pipeline no Mission Control (aspiracional)
- Personalizacao do HTML da LP gerada
- Tracking/analytics de interacao do lead
- Notificacao ao SDR quando lead interage
