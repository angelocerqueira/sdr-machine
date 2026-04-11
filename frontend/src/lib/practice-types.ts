export interface ChatMessage {
  role: "bot" | "user";
  text: string;
}

export interface AgentChatData {
  businessName: string;
  niche: string;
  messages: ChatMessage[];
  quickActions: string[];
  responses: Record<string, ChatMessage[]>;
}

export interface GapBlock {
  severity: "critico" | "gap" | "fraco";
  problem: string;
  detail: string;
  solution: string;
  solutionDetail: string;
}

export interface BlueprintData {
  radarScores: {
    seo: number;
    performance: number;
    mobile: number;
    conteudo: number;
    seguranca: number;
    presenca: number;
  };
  maturityScore: number;
  gaps: GapBlock[];
}

export interface AgentPerformance {
  name: string;
  successRate: number;
  calls: number;
  cost: string;
}

export interface ActivityEvent {
  type: "lead" | "lp" | "resposta" | "outreach";
  title: string;
  detail: string;
  time: string;
}

export interface Integration {
  name: string;
  status: "connected" | "pending";
}

export interface MissionControlData {
  pipeline: {
    leadsCaptados: number;
    outreachEnviado: number;
    respostas: number;
    reunioes: number;
  };
  aiMetrics: {
    custoPorLead: string;
    roiIA: string;
    leadTimeMedio: string;
    taxaSucessoAgentes: string;
  };
  tokensSummary: {
    tokensConsumed: string;
    totalCost: string;
    revenueAttributed: string;
  };
  agents: AgentPerformance[];
  feed: ActivityEvent[];
  integrations: Integration[];
}
