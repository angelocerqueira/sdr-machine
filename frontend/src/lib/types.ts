export interface Lead {
  id: number;
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
  site_analysis: Record<string, unknown>;
  lp_html: string | null;
  job_id: number | null;
  created_at: string;
  updated_at: string;
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
  created_at: string;
}

export const KANBAN_COLUMNS = [
  { id: "scraped", label: "Scrapeado" },
  { id: "enriched", label: "Analisado" },
  { id: "lp_generated", label: "LP Gerada" },
  { id: "outreach_ready", label: "Msg Pronta" },
  { id: "outreach_sent", label: "Msg Enviada" },
  { id: "responded", label: "Respondeu" },
  { id: "in_call", label: "Em Call" },
  { id: "closed", label: "Fechado" },
  { id: "delivered", label: "Entregue" },
] as const;
