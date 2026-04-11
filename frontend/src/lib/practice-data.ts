import type { AgentChatData, BlueprintData, MissionControlData } from "./practice-types";

export const LP_CHAT_DATA: AgentChatData = {
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
      { role: "bot", text: "Temos horarios disponiveis na proxima terca (14h ou 16h) e quinta (10h). A consulta inicial e de 45 minutos. Qual horario funciona melhor?" },
    ],
    "Quais documentos preciso?": [
      { role: "bot", text: "Para divorcio consensual: RG, CPF, certidao de casamento atualizada, pacto antenupcial (se houver) e acordo sobre partilha de bens. Nosso escritorio auxilia na organizacao de toda a documentacao." },
    ],
    "Valores e honorarios": [
      { role: "bot", text: "Os honorarios variam conforme a complexidade. A consulta inicial e R$350 e inclui analise completa do caso com parecer do Dr. Silva. Posso agendar?" },
    ],
    "Areas de atuacao": [
      { role: "bot", text: "O escritorio atua em Direito de Familia, Direito Civil, Direito do Consumidor e Direito Imobiliario. Para cada area temos especialistas dedicados." },
    ],
  },
};

export const LP_BLUEPRINT_DATA: BlueprintData = {
  radarScores: { seo: 25, performance: 35, mobile: 70, conteudo: 55, seguranca: 15, presenca: 20 },
  maturityScore: 32,
  gaps: [
    { severity: "critico", problem: "Site sem SSL", detail: "Google marca 'Nao seguro'", solution: "LP profissional", solutionDetail: "SSL + mobile + SEO" },
    { severity: "critico", problem: "Sem atendimento digital", detail: "Leads perdidos fora do horario", solution: "Chat agentico 24/7", solutionDetail: "Atende, qualifica, agenda" },
    { severity: "fraco", problem: "Sem estrategia de outreach", detail: "Depende de indicacao", solution: "Outreach automatizado", solutionDetail: "WhatsApp + follow-up" },
    { severity: "fraco", problem: "Site lento e nao responsivo", detail: "PageSpeed 23/100", solution: "LP otimizada", solutionDetail: "95+ PageSpeed, mobile-first" },
  ],
};

export const LP_MISSION_DATA: MissionControlData = {
  pipeline: { leadsCaptados: 1247, outreachEnviado: 342, respostas: 67, reunioes: 23 },
  aiMetrics: { custoPorLead: "R$0.42", roiIA: "47x", leadTimeMedio: "3.2min", taxaSucessoAgentes: "94.2%" },
  tokensSummary: { tokensConsumed: "2.4M", totalCost: "R$523", revenueAttributed: "R$24.700" },
  agents: [
    { name: "Enrichment Agent", successRate: 96.1, calls: 840, cost: "R$187" },
    { name: "LP Generator", successRate: 92.8, calls: 412, cost: "R$264" },
    { name: "Outreach Agent", successRate: 88.5, calls: 342, cost: "R$72" },
  ],
  feed: [
    { type: "lead", title: "Lead qualificado", detail: "Clinica Dr. Santos — Score: 91", time: "2min" },
    { type: "lp", title: "LP gerada", detail: "Padaria Dona Maria — 1.2k tokens", time: "8min" },
    { type: "resposta", title: "Resposta recebida", detail: "Auto Mecanica Silva — 'Vamos conversar'", time: "15min" },
    { type: "outreach", title: "Outreach enviado", detail: "12 leads batch — follow-up 48h", time: "32min" },
  ],
  integrations: [
    { name: "WhatsApp", status: "connected" },
    { name: "Analytics", status: "connected" },
    { name: "Claude IA", status: "connected" },
    { name: "CRM", status: "pending" },
  ],
};
