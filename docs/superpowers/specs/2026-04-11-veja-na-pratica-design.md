# Bloco "Veja na Pratica" — Design Spec

**Data:** 2026-04-11
**Status:** Aprovado
**Tipo:** Novas secoes LP + componentes reutilizaveis no app

---

## Objetivo

Adicionar um bloco interativo "Veja na Pratica" na LP de marketing e reutilizar os mesmos componentes no lead detail do app. Tres tabs: Chat Agentico, Blueprint Digital, Mission Control. Na LP os dados sao mockados/aspiracionais; no app sao alimentados por dados reais do enrichment.

## Posicionamento na LP

Flow atualizado: Hero -> Before/After -> Pipeline -> **Veja na Pratica** -> Features Grid -> CTA -> Footer

O bloco fica entre o Pipeline e o Features Grid.

## Arquitetura

### Componentes compartilhados

Cada tab e um componente React independente que aceita uma prop `data` (mockada ou real). A LP passa dados hardcoded; o app passa dados do enrichment.

```
frontend/src/components/marketing/
  practice-block.tsx          <- Container com tabs (Atendimento IA | Blueprint | Mission Control)

frontend/src/components/shared/
  agent-chat.tsx              <- Chat agentico simulado (typewriter + quick actions)
  digital-blueprint.tsx       <- Radar chart + mapa de automacao
  mission-control.tsx         <- Dashboard com KPIs, feed, funil, metricas IA
```

### Dados

```typescript
// Props compartilhadas entre LP (mock) e App (real)
interface AgentChatData {
  businessName: string;
  niche: string;
  messages: ChatMessage[];       // conversa pre-programada
  quickActions: string[];        // opcoes clicaveis
  responses: Record<string, ChatMessage[]>;  // respostas por quick action
}

interface BlueprintData {
  radarScores: {                 // 0-100 por eixo
    seo: number;
    performance: number;
    mobile: number;
    conteudo: number;
    seguranca: number;
    presenca: number;
  };
  maturityScore: number;         // 0-100
  gaps: GapBlock[];              // blocos gap -> solucao
}

interface GapBlock {
  severity: "critico" | "gap" | "fraco";
  problem: string;
  detail: string;
  solution: string;
  solutionDetail: string;
}

interface MissionControlData {
  pipeline: {
    leadsCaptados: number;
    outreachEnviado: number;
    respostas: number;
    reunioes: number;
  };
  aiMetrics: {
    custoPorLead: string;        // "R$0.42"
    roiIA: string;               // "47x"
    leadTimeMedio: string;       // "3.2min"
    taxaSucessoAgentes: string;  // "94.2%"
  };
  agents: AgentPerformance[];
  feed: ActivityEvent[];
  integrations: Integration[];
}
```

## Tab 1: Chat Agentico

### Conceito

Simula o **produto final que o lead vai ter** — um cliente do lead sendo atendido por IA. Se o lead e advogado, mostra um paciente/cliente tirando duvidas juridicas. O assistente responde em nome do escritorio/empresa do lead.

### Tom

Consultor especialista. Linguagem de diagnostico profissional, nao chatbot generico. Termos: "diagnostico", "vulnerabilidades", "recomendacao", "laudo", "plano de acao".

### Visual

- Container centralizado, max-width 60%
- Header: avatar com gradient animado + pulse ring, nome do escritorio/empresa, indicador "Online agora"
- Mensagens: typewriter character-by-character (bot), aparicao instantanea (user)
- Indicador de processamento: waveform bars estilo ElevenLabs + label "processando"
- Metadata sutil no rodape de cada resposta: tempo de resposta, fonte
- Quick actions: pills clicaveis no rodape do chat, disparam respostas pre-programadas
- Badge contextual: "Simulacao baseada no perfil: [nicho]"

### Comportamento

1. Ao ativar a tab, mensagens aparecem com typewriter (delay 30ms/char)
2. Entre mensagens do bot, aparece indicador de processamento por 1-2s
3. Apos conversa inicial, quick actions ficam visiveis
4. Clicar em quick action: mensagem do usuario aparece, indicador de processamento, resposta do bot com typewriter
5. Cada quick action so pode ser clicada uma vez (desabilita apos uso)

### Dados LP (mockados)

```typescript
const LP_CHAT_DATA: AgentChatData = {
  businessName: "Escritorio Silva & Associados",
  niche: "Escritorio de Advocacia",
  messages: [
    { role: "bot", text: "Boa tarde. Sou o assistente digital do escritorio Silva & Associados. Em que posso ajudar?" },
    { role: "user", text: "Preciso de orientacao sobre um processo de divorcio. Quanto tempo leva em media?" },
    { role: "bot", text: "O prazo de um divorcio consensual costuma variar entre 30 a 90 dias. Se for litigioso, pode levar de 1 a 3 anos dependendo da complexidade.\n\nO Dr. Silva atende ambas as modalidades. Posso verificar a agenda e reservar um horario para uma consulta inicial?" },
  ],
  quickActions: ["Agendar consulta", "Quais documentos preciso?", "Valores e honorarios", "Areas de atuacao"],
  responses: {
    "Agendar consulta": [
      { role: "bot", text: "Temos horarios disponiveis na proxima terca (14h ou 16h) e quinta (10h). A consulta inicial e de 45 minutos. Qual horario funciona melhor?" }
    ],
    "Quais documentos preciso?": [
      { role: "bot", text: "Para divorcio consensual: RG, CPF, certidao de casamento atualizada, pacto antenupcial (se houver) e acordo sobre partilha de bens. Nosso escritorio auxilia na organizacao de toda a documentacao." }
    ],
    "Valores e honorarios": [
      { role: "bot", text: "Os honorarios variam conforme a complexidade. A consulta inicial e R$350 e inclui analise completa do caso com parecer do Dr. Silva. Posso agendar?" }
    ],
    "Areas de atuacao": [
      { role: "bot", text: "O escritorio atua em Direito de Familia, Direito Civil, Direito do Consumidor e Direito Imobiliario. Para cada area temos especialistas dedicados." }
    ],
  },
};
```

### Dados App (reais)

No lead detail, o componente recebe `businessName` do lead.nome, `niche` do lead.nicho, e mensagens/quick actions adaptados ao contexto do enrichment (opportunity_reasons, site_analysis).

## Tab 2: Blueprint Digital

### Conceito

Visao dupla: radar chart mostrando maturidade digital (quantitativo) + mapa de automacao mostrando gaps e solucoes (qualitativo).

### Layout

Dois paineis side-by-side dentro do container 60%:
- Esquerda (40%): Radar chart
- Direita (60%): Mapa de automacao (blocos gap -> solucao)

### Radar Chart (esquerda)

6 eixos: SEO, Performance, Mobile, Conteudo, Seguranca, Presenca.

- Shape tracejado verde: perfil ideal (outer ring)
- Shape solido vermelho: perfil atual (inner, irregular)
- Areas de gap destacadas com fill vermelho semi-transparente
- Dots coloridos nos vertices: verde (>=70), amarelo (40-69), vermelho (<40)
- Score total "Maturidade Digital" embaixo (ex: 32/100)

Implementacao: SVG com polygons calculados. Animacao: shape atual cresce de 0 ate o valor real no scroll (Framer Motion useInView).

### Mapa de Automacao (direita)

Blocos verticais conectados. Cada bloco e um par:

```
[Severidade + Problema] ---> [Solucao IA]
```

Severidades com cores:
- Critico: vermelho (#f87171)
- Gap: vermelho claro
- Fraco: amarelo (#fbbf24)

Solucoes sempre em verde (#34d399).

Blocos entram com stagger animation (fade up) no scroll.

### Dados LP (mockados)

```typescript
const LP_BLUEPRINT_DATA: BlueprintData = {
  radarScores: { seo: 25, performance: 35, mobile: 70, conteudo: 55, seguranca: 15, presenca: 20 },
  maturityScore: 32,
  gaps: [
    { severity: "critico", problem: "Site sem SSL", detail: "Google marca 'Nao seguro'", solution: "LP profissional", solutionDetail: "SSL + mobile + SEO" },
    { severity: "critico", problem: "Sem atendimento digital", detail: "Leads perdidos fora do horario", solution: "Chat agentico 24/7", solutionDetail: "Atende, qualifica, agenda" },
    { severity: "fraco", problem: "Sem estrategia de outreach", detail: "Depende de indicacao", solution: "Outreach automatizado", solutionDetail: "WhatsApp + follow-up" },
    { severity: "fraco", problem: "Site lento e nao responsivo", detail: "PageSpeed 23/100", solution: "LP otimizada", solutionDetail: "95+ PageSpeed, mobile-first" },
  ],
};
```

### Dados App (reais)

Radar scores derivados de `site_analysis` (has_ssl, is_responsive, pagespeed_score, etc.). Gaps derivados de `opportunity_reasons`. Mapa de automacao gerado a partir dos gaps reais com solucoes correspondentes do pipeline.

## Tab 3: Mission Control

### Conceito

Dashboard futurista mostrando inteligencia de dados + controle operacional. Comunica: "e assim que voce vai acompanhar tudo funcionando".

### Layout

Dentro do container 60%:

1. **Status bar** — "Sistema Operando" com uptime e ultima sync
2. **KPIs Pipeline** (4 cards, row 1) — Leads captados, Outreach enviado, Respostas, Reunioes. Cada um com variacao percentual.
3. **KPIs IA** (4 cards, row 2, cor azul) — Custo por lead, ROI da IA, Lead time medio, Taxa sucesso agentes
4. **3 colunas**:
   - Feed de Atividade (esquerda): eventos em tempo real com cores por tipo
   - Funil do Pipeline (centro): barras horizontais + integracoes ativas
   - Performance dos Agentes (direita): breakdown por agente com barra de progresso + resumo de tokens/custo/receita

### Metricas de IA (detalhamento)

| Metrica | Valor mock | Calculo |
|---------|-----------|---------|
| Custo por lead | R$0.42 | custo total IA / leads processados |
| ROI da IA | 47x | receita atribuida / custo total IA |
| Lead time medio | 3.2min | tempo medio scrape ate outreach pronto |
| Taxa sucesso agentes | 94.2% | interacoes sem erro / total interacoes |

### Performance por Agente

| Agente | Sucesso mock | Calls | Custo |
|--------|-------------|-------|-------|
| Enrichment Agent | 96.1% | 840 | R$187 |
| LP Generator | 92.8% | 412 | R$264 |
| Outreach Agent | 88.5% | 342 | R$72 |

### Resumo financeiro

- Tokens consumidos: 2.4M
- Custo total IA: R$523
- Receita atribuida: R$24.700

### Animacoes

- KPIs: counter animation (0 -> valor) com useInView trigger
- Feed: entradas aparecem com stagger (simulando tempo real)
- Barras do funil: crescem da esquerda no scroll
- Barras de progresso dos agentes: preenchem ao entrar em view

### Dados LP (mockados)

Todos os numeros sao aspiracionais (levemente inflados). Badge no rodape: "Dados ilustrativos — numeros reais variam por operacao".

### Dados App (futuro — spec separada)

Integracao no lead detail sera definida em spec propria. Os componentes `shared/` ja aceitam dados via props, entao a integracao sera apenas passar os dados reais do enrichment.

## Diretrizes Visuais

- Container centralizado max-width 60% em todas as tabs
- Sem emojis em nenhum lugar
- Dark theme consistente com LP existente (#0a0a0c bg, #34d399 accent)
- Cor azul (#60a5fa) para metricas de IA (diferencia de metricas de pipeline em verde)
- Ambient glow sutil no background do bloco
- Tabs sem emojis, texto limpo
- Border-radius arredondado (12-16px nos containers principais)
- Tipografia mono para numeros e labels (font-[family-name:var(--font-mono)])

## Dependencias

Nenhuma nova. Usa Framer Motion (ja instalado) para animacoes. SVG nativo para radar chart.

## Componentes Novos

```
frontend/src/components/
  marketing/
    practice-block.tsx          <- Wrapper com tabs + section header (LP-specific)
  shared/
    agent-chat.tsx              <- Chat simulado (typewriter + quick actions)
    digital-blueprint.tsx       <- Radar + mapa de automacao
    mission-control.tsx         <- Dashboard completo
```

Nota: `shared/` e um novo diretorio. Componentes aqui sao reutilizados entre LP e app.

## Fora de Escopo

- Chat com IA real (tudo e mockado/pre-programado)
- Dados reais no Mission Control da LP (tudo hardcoded)
- Avatar 3D real (v1 usa gradient animado + pulse, placeholder pra futuro Spline/Three.js)
- Audio/voz no chat (futuro com ElevenLabs)
- Integracoes reais (WhatsApp, Analytics, CRM — apenas visual)
- Adaptacao do lead detail no app (sera feita em spec separada)
