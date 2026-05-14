export type LeadProfile =
  | "hot_no_site"
  | "hot_bad_site"
  | "warm"
  | "cold"
  | "disqualified";

export type NichoCanonico =
  | "dentista" | "estetica" | "salao_barbearia" | "restaurante"
  | "petshop_vet" | "academia" | "contabilidade" | "imobiliaria"
  | "loja_roupas" | "auto_escola" | "advocacia" | "industria"
  | "clinica_medica" | "escola_curso" | "outros";

export type NichoSource =
  | "apify_category" | "fuzzy_match" | "llm_inferred" | "manual" | "failed";

export type PacoteSugerido = "essencial" | "profissional" | "premium" | "skip";

export type Prioridade = "maxima" | "alta" | "media" | "baixa" | "pular";

export const LEAD_PROFILE_LABEL: Record<LeadProfile, string> = {
  hot_no_site: "Sem site validado",
  hot_bad_site: "Site ruim",
  warm: "Oportunidade média",
  cold: "Site ok",
  disqualified: "Desqualificado",
};

export const NICHO_LABEL: Record<NichoCanonico, string> = {
  dentista: "Odontologia",
  estetica: "Estética",
  salao_barbearia: "Salão / Barbearia",
  restaurante: "Restaurante / Bar",
  petshop_vet: "Pet shop / Vet",
  academia: "Academia",
  contabilidade: "Contabilidade",
  imobiliaria: "Imobiliária",
  loja_roupas: "Loja de roupas",
  auto_escola: "Autoescola",
  advocacia: "Advocacia",
  industria: "Indústria",
  clinica_medica: "Clínica médica",
  escola_curso: "Escola / Curso",
  outros: "Outros",
};

export interface Lead {
  id: number;
  public_id: string;
  nome: string;
  telefone: string | null;
  website: string | null;
  endereco: string | null;
  cidade: string | null;
  nicho: string | null;
  categoria: string | null;
  rating: number | null;
  reviews_count: number;
  google_maps_url: string | null;
  top_reviews: string[];
  status: string;
  opportunity_score: number | null;
  opportunity_reasons: string[];
  score_acessibilidade: number;
  score_lp: number;
  score_automacao: number;
  score_mapa: number;
  nivel_recomendado: string | null;
  site_analysis: Record<string, unknown>;
  social_profiles: Record<string, unknown>;
  lp_html: string | null;
  email: string | null;
  cnpj: string | null;
  razao_social: string | null;
  porte: string | null;
  cnae: string | null;
  data_fundacao: string | null;
  socios: Array<{ nome: string }>;
  tech_stack: Array<{ name: string; category: string }>;
  enrichment_sources: Array<{
    provider: string;
    status: string;
    timestamp: string;
    error?: string;
  }>;
  job_id: number | null;
  created_at: string;
  updated_at: string;
  // Classification fields
  perfil_lead: LeadProfile | null;
  nicho_canonico: NichoCanonico | null;
  nicho_source: NichoSource | null;
  nicho_confidence: number | null;
  pacote_sugerido: PacoteSugerido | null;
  prioridade: Prioridade | null;
  has_instagram: boolean | null;
  classified_at: string | null;
}

export interface LeadListResponse {
  items: Lead[];
  total: number;
  page: number;
  per_page: number;
}

export interface Job {
  id: number;
  type: string;
  status: string;
  params: Record<string, unknown>;
  result_summary: Record<string, unknown>;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface JobListResponse {
  items: Job[];
  total: number;
  page: number;
  per_page: number;
}

export interface DashboardStats {
  total_leads: number;
  leads_by_status: Record<string, number>;
  avg_score: number | null;
  total_jobs: number;
  conversion_rate: number | null;
  profile_distribution?: Record<string, number>;
  nicho_distribution?: Record<string, number>;
}

export interface Settings {
  target_niches: string[];
  target_cities: string[];
  min_rating: number;
  max_results_per_search: number;
  opportunity_score_threshold: number;
  business_name: string;
  your_name: string;
}

export interface OutreachMessage {
  id: number;
  lead_id: number;
  type: string;
  message_text: string;
  whatsapp_link: string | null;
  sent_at: string | null;
  response_received_at: string | null;
  needs_review?: boolean;
  copy_count?: number;
  click_count?: number;
  manual_rating?: number | null;
  variant_label?: string | null;
  created_at: string;
}

export interface LandingPage {
  id: number;
  public_id: string;
  lead_id: number;
  version: number;
  is_active: boolean;
  created_at: string;
}

export interface NivelScore {
  score: number;
  sinais: string[];
  oportunidades: string[];
  justificativa: string;
}

export type NivelKey = "lp" | "automacao_basica" | "mapa_automacoes" | "vertical_os";

export interface ServiceLevels {
  lp: NivelScore;
  automacao_basica: NivelScore;
  mapa_automacoes: NivelScore;
  vertical_os: NivelScore;
  nivel_recomendado: NivelKey;
  qualificado: boolean;
  motivo_desqualificacao: string | null;
  resumo_executivo: string;
}

export interface EnrichProvider {
  name: string;
  display_name: string;
  cost: "free" | "freemium";
}

export const ENRICH_PROVIDERS: EnrichProvider[] = [
  { name: "website_crawler", display_name: "Website Crawler", cost: "free" },
  { name: "schema_extractor", display_name: "Schema.org Extractor", cost: "free" },
  { name: "tech_stack", display_name: "Tech Stack Detector", cost: "free" },
  { name: "cnpj_enricher", display_name: "CNPJ (BrasilAPI)", cost: "free" },
  { name: "email_discoverer", display_name: "Email Discoverer", cost: "freemium" },
  { name: "apollo", display_name: "Apollo.io", cost: "freemium" },
];

export interface EnrichRequest {
  lead_ids?: number[];
  skip_providers?: string[];
  force_providers?: string[];
}

export const KANBAN_COLUMNS = [
  { id: "scraped", label: "Scrapeado" },
  { id: "enriched", label: "Analisado" },
  { id: "disqualified", label: "Desqualificado" },
  { id: "failed", label: "Falhou" },
  { id: "lp_generated", label: "LP Gerada" },
  { id: "outreach_ready", label: "Msg Pronta" },
  { id: "outreach_sent", label: "Msg Enviada" },
  { id: "responded", label: "Respondeu" },
  { id: "in_call", label: "Em Call" },
  { id: "closed", label: "Fechado" },
  { id: "delivered", label: "Entregue" },
] as const;

export interface BulkUpdateError {
  lead_id: number;
  error: string;
}

export interface BulkUpdateResult {
  updated: number;
  errors: BulkUpdateError[];
}

export interface BulkDeleteResult {
  deleted: number;
  errors: BulkUpdateError[];
}

export interface LeadIdsResponse {
  ids: number[];
  total: number;
  truncated: boolean;
}

export type PipelineAction = "enrich" | "generate" | "outreach" | "classify";
export type SkippedReason = "disqualified";

export interface PipelinePreviewRequest {
  action: PipelineAction;
  lead_ids: number[];
  options?: Record<string, unknown>;
}

export interface PipelinePreviewResponse {
  action: PipelineAction;
  total_leads: number;
  eligible: number;
  skipped: number;
  skipped_reasons: Partial<Record<SkippedReason, number>>;
  cost_estimate: {
    currency: string;
    total: number;
    breakdown: Array<{ provider: string; calls: number; cost: number }>;
  } | null;
  quota_status: Array<{ provider: string; used: number; limit: number; would_hit_limit: boolean }> | null;
  warnings: string[];
}
