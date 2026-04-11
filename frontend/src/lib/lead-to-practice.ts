import type { Lead } from "./types";
import type {
  BlueprintData,
  GapBlock,
  MissionControlData,
} from "./practice-types";

function mapReasonToGap(reason: string): GapBlock {
  const r = reason.toLowerCase();

  if (r.includes("ssl")) {
    return {
      severity: "critico",
      problem: "Sem certificado SSL",
      detail: "O site nao possui HTTPS, expondo dados dos visitantes.",
      solution: "LP profissional com SSL",
      solutionDetail: "Pagina entregue com HTTPS e criptografia ativa.",
    };
  }

  if (r.includes("responsiv")) {
    return {
      severity: "fraco",
      problem: "Site nao responsivo",
      detail: "Layout quebrado em dispositivos moveis.",
      solution: "LP otimizada mobile-first",
      solutionDetail: "Design responsivo testado em todos os tamanhos de tela.",
    };
  }

  if (r.includes("pagespeed") || r.includes("lento")) {
    return {
      severity: "fraco",
      problem: "Performance baixa",
      detail: "Carregamento lento prejudica conversoes e SEO.",
      solution: "LP com 95+ PageSpeed",
      solutionDetail: "Pagina leve e otimizada para carregamento rapido.",
    };
  }

  if (r.includes("dados estruturados") || r.includes("structured")) {
    return {
      severity: "fraco",
      problem: "Sem dados estruturados",
      detail: "Google nao consegue interpretar o conteudo corretamente.",
      solution: "SEO com schema markup",
      solutionDetail: "Marcacao estruturada para melhor indexacao nos buscadores.",
    };
  }

  if (r.includes("redes sociais") || r.includes("social")) {
    return {
      severity: "gap",
      problem: "Sem presenca em redes",
      detail: "Ausencia em redes sociais reduz visibilidade da marca.",
      solution: "Estrategia de presenca digital",
      solutionDetail: "Perfis otimizados e integrados a pagina de captura.",
    };
  }

  if (r.includes("tech") || r.includes("defasado")) {
    return {
      severity: "fraco",
      problem: "Tech stack defasado",
      detail: "Tecnologia antiga limita performance e seguranca.",
      solution: "Stack moderno e otimizado",
      solutionDetail: "Plataforma atual com melhor performance e suporte.",
    };
  }

  if (r.includes("email") || r.includes("generico")) {
    return {
      severity: "gap",
      problem: "Email generico",
      detail: "Email em dominio generico passa pouca credibilidade.",
      solution: "Email profissional configurado",
      solutionDetail: "Email no dominio proprio para transmitir confianca.",
    };
  }

  return {
    severity: "gap",
    problem: reason,
    detail: "Oportunidade de melhoria identificada na analise do negocio.",
    solution: "Solucao personalizada",
    solutionDetail: "Plano de acao sob medida para este ponto especifico.",
  };
}

export function leadToBlueprintData(lead: Lead): BlueprintData {
  const sa = lead.site_analysis || {};

  const radarScores = {
    seo: (sa.has_meta_description as boolean)
      ? 65
      : (sa.has_structured_data as boolean)
      ? 45
      : 20,
    performance:
      typeof sa.pagespeed_score === "number" ? (sa.pagespeed_score as number) : 30,
    mobile: (sa.is_responsive as boolean) ? 80 : 15,
    conteudo:
      ((sa.has_structured_data as boolean) ? 40 : 10) +
      (lead.top_reviews.length > 3 ? 30 : 10),
    seguranca: (sa.has_ssl as boolean) ? 80 : 10,
    presenca:
      (lead.website ? 40 : 5) +
      (Object.keys(lead.social_profiles || {}).length > 0 ? 30 : 5),
  };

  const maturityScore = Math.max(0, Math.min(100, 100 - (lead.opportunity_score || 50)));

  const gaps: GapBlock[] = (lead.opportunity_reasons || [])
    .slice(0, 6)
    .map(mapReasonToGap);

  return { radarScores, maturityScore, gaps };
}

export function leadToMissionControlData(lead: Lead): MissionControlData {
  return {
    pipeline: { leadsCaptados: 247, outreachEnviado: 74, respostas: 15, reunioes: 5 },
    aiMetrics: {
      custoPorLead: "R$0.42",
      roiIA: "47x",
      leadTimeMedio: "3.2min",
      taxaSucessoAgentes: "94.2%",
    },
    tokensSummary: {
      tokensConsumed: "2.4M",
      totalCost: "R$523",
      revenueAttributed: "R$24.700",
    },
    agents: [
      { name: "Enrichment Agent", successRate: 96.1, calls: 840, cost: "R$187" },
      { name: "LP Generator", successRate: 92.8, calls: 412, cost: "R$264" },
      { name: "Outreach Agent", successRate: 88.5, calls: 342, cost: "R$72" },
    ],
    feed: [
      {
        type: "lead",
        title: "Lead qualificado",
        detail: `${lead.nome} — Score: ${lead.opportunity_score ?? "N/A"}`,
        time: "2min",
      },
      {
        type: "lp",
        title: "LP gerada",
        detail: `${lead.nome} — Landing page personalizada`,
        time: "8min",
      },
      {
        type: "outreach",
        title: "Outreach enviado",
        detail: `${lead.nome} — 3 mensagens WhatsApp`,
        time: "15min",
      },
      {
        type: "resposta",
        title: "Novo lead",
        detail: `${lead.nicho || "negocios"} na regiao — Score: 78`,
        time: "32min",
      },
    ],
    integrations: [
      { name: "WhatsApp", status: "connected" },
      { name: "Analytics", status: "connected" },
      { name: "Claude IA", status: "connected" },
      { name: "CRM", status: "pending" },
    ],
  };
}
