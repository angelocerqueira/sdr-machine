import type { LeadAppItem, LeadAppDetail, LeadGroup, TabConfig, TabAction } from "./lead-app-types";

// ──────────────── Score helpers ────────────────
export function scoreClass(s: number): "high" | "mid" | "low" {
  return s >= 60 ? "high" : s >= 40 ? "mid" : "low";
}

// ──────────────── Status labels ────────────────
export const STATUS_LABELS: Record<string, string> = {
  scraped: "Scrapeado",
  enriched: "Analisado",
  disqualified: "Desqualificado",
  failed: "Falhou",
  lp_generated: "LP Gerada",
  outreach_ready: "Msg Pronta",
  outreach_sent: "Msg Enviada",
  responded: "Respondeu",
  closed: "Fechado",
};

// ──────────────── Leads list ────────────────
export const LEADS: LeadAppItem[] = [
  { id: 1253, name: "Marmoraria Tupi", niche: "Construção", city: "ABC", score: 89, status: "responded", phone: "+55 11 98777-2100" },
  { id: 1248, name: "Studio Dental Vila Nova", niche: "Odonto", city: "São Paulo", score: 84, status: "outreach_sent", phone: "+55 11 98421-9901" },
  { id: 1247, name: "Clínica BelaForma Estética Avançada", niche: "Estética", city: "São Paulo", score: 78, status: "enriched", phone: "+55 11 98421-7733" },
  { id: 1249, name: "Pilates Movimento", niche: "Fitness", city: "Campinas", score: 71, status: "lp_generated", phone: "+55 19 99771-0042" },
  { id: 1251, name: "Auto Center Lapa", niche: "Automotivo", city: "São Paulo", score: 68, status: "lp_generated", phone: "+55 11 98855-1234" },
  { id: 1260, name: "Padaria Santa Clara", niche: "Gastronomia", city: "São Paulo", score: 64, status: "outreach_ready", phone: "+55 11 98232-6677" },
  { id: 1250, name: "Café da Madrugada", niche: "Gastronomia", city: "São Paulo", score: 52, status: "enriched", phone: "+55 11 98232-6677" },
  { id: 1258, name: "Óptica Visão Clara", niche: "Varejo", city: "Guarulhos", score: 47, status: "scraped", phone: "—" },
  { id: 1252, name: "Pet Shop Rex&Cia", niche: "Pet", city: "Santos", score: 45, status: "scraped", phone: "—" },
  { id: 1254, name: "Yoga House", niche: "Bem-estar", city: "São Paulo", score: 33, status: "disqualified", phone: "+55 11 99000-4455" },
];

// ──────────────── Groups ────────────────
const GROUPS_DEF = [
  { key: "hot", title: "Prontas pra call", statuses: ["responded"] },
  { key: "outreach", title: "Em outreach", statuses: ["outreach_sent", "outreach_ready"] },
  { key: "ready", title: "LP gerada", statuses: ["lp_generated"] },
  { key: "enriched", title: "Analisadas", statuses: ["enriched"] },
  { key: "new", title: "Novas", statuses: ["scraped"] },
  { key: "out", title: "Desqualificadas", statuses: ["disqualified"] },
];

export function groupLeads(list: LeadAppItem[]): LeadGroup[] {
  return GROUPS_DEF.map((g) => ({
    ...g,
    items: list.filter((l) => g.statuses.includes(l.status)),
  })).filter((g) => g.items.length > 0);
}

// ──────────────── Lead detail ────────────────
export const LEAD_DETAIL: LeadAppDetail = {
  id: 1247,
  public_id: "lp-clinica-belaforma-7f3a",
  nome: "Clínica BelaForma Estética Avançada",
  telefone: "+55 11 98421-7733",
  website: "belaformaclinica.com.br",
  endereco: "Av. Brigadeiro Faria Lima, 2820, conj. 142",
  cidade: "São Paulo",
  nicho: "Clínica de Estética",
  categoria: "Estética e Beleza",
  rating: 4.8,
  reviews_count: 341,
  status: "enriched",
  opportunity_score: 78,
  scores: { acessibilidade: 62, lp: 84, automacao: 91, mapa: 70 },
  cnpj: "23.187.402/0001-66",
  razao_social: "BelaForma Serviços de Estética LTDA",
  porte: "ME",
  cnae: "9602-5/02 — Atividades de estética",
  email: "contato@belaformaclinica.com.br",
  socios: [{ nome: "Patrícia Mendes Vasconcelos" }, { nome: "Rafael Augusto Mendes" }],
  tech_stack: [
    { name: "WordPress 5.8", category: "CMS" },
    { name: "jQuery 1.12", category: "JS" },
    { name: "Bootstrap 3", category: "CSS" },
    { name: "Google Tag Manager", category: "Analytics" },
  ],
  gaps: [
    { dim: "lp", text: "Sem proposta de valor clara acima da dobra", weight: "high" },
    { dim: "lp", text: "CTA genérico ('Saiba mais') em vez de ação direta", weight: "high" },
    { dim: "automacao", text: "Sem WhatsApp Business integrado", weight: "high" },
    { dim: "automacao", text: "Formulário com 9 campos (recomendado: 3)", weight: "mid" },
    { dim: "acessibilidade", text: "PageSpeed mobile: 31/100", weight: "high" },
    { dim: "acessibilidade", text: "Sem responsividade em telas <768px", weight: "mid" },
    { dim: "mapa", text: "Stack defasado (jQuery 1.x, Bootstrap 3)", weight: "mid" },
    { dim: "mapa", text: "Sem Schema.org de LocalBusiness", weight: "low" },
  ],
  sources: [
    { provider: "google_places", status: "ok", time: "08:42", note: "341 reviews" },
    { provider: "website_crawler", status: "ok", time: "08:43", note: "12 páginas" },
    { provider: "schema_extractor", status: "skip", time: "08:43", note: "sem dados estruturados" },
    { provider: "tech_stack", status: "ok", time: "08:43", note: "4 tecnologias" },
    { provider: "cnpj_brasilapi", status: "ok", time: "08:44", note: "registro ativo" },
    { provider: "email_discoverer", status: "ok", time: "08:44", note: "1 email validado" },
    { provider: "apollo", status: "fail", time: "08:45", note: "rate limit" },
  ],
  messages: [
    {
      id: 1, type: "inicial", sent_at: null,
      text: `Oi Patrícia, tudo bem? Sou o Angelo.\n\nVi a BelaForma no Maps — 4.8 com 341 reviews é um patamar raro pra estética em SP.\n\nOlhei o site de vocês. A presença é boa, mas tô vendo 3 pontos onde tá perdendo paciente todo dia: PageSpeed mobile em 31, CTA genérico, e o WhatsApp não tá conectado direto.\n\nFiz um diagnóstico em vídeo de 4 minutos com a solução pra cada um. Posso te mandar?`,
    },
    {
      id: 2, type: "follow_up_1", sent_at: null,
      text: `Patrícia, deu uma olhada no diagnóstico?\n\nO ponto do WhatsApp sozinho — pelo volume que vocês têm — deve estar custando uns 8-12 agendamentos por semana.`,
    },
    {
      id: 3, type: "follow_up_2", sent_at: null,
      text: `Última: deixei tudo numa página personalizada pra BelaForma —\nbelaforma.sdr.machine/diagnostico\n\nSe não fizer sentido, sem stress.`,
    },
  ],
  recommendation: {
    level: "automacao_basica",
    label: "Automação Básica",
    summary: "Stack defasado + sem WhatsApp integrado = volume alto travado em gargalo operacional. Aplicar pacote que resolve funil + integração em 7 dias.",
    price_low: 2800,
    price_high: 4200,
    delivery_weeks: 1,
  },
  score_previous: 71,
  checklist: [
    { id: "wa", dim: "automacao", dim_label: "Automação", title: "WhatsApp Business não está integrado ao site", weight: "high", evidence: "Formulário envia por email padrão. Paciente aguarda resposta por horas — em estética, 60% fecham com quem responde primeiro.", impact: "8–12 agend/sem", impact_detail: "perdidos" },
    { id: "cta", dim: "lp", dim_label: "Landing", title: "CTA genérico acima da dobra", weight: "high", evidence: 'Botão atual: "Saiba mais". Em estética, CTAs de ação direta ("Agendar avaliação gratuita") convertem 2.1× mais.', impact: "+2.1×", impact_detail: "conversão" },
    { id: "speed", dim: "acessibilidade", dim_label: "Acessib.", title: "PageSpeed mobile em 31/100", weight: "high", evidence: "Hero em PNG de 2.4MB, jQuery 1.12 bloqueante, sem lazy-load. Cada segundo adicional = −7% nas conversões.", impact: "−43%", impact_detail: "conversão mobile" },
    { id: "form", dim: "automacao", dim_label: "Automação", title: "Formulário com 9 campos", weight: "mid", evidence: "Nome, sobrenome, email, telefone, CPF, procedimento, dia preferido, horário, mensagem. Recomendado pra estética: 3 campos.", impact: "+70%", impact_detail: "submissões estimadas" },
    { id: "responsive", dim: "acessibilidade", dim_label: "Acessib.", title: "Sem responsividade abaixo de 768px", weight: "mid", evidence: "Grid quebra em telas <768px; 74% do tráfego é mobile segundo GTM detectado.", impact: "74% tráfego", impact_detail: "afetado" },
    { id: "stack", dim: "mapa", dim_label: "Stack", title: "Stack defasado (jQuery 1.12, Bootstrap 3, WP 5.8)", weight: "mid", evidence: "Vulnerabilidades conhecidas no WP 5.8 (2021). jQuery 1.x sem suporte desde 2016.", impact: "CVE alto", impact_detail: "risco" },
    { id: "schema", dim: "mapa", dim_label: "Stack", title: "Sem Schema.org LocalBusiness", weight: "low", evidence: "Nenhum dado estruturado detectado. Afeta rich results no Google e rankeamento local.", impact: "SEO local", impact_detail: "afetado" },
    { id: "reviews", dim: "lp", dim_label: "Landing", title: "Reviews não aparecem no site", weight: "low", evidence: "4.8 estrelas · 341 reviews no Maps, zero exposição no site. Social proof grátis sendo deixada na mesa.", impact: "Confiança", impact_detail: "sub-utilizada" },
  ],
  checklist_groups: [
    { key: "core", title: "Core — incluso no pacote recomendado", hint: "Entrega em 7 dias", ids: ["wa", "cta", "speed", "form"] },
    { key: "upsell", title: "Upsell — Mapa de Automações (+ R$ 1.8k)", hint: "Entrega em +14 dias", ids: ["stack", "responsive"] },
    { key: "opt", title: "Opcional — melhorias incrementais", hint: "Cobrança à parte", ids: ["schema", "reviews"] },
  ],
  lp_metrics: {
    visits: 47,
    clicks_wa: 11,
    ctr: 23.4,
    period: "7 dias",
    delta_ctr: 23.4,
    active_version: 3,
    first_visit: "há 6 dias",
  },
  lp_versions: [
    { v: 3, created: "18/04 · 14:22", note: "CTA reescrito", active: true },
    { v: 2, created: "18/04 · 11:08", note: "Hero com reviews" },
    { v: 1, created: "16/04 · 09:41", note: "Geração inicial" },
  ],
};

// ──────────────── Tabs ────────────────
export const TABS: TabConfig[] = [
  { key: "diag", label: "Diagnóstico", count: LEAD_DETAIL.checklist.length },
  { key: "lp", label: "Landing Page", count: LEAD_DETAIL.lp_versions.length, suffix: "v" },
  { key: "msgs", label: "Mensagens", count: LEAD_DETAIL.messages.length },
  { key: "info", label: "Informações" },
];

export const TAB_ACTIONS: Record<string, TabAction> = {
  diag: { primary: "Re-enriquecer", secondary: "Exportar diagnóstico" },
  lp: { primary: "Regenerar LP", secondary: "Copiar link público" },
  msgs: { primary: "Gerar variação", secondary: "Exportar conversa" },
  info: { primary: null, secondary: "Editar" },
};

// ──────────────── Dimension labels ────────────────
export const DIM_LABEL: Record<string, string> = {
  lp: "Landing",
  automacao: "Automação",
  acessibilidade: "Acessib.",
  mapa: "Mapa",
};
